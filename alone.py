#!/usr/bin/python
# -*- coding: utf-8 -*-
from world import *

import argparse
import random
import os

import cherrypy

from cherrypy.process import plugins

from ws4py.server.cherrypyserver import WebSocketPlugin, WebSocketTool
from ws4py.server.handler.threadedhandler import WebSocketHandler

KEYDOWN = 1
KEYUP = 2
LEFT_MOUSE_CLICK = 3
RIGHT_MOUSE_CLICK = 4


class WorldRunner(plugins.SimplePlugin):
  def stop(self):
    world.stop()

class AloneWebSocketHandler(WebSocketHandler):
  def __init__(self, sock, protocols, extensions):
    #print "Player joined."
    WebSocketHandler.__init__(self, sock, protocols, extensions)
    world.add_player(self)

  def received_message(self, m):
    #print "Got: %s" % list(m.data)
    
    if m.data[0] == LEFT_MOUSE_CLICK:
      x, y = struct.unpack("<hh", str(bytearray(m.data[2:])))
      world.click(self, x, y)
    elif m.data[0] == RIGHT_MOUSE_CLICK:
      x, y = struct.unpack("<hh", str(bytearray(m.data[2:])))
      world.rightclick(self, x, y)

class Root(object):
  def __init__(self, host, port):
    self.host = host
    self.port = port

  @cherrypy.expose
  def ws(self):
    cherrypy.log("Handler created: %s" % repr(cherrypy.request.ws_handler))

if __name__ == '__main__':
  world = World()
  world.start()
  
  parser = argparse.ArgumentParser(description='\'malone? Server')
  parser.add_argument('--host', default='0.0.0.0')
  parser.add_argument('-p', '--port', default=9000, type=int)
  args = parser.parse_args()

  cherrypy.config.update({'server.socket_host': args.host,
                          'server.socket_port': args.port,
                          'tools.staticdir.root': os.path.abspath(os.path.join(os.path.dirname(__file__), 'static'))})

  WebSocketPlugin(cherrypy.engine).subscribe()
  WorldRunner(cherrypy.engine).subscribe()
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

