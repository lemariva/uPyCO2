"""
Copyright 2020 LeMaRiva|Tech (Mauro Riva) info@lemariva.com
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
    http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import argparse
import requests
import logging
import sys
import json
from google.cloud import pubsub_v1
from datetime import datetime

import time
from flask import Flask, render_template, Response, request, jsonify, url_for

LOOP_TIME_SLEEP = 60 * 10

subscriber = pubsub_v1.SubscriberClient()

app = Flask(__name__)
app.config["DEBUG"] = True

devices = {}

@app.route('/', methods=['GET'])
def home():
    device_id = request.args.get("deviceId")
    tvoc = 0
    eco2 = 0
    timestamp = 0

    if device_id in devices:
        device = devices[device_id]
        data = {  
            "device_id": device_id,
            "tvoc": device['tvoc'],
            "eco2,": device['eco2'],
            "timestamp": datetime.fromtimestamp(device['timestamp']),
            "found": True
        }
    else:
        data = {
            "found": False
        }

    return jsonify(data), 200

def callback(message):
    device_id = message.attributes['deviceId']
    device_data = json.loads(message.data.decode('utf-8'))

    print(device_data)
    if device_id not in devices:
        devices[device_id] = {}
        devices[device_id]['tvoc'] = device_data['tvoc']
        devices[device_id]['timestamp'] = device_data['timestamp']
        devices[device_id]['eco2'] = device_data['eco2']
    else:
        devices[device_id]['tvoc'] = device_data['tvoc']
        devices[device_id]['timestamp'] = device_data['timestamp']
        devices[device_id]['eco2'] = device_data['eco2']

    message.ack()  
    
if __name__ == "__main__":
    assert sys.version_info >= (3, 6), sys.version_info

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000, help="server port for information")
    parser.add_argument("--project", default="core-iot-sensors", help="google project id")
    parser.add_argument("--subscription", default="esp32-iot-tvoc", help="subscription name")

    args = parser.parse_args()

    subscription_path = subscriber.subscription_path(args.project, args.subscription)
    future = subscriber.subscribe(subscription_path, callback)

    app.run(
        host="0.0.0.0", debug=True, port=args.port, threaded=True, use_reloader=False
    )
