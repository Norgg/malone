/****** Constants ******/
var KEYDOWN = 1;
var KEYUP = 2;
var LEFT_MOUSE_CLICK = 3;
var RIGHT_MOUSE_CLICK = 4;

var PLAYER_TYPE = 1;
var BULLET_TYPE = 2;
var DEADED_TYPE = 3;
var DEATHSOUND_TYPE = 4;

var WORLD_SIZE = 200;

/****** Other Globals *******/
var players = {};
var bullets = {};
var myId = 0;
var deaded = false;

var snds;
var boopBuffer;
var deathsoundBuffer;

var ws;
var wsPath = "ws://" + window.location.host + "/ws";

var zoom = 4;

/****** Init *******/
$(function() {
  if (muted) { $('#mute').text("unmute"); }
  
  if ("webkitAudioContext" in window) {
    snds = new webkitAudioContext();
    
    var request = new XMLHttpRequest();
    request.open("GET", "boop2.ogg", true);
    request.responseType = "arraybuffer";
    request.onload = function() { 
      boopBuffer = snds.createBuffer(request.response, true);
    }
    request.send();

    var dRequest = new XMLHttpRequest();
    dRequest.open("GET", "death.ogg", true);
    dRequest.responseType = "arraybuffer";
    dRequest.onload = function() { 
      deathsoundBuffer = snds.createBuffer(dRequest.response, true);
    }
    dRequest.send();
  } else {
    $('#mute').hide();
    muted = true;
  }

  document.body.onkeydown = function(e) {
    if (ws.readyState == WebSocket.OPEN) {
      ws.send(new Uint8Array([KEYDOWN, e.keyCode]).buffer);
    }
  }
  document.body.onkeyup = function(e) {
    if (ws.readyState == WebSocket.OPEN) {
      ws.send(new Uint8Array([KEYUP, e.keyCode]).buffer);
    }
  }

  $('canvas').mousedown({}, function(e) {
    if (ws.readyState == WebSocket.OPEN) {
      var x = e.clientX - $('canvas').offset().left - 300
      var y = 300 - e.clientY + $('canvas').offset().top
      var buffer = new ArrayBuffer(6);
      if (e.which == 1) {
        new Uint8Array(buffer)[0] = LEFT_MOUSE_CLICK;
      } else if (e.which == 3) {
        new Uint8Array(buffer)[0] = RIGHT_MOUSE_CLICK;
      } else {
        return;
      }

      new Uint16Array(buffer)[1] = x;
      new Uint16Array(buffer)[2] = y;
      ws.send(buffer);
      e.stopImmediatePropagation();

      if (!muted) {
        var boop = snds.createBufferSource();
        boop.connect(snds.destination);   
        boop.buffer = boopBuffer;
        var r = Math.random();
        var cents = 600.0 * (r - 0.5);
        var rate = Math.pow(2.0, cents / 1200.0);
        boop.playbackRate.value = rate;
        boop.noteOn(0);
      }
    }
  })

  //Stop double-clicking from selecting anything else other than the canvas.
  $('canvas')[0].onselectstart = function () { return false; }

  //Disable right-click menu
  $('canvas').bind("contextmenu",function(e){
    return false;
  });
});

/****** Websocket setup ********/
if ("WebSocket" in window) {
  ws = new WebSocket(wsPath);
} else if ("MozWebSocket" in window) {
  WebSocket = MozWebSocket;
  ws = new MozWebSocket(wsPath);
} else {
  $('#message').text("sorry, not supported on this browser.");
}

ws.onopen = function() { 
  $('#message').text("left/right mouse");
  $('canvas').show();
  console.log("Opened.");
  draw();
};
ws.onclose = function() { 
  if (!deaded) {
    $('#message').html('oh no. <a href="#" onclick="window.location.reload();">retry?</a>'); 
    //setTimeout(function(){window.location.reload();}, 4000);
  }
};
ws.onerror = function(e) { console.log("ERROR: ", e.data); };


