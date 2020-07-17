"""
CAST.
Author: Ben Salter

CAST (Collaboraive Addition of Spotify Tunes) is a simple program to
allow multiple people on the same network to add to the same Spotify
queue without requiring a dedicated laptop in the corner of the room
for people to walk _all_ the way over to.

At its heart, CAST hosts a very simple webserver on a port specified by
the environment variable CAST_PORT. By default, this is 8080. The
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
URI. This should be set to http://localhost:8080/callback (8080 should
be replaced with the value of the environment variable CAST_PORT if you
set it).

Adding to the queue will require an active Spotify device. To do this,
you may need to start playing directly from your laptop/whatever before
using CAST to interact.

All of the heavy lifting and communications with the Spotify API are
done using the excellent spotipy library.
"""

import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import spotipy

SCOPE = "user-read-playback-state,user-modify-playback-state"
CAST_PORT = int(os.getenv("CAST_PORT")) or 8080
REDIRECT_URI = f"http://localhost:{CAST_PORT}/callback"
SEARCH_FORM = """
<form id="form1">
    <label for="search">Search:</label><br>
    <input type="text" id="search" name="search"><br>
</form>

<button type="submit" form="form1" value="Submit">Submit</button>
"""

def search_and_queue(track_name, spotify_ctx):
    """Search Spotify with the desired track name, and add the first
    thing found to the list.
    """
    search = spotify_ctx.search(track_name, type="track", limit=1)
    track = search["tracks"]["items"][0]
    spotify_ctx.add_to_queue(track["uri"])
    return_string = (f"Queued:<br>"
                     f"Song: {track['name']}<br>"
                     f"Artist: {track['artists'][0]['name']}<br>"
                     f"Album: {track['album']['name']}<br>")
    return return_string

def admin_control(arg, spotify_ctx):
    """Perform one of a limited set of actions (other than queuing).
    Options are: pause
                 current
                 skip
                 resume
    """
    arg = arg.lower()
    if arg == "pause":
        spotify_ctx.pause_playback()
        response = "Playback paused"
    elif arg == "current":
        track = spotify_ctx.currently_playing()["item"]
        response = (f"Currently playing:<br>"
                    f"Song: {track['name']}<br>"
                    f"Artist: {track['artists'][0]['name']}<br>"
                    f"Album: {track['album']['name']}<br>")
    elif arg in ("skip", "next"):
        spotify_ctx.next_track()
        response = "Skipped to next track"
    elif arg in ("resume", "play"):
        spotify_ctx.start_playback()
        response = "Playback resumed"
    return response


class HTTPRequestHandler(BaseHTTPRequestHandler):
    """A simple request handler to deal with the limited set of requests
    that CAST expects to receive. Absolutely zero security has gone into
    this. If it breaks then welp.
    """
    def _write_page(self, premsg=b""):
        """Helper function to write the basic HTML page, with a
        prepended string if desired"""
        if premsg:
            self.wfile.write(premsg)
        self.wfile.write(SEARCH_FORM.encode())

    def do_GET(self):
        """Respond to HTTP GET request"""
        parts = urlparse(self.path)
        path = parts.path
        full_path = self.path
        query_string = parse_qs(parts.query)
        cache_path = ".cast_cache"
        client_id = os.getenv("CAST_CLIENT_ID")
        client_secret = os.getenv("CAST_CLIENT_SECRET")
        auth_manager = spotipy.oauth2.SpotifyOAuth(scope=SCOPE,
                                                   cache_path=cache_path,
                                                   client_id=client_id,
                                                   client_secret=client_secret,
                                                   redirect_uri=REDIRECT_URI)
        if path == "/favicon.ico":
            pass
        elif path == "/callback":
            # This will cache the token by saving it to a file, so we
            # don't need to store it in a variable.
            auth_manager.get_access_token(query_string["code"], check_cache=False)
            self.send_response(301)
            self.send_header("Location", "/")
            self.end_headers()

        elif path == "/":
            # Though not documented, this _should_ refresh the token if it's expired
            tokens = auth_manager.get_cached_token()
            if not tokens:
                auth_url = auth_manager.get_authorize_url()
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(f'<h2><a href="{auth_url}">'
                                 f'Click to cache auth tokens</a></h2>'.encode())
                return

            # If here, then we have valid auth tokens
            if full_path == "/":
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

                spotify_ctx = spotipy.Spotify(auth=tokens["access_token"])
                if search.startswith("ADMIN"):
                    output = admin_control(search[5:], spotify_ctx)
                else:
                    output = search_and_queue(search, spotify_ctx)
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self._write_page(premsg=output.encode())

if __name__ == "__main__":
    server_address = ("", CAST_PORT)
    httpd = HTTPServer(server_address, HTTPRequestHandler)
    print(f"Starting CAST server on localhost, port {CAST_PORT}")
    httpd.serve_forever()
