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
import gc
from machine import Pin, SoftI2C, reset, I2S, deepsleep
import network
from neopixel import NeoPixel

import ujson
import utime

from third_party import string
from third_party import rsa
from umqtt.simple import MQTTClient
from ubinascii import b2a_base64

from sgp30 import SGP30
from config import *

from restapi import RestApi

sta_if = network.WLAN(network.STA_IF)
epoch_offset = 946684800

## sgp30 setup
i2c = SoftI2C(scl=Pin(device_config['scl']), sda=Pin(device_config['sda']), freq=100000)
sgp30 = SGP30(i2c)
sgp30.initialise_indoor_air_quality()

## neopixel
np = NeoPixel(Pin(device_config['led']), 1)

if app_config['audio']:
    ## audio setup
    SAMPLES_PER_SECOND = 11025

    audio_out = I2S(I2S.NUM0, bck=Pin(device_config['bck']), 
                ws=Pin(device_config['ws']), 
                sdout=Pin(device_config['sdout']), 
                standard=I2S.PHILIPS, mode=I2S.MASTER_TX,
                dataformat=I2S.B16, channelformat=I2S.ONLY_RIGHT,
                samplerate=SAMPLES_PER_SECOND, apllrate=0,
                dmacount=6, dmalen=60)

    def warning_sound():
        track = open('warning.wav','rb')
        stop = False
        track.seek(0)
        while not stop:
            audio_samples = bytearray(track.read(1024))
            numwritten = 0
            if len(audio_samples) == 0:
                print("STOP")
                stop = True
            else:
                # loop until samples can be written to DMA
                while numwritten == 0:
                    # return immediately when no DMA buffer is available (timeout=0)
                    numwritten = audio_out.write(audio_samples, timeout=0)
                    # await - allow other coros to run
        print("done")
        gc.collect()

if app_config['gcp']:
    ## google iot core functions
    def on_message(topic, message):
        print((topic,message))

    def b42_urlsafe_encode(payload):
        return string.translate(b2a_base64(payload)[:-1].decode('utf-8'),{ ord('+'):'-', ord('/'):'_' })

    def create_jwt(project_id, private_key, algorithm, token_ttl):
        print("Creating JWT...")
        private_key = rsa.PrivateKey(*private_key)
        claims = {
                'iat': utime.time() + epoch_offset,
                'exp': utime.time() + epoch_offset + token_ttl,
                'aud': project_id
        }
        header = { "alg": algorithm, "typ": "JWT" }
        content = b42_urlsafe_encode(ujson.dumps(header).encode('utf-8'))
        content = content + '.' + b42_urlsafe_encode(ujson.dumps(claims).encode('utf-8'))
        signature = b42_urlsafe_encode(rsa.sign(content,private_key,'SHA-256'))
        return content+ '.' + signature 

    def get_mqtt_client(project_id, cloud_region, registry_id, device_id, jwt):
        """Create our MQTT client. The client_id is a unique string that identifies
        this device. For Google Cloud IoT Core, it must be in the format below."""
        client_id = 'projects/{}/locations/{}/registries/{}/devices/{}'.format(project_id, cloud_region, registry_id, device_id)
        print('Sending message with password {}'.format(jwt))
        client = MQTTClient(client_id.encode('utf-8'),server=google_cloud_config['mqtt_bridge_hostname'],port=google_cloud_config['mqtt_bridge_port'],user=b'ignored',password=jwt.encode('utf-8'),ssl=True)
        client.set_callback(on_message)
        client.connect()
        client.subscribe('/devices/{}/config'.format(device_id), 1)
        client.subscribe('/devices/{}/commands/#'.format(device_id), 1)
        return client

def main():

    if app_config['restapi']:
        restapi = RestApi()
        restapi.run()

    # Retrieve previously stored baselines, if any (helps the compensation algorithm).
    has_baseline = False
    try:
        f_co2 = open('co2eq_baseline.txt', 'r')
        f_tvoc = open('tvoc_baseline.txt', 'r')

        co2_baseline = int(f_co2.read())
        tvoc_baseline = int(f_tvoc.read())
        #Use them to calibrate the sensor
        sgp30.set_indoor_air_quality_baseline(co2_baseline, tvoc_baseline)

        f_co2.close()
        f_tvoc.close()

        has_baseline = True
    except:
        print('Impossible to read SGP30 baselines!')

    #Store the time at which last baseline has been saved
    baseline_time = utime.time()

    if app_config['gcp']:
        # cloud connection
        jwt = create_jwt(google_cloud_config['project_id'], jwt_config['private_key'], jwt_config['algorithm'], jwt_config['token_ttl'])
        client = get_mqtt_client(google_cloud_config['project_id'], google_cloud_config['cloud_region'], google_cloud_config['registry_id'], config.google_cloud_config['device_id'], jwt)
        gc.collect()
    
    # acquiring and sending data
    while True:
        # acquiring data
        tvoc, eco2 = sgp30.indoor_air_quality
        timestamp = utime.time() + epoch_offset

        if app_config['restapi']:
            restapi.tvoc = tvoc
            restapi.eco2 = eco2
            restapi.timestamp = timestamp

        if app_config['gcp']:
            #sending data to gcp
            message = {
                "device_id": google_cloud_config['device_id'],
                "tvoc": tvoc,
                "eco2": eco2,
                "timestamp": timestamp
            }
            print("Publishing message "+str(ujson.dumps(message)))
            mqtt_topic = '/devices/{}/{}'.format(google_cloud_config['device_id'], 'events')
            client.publish(mqtt_topic.encode('utf-8'), ujson.dumps(message).encode('utf-8'))
            client.check_msg()

        if tvoc > app_config['warning']:
            np[0] = (255, 255, 0)
            np.write()
            if app_config['audio']:
                warning_sound()
        elif tvoc > app_config['danger']:
            np[0] = (255, 0, 0)
            np.write()
            if app_config['audio']:
                warning_sound()
        else:
            np[0] = (0, 255, 0)
            np.write()

        gc.collect()

        # Baselines should be saved after 12 hour the first 
        # timen then every hour according to the doc.
        if (has_baseline and (utime.time() - baseline_time >= 3600)) \
            or ((not has_baseline) and (utime.time() - baseline_time >= 43200)):

            print('Saving baseline!')
            baseline_time = utime.time()

            try:
                f_co2 = open('co2eq_baseline.txt', 'w')
                f_tvoc = open('tvoc_baseline.txt', 'w')

                bl_co2, bl_tvoc = sgp30.indoor_air_quality_baseline
                f_co2.write(str(bl_co2))
                f_tvoc.write(str(bl_tvoc))

                f_co2.close()
                f_tvoc.close()

                has_baseline = True
            except:
                print('Impossible to write SGP30 baselines!')

        gc.collect()
        
        print("Going to sleep for about %s milliseconds!" % app_config["deepsleepms"])
        if app_config['restapi']:
            utime.sleep(app_config["deepsleepms"])
        else:
            deepsleep(app_config["deepsleepms"])

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        raise
    except OSError as exc:
        print(exc)
        utime.sleep(5)
        reset()