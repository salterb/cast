"""
CAST.
Author: Ben Salter

CAST (Collaboraive Addition of Spotify Tunes) is a simple program to
allow multiple people on the same network to add to the same Spotify
queue without requiring a dedicated laptop in the corner of the room
for people to walk _all_ the way over to.

At its heart, CAST hosts a very simple webserver on a port specified by
the environment variable CAST_PORT. By default, this is 3141. The
website served by the server contains a tiny form. The input to this
form will be searched in Spotify, and the first track found is added to
the queue.

Spotify Premium is required to interface with this app. To handle
authentication, the Spotify API uses OAuth2. To interface with this, you
will need to set the environment variables CAST_CLIENT_ID and
CAST_CLIENT_SECRET. To obtain these, set up a dummy application at
https://developer.spotify.com/dashboard/applications - this will give
you your ID and secret.

In your dummy application settings, you will also need to set a redirect
URI. This should be set to http://localhost:9999. If you wish to use a
different port, you can set the environment variable CAST_REDIRECT_PORT
to another valid port, and change the redirect URI accordingly in the
developer dashboard.

Adding to the queue will require an active Spotify device. To do this,
you may need to start playing directly from your laptop/whatever before
using CAST to interact.

All of the heavy lifting and communications with the Spotify API are
done using the excellent spotipy library.
"""

import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
import spotipy

SCOPE = "user-read-playback-state,user-modify-playback-state"
CACHE_PATH = ".cast_token_cache"
QUEUE_PATH = ".cast_queue"
CLIENT_ID = os.getenv("CAST_CLIENT_ID")
CLIENT_SECRET = os.getenv("CAST_CLIENT_SECRET")
CAST_PORT = os.getenv("CAST_PORT") or 3141
CAST_REDIRECT_PORT = os.getenv("CAST_REDIRECT_PORT") or 9999
REDIRECT_URI = f"http://localhost:{CAST_REDIRECT_PORT}"

SEARCH_FORM = """
<form id="form1">
    <label for="search">Search:</label><br>
    <input type="text" id="search" name="search"><br>
</form>

<button type="submit" form="form1" value="Submit">Submit</button>
"""

def is_queued(track):
    """Check the queue file to see if a given URI has been queued.
    In an ideal world, Spotify will update their API to allow users to
    search the queue, but for the time being, we have to check a file
    that we update manually. This functionality may change (and may be
    moved inside the CastHTTPRequestHandler class) if this functionality
    is ever provided.
    """
    try:
        with open(QUEUE_PATH, "r") as queue:
            data = queue.read().splitlines()
    except FileNotFoundError:
        data = []
    for item in data:
        uri, _ = item.split(" ", maxsplit=1)
        if uri == track["uri"]:
            return True
    return False


class CastHTTPRequestHandler(BaseHTTPRequestHandler):
    """A simple request handler to deal with the limited set of requests
    that CAST expects to receive. Absolutely zero security has gone into
    this. If it breaks then welp.
    """
    def __init__(self, *args, **kwargs):
        self.spotify_ctx = None
        super().__init__(*args, **kwargs)

    def _write_page(self, premsg=b""):
        """Helper function to write the basic HTML page, with a
        prepended string if desired."""
        if premsg:
            self.wfile.write(premsg)
        self.wfile.write(SEARCH_FORM.encode())

    def do_GET(self):
        """Respond to HTTP GET request.

        If no cached access token is found, this spins up another little
        webserver on localhost:CAST_REDIRECT_PORT (default 9999) and
        opens a web browser to handle the redirect. This is perhaps a
        little more heavyweight than is necessary (since we could just
        redirect to this webserver and handle it ourselves), but the
        get_access_token() method does so much for us that it seems
        wasteful to reimplement its functionality. This will only happen
        the first time the app is used, since after that we'll have
        cached tokens."""
        parts = urlparse(self.path)
        path = parts.path
        if path == "/":
            query_string = parse_qs(parts.query)
            auth_manager = spotipy.oauth2.SpotifyOAuth(scope=SCOPE,
                                                       cache_path=CACHE_PATH,
                                                       client_id=CLIENT_ID,
                                                       client_secret=CLIENT_SECRET,
                                                       redirect_uri=REDIRECT_URI)
            # Spins up a tiny webserver if no cache exists
            token = auth_manager.get_access_token(as_dict=False)

            # If here, then we have valid auth tokens
            if not query_string:
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self._write_page(premsg="Hello!".encode())
            else:
                try:
                    search = query_string["search"][0]
                except KeyError:
                    self.send_response(404)
                    return

                self.spotify_ctx = spotipy.Spotify(auth=token)
                if search.startswith("ADMIN"):
                    output = self.admin_control(search[5:])
                else:
                    output = self.search_and_queue(search)
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self._write_page(premsg=output.encode())

    def _queue_track(self, track):
        """Queue a track. Adds to the Spotify queue, and updates the
        queue file with the new track.
        """
        self.spotify_ctx.add_to_queue(track["uri"])
        with open(QUEUE_PATH, "a") as queue:
            queue.write(f"{track['uri']} {track['name']}{os.linesep}")

    def search_and_queue(self, track_name, check_queue=True):
        """Search Spotify with the desired track name, and add the first
        thing found to the list.
        """
        search = self.spotify_ctx.search(track_name, type="track", limit=1)
        if search["tracks"]["total"] == 0:
            return f"No results found for {track_name}.<br><br>"

        track = search["tracks"]["items"][0]
        if check_queue and is_queued(track):
            return f"{track['name']} has already been queued.<br><br>"

        try:
            self._queue_track(track)
            return_string = (f"Queued:<br>"
                             f"Song: {track['name']}<br>"
                             f"Artist: {track['artists'][0]['name']}<br>"
                             f"Album: {track['album']['name']}<br><br>")
        except spotipy.exceptions.SpotifyException as exc:
            print(exc)
            return_string = "Error queuing track - possibly no active device?<br><br>"
        return return_string

    def admin_control(self, arg):
        """Perform one of a limited set of actions (other than queuing).
        Options are: pause
                     current
                     skip
                     resume
                     force (add to queue even if already queued)
        """
        arg = arg.lower()
        if arg == "pause":
            self.spotify_ctx.pause_playback()
            response = "Playback paused."
        elif arg == "current":
            track = self.spotify_ctx.currently_playing()["item"]
            response = (f"Currently playing:<br>"
                        f"Song: {track['name']}<br>"
                        f"Artist: {track['artists'][0]['name']}<br>"
                        f"Album: {track['album']['name']}<br><br>")
        elif arg in ("skip", "next"):
            self.spotify_ctx.next_track()
            response = "Skipped to next track."
        elif arg in ("resume", "play"):
            self.spotify_ctx.start_playback()
            response = "Playback resumed."
        elif arg[:6] == "force ":
            response = self.search_and_queue(arg[6:], check_queue=False)
        else:
            response = ""
        return response


if __name__ == "__main__":
    server_address = ("", int(CAST_PORT))
    httpd = ThreadingHTTPServer(server_address, CastHTTPRequestHandler)
    print(f"Starting CAST server on localhost, port {CAST_PORT}.")
    httpd.serve_forever()
