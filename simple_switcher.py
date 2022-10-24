from json import load
from time import monotonic
from obswebsocket import obsws, requests
from functools import partial
import tkinter as tk

# Loading creditentials for OBSwebsocket
print("Loading creditentials...")
with open("creditentials.json", 'r') as creds:
    creditentials: dict = load(creds)
ws = obsws(creditentials["host"],
           creditentials["port"], creditentials["password"])
delay, future_delay = monotonic(), 2
try:
    print("Connecting to OBS...")
    ws.connect()
except:
    pass


def switch(ws: obsws, requested_name: str) -> None:
    print(f"Tried to call scene {requested_name}")
    ws.call(requests.SetCurrentScene(requested_name))


scenes_switcher: list = [
    "Discussion_Solo",
    "Scène_Interview",
    "Scène_Enregistrement"
]

layout: int = 160

root = tk.Tk()
root.geometry(f"{layout}x{(len(scenes_switcher)*layout)//2}")
root.title('Switcher')
root.resizable(0, 0)
tk.Grid.columnconfigure(root, 0, weight=1)
for i in range(len(scenes_switcher)):
    tk.Grid.rowconfigure(root, i, weight=1)
button_list = [tk.Button(master=root, text=scene, bg='#2f3136', fg='white', command=partial(
    switch, ws=ws, requested_name=scene)) for scene in scenes_switcher]
[button.grid(sticky="nswe", column=0, row=i)
 for i, button in enumerate(button_list)]
root.mainloop()
