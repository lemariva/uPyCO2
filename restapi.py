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
import json
import time

from microWebSrv import MicroWebSrv

class RestApi():

    def __init__(self):

        self.timestamp = 0
        self.tvoc = 0
        self.eco2 = 0

        self.routeHandlers = [
            ("/json", "GET", self._httpHandlerJson),
            ("/", "GET", self._httpHandlerIndex),
            ("/js/kuma-gauge.jquery.js", "GET", self._httpHandlerJs),
            ("/memory/<query>", "GET", self._httpHandlerMemory)
        ]

    def run(self):
        mws = MicroWebSrv(routeHandlers=self.routeHandlers, webPath="/flash/www")
        mws.Start(threaded=True)
        gc.collect()

    def busy(self, state=None):
        if state is not None:
            self._busy = state
        else:
            return self._busy

    def check_data(self):
        newdata = self._newdata
        self._newdata = False
        return newdata

    def _httpHandlerIndex(self, httpClient, httpResponse):
        f = open('www/index.html')
        content = f.read()

        gc.collect()
        httpResponse.WriteResponseOk(headers=None,
                                 contentType="text/html",
                                 contentCharset="UTF-8",
                                 content=content)
        gc.collect()

    def _httpHandlerJs(self, httpClient, httpResponse):
        f = open('www/js/kuma-gauge.jquery.js')
        content = f.read()
        
        gc.collect()
        httpResponse.WriteResponseOk(headers=None,
                                 contentType="text/javascript",
                                 contentCharset="UTF-8",
                                 content=content)
        gc.collect()

    def _httpHandlerJson(self, httpClient, httpResponse):
        data = {
            'timestamp': self.timestamp,
            'tvoc': self.tvoc,
            'eco2': self.eco2
        }

        httpResponse.WriteResponseOk(headers=None,
                                        contentType="text/html",
                                        contentCharset="UTF-8",
                                        content=json.dumps(data))
        gc.collect()



    def _httpHandlerMemory(self, httpClient, httpResponse, routeArgs):
        print("In Memory HTTP variable route :")
        query = str(routeArgs['query'])

        if 'gc' in query or 'collect' in query:
            gc.collect()

        content = """\
            {}
            """.format(gc.mem_free())
        httpResponse.WriteResponseOk(headers=None,
                                    contentType="text/html",
                                    contentCharset="UTF-8",
                                    content=content)