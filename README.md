# OBS Studio scene autoswitcher from sound level

[![](https://img.shields.io/badge/Build-stable-green.svg)](https://github.com/Tharos-ux/autoswitcher/)
[![](https://img.shields.io/badge/Interface-unfinished-red.svg)](https://github.com/Tharos-ux/autoswitcher/)

Project made to interact with OBS Studio scenes, making dynamic switching in reaction to dB levels.
You may enter your rest and follow scenes in the constants at the start of the .py file to fit program to your setup.

<p align="center">
  <img src="https://github.com/Tharos-ux/autoswitcher/blob/main/example.gif" />
</p>

You need a *creditentials.json* file to allow access to OBS Studio via websocket.
To create such a file, head to your OBS websockets configuration window to get IP adress, password and port.
File should look like that :
```json
{
    "host": "XXX.XXX.X.XX",
    "port": 0,
    "password": "my_secure_password"
}
```
Dependencies listed in *requirements.txt*. You can install them with `pip install -r requirements.txt`.
You may access to audio mapping information with `python autoswitcher.py -b` and start the program with `python autoswitcher.py` once you're done configuring.


:warning: It will crash if OBS Studio and/or OBS websockets are not up and running !