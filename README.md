# CAST

## What is it?
CAST (Collaborative Addition of Spotify Tunes) is a simple program to allow multiple people on the same network to add to the same Spotify queue directly from their phones (i.e. without requiring a dedicated laptop in the middle of the room for people to walk _all_ the way over to).

## How does it work?
At its heart, CAST hosts a very simple webserver, which contains a tiny HTML form. The input to this form is searched in Spotify, and the first track found is added to the queue.

ALL of the heavy lifting is done using the excellent `spotipy` library, which I highly recommend for other Python-based Spotify projects.

Note that Spotify Premium is required to use this app.

## How do I use it?

A small amount of work is required to set up the app (but most of this is one-time work).

1. Clone this repository (`git clone git@bitbucket.org:AugmentedCaribou/cast.git`)
1. Register a dummy app on the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/). The name and description aren't important, though you may wish to call it "CAST" or similar. This provides you with a Client ID and a Client Secret, which you'll need.
1. Inside the app settings, you'll need to set a Redirect URI. This should be set to `http://localhost:9999`.
1. Save the Client ID and Client Secret as the environment variables `CAST_CLIENT_ID` and `CAST_CLIENT_SECRET`.
  - In Bash and other Unix shells, this is done by running `export CAST_CLIENT_ID='...'` (and similar for the Client Secret).
  - In Windows, Google will be able to tell you how to set environment variables.
1. Install the CAST dependencies (`python3 -m pip install -r requirements.txt`)


Now everything should be in place to run CAST:

1. Spin up the CAST webserver with `python3 cast.py`.
1. Navigate to `http://localhost:3141`. The first time you use the app, you may be prompted with a Spotify login page, which you should use to login. Your access tokens are cached and refreshed automatically, so you shouldn't need to do this more than once.
1. Once you've logged in, you should see the CAST homepage saying "Hello!"
1. Other devices connected to the same network should now be able to navigate to the CAST page on `http://<your_machine's_IP_or_hostname>:3141` (e.g. `http://192.168.1.66:3141`.
1. Users can now add tracks to the Spotify queue using the input box and hitting "Submit".

## FAQs

- When I try to add a track, my terminal prints `Player command failed: No active device found`.
    - CAST requires an active Spotify device to queue to. Try starting a song manually on your intended device, and then try again.
- My browser only prints the message "Invalid Redirect URI".
    - Make sure the redirect URI is set correctly in the Spotify dashboard. If it definitely is, then there's a chance your browser has cached the site with the error message. Try clearing your cache, or using private browsing/a different browser.
- How do I find my computer's IP address/hostname to give to my friends?
    - Google will be able to answer this question better than me, but this may help:
        - On Linux: run `hostname`/`hostname -I` to get your hostname/IP address.
        - On MacOS: open System Preferences -> Network, and click on the first option. Below the "Status" field, it should state your local IP address. 
        - On Windows: Google will be able to tell you how to find it.
- How do I add an podcast/entire album/something that isn't an individual track to the queue?
   - Currently, we don't support adding anything other than individual tracks to the queue.
- When I refresh the page, it queues the same song twice. How do I stop this behaviour?
    - The search query is encoded in the URL as `http://hostname:3141/?search=track_name`. Refreshing the page will send this query again. You should explicitly navigate to the "root" page (i.e. `http://hostname:3141/`) instead to avoid this.
- I tried to add a song, and it added one by the wrong artist.
    - Sadly, CAST cannot read your mind. It simply searches Spotify with your query and puts the first track it finds on the queue. For the best chance of success, put both the track name and the artist in the search field.
- Can I skip a track?
    - There's a limited number of "admin" actions (that may change/increase over time), including the ability to skip a track. They currently aren't documented, but you could probably work it out from the source code.
- How do I shuffle the queue?
    - Unfortunately, Spotify doesn't support shuffling the playback queue. Future versions of CAST may choose to add to a playlist, which CAN be shuffled.
- Does the device playing back the music have to be the same one hosting the webserver?
    - No! CAST (or really, spotipy) uses the Spotify API to look for the "active device", and just queues to that. I usually host the webserver on my Raspberry Pi, but use my Smart TV's Spotify app for playback.
- I tried going to `hostname:3141`, but it just searches it in Google.
    - You probably need to manually write the `http://` at the beginning of the search to force your browser to interpret it as a web address (since it's not on a standard HTTP port). Make sure you've actually put the machine's hostname or IP in the URL, rather than just the literal string `hostname`!
- Does my device have to be on the same network as the webserver?
    - Yes. CAST only hosts the webserver locally (and there's several good reasons why hosting it globally might be a bad idea), so it's only visible to people on the same network.
- I already run a service on port 3141/9999 - can I get CAST to use a different port?
    - To change the port numbers used, you can set the environment variables `CAST_PORT` and `CAST_REDIRECT_PORT` to whatever (valid) port numbers you like. Note that if you change `CAST_REDIRECT_PORT`, you'll also need to change the Redirect URI accordingly in the Spotify App Dashboard.
- When trying to run CAST on a device via SSH, I don't get prompted with a window to put my Spotify login details in.
    - CAST will attempt to open a physical web browser using Python's `webbrowser` module. If you're doing this over SSH, you will probably need to ensure you have X11 forwarding enabled.
- I have a honking great idea for how to improve this app - how do I contribute?
    - Speak to me (Ben).
- Are these questions really "Frequently Asked"?
    - In this case, "FAQs" stands for "Fully Anticipated Questions".
