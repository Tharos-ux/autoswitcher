from time import monotonic
from sounddevice import sleep, Stream
from numpy import linalg
from obswebsocket import obsws, requests
from random import choice
from functools import partial
from json import load
from contextlib import ExitStack
from argparse import ArgumentParser


class Autoswitcher():

    def __init__(self, users: list[str], devices: list[int], scene_speaker: list[str], scene_edito: list[str], scene_fill: list[str], obs_creditentials: dict, threshold: int = 5):
        """Creates a Autoswitcher interface

        Args:
            users (list[str]): usernames (speakers)
            devices (list[int]): devices codes (of respective speakers)
            scene_speaker (list[str]): OBS scenes names (of respective speakers, mode 1)
            scene_edito (list[str]): OBS scenes names (of respective speakers, mode 2)
            scene_fill (list[str]): OBS scenes names (scenes when no one speaks)
            obs_creditentials (dict): OBS websocket creditentials (must contain host, port, password)
            threshold (int, optional): filter for db level. Defaults to 5.
        """
        self.THRESHOLD: int = threshold
        self.USERS: list[str] = users
        self.DEVICES: list[tuple] = [(inpt, None) for inpt in devices]
        self.BUFFERS: list[list] = [[] for _ in users]
        self.SCENE_SPEAKER: list[str] = scene_speaker
        self.SCENE_EDITO: list[str] = scene_edito
        self.SCENE_FILL: list[str] = scene_fill
        self.SUPPORTED_SCENES: list[str] = self.SCENE_SPEAKER + self.SCENE_FILL
        self.DELAY: int = int(monotonic())
        self.FUTURE_DELAY: int = 2
        self.RUNNING: bool = False
        self.WS = obsws(
            obs_creditentials["host"], obs_creditentials["port"], obs_creditentials["password"])

    def __callback__(self, indata, outdata, frames, time, status, buffer: list) -> None:
        """Callback func to update buffers

        Args:
            buffer (list): target buffer
        """
        volume_norm_in = int(linalg.norm(indata)*10)
        if volume_norm_in > self.THRESHOLD:
            # add stuff if above threshold
            self.__buffering__('increase', volume_norm_in, buffer)
        else:
            # remove stuff if above threshold
            self.__buffering__('decrease', volume_norm_in, buffer)

    def __buffering__(self, status: str, value: int, buffer: list) -> None:
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

    def __scene_caller__(self, ws: obsws, delay: int, future_delay: int, requested_name: str, override: bool) -> tuple:
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
            delay = int(monotonic())
            if override:
                future_delay = 3
            else:
                future_delay = choice([6, 8, 10])
        return delay, future_delay

    def switch(self):
        """Init switching between scenes. Setting self.RUNNING to false will disarm this.

        Raises:
            exc: catches error with OBS connexion or random interrupt
        """
        self.RUNNING = True
        try:
            self.WS.connect()
            with ExitStack() as stream_stack:
                streams = [stream_stack.enter_context(Stream(device=self.DEVICES[i], callback=partial(
                    self.__callback__, buffer=self.BUFFERS[i]))) for i, _ in enumerate(self.USERS)]
                while(self.RUNNING):
                    name = self.WS.call(requests.GetCurrentScene()).getName()
                    if name in self.SUPPORTED_SCENES:
                        if max([len(bf) for bf in self.BUFFERS]) > 5:
                            target = [len(bf) for bf in self.BUFFERS].index(
                                max([len(bf) for bf in self.BUFFERS]))
                            if name in self.SCENE_SPEAKER:
                                self.DELAY, self.FUTURE_DELAY = self.__scene_caller__(
                                    self.WS, self.DELAY, self.FUTURE_DELAY, self.SCENE_SPEAKER[target], False)
                            else:
                                self.DELAY, self.FUTURE_DELAY = self.__scene_caller__(
                                    self.WS, self.DELAY, self.FUTURE_DELAY, self.SCENE_SPEAKER[target], False)
                        else:
                            self.DELAY, self.FUTURE_DELAY = self.__scene_caller__(
                                self.WS, self.DELAY, self.FUTURE_DELAY, choice(self.SCENE_FILL), False)
                    elif name in self.SCENE_EDITO:
                        target = [sum(bf) for bf in self.BUFFERS].index(
                            max([sum(bf) for bf in self.BUFFERS]))
                        self.DELAY, self.FUTURE_DELAY = self.__scene_caller__(
                            self.WS, self.DELAY, self.FUTURE_DELAY, self.SCENE_EDITO[target], True)
                        sleep(200)

        except Exception as exc:
            raise exc
        finally:
            self.RUNNING = False
            self.WS.disconnect()
