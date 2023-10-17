import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from spotipy.oauth2 import SpotifyOAuth

import json
import time


class SpotifyManager:
    def __init__(self, client_id, client_secret, redirect_uri):
        self.auth = SpotifyOAuth(
            client_id, client_secret, redirect_uri,
            scope="user-read-currently-playing",
            open_browser=False,
        )

        self._refresh_token = None
        self._access_token = None

    def init_auth(self):
        access_data = self.auth.get_access_token(as_dict=True)

        self._refresh_token = access_data["refresh_token"]
        self._access_token = access_data["access_token"]

    def current_playback(self):
        token = self._get_access_token()

        if token is not None:
            try:
                sp = spotipy.Spotify(auth=token, oauth_manager=self.auth)
                return sp.current_user_playing_track()
            except spotipy.SpotifyException as e:
                print(e)

        return None

    def _get_access_token(self):
        access_token = self.auth.validate_token(self._access_token)

        if access_token is None:
            try:
                if self._refresh_token is None:
                    self.init_auth()

                access_data = self.auth.refresh_access_token(self._refresh_token)

                self._access_token = access_data["access_token"]
                self._refresh_token = access_data["refresh_token"]

                access_token = self._access_token

            except spotipy.SpotifyOauthError as e:
                print(e)

        return access_token
