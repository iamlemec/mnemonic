import os
import sys
import re
import json
import argparse
import traceback
import operator as op
import subprocess as sub

import tornado.ioloop
import tornado.web
import tornado.websocket

# ag --nobreak --nonumbers --noheading . | sort -u | fzf

# parse input arguments
parser = argparse.ArgumentParser(description='Mnemonic Server.')
parser.add_argument('--path', type=str, help='location of files')
parser.add_argument('--port', type=int, default=9020, help='port to serve on')
args = parser.parse_args()

# searching
def search(words):
    query = '|'.join(words.split())
    with sub.Popen(['ag', query, args.path], stdout=sub.PIPE) as proc:
        outp, _ = proc.communicate()
        for line in outp.decode().split('\n'):
            if len(line) > 0:
                fpath, line, text = line.split(':', maxsplit=2)
                fname = os.path.basename(fpath)
                yield {'file': fname, 'line': line, 'text': text}

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

    def write_json(self, js):
        self.write_message(json.dumps(js))

    def on_message(self, msg):
        try:
            print(u'received message: {0}'.format(msg))
        except Exception as e:
            print(e)
        data = json.loads(msg)
        (cmd, cont) = (data['cmd'], data['content'])
        if cmd == 'query':
            try:
                print('Query: ' + cont)
                ret = list(search(cont))
                self.write_json({'cmd': 'results', 'content': ret})
            except Exception as e:
                print(e)
                print(traceback.format_exc())
        elif cmd == 'text':
            try:
                print('Text: ' + cont)
                fpath = os.path.join(args.path, cont)
                with open(fpath) as fid:
                    text = fid.read()
                    if text.startswith('!'):
                        if '\n' not in text:
                            text += '\n'
                        head, body = text[1:].split('\n', maxsplit=1)
                        head = head.split()
                        title = ' '.join([s for s in head if not s.startswith('#')])
                        tags = [s[1:] for s in head if s.startswith('#')]
                    else:
                        title = ''
                        tags = []
                    body = body.strip().replace('\n', '<br/>')
                    self.write_json({'cmd': 'text', 'content': {'file': cont, 'title': title, 'tags': tags, 'body': body}})
            except Exception as e:
                print(e)
                print(traceback.format_exc())

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

