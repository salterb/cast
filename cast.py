"""
CAST.
Author: Ben Salter

CAST (Collaboraive Addition of Spotify Tunes) is a simple program to
allow multiple people on the same network to add to the same Spotify
queue without requiring a dedicated laptop in the corner of the room
for people to walk _all_ the way over to.

At its heart, CAST hosts a very simple webserver containing a tiny form.
The input to this form will be searched in Spotify, and the first track
found is added to the queue.

Spotify Premium is required to interface with this app. To handle
authentication, the Spotify API uses OAuth2. To interface with this, you
will need a client id and secret.

All of the heavy lifting and communications with the Spotify API are
done using the excellent spotipy library. You will need to set the
environment variables SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET to
your client id and secret (available from the Spotify developer page).
You will also need to set SPOTIPY_REDIRECT_URL to
http://localhost:8080/callback.
TODO We can handle this better surely? Maybe have CAST_CLIENT_ID etc?

Adding to the queue will require an active Spotify device. To do this,
you may need to start playing directly from your laptop/whatever before
interfacing with this.
"""

from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import spotipy

SCOPE = "user-read-playback-state,user-modify-playback-state"

SEARCH_FORM = """
<form id="form1">
    <label for="search">Search:</label><br>
    <input type="text" id="search" name="search"><br>
</form>

<button type="submit" form="form1" value="Submit">Submit</button>
"""

def search_and_queue(track_name, access_token):
    """Search Spotify with the desired track name, and add the first
    thing found to the list.
    """
    sp = spotipy.Spotify(auth=access_token)
    search = sp.search(track_name, type="track", limit=1)
    track = search["tracks"]["items"][0]
    sp.add_to_queue(track["uri"])
    return_string = (f"Queued:<br>"
                     f"Song: {track['name']}<br>"
                     f"Artist: {track['artists'][0]['name']}<br>"
                     f"Album: {track['album']['name']}<br>")
    return return_string

def admin_control(arg, access_token):
    """Perform one of a limited set of actions (other than queuing).
    Options are: pause
                 current
                 skip
                 resume
                 shuffle
    """
    sp = spotipy.Spotify(auth=access_token)
    arg = arg.lower()
    if arg == "pause":
        sp.pause_playback()
        response = "Playback paused"
    elif arg == "current":
        track = sp.currently_playing()["item"]
        response = (f"Currently playing:<br>"
                    f"Song: {track['name']}<br>"
                    f"Artist: {track['artists'][0]['name']}<br>"
                    f"Album: {track['album']['name']}<br>")
    elif arg in ("skip", "next"):
        sp.next_track()
        response = "Skipped to next track"
    elif arg in ("resume", "play"):
        sp.start_playback()
        response = "Playback resumed"
    elif arg in ("shuffle", "shuffleon"):
        sp.shuffle(True)
        response = "Shuffle on"
    elif arg in ("noshuffle, shuffleoff"):
        sp.shuffle(False)
        response = "Shuffle off"
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
        qs = parse_qs(parts.query)
        cache_path = ".cast_cache"
        auth_manager = spotipy.oauth2.SpotifyOAuth(scope=SCOPE, cache_path=cache_path)
        if path == "/favicon.ico":
            pass
        elif path == "/callback":
            # This will cache the token by saving it to a file, so we
            # don't need to store it in a variable.
            auth_manager.get_access_token(qs["code"], check_cache=False)
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
                    search = qs["search"][0]
                except KeyError:
                    self.send_response(404)
                    return
                if search.startswith("ADMIN"):
                    output = admin_control(search[5:], tokens["access_token"])
                else:
                    output = search_and_queue(search, tokens["access_token"])
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self._write_page(premsg=output.encode())

if __name__ == "__main__":
    server_address = ("", 8080)
    httpd = HTTPServer(server_address, HTTPRequestHandler)
    print("Starting CAST server on localhost, port 8080")
    httpd.serve_forever()
