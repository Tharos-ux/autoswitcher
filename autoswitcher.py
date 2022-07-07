from time import monotonic
import sounddevice as sd
import numpy as np
from obswebsocket import obsws, requests
from random import choice
from functools import partial
from json import load

# init memories
THRESHOLD: int = 5
USERS: list[str] = ['Tharos', 'Yoka', 'Invité_1', 'Invité_2']
DEVICES: list[tuple] = [(1, None), (3, None), (6, None), (8, None)]
BUFFERS: list[list] = [[] for _ in range(4)]

# init scenes to work with
SCENE_SPEAKER: list[str] = [f'Rolls_Solo_{user}' for user in USERS]
SCENE_EDITO: list[str] = [f'Rolls_Edito_{user}' for user in USERS]
SCENE_FILL: list[str] = ['Rolls_Multicam']
SUPPORTED_SCENES: list[str] = SCENE_SPEAKER + SCENE_FILL


def callback(indata, outdata, frames, time, status, input, symbol, buffer):
    volume_norm_in = int(np.linalg.norm(indata)*10)
    if volume_norm_in > THRESHOLD:
        # add stuff if above threshold
        buffering('increase', volume_norm_in, input, buffer)
        print(f"{symbol * int(volume_norm_in)}")
    else:
        # remove stuff if above threshold
        buffering('decrease', volume_norm_in, input, buffer)


def buffering(status: str, value: int, target: int, buffer: list):
    match status, len(buffer):
        case 'increase', 14:
            pass
        case 'increase', _:
            buffer.append(value)
        case 'decrease', 0:
            pass
        case 'decrease', _:
            buffer.remove(buffer[-1])


def scene_caller(ws, delay, future_delay, requested_name, override: bool) -> tuple:
    if monotonic() - delay > future_delay or override:
        ws.call(requests.SetCurrentScene(requested_name))
        delay = monotonic()
        if override:
            future_delay = 2
        else:
            future_delay = choice([6, 8, 10])
    return delay, future_delay



print(sd.query_devices())

with open("creditentials.json",'r') as creds:
    creditentials:dict = load(creds)
    
ws = obsws(creditentials["host"], creditentials["port"], creditentials["password"])


delay, future_delay = monotonic(), 2


try:
    ws.connect()
    spart_orator = [
        partial(callback, input=i, symbol=f'{i}', buffer=BUFFERS[i]) for i in range(4)]
    with (
        sd.Stream(device=DEVICES[0], callback=spart_orator[0]),
        sd.Stream(device=DEVICES[1], callback=spart_orator[1]),
        sd.Stream(device=DEVICES[2], callback=spart_orator[2]),
        sd.Stream(device=DEVICES[3], callback=spart_orator[3])
    ):
        while(True):
            name = ws.call(requests.GetCurrentScene()).getName()
            if name in SUPPORTED_SCENES:
                if max([sum(bf) for bf in BUFFERS]) > 10:
                    target = [sum(bf) for bf in BUFFERS].index(
                        max([sum(bf) for bf in BUFFERS]))
                    delay, future_delay = scene_caller(
                        ws, delay, future_delay, SCENE_SPEAKER[target], True)
                else:
                    delay, future_delay = scene_caller(
                        ws, delay, future_delay, choice(SCENE_FILL), False)
            elif name in SCENE_EDITO:
                target = [sum(bf) for bf in BUFFERS].index(
                    max([sum(bf) for bf in BUFFERS]))
                delay, future_delay = scene_caller(
                    ws, delay, future_delay, SCENE_EDITO[target], False)
                sd.sleep(200)
except Exception as exc:
    raise exc
finally:
    ws.disconnect()
