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

// escaping
function strip_tags(html) {
    return html.replace(/<div ?.*?>/g, '')
               .replace(/<\/div>/g, '\n')
               .replace(/<br>/g, '\n')
               .replace(/<span ?.*?>/g, '')
               .replace(/<\/span>/g, '');
};

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
        $('.res_box').removeClass('selected');
        box.addClass('selected');
        var newfile = box.attr('file');
        if (newfile == file) {
            return;
        }
        send_command('text', newfile);
    });
}

function render_entry(info) {
    console.log(info);
    var box = $('<div>',{class: 'res_box', file: info['file'], line: info['line']});
    var span = $('<span>',{class: 'res_title', html: info['file'] + '[' + info['line'] + ']' + ': ' + info['text']});
    box.append(span);
    connectHandlers(box);
    return box;
}

function render_tag(label) {
    return $('<span>',{class: 'out_tag', html: label});
}

function render_results(res) {
    results.empty();
    $(res).each(function(i,bit) {
        var box = render_entry(bit);
        results.append(box);
    });
}

function render_output(info) {
    title.html(info['title']);
    tags.empty();
    $(info['tags']).each(function(i,s) { tags.append(render_tag(s)); });
    body.html(info['body']);
}

function create_websocket(first_time) {
    ws = new WebSocket(ws_con);

    ws.onopen = function() {
        console.log('websocket connected!');
    };

    ws.onmessage = function (evt) {
        var msg = evt.data;
        console.log('Received: ' + msg);

        var json_data = JSON.parse(msg);
        if (json_data) {
            var cmd = json_data['cmd'];
            var cont = json_data['content'];
            if (cmd == 'results') {
                render_results(cont);
                results[0].scrollTop = 0;
            } else if (cmd == 'text') {
                render_output(cont);
                file = cont['file'];
                output.removeClass('modified');
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

function save_output(box) {
    var tit = title.text();
    var tag = tags.find('.out_tag').map(function(i, t) { return t.innerHTML; } ).toArray();
    var bod = strip_tags(body.html());
    send_command('save', {'file': file, 'title': tit, 'tags': tag, 'body': bod});
    output.removeClass('modified');
}

$(document).ready(function () {
    results = $('#results');
    query = $('#query');
    output = $('#output');
    head = $('#head');
    body = $('#body');
    title = $('#title');
    tags = $('#tags');

    file = null;

    connect();
    query.focus();

    query.keypress(function(event) {
        if (event.keyCode == 13) {
            var text = query.attr('value');
            send_command('query', text);
            event.preventDefault();
        }
    });

    output.keypress(function(event) {
        if ((event.keyCode == 13) && event.shiftKey) {
            if (output.hasClass('modified')) {
                save_output();
            }
            event.preventDefault();
        } else if ((event.keyCode == 13) && event.metaKey) {
            new_tag(box);
        } else if (event.keyCode == 27) {
            if (output.hasClass('modified')) {
                revert_box(box);
            }
        }
    });

    title.keydown(function(event) {
        if (event.keyCode == 13) {
            if (!event.shiftKey) {
                event.preventDefault();
            }
        }
    });

    output.bind('input', function() {
        output.addClass('modified');
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

