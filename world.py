from Box2D import *
from threading import *
from random import random
import time
import struct
import traceback

KEY_W = 87
KEY_S = 83
KEY_A = 65
KEY_D = 68

PLAYER_TYPE = 1
BULLET_TYPE = 2
DEADED_TYPE = 3
DEATHSOUND_TYPE = 4

class World(Thread):
  size = 200
  
  def __init__(self):
    self.players = {}
    self.npcs = []
    self.bullets = []
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

  def add_player(self, conn):
    player = Player(self, conn)
    self.players[conn] = player
    print("Added player %d." % player.id)

  def add_npc(self):
    npc = NPC(self)
    self.npcs.append(npc)
    print("Added npc %d." % npc.id)
  
  def del_player(self, conn, player):
    self.phys_lock.acquire()
    for p in self.players.values():
      p.send_death_sound = True

    self.phys.DestroyBody(player.body)

    if conn:
      del self.players[conn]
      
      try:
        conn.send(struct.pack("<H", DEADED_TYPE), binary=True)
      except: #Probably because player has disconnected, ignore.
        print("Failed to send death notification.")
        traceback.print_exc()
      
      print("Removed player %d." % player.id)
    else:
      self.npcs.remove(player)
      print("Removed npc %d." % player.id)
    self.phys_lock.release()

  def killall(self):
    for player in self.players.values():
      self.del_player(player.conn, player)

  def serialise(self, for_player):
    data = ""

    #Ensure this player is at the end of the player list.
    player_list = self.players.values()
    player_list.remove(for_player)
    player_list += self.npcs
    player_list.append(for_player)
    
    forX = for_player.body.position.x
    forY = for_player.body.position.y

    viewport = 80

    for player in player_list:
      if abs(player.body.position.x - forX) < viewport and abs(player.body.position.y - forY) < viewport:
        data += struct.pack("<HHffff", PLAYER_TYPE, 
                                      player.id % 65536, 
                                      player.body.position.x, 
                                      player.body.position.y, 
                                      player.body.angle,
                                      player.r)
    for bullet in self.bullets:
      if abs(bullet.body.position.x - forX) < viewport and abs(bullet.body.position.y - forY) < viewport:
        data += struct.pack("<HHff", BULLET_TYPE, 
                                      bullet.id % 65536, 
                                      bullet.body.position.x, 
                                        bullet.body.position.y)
    return bytearray(data)

  def click(self, conn, x, y):
    if not conn in self.players:
      return
    self.players[conn].fire_at(x, y)
    pass
  
  def rightclick(self, conn, x, y):
    if not conn in self.players:
      return
    self.players[conn].move_towards(x, y)
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

      for bullet in self.bullets:
        bullet.update()

      for player in self.players.values():
        if self.tick % 2 == 0:
          #Send update
          player.send_update(self.serialise(player))
        pass
    print("World stopped")
      
  def stop(self):
    self.killall()
    self.running = False

class Player(object):
  id = 0
  force = 100
  r = 2
  health = 2
  range = 100

  def __init__(self, world, conn):
    self.health = Player.health
    self.world = world
    self.conn = conn
    Player.id += 1
    self.id = Player.id
    
    self.killed_by = None
    self.send_death_sound = False

    self.r = Player.r
    self.kills = 0

    self.shots = 1
    self.range = Player.range

    self.do_grow = False

    #Create physics shape
    world.phys_lock.acquire()
    self.body = world.phys.CreateDynamicBody(position=(200*random(), 200*random()))
    self.body.userData = self
    self.fixture = self.body.CreateCircleFixture(radius=self.r, density=0.01, restitution=0.1)
    world.phys_lock.release()
    
  def damage(self, d):
    self.health -= d
    #print "%s health left" % self.health

  def update(self):
    pos = self.body.position
    
    if self.do_grow:
      self.do_grow = False
      self.r *= 1.2
      self.body.DestroyFixture(self.fixture)
      self.fixture = self.body.CreateCircleFixture(radius=self.r, density=0.01 * self.kills, restitution=0.1)

    if (self.health < 0):
      if self.killed_by:
        self.killed_by.add_kill()
      if (self.conn):
        self.send_update(self.world.serialise(self))
      self.world.del_player(self.conn, self)
    
  def fire_at(self, x, y):
    for i in range(0, self.shots):
      bullet = Bullet(self.world, self, x + self.shots*(random()-0.5), y + self.shots*(random()-0.5), self.range)
      self.world.bullets.append(bullet)
  
  def move_towards(self, x, y):
    print("Moving towards %d, %d" % (x, y))
    imp = b2Vec2(x, y)/30
    self.body.ApplyLinearImpulse(imp, (self.body.position.x, self.body.position.y))

  def send_update(self, update):
    try: 
      #print "Sending %s" % list(update)
      if self.send_death_sound:
        update = update + struct.pack("<HH", DEATHSOUND_TYPE, self.id % 65536)
        self.send_death_sound = False
      self.conn.send(update, binary=True)
    except:
      print "Failed to send update to %d, disconnecting." % self.id
      traceback.print_exc()
      self.world.del_player(self.conn, self)

  def add_kill(self):
    self.kills += 1
    if self.kills % 2 == 0:
      self.shots += 1
    self.health += 1 
    self.do_grow = True
    self.range = Player.range - self.kills*5