/******* Message handling ********/
ws.onmessage = function(e) {
  fr = new FileReader()
  fr.readAsArrayBuffer(e.data)
  fr.onloadend = function(ev) {
    if (!fr.result) return;
    
    var i = 0
    while (i < fr.result.byteLength) {

      var type = new Uint16Array(fr.result, i, 1)[0];
      i+=2;

      //console.log("Type: ", type);
      //console.log(fr.result.byteLength);

      if (type == PLAYER_TYPE) {
        var id = new Uint16Array(fr.result, i, 1)[0]; 
        i += 2;
        //console.log("Player", id);
        var xyr = new Float32Array(fr.result, i, 4);
        i += 12;
        var x = xyr[0];
        var y = xyr[1];
        var angle = xyr[2];
        var r = xyr[3];
        //console.log("At", x, ",", y);
        players[id] = {x: x, y: -y, angle: angle, r: r, keep: true};
        myId = id; //This player will be last in list.
      } else if (type == BULLET_TYPE) {
        var id = new Uint16Array(fr.result, i, 1)[0]; 
        i += 2;
        var xyr = new Float32Array(fr.result, i, 2);
        i += 8;
        var x = xyr[0];
        var y = xyr[1];
        bullets[id] = {x: x, y: -y, keep: true};
      } else if (type == DEADED_TYPE) {
        $('#message').html("dead: <a href='#' onclick='window.location.reload();'>reload</a> ⇛ respawn.");
        deaded = true;
        playDeathSound();
        ws.close();
      } else if (type == DEATHSOUND_TYPE) {
        var id = new Uint16Array(fr.result, i, 1)[0]; 
        i += 2;
        playDeathSound();
      }
    }

    for (var id in bullets) {
      bullet = bullets[id];
      if (!bullet.keep) delete bullets[id];
      bullet.keep = false
    }

    for (var id in players) {
      player = players[id];
      if (!player.keep) delete players[id];
      player.keep = false
    }
  }
};

var muted = document.cookie.indexOf("muted") > 0;
function mute() {
  if (muted) {
    document.cookie = "sound=on";
    muted=false;
    $('#mute').text("mute");
  } else {
    document.cookie = "sound=muted";
    muted=true;
    $('#mute').text("unmute");
  }
}

function playDeathSound() {
  if (!muted) {
    var deathsound = snds.createBufferSource();
    deathsound.connect(snds.destination);   
    deathsound.buffer = deathsoundBuffer;
    var r = Math.random();
    var cents = 600.0 * (r - 0.5);
    var rate = Math.pow(2.0, cents / 1200.0);
    deathsound.noteOn(0);
  }
}

/***** Draw loop ******/
function draw() {
  var canvas = $('canvas')[0];
  var ctx = canvas.getContext('2d');
  var me = players[myId]; 
  
  if (deaded) {
    ctx.fillStyle = "rgba(150, 0, 0, 0.1)";
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    setTimeout(draw, 15);
    return;
  }

  if (!me) {
    setTimeout(draw, 15);
    return;
  }
  //Reset canvas
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.scale(zoom, zoom);
  ctx.translate(-me.x+canvas.width/2/zoom, -me.y+canvas.height/2/zoom);

  var bg = ctx.createPattern($('#bg')[0], 'repeat');
  ctx.fillStyle=bg;
  ctx.fillRect(-WORLD_SIZE, -WORLD_SIZE, WORLD_SIZE*2, WORLD_SIZE*2);

  ctx.fillStyle = "rgba(150, 0, 0, 0.8)";
  for (var id in bullets) {
    var bullet = bullets[id];
    ctx.beginPath();
    ctx.arc(bullet.x, bullet.y, 0.8, 0, Math.PI*2, true);
    ctx.fill();
  }

  for (var id in players) {
    var player = players[id];
    
    ctx.translate(player.x, player.y);
    ctx.rotate(-player.angle);
    
    ctx.fillStyle = "rgba(0, 0, 0, 0.8)";
    ctx.beginPath();
    ctx.arc(0, 0, player.r, 0, Math.PI*2, true);
    ctx.fill();


    ctx.shadowBlur = 1;
    if (id == myId) {
      ctx.shadowColor = "yellow";
    } else {
      ctx.shadowColor = "red";
    }

    ctx.fillStyle = "rgba(0, 0, 0, 0.5)";
    ctx.fillRect(-0.1, -player.r,   0.2, 2*player.r);
    ctx.fillRect(-player.r,   -0.1, 2*player.r,   0.2);
    ctx.fillStyle = "black";
    
    ctx.shadowBlur = 0;
    
    ctx.rotate(player.angle);
    ctx.translate(-player.x, -player.y);
  }

  ctx.strokeRect(-WORLD_SIZE, -WORLD_SIZE, WORLD_SIZE*2, WORLD_SIZE*2);

  setTimeout(draw, 15);
}



