from time import monotonic
from sounddevice import sleep, query_devices, Stream
from numpy import linalg
from obswebsocket import obsws, requests
from random import choice, random
from functools import partial, wraps
from json import load
from contextlib import ExitStack
from argparse import ArgumentParser
from html_writer import write_bubble, write_css
import os


def called(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not wrapper.called:
            wrapper.old_string = "Initialisation terminée !"
            wrapper.new_string = "Initialisation terminée !"
            wrapper.patounes_active = False
        wrapper.called = True
        return func(*args, **kwargs)
    wrapper.called = False
    return wrapper


def callback(indata, outdata, frames, time, status, buffer: list, intcode: int) -> None:
    """Callback func to update buffers
    Args:
        buffer (list): target buffer
    """
    volume_norm_in = int(linalg.norm(indata)*10)  # *NORMALISER[intcode]
    if volume_norm_in > THRESHOLD:
        # add stuff if above threshold
        buffering('increase', volume_norm_in, buffer)
    else:
        # remove stuff if above threshold
        buffering('decrease', volume_norm_in, buffer)


def buffering(status: str, value: int, buffer: list) -> None:
    """Updates buffer status
    Args:
        status (str): increase or decrease instruction
        value (int): dB level to be write
        buffer (list): targeted buffer
    """
    match status, len(buffer):
        case 'increase', 14:
            pass
        case 'increase', _:
            buffer.append(value)
        case 'decrease', 0:
            pass
        case 'decrease', _:
            buffer.remove(buffer[-1])


@called
def scene_caller(ws: obsws, delay: int, future_delay: int, requested_name: str, override: bool) -> tuple:
    """Calls for a specific OBS Studio scene
    Args:
        ws (obsws): a connexion socket
        delay (int): current dealy
        future_delay (int): delay to match against
        requested_name (str): name of scene request
        override (bool): if time should be accounted
    Returns:
        tuple: delay informations
    """
    if monotonic() - delay > future_delay:
        old_scene = ws.call(requests.GetCurrentScene()).getName()
        ws.call(requests.SetCurrentScene(requested_name))
        delay = monotonic()
        if override:
            future_delay = 3
        else:
            future_delay = choice([6, 8, 10])
        # calling for html writing only if Patounes is displayed
        if scene_caller.patounes_active:
            while scene_caller.new_string == scene_caller.old_string:
                if old_scene != requested_name:
                    scene_caller.new_string = choice(
                        [
                            "Oops, trop long sur ce plan !",
                            f"Attends, je switch vers {requested_name.split('_')[-1]}",
                            "Oooh, c'est super joli ici !",
                            "Vous vouliez changer de vue ?",
                            "On va voir d'autres têtes sympathiques !"
                        ])
                else:
                    scene_caller.new_string = choice(
                        [
                            "On reste un peu sur ce plan ?",
                            f"On reste un peu sur {requested_name.split('_')[-1]} ?",
                            "C'est pas si mal, ici !",
                            "Vous vouliez garder cette vue ?",
                            "Ca parle longtemps, par ici !"
                        ])
            write_bubble(scene_caller.old_string,
                         scene_caller.new_string, future_delay+0.5)
            scene_caller.old_string = scene_caller.new_string
    return delay, future_delay


###################### MAIN ########################

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "-d", "--devices", help="Prints the list of available devices and exits", action='store_true')
    args = parser.parse_args()

    if (args.devices):
        for device in query_devices():
            print(device)

    else:
        write_css()
        # init mapping => you need to set names that are not ambiguous on your system !!!
        ORATOR_DEVICES: list = [
            ('Tharos', 'Chat Mic'),
            ('Yoka', 'VoiceMeeter Output'),
            ('Invité_1', 'VoiceMeeter Aux Output'),
            # ('Invité_2', 'VoiceMeeter VAIO3 Output')
        ]

        # Forming mapping between devices and orators
        assignator: dict = {}
        print("Starting mapping...")
        for orator, target in ORATOR_DEVICES:
            for i, device in enumerate(query_devices()):
                if target in device['name'] and orator not in assignator:
                    print(
                        f"   Orator {orator} has been assigned to device #{i}, namely {device['name']}!")
                    if device['max_input_channels'] == 0:
                        print(
                            f"   /!\\ Beware, device {device['name']} does not have inputs. It may cause crashes.")
                    assignator[orator] = i

        # init memories
        THRESHOLD: int = 5
        USERS: list[str] = [user for (user, _) in ORATOR_DEVICES]
        DEVICES: list[tuple] = [(assignator[user], None) for user in USERS]
        BUFFERS: list[list] = [[] for _ in USERS]

        # init scenes to work with
        # list of solo fullscreen scenes
        SCENE_SPEAKER: list[str] = [f'Rolls_Solo_{user}' for user in USERS]
        # list of solo edito scenes
        SCENE_EDITO: list[str] = [f'Rolls_Edito_{user}' for user in USERS]
        # list of scenes to use when no one's talking
        SCENE_FILL: list[str] = [f'Rolls_Main_{user}' for user in USERS]
        # SCENE_FILL: list[str] = ['Rolls_Multicam']
        # list of scenes software is allowed to switch from
        SUPPORTED_SCENES: list[str] = SCENE_SPEAKER + SCENE_FILL
        # where Patounes websource is
        NAME_OF_EMBED_SCENE: str = "--Patounes"
        scene_caller.patounes_active = False
        timer: int = 0

        # Loading creditentials for OBSwebsocket
        print("Loading creditentials...")
        with open(f"{os.path.dirname(__file__)}/creditentials.json", 'r') as creds:
            creditentials: dict = load(creds)
        ws = obsws(creditentials["host"],
                   creditentials["port"], creditentials["password"])
        delay, future_delay = monotonic(), 2
        write_bubble("Initialisation terminée !",
                     "Initialisation terminée !", future_delay)
        try:
            print("Connecting to OBS...")
            ws.connect()
            for scene in SCENE_EDITO + SUPPORTED_SCENES:
                ws.call(requests.SetSceneItemRender(
                    scene_name=scene, source=NAME_OF_EMBED_SCENE, render=False))
            print("Opening fluxes...")
            with ExitStack() as stream_stack:
                streams = [stream_stack.enter_context(Stream(device=DEVICES[i], callback=partial(
                    callback, buffer=BUFFERS[i], intcode=i))) for i, _ in enumerate(USERS)]
                print("Starting main loop!")
                while(True):
                    # random condition to make Patounes appear
                    if scene_caller.patounes_active == False and random() < 0.01 and timer > 18.0:
                        timer = 0  # reset timer for showing/hiding
                        scene_caller.patounes_active = True
                        scene_caller.old_string = "Initialisation terminée !"
                        scene_caller.new_string = "Initialisation terminée !"
                        [ws.call(requests.SetSceneItemRender(
                            scene_name=scene, source=NAME_OF_EMBED_SCENE, render=True)) for scene in SCENE_EDITO + SUPPORTED_SCENES]
                    if scene_caller.patounes_active == True and random() < 0.02 and timer > 12.0:
                        timer = 0  # reset timer for showing/hiding
                        scene_caller.patounes_active = False
                        [ws.call(requests.SetSceneItemRender(
                            scene_name=scene, source=NAME_OF_EMBED_SCENE, render=False)) for scene in SCENE_EDITO + SUPPORTED_SCENES]
                        write_bubble("Initialisation terminée !",
                                     "Initialisation terminée !", future_delay)
                    # main loop to switch scenes
                    name = ws.call(requests.GetCurrentScene()).getName()
                    if name in SUPPORTED_SCENES:
                        if max([len(bf) for bf in BUFFERS]) > 5:
                            target = [len(bf) for bf in BUFFERS].index(
                                max([len(bf) for bf in BUFFERS]))
                            if name in SCENE_SPEAKER:
                                delay, future_delay = scene_caller(
                                    ws, delay, future_delay, choice([SCENE_SPEAKER[target], SCENE_FILL[target]]), False)
                            else:
                                delay, future_delay = scene_caller(
                                    ws, delay, future_delay, SCENE_SPEAKER[target], False)
                        else:
                            delay, future_delay = scene_caller(
                                ws, delay, future_delay, choice(SCENE_FILL), False)
                    elif name in SCENE_EDITO:
                        target = [sum(bf) for bf in BUFFERS].index(
                            max([sum(bf) for bf in BUFFERS]))
                        delay, future_delay = scene_caller(
                            ws, delay, future_delay, SCENE_EDITO[target], True)
                        sleep(200)
                        timer += 0.2
        except Exception as exc:
            raise exc
        finally:
            ws.disconnect()
