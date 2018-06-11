import os
import json
import argparse
import traceback
from collections import OrderedDict

import tornado.ioloop
import tornado.web
import tornado.websocket

from ..database import search_elast as se
from ..database import wiki_parser as wp

# portable
root = os.path.dirname(__file__)

# searching
def make_result(info):
    return {s: info[s] for s in ['aid', 'title']}

def search(terms, block=True):
    ret = se.search_title(terms)
    return [make_result(x) for x in ret]

# input
def load_entry(aid):
    ret = se.get_by_id(aid)
    title = ret['title']
    wiki = ret['wiki']
    body = wp.to_html(wiki)
    return {'title': title, 'body': body}

class ViewerHandler(tornado.web.RequestHandler):
    def get(self):
        self.render('viewer.html')

class DataHandler(tornado.websocket.WebSocketHandler):
    def initialize(self):
        print('initializing')

    def allow_draft76(self):
        return True

    def open(self):
        print('connection received')

    def on_close(self):
        print('connection closing')

    def error_msg(self, error_code):
        if error_code is not None:
            self.send_command('error', error_code)
        else:
            print('error code not found')

    def send_command(self, cmd, cont):
        self.write_message(json.dumps({'cmd': cmd, 'content': cont}))

    def on_message(self, msg):
        data = json.loads(msg)
        cmd, cont = data['cmd'], data['content']

        if cmd == 'query':
            try:
                print('Query: %s' % cont)
                ret = search(cont)
                self.send_command('results', ret)
            except Exception as e:
                print(e)
                print(traceback.format_exc())
        elif cmd == 'load':
            try:
                print('Loading: %s' % cont)
                info = load_entry(cont)
                self.send_command('text', info)
            except Exception as e:
                print(e)
                print(traceback.format_exc())

# tornado content handlers
class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r'/', ViewerHandler),
            (r'/data', DataHandler),
        ]
        settings = dict(
            app_name='Nemonic',
            template_path=os.path.join(root, 'templates'),
            static_path=os.path.join(root, 'static'),
        )
        tornado.web.Application.__init__(self, handlers, debug=True, **settings)

# create server
def start_server(ip='127.0.0.1', port=9050):
    application = Application()
    application.listen(port, address=ip)
    tornado.ioloop.IOLoop.current().start()
