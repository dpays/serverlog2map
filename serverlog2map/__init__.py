import glob
import json
import os

import grequests
from flask import Flask, render_template, jsonify

from serverlog2map.log_reader import parse_log_files

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "..", "config.json")
DEFAULT_CONFIG = {
    "log_dir": "/var/log/nginx",
    "file_pattern": "access.log*",
    "marker_color": "#00000055",
    "marker_size": 20,
    "request_regex": '([(\d\.)]+) .*? .*? \[(.*?)\] ".*? .*? .*?" \d+ \d+(?: ".*?" ".*?")?',
    "time_format": "%d/%b/%Y:%H:%M:%S %z",
    "time_first": False,
    "ignore_local": True,
    "ignore_duplicates": False,
}


def _load_config():
    if os.path.isfile(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as fd:
            user_config = json.load(fd)
            for key, value in DEFAULT_CONFIG.items():
                if key not in user_config:
                    user_config[key] = value

            return user_config

    else:
        return DEFAULT_CONFIG


app = Flask(__name__)
config = _load_config()


@app.route("/")
def index():
    return render_template(
        "map.html",
        marker_color=config["marker_color"],
        marker_size=config["marker_size"],
    )


@app.route("/data")
def data():
    # TODO: Change GeoIP API
    files = glob.glob(os.path.join(config["log_dir"], config["file_pattern"]))

    # Not to confuse with the popular requests package...
    requests_ = parse_log_files(
        files,
        config["request_regex"],
        config["time_format"],
        config["time_first"],
        config["ignore_local"],
        config["ignore_duplicates"],
    )

    ip_addresses = [req.ip for req in requests_]
    locations = {
        resp.json()["ip"]: {
            "latitude": resp.json()["latitude"], "longitude": resp.json()["longitude"]
        }
        for resp in grequests.map(
            (
                grequests.get("https://freegeoip.net/json/{ip}".format(ip=ip))
                for ip in set(ip_addresses)
            ),
            size=10,
        )
    }
    return jsonify({"ip_addresses": ip_addresses, "locations": locations})


# This is really for development only! (running the script directly from PyCharm)
# Please USE the flask command or something more advanced for deployment, examples
# are provided in the README.
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
