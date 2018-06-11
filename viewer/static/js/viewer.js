/* fuzzy editor */

// tools
function is_editable(element) {
    return (event.target.getAttribute('contentEditable') || (event.target.tagName.toLowerCase() == 'input'));
}

function scroll_top() {
    output[0].scrollTop = 0;
}

// scroll cell into view
var scrollSpeed = 100;
var scrollFudge = 100;
function ensure_visible(element) {
    var res_top = results.offset().top;
    var cell_top = results.scrollTop() + element.offset().top;
    var cell_bot = cell_top + element.height();
    var page_top = results.scrollTop() + res_top;
    var page_bot = page_top + results.innerHeight();
    if (cell_top < page_top + 20) {
        results.stop();
        results.animate({scrollTop: cell_top - res_top - scrollFudge}, scrollSpeed);
    } else if (cell_bot > page_bot - 20) {
        results.stop();
        results.animate({scrollTop: cell_bot - res_top - results.innerHeight() + scrollFudge}, scrollSpeed);
    }
}

function send_command(cmd, cont) {
    var msg = JSON.stringify({'cmd': cmd, 'content': cont});
    ws.send(msg);
    console.log('Sent: ' + cmd);
}

function select_entry(box) {
    $('.res_box').removeClass('selected');
    box.addClass('selected');
    ensure_visible(box);
    var aid = box.attr('aid');
    if (aid != current) {
        send_command('load', aid);
    }
}

function ensure_active() {
    if (!active) {
        fuzzy.addClass('active');
        active = true;
    }
}

function ensure_inactive() {
    if (active) {
        title.empty();
        body.empty();
        fuzzy.removeClass('active');
        active = false;
    }
}

function render_entry(info) {
    var aid = info['aid'];
    var title = info['title'];
    var box = $('<div>', {class: 'res_box', aid: aid});
    var span = $('<span>', {class: 'res_title', html: title});
    box.append(span);
    box.click(function(event) {
        select_entry(box);
        return false;
    });
    return box;
}

function render_results(res) {
    results.empty();
    $(res).each(function(i, bit) {
        var box = render_entry(bit);
        results.append(box);
    });
}

function render_output(info) {
    ensure_active();
    title.html(info['title']);
    body.html(info['body']);
}

function create_websocket(first_time) {
    ws = new WebSocket(ws_con);

    ws.onopen = function() {
        console.log('websocket connected!');
    };

    ws.onmessage = function (evt) {
        var msg = evt.data;
        // console.log('Received: ' + msg);

        var json_data = JSON.parse(msg);
        if (json_data) {
            var cmd = json_data['cmd'];
            var cont = json_data['content'];
            if (cmd == 'results') {
                render_results(cont);
                results[0].scrollTop = 0;
            } else if (cmd == 'text') {
                render_output(cont);
                scroll_top();
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
        ws_con = 'ws://' + window.location.host + '/data';
        console.log(ws_con);
        create_websocket(true);
    } else {
        console.log('Sorry, your browser does not support websockets.');
    }
}

$(document).ready(function () {
    fuzzy = $('#fuzzy');
    results = $('#results');
    query = $('#query');
    output = $('#output');
    head = $('#head');
    body = $('#body');
    title = $('#title');

    // global states
    current = -1;
    active = false;

    // connect handlers
    connect();
    query.focus();

    query.keypress(function(event) {
        if (event.keyCode == 13) { // return
            var text = query.val();
            send_command('query', text);
            return false;
        }
    });

    $(document).unbind('keydown').bind('keydown', function(event) {
        if (event.keyCode == 8) {
            if (!is_editable(event.target)) {
                console.log('rejecting editing key: ', event.target.tagName.toLowerCase());
                return false;
            }
        }
        if (event.target.id == 'query') {
            if (event.keyCode == 9) {
                return false;
            }
            if ((event.keyCode == 38) || (event.keyCode == 40)) {
                var box = $('.res_box.selected');
                var other;
                if (event.keyCode == 40) { // down
                    if (box.length == 0) {
                        other = $('.res_box:first-child');
                    } else {
                        other = box.next();
                    }
                } else if (event.keyCode == 38) { // up
                    if (box.length == 0) {
                        return;
                    } else {
                        other = box.prev();
                    }
                }
                if (other.length > 0) {
                    select_entry(other);
                }
                return false;
            } else if (event.keyCode == 33) { // pgup
                output.stop(true, true);
                output.animate({ scrollTop: output.scrollTop() - 300 }, 200);
                return false;
            } else if (event.keyCode == 34) { // pgdn
                output.stop(true, true);
                output.animate({ scrollTop: output.scrollTop() + 300 }, 200);
                return false;
            }
        }
    });

    $(document).unbind('click').bind('click', function(event) {
        query.focus();
        return false;
    });
});
