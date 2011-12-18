from Box2D import *
from threading import Thread
from random import random
import time
import struct

KEY_W = 87
KEY_S = 83
KEY_A = 65
KEY_D = 68

PLAYER_TYPE = 1
BULLET_TYPE = 2

class World(b2World, Thread):
  def __init__(self):
    aabb = b2AABB()
    aabb.lowerBound = (-220, -220)
    aabb.upperBound = ( 220,  220)
    gravity = b2Vec2(0, 0)
   
    self.players = {}

    b2World.__init__(self, aabb, gravity, False)
    
    Thread.__init__(self)
    
    self.running = True
    self.tick = 0

    #Create walls
    top = b2BodyDef()
    bottom = b2BodyDef()
    left = b2BodyDef()
    right = b2BodyDef()
    top.position    = (0,  210)
    bottom.position = (0, -210)
    left.position   = (-210, 0)
    right.position  = ( 210, 0)

    top_body = self.CreateBody(top)
    bottom_body = self.CreateBody(bottom)
    left_body = self.CreateBody(left)
    right_body = self.CreateBody(right)

    top_bottom_shape = b2PolygonDef()
    top_bottom_shape.SetAsBox(210, 10)
    left_right_shape = b2PolygonDef()
    left_right_shape.SetAsBox(10, 210)

    top_body.CreateShape(top_bottom_shape)
    bottom_body.CreateShape(top_bottom_shape)
    left_body.CreateShape(left_right_shape)
    right_body.CreateShape(left_right_shape)
 
    
    #self.SetContactFilter(MyContactFilter())

  def add_player(self, conn):
    self.players[conn] = Player(self, conn)
    print("Added player to world.")
  
  def del_player(self, conn):
    player = self.players[conn]
    for bullet in player.bullets.values():
      bullet.destroy()
    
    self.DestroyBody(player.body)

    del self.players[conn]
    print("Removed player.")

  def serialise(self, forPlayer):
    data = ""

    #Ensure this player is at the end of the player list.
    player_list = self.players.values()
    player_list.remove(forPlayer)
    player_list.append(forPlayer)

    for player in player_list:
      data += struct.pack("<HHfff", PLAYER_TYPE, 
                                    player.id, 
                                    player.body.position.x, 
                                    player.body.position.y, 
                                    player.body.angle)
      for bullet in player.bullets.values():
        data += struct.pack("<HHff", BULLET_TYPE, 
                                      bullet.id, 
                                      bullet.body.position.x, 
                                      bullet.body.position.y)
        
   
    return bytearray(data)


  def keydown(self, conn, key):
    player = self.players[conn]
    
    if (key == KEY_W):
      player.up = True
      player.down = False
    elif (key == KEY_S):
      player.down = True
      player.up = False
    elif (key == KEY_A):
      player.left = True
      player.right = False
    elif (key == KEY_D):
      player.right = True
      player.left = False

  def keyup(self, conn, key):
    player = self.players[conn]
    
    if (key == KEY_W):
      player.up = False
    elif (key == KEY_S):
      player.down = False
    elif (key == KEY_A):
      player.left = False
    elif (key == KEY_D):
      player.right = False

  def click(self, conn, x, y):
    self.players[conn].fire_at(x, y)
    pass


  def run(self):
    print("World started")
    while(self.running):
      time.sleep(0.015)
      self.Step(1.0/60, 10, 10)
      self.tick += 1

      for player in self.players.values():
        player.update()

        #player.body.ApplyForce((0.1, 0), (0, 0))
        #if self.tick % 100 == 0:
        #  print player.body.position

        if self.tick % 2 == 0:
          #Send update
          player.send_update(self.serialise(player))
        pass
    print("World stopped")
      
  def stop(self):
    self.running = False

class Player(object):
  id = 0
  force = 5
  r = 2
  def __init__(self, world, conn):
    self.health = 100
    self.world = world
    self.conn = conn
    Player.id += 1
    self.id = Player.id

    self.left = False
    self.right = False
    self.up = False
    self.down = False

    #Create physics shape
    bodyDef = b2BodyDef()
    bodyDef.position = (random(), random())
    self.body = world.CreateBody(bodyDef)
    self.body.userData = self
    shape = b2CircleDef()
    shape.pos=(0,0)
    shape.radius = Player.r
    shape.density = 0.01
    shape.restitution = 0.1
    self.body.CreateShape(shape)
    self.body.SetMassFromShapes()

    self.bullets = {}

  def damage(self, d):
    health -= d
    if (health < 0):
      self.world.del_player(self.conn)

  def update(self):
    pos = self.body.position
    if self.left:
      self.body.ApplyForce((-Player.force, 0), pos)
    if self.right:
      self.body.ApplyForce((Player.force, 0), pos)
    if self.up:
      self.body.ApplyForce((0, Player.force), pos)
    if self.down:
      self.body.ApplyForce((0, -Player.force), pos)
    for bullet in self.bullets.values():
      bullet.update()

  def fire_at(self, x, y):
    bullet = Bullet(self.world, self, x, y)
    self.bullets[bullet.id] = bullet

  def send_update(self, update):
    try: 
      #print "Sending %s" % list(update)
      self.conn.send(update, binary=True)
    except:
      self.world.del_player(self.conn)

class Bullet(object):
  id = 0
  r = 0.8
  ttl = 300
  def __init__(self, world, player, aimX, aimY):
    x = player.body.position.x
    y = player.body.position.y
    Bullet.id += 1
    self.id = Bullet.id
    self.ttl = Bullet.ttl
    self.world = world
    self.player = player

    #Create physics shape
    bodyDef = b2BodyDef()
    vel = b2Vec2(aimX, aimY)
    print "Firing towards", (aimX, aimY)
    print "Normalized", vel.Normalize()
    offset = (vel/vel.Normalize()) * Player.r
    print "Offset by", offset

    bodyDef.position = (x+offset.x, y+offset.y)
    bodyDef.bullet = True
    print "Placing at", bodyDef.position
    print "Player at", player.body.position
    self.body = world.CreateBody(bodyDef)
    self.body.userData = self
    shape = b2CircleDef()
    shape.pos=(0,0)
    shape.radius = Bullet.r
    shape.density = 0.01
    shape.restitution = 0.3
    self.body.CreateShape(shape)
    self.body.SetMassFromShapes()
    self.body.linearVelocity = player.body.linearVelocity
    self.body.ApplyForce(40*vel, (x,y))
  
  def update(self):
    self.ttl -= 1
    if self.ttl <= 0:
      self.destroy()
    
  def destroy(self):
    self.world.DestroyBody(self.body)
    del(self.player.bullets[self.id])

class MyContactFilter(b2ContactFilter):
    def __init__(self):
        b2ContactFilter.__init__(self)
    def ShouldCollide(self, shape1, shape2):
        body1 = shape1.fixture.body
        body2 = shape2.fixture.body
        if (isinstance(body1.userData, Bullet)):
          if (isinstnce(body2.userData, Person)):
            if body1.userData in body2.userData.bullets:
              return False

        if (isinstance(body2.userData, Person)):
          if (isinstance(body1.userData, Bullet)):
            if body2.userData in body1.userData.bullets:
              return False

        return True
