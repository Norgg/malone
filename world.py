from Box2D import *
from threading import Thread
from random import random
import time

KEY_W = 119
KEY_S = 115
KEY_A = 97
KEY_D = 100

class World(b2World, Thread):
  def __init__(self):
    aabb = b2AABB()
    aabb.lowerBound = (-100, -100)
    aabb.upperBound = ( 100,  100)
    gravity = b2Vec2(0, 0)
    self.players = {}
    b2World.__init__(self, aabb, gravity, True)
    Thread.__init__(self)
    self.running = True
    self.tick = 0

  def add_player(self, conn):
    self.players[conn] = Player(self, conn)
    print("Added player to world.")

  def del_player(self, conn):
    del self.players[conn]
    print("Removed player.")

  def keydown(self, conn, key):
    player = self.players[conn]
    
    if (key == KEY_W):
      player.body.ApplyForce((0, 0.1), (0, 0))
    elif (key == KEY_S):
      player.body.ApplyForce((0, -0.1), (0, 0))
    elif (key == KEY_A):
      player.body.ApplyForce((-0.1, 0), (0, 0))
    elif (key == KEY_D):
      player.body.ApplyForce((0.1, 0), (0, 0))

  def run(self):
    print("World started")
    while(self.running):
      time.sleep(0.015)
      self.Step(1.0/60, 10, 10)
      self.tick += 1

      for player in self.players.values():
        #player.body.ApplyForce((0.1, 0), (0, 0))
        if self.tick % 100 == 0:
          print player.body.position
        pass
      
  def stop(self):
    print("World Stopped")
    self.running = False


class Player(object):
  def __init__(self, world, conn):
    health = 100
    self.world = world
    self.conn = conn

    #Create physics shape
    bodyDef = b2BodyDef()
    bodyDef.position = (random(), random())
    self.body = world.CreateBody(bodyDef)
    shape = b2CircleDef()
    shape.pos=(0,0)
    shape.radius = 0.5
    shape.density = 1
    self.body.CreateShape(shape)
    self.body.SetMassFromShapes()

  def damage(d):
    health -= d
    if (health < 0):
      self.world.del_player(self.conn)
