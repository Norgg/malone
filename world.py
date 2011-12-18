from Box2D import *
from threading import *
from random import random
import time
import struct

KEY_W = 87
KEY_S = 83
KEY_A = 65
KEY_D = 68

PLAYER_TYPE = 1
BULLET_TYPE = 2

class World(Thread):
  size = 200
  
  def __init__(self):
    self.players = {}
    self.npcs = []
    self.phys = b2World((0,0), False, 
                        contactListener = MaloneContactListener(),
                        contactFilter   = MaloneContactFilter())
    self.phys_lock = RLock()
    
    Thread.__init__(self)
    
    self.running = True
    self.tick = 0

    #Create walls
    top    = b2BodyDef()
    bottom = b2BodyDef()
    left   = b2BodyDef()
    right  = b2BodyDef()
    
    top.position    = (0,  World.size + 10)
    bottom.position = (0, -World.size - 10)
    left.position   = (-World.size - 10, 0)
    right.position  = ( World.size + 10, 0)

    top_body    = self.phys.CreateBody(top)
    bottom_body = self.phys.CreateBody(bottom)
    left_body   = self.phys.CreateBody(left)
    right_body  = self.phys.CreateBody(right)

    top_body.CreatePolygonFixture(   box=(World.size + 10, 10))
    bottom_body.CreatePolygonFixture(box=(World.size + 10, 10))
    left_body.CreatePolygonFixture(  box=(10, World.size + 10))
    right_body.CreatePolygonFixture( box=(10, World.size + 10))

    self.add_npc()
    self.add_npc()
    self.add_npc()
    self.add_npc()
    self.add_npc()
  
  def add_player(self, conn):
    self.players[conn] = Player(self, conn)
    print("Added player to world.")

  def add_npc(self):
    self.npcs.append(NPC(self, None))
    print("Added npc.")
  
  def del_player(self, conn, player):
    for bullet in player.bullets.values():
      bullet.destroy()
    
    self.phys_lock.acquire()
    self.phys.DestroyBody(player.body)
    self.phys_lock.release()

    if conn:
      del self.players[conn]
      print("Removed player.")
    else:
      self.npcs.remove(player)
      print("Removed npc.")

  def serialise(self, forPlayer):
    data = ""

    #Ensure this player is at the end of the player list.
    player_list = self.players.values()
    player_list.remove(forPlayer)
    player_list.extend(self.npcs)
    player_list.append(forPlayer)
    
    forX = forPlayer.body.position.x
    forY = forPlayer.body.position.y

    viewport = 50

    for player in player_list:
      if abs(player.body.position.x - forX) < viewport and abs(player.body.position.y - forY) < viewport:
        data += struct.pack("<HHfff", PLAYER_TYPE, 
                                      player.id, 
                                      player.body.position.x, 
                                      player.body.position.y, 
                                      player.body.angle)
      for bullet in player.bullets.values():
        if abs(bullet.body.position.x - forX) < viewport and abs(bullet.body.position.y - forY) < viewport:
          data += struct.pack("<HHff", BULLET_TYPE, 
                                        bullet.id, 
                                        bullet.body.position.x, 
                                        bullet.body.position.y)
        
   
    return bytearray(data)


  def keydown(self, conn, key):
    if not conn in self.players:
      return
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
    if not conn in self.players:
      return
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
    if not conn in self.players:
      return
    self.players[conn].fire_at(x, y)
    pass


  def run(self):
    print("World started")
    while(self.running):
      time.sleep(0.015)
      self.phys_lock.acquire()
      self.phys.Step(1.0/60, 10, 10)
      self.phys_lock.release()
      self.tick += 1

      for player in self.players.values():
        player.update()

      for player in self.npcs:
        player.update()

      for player in self.players.values():
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
  health = 10
  def __init__(self, world, conn):
    self.health = Player.health
    self.world = world
    self.conn = conn
    Player.id += 1
    self.id = Player.id

    self.left = False
    self.right = False
    self.up = False
    self.down = False

    #Create physics shape
    world.phys_lock.acquire()
    self.body = world.phys.CreateDynamicBody(position=(200*random(), 200*random()))
    self.body.userData = self
    self.body.CreateCircleFixture(radius=Player.r, density=0.01, restitution=0.1)
    world.phys_lock.release()
    
    self.bullets = {}

  def damage(self, d):
    self.health -= d
    print "%s health left" % self.health

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

    if (self.health < 0):
      self.world.del_player(self.conn, self)

  def fire_at(self, x, y):
    bullet = Bullet(self.world, self, x, y)
    self.bullets[bullet.id] = bullet

  def send_update(self, update):
    try: 
      #print "Sending %s" % list(update)
      self.conn.send(update, binary=True)
    except:
      self.world.del_player(self.conn, self)

class NPC(Player):
  def __init__(self, world, conn):
    Player.__init__(self, world, conn)

  def update(self):
    Player.update(self)
    if (random() > 0.98):
      self.fire_at(100*(random()-0.5), 100*(random()-0.5))
    if (self.health < 0):
      self.world.add_npc()

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
    vel.Normalize()
    offset = vel * (Player.r+Bullet.r+0.1)
    pos = (x+offset.x, y+offset.y)
    
    self.world.phys_lock.acquire()
    self.body = world.phys.CreateDynamicBody(position=pos, bullet=True, userData=self)
    self.body.CreateCircleFixture(radius=Bullet.r, density=0.01, restitution=0.3)
    self.body.linearVelocity = player.body.linearVelocity
    self.body.ApplyForce(40*vel, (x,y))
    self.world.phys_lock.release()
  
  def update(self):
    self.ttl -= 1
    if self.ttl <= 0:
      self.destroy()
    
  def destroy(self):
    self.world.phys_lock.acquire()
    self.world.phys.DestroyBody(self.body)
    self.world.phys_lock.release()
    del(self.player.bullets[self.id])

class MaloneContactListener(b2ContactListener):
  def __init__(self):
    b2ContactListener.__init__(self)

  def BeginContact(self, contact):
    pass
  def EndContact(self, contact):
    pass
  def PreSolve(self, contact, oldManifold):
    pass

  def PostSolve(self, contact, impulse):
    objA = contact.fixtureA.body.userData
    objB = contact.fixtureB.body.userData

    if isinstance(objA, Player) and isinstance(objB, Bullet):
      damage = abs(impulse.normalImpulses[0] - impulse.normalImpulses[1])
      objA.damage(damage)
      objB.ttl = 0

    if isinstance(objB, Player) and isinstance(objA, Bullet):
      damage = abs(impulse.normalImpulses[0] - impulse.normalImpulses[1])
      objB.damage(damage)
      objA.ttl = 0
    
class MaloneContactFilter(b2ContactFilter):
  def __init__(self):
    b2ContactFilter.__init__(self)

  def ShouldCollide(self, fixture1, fixture2):
    return True
    obj1 = fixture1.body.userData
    obj2 = fixture2.body.userData
    if (isinstance(obj1, Bullet)):
      if (isinstance(obj2, Player)):
        if obj1 in obj2.bullets.values():
          return False

    if (isinstance(obj2, Bullet)):
      if (isinstance(obj1, Player)):
        if obj2 in obj1.bullets.values():
          return False

    return True
