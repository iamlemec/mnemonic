import json
import argparse
import traceback
from collections import OrderedDict

import tornado.ioloop
import tornado.web
import tornado.websocket

import search_elast as se
import wiki_parser as wp

# parse input arguments
parser = argparse.ArgumentParser(description='Fuzzy Server.')
parser.add_argument('--ip', type=str, default='127.0.0.1', help='ip address to listen on')
parser.add_argument('--port', type=int, default=9050, help='port to serve on')
args = parser.parse_args()

# hardcoded
max_res = 20

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
    body = ret['wiki']
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
            json_string = json.dumps({'type': 'error', 'code': error_code})
            self.write_message(json_string)
        else:
            print('error code not found')

    def send_command(self, cmd, cont):
        self.write_message(json.dumps({'cmd': cmd, 'content': cont}))

    @authenticated
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
            (r'/', EditorHandler),
            (r'/data', DataHandler),
        ]
        settings = dict(
            app_name='Nemonic',
            template_path='templates',
            static_path='static',
            cookie_secret=cookie_secret
        )
        tornado.web.Application.__init__(self, handlers, debug=True, **settings)

# create server
application = Application()
application.listen(args.port, address=args.ip)
tornado.ioloop.IOLoop.current().start()
