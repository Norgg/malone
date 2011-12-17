from Box2D import *

class World(object):
  def __init__(self):
    aabb = b2AABB()
    aabb.lowerBound = (-100, -100)
    aabb.upperBound = ( 100,  100)
    gravity = b2Vec2(0, -10)
    self.world = b2World(aabb, gravity, True)

