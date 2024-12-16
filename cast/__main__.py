"""Run the CAST application."""

import argparse
import functools
from http.server import ThreadingHTTPServer

from cast.cast import CastHTTPRequestHandler
from cast.config import CastConfig


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", required=True, help="Config file")
    return parser.parse_args()


args = parse_args()
config = CastConfig.from_config_file(args.config)
handler = functools.partial(CastHTTPRequestHandler, config)
server_address = ("", int(config.port))
httpd = ThreadingHTTPServer(server_address, handler)
print(f"Starting CAST server on localhost, port {config.port}.")
httpd.serve_forever()
