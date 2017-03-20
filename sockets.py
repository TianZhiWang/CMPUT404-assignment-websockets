#!/usr/bin/env python
# coding: utf-8
# Copyright (c) 2013-2014 Abram Hindle, Tian Zhi Wang
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import flask
from flask import Flask, request
from flask_sockets import Sockets
import gevent
from gevent import queue
import time
import json
import os

app = Flask(__name__)
sockets = Sockets(app)
app.debug = True

clients = list()
#From https://github.com/abramhindle/WebSocketsExamples/blob/master/chat.py Abram Hindle
class Client:
    def __init__(self):
        self.queue = queue.Queue()

    def put(self, v):
        self.queue.put_nowait(v)

    def get(self):
        return self.queue.get()

class World:
    def __init__(self):
        self.clear()
        # we've got listeners now!
        self.listeners = list()
        
    def add_set_listener(self, listener):
        self.listeners.append( listener )

    def update(self, entity, key, value):
        entry = self.space.get(entity,dict())
        entry[key] = value
        self.space[entity] = entry
        self.update_listeners( entity )

    def set(self, entity, data):
        self.space[entity] = data
        self.update_listeners( entity )

    def update_listeners(self, entity):
        '''update the set listeners'''
        for listener in self.listeners:
            listener(entity, self.get(entity))

    def clear(self):
        self.space = dict()

    def get(self, entity):
        return self.space.get(entity,dict())
    
    def world(self):
        return self.space

myWorld = World()        

def set_listener( entity, data ):
    ''' do something with the update ! '''
    for client in clients:
        client.put(json.dumps({entity : data}))

myWorld.add_set_listener( set_listener )
         
@app.route('/')
def hello():
    '''Return something coherent here.. perhaps redirect to /static/index.html '''
    return flask.redirect("/static/index.html")

#From https://github.com/abramhindle/WebSocketsExamples/blob/master/chat.py Abram Hindle
def read_ws(ws,client):
    '''A greenlet function that reads from the websocket'''
    try:
        while True:
            msg = ws.receive()
            # print "WS RECV: %s" % msg
            if (msg is not None):
                packet = json.loads(msg)
                for key in packet:
                    val = packet[key]
                    myWorld.set(key, val)
            else:
                break
    except:
        '''Done'''

#From https://github.com/abramhindle/WebSocketsExamples/blob/master/chat.py Abram Hindle
@sockets.route('/subscribe')
def subscribe_socket(ws):
    '''Fufill the websocket URL of /subscribe, every update notify the
       websocket and read updates from the websocket '''
    client = Client()
    clients.append(client)
    g = gevent.spawn( read_ws, ws, client )    
    print "Subscribing"
    try:
        while True:
            # block here
            msg = client.get()
            print "Got a message!"
            ws.send(msg)
    except Exception as e:# WebSocketError as e:
        print "WS Error %s" % e
    finally:
        clients.remove(client)
        gevent.kill(g)

if __name__ == "__main__":
    ''' This doesn't work well anymore:
        pip install gunicorn
        and run
        gunicorn -k flask_sockets.worker sockets:app
    '''
    app.run()
