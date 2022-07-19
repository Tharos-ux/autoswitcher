from time import monotonic
from sounddevice import sleep, query_devices, Stream
from numpy import linalg
from obswebsocket import obsws, requests
from random import choice
from functools import partial
from json import load
from contextlib import ExitStack
from argparse import ArgumentParser


def callback(indata, outdata, frames, time, status, buffer: list) -> None:
    """Callback func to update buffers
    Args:
        buffer (list): target buffer
    """
    volume_norm_in = int(linalg.norm(indata)*10)
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

    # init memories
    THRESHOLD: int = 5
    USERS: list[str] = ['Tharos', 'Yoka', 'Invité_1', 'Invité_2']
    DEVICES: list[tuple] = [(1, None), (3, None), (6, None), (8, None)]
    BUFFERS: list[list] = [[] for _ in USERS]

    # init scenes to work with
    SCENE_SPEAKER: list[str] = [f'Rolls_Solo_{user}' for user in USERS]
    SCENE_EDITO: list[str] = [f'Rolls_Edito_{user}' for user in USERS]
    SCENE_FILL: list[str] = ['Rolls_Multicam']
    SUPPORTED_SCENES: list[str] = SCENE_SPEAKER + SCENE_FILL

    parser = ArgumentParser()
    parser.add_argument(
        "-d", "--devices", help="Prints the list of available devices and exits", action='store_true')
    args = parser.parse_args()

    if (args.devices):
        print(query_devices())
    else:
        with open("creditentials.json", 'r') as creds:
            creditentials: dict = load(creds)
        ws = obsws(creditentials["host"],
                   creditentials["port"], creditentials["password"])
        delay, future_delay = monotonic(), 2
        try:
            ws.connect()
            with ExitStack() as stream_stack:
                streams = [stream_stack.enter_context(Stream(device=DEVICES[i], callback=partial(
                    callback, buffer=BUFFERS[i]))) for i, _ in enumerate(USERS)]
                while(True):
                    name = ws.call(requests.GetCurrentScene()).getName()
                    if name in SUPPORTED_SCENES:
                        if max([len(bf) for bf in BUFFERS]) > 5:
                            target = [len(bf) for bf in BUFFERS].index(
                                max([len(bf) for bf in BUFFERS]))
                            if name in SCENE_SPEAKER:
                                delay, future_delay = scene_caller(
                                    ws, delay, future_delay, SCENE_SPEAKER[target], False)
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
        except Exception as exc:
            raise exc
        finally:
            ws.disconnect()
