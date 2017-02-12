// Why!?!
Array.prototype.contains = function(obj) {
  var i = this.length;
  while (i--) {
    if (this[i] === obj) {
      return true;
    }
  }
  return false;
}

function send_command(cmd,cont) {
  try {
    var msg = JSON.stringify({'cmd': cmd, 'content': cont});
    ws.send(msg);
    console.log('Sent: ' + msg);
  } catch (exception) {
    console.log('Error (' + txt + '):' + exception);
  }
}

function create_websocket(first_time) {
  ws = new WebSocket(ws_con);

  ws.onopen = function() {
    console.log('websocket connected!');
    if (first_time) {
      // send_command('query','');
    }
  };

  ws.onmessage = function (evt) {
    var msg = evt.data;
    // console.log('Received: ' + msg);

    var json_data = JSON.parse(msg);
    if (json_data) {
      var cmd = json_data['cmd'];
      var cont = json_data['content'];
      if (cmd == 'results') {
        if (cont['reset']) {
          results.empty();
        }
        $(cont['results']).each(function(i,bit) {
          var box = $('<div>',{class: 'tb_box', tid: bit['tid']});
          var span = $('<span>',{class: 'tb_title', html: bit['title']});
          box.append(span);
          connectHandlers(box);
          results.append(box);
        });
        if (cont['done']) {
          results.addClass('done');
        } else {
          results.removeClass('done');
        }
      } else if (cmd == 'text') {
        output.html(cont);
        output[0].scrollTop = 0;
        output.find('.wikilink').click(function(link) {
          link.preventDefault();
          var href = $(this).text();
          send_command('link',href);
        });
      }
    }
  };

  ws.onclose = function() {
    console.log('websocket closed, attempting to reconnect');
    setTimeout(function() {
      create_websocket(false);
    }, 1);
  };
}

function connect()
{
  if ('MozWebSocket' in window) {
    WebSocket = MozWebSocket;
  }
  if ('WebSocket' in window) {
    ws_con = 'ws://' + window.location.host + '/tidbit';
    console.log(ws_con);
    create_websocket(true);
  } else {
    console.log('Sorry, your browser does not support websockets.');
  }
}

function disconnect()
{
  if (ws) {
    ws.close();
  }
}

function connectHandlers(box) {
  box.click(function(event) {
    $('.tb_box').removeClass('selected');
    box.addClass('selected');
    var tid = box.attr('tid');
    send_command('text',tid);
  });
}

$(document).ready(function () {
  results = $('#results');
  query = $('#query');
  output = $('#output');

  connect();

  query.keypress(function(event) {
    if (event.keyCode == 13) {
      var text = query.attr('value');
      send_command('query',text);
      event.preventDefault();
    }
  });

  results.scroll(function() {
    if (!results.hasClass('done')) {
      if (this.scrollHeight - this.scrollTop === this.clientHeight) {
        var msg = JSON.stringify({"cmd": "moar", "content": ""});
        ws.send(msg);
      }
    }
  });

  $(document).unbind('keydown').bind('keydown',function() {
    if (event.keyCode == 8) {
      if (!event.target.getAttribute('contentEditable') && (event.target.tagName.toLowerCase() != 'input')) {
        console.log('rejecting backspace: ',event.target.tagName);
        event.preventDefault();
      }
    }
  });
});
