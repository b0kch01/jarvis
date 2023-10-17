import asyncio
import logging
from dataclasses import asdict
import traceback
from io import BytesIO

import os
import time
from dotenv import load_dotenv

import flask
import numpy as np
import requests
from govee_api_laggat import Govee
from PIL import Image
import colorthief

from color import SpotifyBackgroundColor
from spotify import SpotifyManager
from goveeStorage import YamlLearningStorage
from light_control import get_lights, turn_off_lights, warm_lights

import threading

load_dotenv()

KEY = os.getenv("GOVEE_KEY")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

_LOGGER = logging.getLogger("lights")


class GlobalState:
    current_song = None
    current_color = (255, 255, 255)
    action = None

    sp = SpotifyManager(
        redirect_uri="http://192.168.0.239:9998",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
    )

    govee = None


global_states = GlobalState()


async def load_devices():

    global_states.govee = await Govee.create(KEY, learning_storage=YamlLearningStorage())
    devices, err = await global_states.govee.get_devices()

    if err or not devices:
        _LOGGER.error("Error: ", err)
        await global_states.govee.close()
        return

    await global_states.govee.get_states()


async def change_color_lights(dominant_color: tuple):

    print(" -", dominant_color)

    for device in await get_lights(global_states.govee):
        success, err = await global_states.govee.set_color(device, dominant_color)

        if success != True:
            print("Error: ", err, success)
            await asyncio.sleep(15)
            return False

    return True


async def get_now_playing_color(now_playing: any):

    if now_playing == None:
        return (255, 255, 255)

    pic_url = now_playing["item"]["album"]["images"][1]["url"]

    image_byes = BytesIO(requests.get(pic_url).content)

    # dominant = colorthief.ColorThief(image_byes).get_palette(color_count=3)[3]

    # return dominant

    image = np.array(Image.open(image_byes))

    colorProcessor = SpotifyBackgroundColor(img=image, image_processing_size=(300, 300))
    best_colors = colorProcessor.best_color(k=8, color_tol=10, plot=False)

    # Round the colors to integers
    return (round(best_colors[0]), round(best_colors[1]), round(best_colors[2]))


async def main():
    global global_states

    print("📦 Loading devices...")

    await load_devices()

    print("🎉 Devices loaded!")

    while True:

        if global_states.action == "off":
            await turn_off_lights(global_states.govee)
            reset_spotify()

        elif global_states.action == "on":
            await warm_lights(global_states.govee)
            reset_spotify()

        elif global_states.action == "spotify":
            now_playing = global_states.sp.current_playback()

            if now_playing is None:
                print("⏺", "No song playing")
                await asyncio.sleep(7)

            elif (global_states.current_song is None or
                  global_states.current_song["item"]["album"]["id"] != now_playing["item"]["album"]["id"]):

                print("⏺", now_playing["item"]["name"], end="", flush=True)

                global_states.current_song = now_playing
                new_color = await get_now_playing_color(now_playing)
                global_states.current_color = new_color

                await change_color_lights(new_color)

            await asyncio.sleep(3)
        else:
            await asyncio.sleep(0.5)


def reset_spotify():
    if os.path.exists(".cache"):
        os.remove(".cache")

    global_states.sp = SpotifyManager(
        redirect_uri="http://192.168.0.239:9998",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
    )
    global_states.current_color = (255, 255, 255)
    global_states.current_song = None
    global_states.action = None


app = flask.Flask(__name__)


@app.route("/")
def main_page():

    text_color = "black"

    if global_states.current_song is not None:
        luminance = (0.2126 * global_states.current_color[0] +
                     0.7152 * global_states.current_color[1] +
                     0.0722 * global_states.current_color[2])

        if luminance < 128:
            text_color = "white"

    return flask.render_template(
        "index.html",
        current_song=global_states.current_song,
        auth_url=global_states.sp.auth.get_authorize_url(),
        current_color=global_states.current_color,
        text_color=text_color,
        action=global_states.action,
    )


@app.route("/loading")
def loading():
    return flask.render_template("loading.html")


@app.route("/logout")
def logout():
    reset_spotify()
    return flask.redirect("/")


@app.route("/song_id")
def song_id():
    if global_states.current_song is None:
        return ""

    return global_states.current_song["item"]["id"]


@app.route("/load_state")
def load_state():
    if global_states.action == None:
        return "ready"
    if global_states.action == "spotify":
        return "ready"

    print(global_states.action)
    return ""


@app.route("/lights/<action>")
def lights(action):
    if action == "on":
        global_states.action = "on"
    elif action == "off":
        global_states.action = "off"
    elif action == "spotify":
        global_states.action = "spotify"
        return flask.redirect(global_states.sp.auth.get_authorize_url())

    return flask.redirect("/loading")


if __name__ == "__main__":
    if os.path.exists(".cache"):
        os.remove(".cache")

    # from waitress import serve

    # app_thread = threading.Thread(target=lambda: serve(app, host="0.0.0.0", port=9999))
    # app_thread.start()

    thread = threading.Thread(target=lambda: app.run(host="0.0.0.0", port=9999, debug=False))
    thread.start()

    while True:
        try:
            asyncio.run(main())
        except Exception as e:
            print(traceback.format_exc())

        print("\nRetrying in 5 seconds...\n")
        time.sleep(5)

    # app.run(host="0.0.0.0", port=9999, use_reloader=False)
    # asyncio.run(main())