class NPC(Player):
  def __init__(self, world):
    Player.__init__(self, world, None)

  def update(self):
    Player.update(self)
    if (random() > 0.98):
      self.fire_at(100*(random()-0.5), 100*(random()-0.5))
    if (self.health < 0):
      self.world.add_npc()

    #TODO: Fix the maths here.
    if (random() > 0.95):
      self.up = 50
      self.down = self.left = self.right = 0 
    elif (random() > 0.90):
      self.down = 50
      self.up = self.left = self.right = 0 
    elif (random() > 0.85):
      self.left = 50
      self.up = self.down = self.right = 0 
    elif (random() > 0.80):
      self.right = 50
      self.up = self.down = self.left = 0 


class Bullet(object):
  id = 0
  r = 0.8
  def __init__(self, world, player, aimX, aimY, ttl):
    x = player.body.position.x
    y = player.body.position.y
    Bullet.id += 1
    self.id = Bullet.id
    self.ttl = ttl
    self.world = world
    self.player = player

    #Create physics shape
    bodyDef = b2BodyDef()
    vel = b2Vec2(aimX, aimY)
    vel.Normalize()
    offset = vel * (player.r+Bullet.r+0.1)
    pos = (x+offset.x, y+offset.y)
    
    self.world.phys_lock.acquire()
    self.body = world.phys.CreateDynamicBody(position=pos, bullet=True, userData=self)
    self.body.CreateCircleFixture(radius=Bullet.r, density=0.01, restitution=0.3)
    self.body.linearVelocity = player.body.linearVelocity
    self.body.ApplyLinearImpulse(5*vel, (x,y))
    self.world.phys_lock.release()
  
  def update(self):
    self.ttl -= 1
    if self.ttl <= 0:
      self.destroy()
    
  def destroy(self):
    self.world.phys_lock.acquire()
    self.world.phys.DestroyBody(self.body)
    self.world.phys_lock.release()
    self.world.bullets.remove(self)
  

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
    
    player = objA if isinstance(objA, Player) else objB if isinstance(objB, Player) else None
    bullet = objA if isinstance(objA, Bullet) else objB if isinstance(objB, Bullet) else None

    if player and bullet:
      damage = abs(impulse.normalImpulses[0] - impulse.normalImpulses[1])
      player.damage(damage)
      if player.health <= 0:
        player.killed_by = bullet.player
        killee = "player" if player.conn else "bot"
        killer = "player" if bullet.player.conn else "bot"
        print "%s %d killed by %s %d" % (killee, player.id, killer, bullet.player.id)

class MaloneContactFilter(b2ContactFilter):
  def __init__(self):
    b2ContactFilter.__init__(self)

  def ShouldCollide(self, fixture1, fixture2):
    obj1 = fixture1.body.userData
    obj2 = fixture2.body.userData
    if (isinstance(obj1, Bullet)):
      if (isinstance(obj2, Player)):
        if obj1.player == obj2:
          return False

    if (isinstance(obj2, Bullet)):
      if (isinstance(obj1, Player)):
        if obj2.player == obj1:
          return False

    return True
