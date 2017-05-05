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
    var file = box.attr('file');
    send_command('text',file);
  });
}

function make_entry(info) {
    console.log(info);
    var box = $('<div>',{class: 'res_box', file: info['file'], line: info['line']});
    var span = $('<span>',{class: 'res_title', html: info['file'] + '[' + info['line'] + ']' + ': ' + info['text']});
    box.append(span);
    connectHandlers(box);
    return box;
}

function make_output(info) {
    var tags = info['tags'].map(function(s) { return '#' + s; }).join(' ');
    var title = $('<span>',{class: 'out_title', html: info['title'], contentEditable: true});
    var tags = $('<span>',{class: 'out_tags'});
    $(info['tags']).each(function(i,s) { tags.append($('<span>',{class: 'out_tag', html: s})); });
    var head = $('<div>',{class: 'out_head'});
    head.append(title);
    head.append(tags);
    var body = $('<div>',{class: 'out_body', html: info['body'], contentEditable: true});
    var box = $('<div>');
    box.append(head);
    box.append(body);
    return box;
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
    console.log('Received: ' + msg);

    var json_data = JSON.parse(msg);
    if (json_data) {
      var cmd = json_data['cmd'];
      var cont = json_data['content'];
      if (cmd == 'results') {
        results.empty();
        $(cont).each(function(i,bit) {
          var box = make_entry(bit);
          results.append(box);
        });
        if (cont['done']) {
          results.addClass('done');
        } else {
          results.removeClass('done');
        }
      } else if (cmd == 'text') {
        console.log(cont['file']);
        var box = make_output(cont);
        console.log(box);
        output.empty();
        output.append(box);
        output[0].scrollTop = 0;
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
  query.focus();

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
