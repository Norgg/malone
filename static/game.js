/****** Constants ******/
KEYDOWN = 1;
KEYUP = 2;
MOUSECLICK = 3;

PLAYER_TYPE = 1;
BULLET_TYPE = 2;
DEADED_TYPE = 3;
DEATHSOUND_TYPE = 4;

/***** Globals *******/
var players = {};
var bullets = {};
var myId = 0;
var worldSize = 200;
var deaded = false;


var snds;
var boopBuffer;
var deathsoundBuffer;

/****** Websocket setup ********/
var ws;
var ws_path = "ws://" + window.location.host + "/ws";
if ("WebSocket" in window) {
  ws = new WebSocket(ws_path);
} else if ("MozWebSocket" in window) {
  WebSocket = MozWebSocket;
  ws = new MozWebSocket(ws_path);
} else {
  $('#message').text("sorry, not supported on this browser.");
}

ws.onopen = function() { 
  $('#message').text("wasd/mouse");
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
        var xyr = new Float32Array(fr.result, i, 3);
        i += 12;
        var x = xyr[0];
        var y = xyr[1];
        var r = xyr[2];
        //console.log("At", x, ",", y);
        players[id] = {x: x, y: -y, r: r, keep: true};
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
        ws.close();
      } else if (type == DEATHSOUND_TYPE) {
        if (!muted) {
          var deathsound = snds.createBufferSource();
          deathsound.connect(snds.destination);   
          deathsound.buffer = deathsoundBuffer;
          deathsound.noteOn(0);
        }
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
  ctx.scale(6, 6);
  ctx.translate(-me.x+50, -me.y+50);

  var bg = ctx.createPattern($('#bg')[0], 'repeat');
  ctx.fillStyle=bg;
  ctx.fillRect(-worldSize, -worldSize, worldSize*2, worldSize*2);

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
    ctx.rotate(-player.r);
    
    ctx.fillStyle = "rgba(0, 0, 0, 0.8)";
    ctx.beginPath();
    ctx.arc(0, 0, 2, 0, Math.PI*2, true);
    ctx.fill();


    ctx.shadowBlur = 1;
    if (id == myId) {
      ctx.shadowColor = "yellow";
    } else {
      ctx.shadowColor = "red";
    }

    ctx.fillStyle = "rgba(0, 0, 0, 0.5)";
    ctx.fillRect(-0.1, -2,   0.2, 4);
    ctx.fillRect(-2,   -0.1, 4,   0.2);
    ctx.fillStyle = "black";
    
    ctx.shadowBlur = 0;
    
    ctx.rotate(player.r);
    ctx.translate(-player.x, -player.y);
  }

  ctx.strokeRect(-worldSize, -worldSize, worldSize*2, worldSize*2);

  setTimeout(draw, 15);
}

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

  $('canvas').click({}, function(e) {
    if (ws.readyState == WebSocket.OPEN) {
      var x = e.clientX - $('canvas').offset().left - 300
      var y = 300 - e.clientY + $('canvas').offset().top
      var buffer = new ArrayBuffer(6);
      new Uint8Array(buffer)[0] = MOUSECLICK;
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
  $('canvas')[0].onselectstart = function () { return false; }
});


