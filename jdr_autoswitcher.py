from time import monotonic
from sounddevice import sleep, query_devices, Stream
from numpy import linalg
from obswebsocket import obsws, requests
from random import choices, choice
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
    volume_norm_in = int(linalg.norm(indata)*50)  # *NORMALISER[intcode]
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
        ws.call(requests.SetCurrentProgramScene(sceneName=requested_name))
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
    parser.add_argument('-n', '--number', help="Number of orators in vocal",
                        default=5, type=int)
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
            ('Joueur1', 'CABLE-A Output', 6),
            ('Joueur2', 'CABLE-B Output', 1),
            ('Joueur3', 'CABLE-C Output', 1),
            ('Joueur4', 'CABLE-D Output', 1),
            ('Joueur5', 'CABLE Output', 1)
        ]
        n_orators: int = args.number if args.number > 0 and args.number < len(
            ORATOR_DEVICES) else len(ORATOR_DEVICES)
        ORATOR_DEVICES = ORATOR_DEVICES[:n_orators]

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
        SCENE_SPEAKER: list[str] = [f'JdR_Solo_{user}' for user in USERS]
        # list of solo scenes with cam at bottom and overlay
        SCENE_ALT: list[str] = [f'JdR_Cam_{user}' for user in USERS]
        # list of scenes to use when no one's talking
        SCENE_FILL: list[str] = {
            1: [f'JdR_Solo_{USERS[0]}'],
            2: ['JdR_Duo'],
            3: ['JdR_Trio'],
            4: ['JdR_Quatuor'],
            5: ['JdR_Multicam'],
            6: ['JdR_Multicam'],
        }[len(USERS)]
        print(f"   Using {', '.join(SCENE_FILL)} as filler scenes")
        # list of scenes software is allowed to switch from
        SUPPORTED_SCENES: list[str] = SCENE_SPEAKER + SCENE_ALT + SCENE_FILL
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
                while (True):
                    # print(BUFFERS)
                    # main loop to switch scenes
                    name = ws.call(requests.GetCurrentProgramScene()
                                   ).getcurrentProgramSceneName()
                    if name in SUPPORTED_SCENES:
                        if max([sum(bf) for bf in BUFFERS]) > 5:
                            target = [sum(bf) for bf in BUFFERS].index(
                                max([sum(bf) for bf in BUFFERS]))
                            delay, future_delay = scene_caller(
                                ws, delay, future_delay, choices([SCENE_SPEAKER[target], SCENE_ALT[target], choice(SCENE_FILL)], weights=[0.6, 0.15, 0.25])[0], False)
                        else:
                            # Nobody's talking
                            delay, future_delay = scene_caller(
                                ws, delay, future_delay, SCENE_FILL, False)
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
