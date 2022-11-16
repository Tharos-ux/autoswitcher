from os import path
from argparse import ArgumentParser
from json import load
from time import monotonic
from obswebsocket import obsws, requests, exceptions
from random import random, choices
from time import sleep


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('creds', nargs='?', help="Optional path to creditentials",
                        default=f"{path.dirname(__file__)}/creditentials.json")
    args = parser.parse_args()

    UPDATE_INTERVAL: float = 0.5  # stepsize in seconds
    CHECK_INTERVAL: float = 3  # time before check if scene is in list
    # init scenes to work with
    # list of solo fullscreen scenes
    SCENE_SPEAK: list[str] = ['Presentation', 'Dual']
    SCENE_PROBAS: list[int] = [66, 33]

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
        timer: float = 0.0
        print("Starting main loop!")

        while(True):
            if ws.call(requests.GetCurrentScene()).getName() in SCENE_SPEAK:
                if random() < 0.08 and timer > 8.0:
                    print(ws.call(requests.SetCurrentScene(
                        choices(SCENE_SPEAK, weights=SCENE_PROBAS, k=1)[0])))
                    timer = 0  # reset timer for scene switch
                else:
                    sleep(UPDATE_INTERVAL)
                    timer += UPDATE_INTERVAL
            else:
                sleep(CHECK_INTERVAL)
                timer = 0
    except KeyboardInterrupt:
        ws.disconnect()
        print("Connexion closed!")
    except exceptions.ConnectionFailure:
        print("Could not connect to OBS ; please check creditentials file and if OBS is up and running.")
    finally:
        ws.disconnect()
