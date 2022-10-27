import os
import requests as rq
from urllib.parse import urlencode
import tkinter as tk
from tkinter import ttk
from functools import partial
from json import load
from time import sleep
from obswebsocket import obsws, requests

SCENES_WHERE_SHOWING: list = ["Discussion_Solo",
                              "Presentation", "Dual", "Fullscreen"]
NAME_OF_EMBED_SCENE: str = "Embed"
NAME_OF_BROWSER_SOURCE: str = "twitter_embed"
X_IN_SCENE: int = 1580
X_OUT_OF_BOUNDS: int = 2000
Y_POS: int = 150


def get_embed(ws, url):
    url = url.get()
    if url != "":
        print(f"Displaying <{url}>")
        query_string = urlencode({'url': url})
        oembed_url = f"https://publish.twitter.com/oembed?{query_string}&theme=dark&lang=fr&hideConversation=on"

        r = rq.get(oembed_url)
        if r.status_code == 200:
            result = r.json()
            html = result['html'].strip()

        full_str: str = f"""
            <!DOCTYPE html>
            <html>
            <head>
            <link rel="stylesheet" href="tweet.css">
            </head>
            <body>
            <div class = "main">
            <div class = "wrapper">
            {html}
            </div>
            </div>
            </body>
            </html>
            """
    else:
        full_str: str = """
            <!DOCTYPE html>
            <html>
            <head>
            <link rel="stylesheet" href="tweet.css">
            </head>
            <body>
            </body>
            </html>
        """
    # reload from cache
    with open(f"{os.path.dirname(__file__)}/tweet_display.html", 'w', encoding='utf-8') as htmlwriter:
        htmlwriter.write(full_str)
    [ws.call(requests.SetSceneItemRender(
        scene_name=scene, source=NAME_OF_EMBED_SCENE, render=True)) for scene in SCENES_WHERE_SHOWING]
    sleep(4)
    # fade in
    ws.call(requests.SetSceneItemPosition(
        item=NAME_OF_BROWSER_SOURCE, x=X_IN_SCENE, y=Y_POS, scene_name=NAME_OF_EMBED_SCENE))
    for i in range(0, 101, 5):
        ws.call(requests.SetSourceFilterSettings(sourceName=NAME_OF_BROWSER_SOURCE,
                filterName="visibility", filterSettings={'opacity': i/100}))

    # standing still
    sleep(10)

    # fade out
    for i in range(100, -1, -5):
        ws.call(requests.SetSourceFilterSettings(sourceName=NAME_OF_BROWSER_SOURCE,
                filterName="visibility", filterSettings={'opacity': i/100}))
    ws.call(requests.SetSceneItemPosition(
        item=NAME_OF_BROWSER_SOURCE, x=X_OUT_OF_BOUNDS, y=Y_POS, scene_name=NAME_OF_EMBED_SCENE))
    [ws.call(requests.SetSceneItemRender(
        scene_name=scene, source=NAME_OF_EMBED_SCENE, render=False)) for scene in SCENES_WHERE_SHOWING]
    # slide out
    # for i in range(1350, 1900, 5):
    #    ws.call(requests.SetSceneItemPosition(item=NAME_OF_BROWSER_SOURCE, x=i, y=150, scene_name=NAME_OF_EMBED_SCENE))
    # print(ws.call(requests.GetSourceSettings(sourceName=NAME_OF_BROWSER_SOURCE)))
    #ws.call(requests.SetSceneItemRender(scene_name=NAME_OF_EMBED_SCENE, source=NAME_OF_BROWSER_SOURCE, render=False))
    #ws.call(requests.SetSceneItemPosition(item=NAME_OF_BROWSER_SOURCE, x=i, y=150, scene_name=NAME_OF_EMBED_SCENE))
    #


if __name__ == "__main__":
    # Loading creditentials for OBSwebsocket
    print("Loading creditentials...")
    with open(f"{os.path.dirname(__file__)}/creditentials.json", 'r') as creds:
        creditentials: dict = load(creds)
    ws = obsws(creditentials["host"],
               creditentials["port"], creditentials["password"])
    try:
        print("Connecting to OBS...")
        ws.connect()
    except:
        pass

    layout: int = 160
    root = tk.Tk()
    root.geometry(f"{layout*4}x{layout//5}")
    root.title('TwEmbed')
    root.resizable(0, 0)
    tk.Grid.rowconfigure(root, 0, weight=1)
    tk.Grid.columnconfigure(root, 0, weight=1)
    tk.Grid.columnconfigure(root, 1, weight=2)
    name = tk.StringVar()
    tb = ttk.Entry(root, width=15, textvariable=name)
    tb.grid(sticky="nswe", column=1, row=0)
    button_embed = tk.Button(master=root, text="Generate embed",
                             bg='#2f3136', fg='white', command=partial(get_embed, ws=ws, url=name))
    button_embed.grid(sticky="nswe", column=0, row=0)
    root.mainloop()
