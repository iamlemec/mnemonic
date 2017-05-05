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
    console.log('Error (' + msg + '):' + exception);
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

function make_entry(info) {
    var box = $('<div>',{class: 'tb_box', tid: info['tid'], title: info['title']});
    var span = $('<span>',{class: 'tb_title', html: info['title']});
    box.append(span);
    connectHandlers(box);
    return box;
}

function add_history(info) {
    var found = false;
    hist.find('.tb_box').each(function(i) {
        var box = $(this);
        if (box.attr('tid') == info['tid']) {
            found = true;
        }
    });
    if (!found) {
        var box = make_entry(info);
        hist.prepend(box);
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
          var box = make_entry(bit);
          results.append(box);
        });
        if (cont['done']) {
          results.addClass('done');
        } else {
          results.removeClass('done');
        }
      } else if (cmd == 'text') {
        console.log(cont['tid'],cont['title']);
        output.html(cont['html']);
        output[0].scrollTop = 0;
        output.find('.wikilink').click(function(link) {
          link.preventDefault();
          var href = $(this).text();
          send_command('link',href);
        });
        add_history(cont);
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
    ws_con = 'ws://' + window.location.host + '/fuzzy';
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

$(document).ready(function () {
  results = $('#results');
  query = $('#query');
  output = $('#output');
  hist = $('#history');

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
