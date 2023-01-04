from time import monotonic
from sounddevice import sleep, query_devices, Stream
from numpy import linalg
from obswebsocket import obsws, requests
from random import choice, random
from functools import partial, wraps
from json import load
from contextlib import ExitStack
from argparse import ArgumentParser
from os import path
from obswebsocket.exceptions import ConnectionFailure
from websocket._exceptions import WebSocketConnectionClosedException


def callback(indata, outdata, frames, time, status, buffer: list, intcode: int, ratio: float) -> None:
    """Callback func to update buffers
    Args:
        buffer (list): target buffer
    """
    volume_norm_in = int(linalg.norm(indata)*10)  # *NORMALISER[intcode]
    if volume_norm_in > THRESHOLD:
        # add stuff if above threshold
        buffering('increase', volume_norm_in, buffer, ratio)
    else:
        # remove stuff if above threshold
        buffering('decrease', volume_norm_in, buffer, ratio)


def buffering(status: str, value: int, buffer: list, ratio: float) -> None:
    """Updates buffer status
    Args:
        status (str): increase or decrease instruction
        value (int): dB level to be write
        buffer (list): targeted buffer
    """
    match status, len(buffer):
        case 'increase', 20:
            pass
        case 'increase', _:
            buffer.append(value*ratio)
        case 'decrease', 0:
            pass
        case 'decrease', _:
            buffer.remove(buffer[-1])


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
        ws.call(requests.SetCurrentScene(requested_name))
        delay = monotonic()
        if override:
            future_delay = 3
        else:
            future_delay = choice([6, 8, 10])
    return delay, future_delay


###################### MAIN ########################

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "-d", "--devices", help="Prints the list of available devices and exits", action='store_true')
    parser.add_argument('creds', nargs='?', help="Optional path to creditentials",
                        default=f"{path.dirname(__file__)}/creditentials.json")
    args = parser.parse_args()

    if (args.devices):
        for device in query_devices():
            print(device)

    else:
        # init mapping => you need to set names that are not ambiguous on your system !!!
        ORATOR_DEVICES: list = [
            ('MJ', 'Chat Mic', 3),
            ('Joueur1', 'VoiceMeeter Output', 1),
            ('Joueur2', 'VoiceMeeter Aux Output', 1),
            ('Joueur3', 'VoiceMeeter VAIO3 Output', 1),
            ('Joueur4', 'CABLE Output (VB-Audio Virtual', 1)
        ]

        # Forming mapping between devices and orators
        assignator: dict = {}
        print("Starting mapping...")
        for orator, target, ratio in ORATOR_DEVICES:
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
        USERS: list[str] = [user for (user, _, _) in ORATOR_DEVICES]
        RATIOS: list[float] = [ratio for (_, _, ratio) in ORATOR_DEVICES]
        DEVICES: list[tuple] = [(assignator[user], None) for user in USERS]
        BUFFERS: list[list] = [[] for _ in USERS]

        # init scenes to work with
        # list of solo fullscreen scenes
        SCENE_SPEAKER: list[str] = [f'Cam_{user}' for user in USERS]
        # list of solo edito scenes
        #SCENE_EDITO: list[str] = [f'Rolls_Edito_{user}' for user in USERS]
        # list of scenes to use when no one's talking
        #SCENE_FILL: list[str] = [f'Rolls_Main_{user}' for user in USERS]
        # SCENE_FILL: list[str] = ['Rolls_Multicam']
        # list of scenes software is allowed to switch from
        SUPPORTED_SCENES: list[str] = SCENE_SPEAKER
        # where Patounes websource is
        timer: int = 0

        # Loading creditentials for OBSwebsocket
        print("Loading creditentials...")
        with open(args.creds, 'r') as creds:
            creditentials: dict = load(creds)
        ws = obsws(creditentials["host"],
                   creditentials["port"], creditentials["password"])
        delay, future_delay = monotonic(), 2
        try:
            print("Connecting to OBS...")
            ws.connect()
            print("Opening fluxes...")
            with ExitStack() as stream_stack:
                streams = [stream_stack.enter_context(Stream(device=DEVICES[i], callback=partial(
                    callback, buffer=BUFFERS[i], intcode=i, ratio=RATIOS[i]))) for i, _ in enumerate(USERS)]
                print("Starting main loop!")
                while(True):
                    # main loop to switch scenes
                    name = ws.call(requests.GetCurrentScene()).getName()
                    if name in SUPPORTED_SCENES:
                        if max([sum(bf) for bf in BUFFERS]) > 5:
                            target = [sum(bf) for bf in BUFFERS].index(
                                max([sum(bf) for bf in BUFFERS]))
                            delay, future_delay = scene_caller(
                                ws, delay, future_delay, SCENE_SPEAKER[target], False)
                        sleep(200)
                        timer += 0.2
        except KeyboardInterrupt:
            ws.disconnect()
            print("Connexion closed!")
        except ConnectionFailure:
            print(
                "Could not connect to OBS ; please check creditentials file and if OBS is up and running.")
        except WebSocketConnectionClosedException:
            print("Connexion to OBS was prematurely closed ; aborting...")
        except ConnectionRefusedError:
            print("OBS refused connexion to the switcher.")
