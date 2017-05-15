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

function set_caret_at_end(element) {
    element.focus();
    var range = document.createRange();
    range.selectNodeContents(element);
    range.collapse(false);
    var sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
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

function select_entry(box) {
    $('.res_box').removeClass('selected');
    box.addClass('selected');
    var newfile = box.attr('file');
    if (newfile == file) {
        return;
    }
    send_command('text', newfile);
}

function connectHandlers(box) {
    box.click(function(event) {
        select_entry(box);
    });
}

function render_entry(info) {
    var name = '<span class="res_name">' + info['file'] + ' - ' + info['line'] + '</span>';
    var text = info['text'];
    var box = $('<div>', {class: 'res_box', file: info['file'], line: info['line']});
    var span = $('<span>', {class: 'res_title', html: name + '<br/>' + text});
    box.append(span);
    connectHandlers(box);
    return box;
}

function render_tag(label) {
    var lab = $('<span>', {class: 'tag_lab', html: label});
    var del = $('<span>', {class: 'tag_del', html: '&#x2716;'});
    var tag = $('<span>', {class: 'tag_box'});
    tag.append(lab);
    tag.append(del);
    del.click(function(event) {
        tag.remove();
        output.addClass('modified');
        output.focus();
    });
    return tag;
}

function render_results(res) {
    results.empty();
    $(res).each(function(i, bit) {
        var box = render_entry(bit);
        results.append(box);
    });
}

function render_output(info) {
    title.html(info['title']);
    tags.empty();
    $(info['tags']).each(function(i,s) {
        tags.append(render_tag(s));
        tags.append(' ');
    });
    body.html(info['body']);
}


function create_tag(box) {
    var tag = render_tag('');
    tags.append(tag);
    tags.append(' ');
    output.addClass('modified');
    var lab = tag.children(".tag_lab");
    var del = tag.children(".tag_del");
    lab.attr('contentEditable', 'true');
    set_caret_at_end(lab[0]);
    lab.keydown(function(event) {
        if (event.keyCode == 13) {
            lab.attr('contentEditable', 'false');
            body.focus();
            event.preventDefault();
        }
    });
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
    var tag = tags.find('.tag_lab').map(function(i, t) { return t.innerHTML; } ).toArray();
    var bod = strip_tags(body.html());
    if (file == null) {
        file = tit.toLowerCase().replace(/\W/g, '_');
    }
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
    newdoc = $('#newdoc');

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

    newdoc.click(function(event) {
        file = null;
        render_output({
            'title': 'Title',
            'tags': [],
            'body': ''
        });
    });

    output.keypress(function(event) {
        console.log(event.keyCode);
        console.log(event.metaKey);
        console.log(event.shiftKey);
        if (((event.keyCode == 10) || (event.keyCode == 13)) && event.shiftKey) {
            if (output.hasClass('modified')) {
                save_output();
            }
            event.preventDefault();
        } else if (((event.keyCode == 10) || (event.keyCode == 13)) && event.metaKey) {
            create_tag();
        } else if (event.keyCode == 27) {
            if (output.hasClass('modified')) {
                revert();
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

