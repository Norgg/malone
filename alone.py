# -*- coding: utf-8 -*-
from world import *

import argparse
import random
import os

import cherrypy

from ws4py.server.cherrypyserver import WebSocketPlugin, WebSocketTool
from ws4py.server.handler.threadedhandler import WebSocketHandler, EchoWebSocketHandler

world = World()

class AloneWebSocketHandler(WebSocketHandler):
    def received_message(self, m):
        print "Got: %s" % m
        cherrypy.engine.publish('websocket-broadcast', str(m))

class Root(object):
    def __init__(self, host, port):
        self.host = host
        self.port = port

    @cherrypy.expose
    def ws(self):
        cherrypy.log("Handler created: %s" % repr(cherrypy.request.ws_handler))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Echo CherryPy Server')
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('-p', '--port', default=9000, type=int)
    args = parser.parse_args()

    cherrypy.config.update({'server.socket_host': args.host,
                            'server.socket_port': args.port,
                            'tools.staticdir.root': os.path.abspath(os.path.join(os.path.dirname(__file__), 'static'))})

    WebSocketPlugin(cherrypy.engine).subscribe()
    cherrypy.tools.websocket = WebSocketTool()

    cherrypy.quickstart(Root(args.host, args.port), '', config={
        '/ws': {
            'tools.websocket.on': True,
            'tools.websocket.handler_cls': AloneWebSocketHandler
            },
        '/': {
              'tools.staticdir.on': True,
              'tools.staticdir.dir': '',
              'tools.staticdir.index': 'index.html'
            }
        }
    )

