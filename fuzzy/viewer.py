import os
import sys
import re
import json
import argparse
import traceback
import operator as op

import tornado.ioloop
import tornado.web
import tornado.websocket

# ag --nobreak --nonumbers --noheading . | sort -u | fzf

# parse input arguments
parser = argparse.ArgumentParser(description='Mnemonic Server.')
parser.add_argument('--path', type=str, help='location of files')
parser.add_argument('--port', type=int, default=9020, help='port to serve on')
args = parser.parse_args()

class EditorHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("editor.html")

class FuzzyHandler(tornado.websocket.WebSocketHandler):
    def initialize(self):
        print("initializing")
        self.results = None

    def allow_draft76(self):
        return True

    def open(self):
        print("connection received")

    def on_close(self):
        print("connection closing")

    def error_msg(self, error_code):
        if not error_code is None:
            json_string = json.dumps({"type": "error", "code": error_code})
            self.write_message("{0}".format(json_string))
        else:
            print("error code not found")

    def on_message(self, msg):
        try:
            print(u'received message: {0}'.format(msg))
        except Exception as e:
            print(e)
        data = json.loads(msg)
        (cmd, cont) = (data['cmd'], data['content'])
        if cmd == 'query':
            try:
                print(cont)
            except Exception as e:
                print(e)
                print(traceddback.format_exc())
        elif cmd == 'text':
            try:
                print(cont)
            except Exception as e:
                print(e)
                print(traceddback.format_exc())

# tornado content handlers
class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", EditorHandler),
            (r"/fuzzy", FuzzyHandler)
        ]
        settings = dict(
            app_name=u"Fuzzy Editor",
            template_path="templates",
            static_path="static",
            xsrf_cookies=True,
        )
        tornado.web.Application.__init__(self, handlers, debug=True, **settings)

# create server
application = Application()
application.listen(args.port)
tornado.ioloop.IOLoop.current().start()

