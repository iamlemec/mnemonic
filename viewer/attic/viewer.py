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

# what shit
sys.path.append(os.path.abspath('../database'))
import wiki_parser as wp
import indexer_elast as ix

# options
block_size = 25 # result chunk size

# utils
tagsort = lambda x: sorted(x,key=str.lower)
quotes = re.compile(r'\"([^\"]*)\"')

# parse input arguments
parser = argparse.ArgumentParser(description='Mnemonic Server.')
parser.add_argument('--index', type=str, default='wikipedia', help='name of index')
parser.add_argument('--port', type=int, default=9010, help='port to serve on')
args = parser.parse_args()

# initialize connection
con = ix.Connection(index=args.index)

# code generation
wiki_template = """
<h1>{title}</h1>

{body}
"""

class EditorHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("editor.html")

class TidbitHandler(tornado.websocket.WebSocketHandler):
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
        (cmd,cont) = (data['cmd'],data['content'])
        if cmd == 'query':
            try:
                self.results = con.search(cont, size=block_size)
                block = [{'tid': i, 'title': t} for (i, t) in self.results]
                reset = True
                done = (len(block) < block_size)
            except Exception as e:
                print(e)
                print(traceback.format_exc())
                reset = True
                done = True
                block = [{'tid': -1, 'title': 'Error'}]
            self.write_message(json.dumps({'cmd': 'results', 'content': {'reset': reset, 'done': done, 'results': block}}))
        elif cmd == 'moar':
            self.results.next()
            block = [{'tid': i, 'title': t} for (i, t) in self.results]
            reset = False
            done = (len(block) < block_size)
            self.write_message(json.dumps({'cmd': 'results', 'content': {'reset': reset, 'done': done, 'results': block}}))
        elif cmd == 'text':
            try:
                doc = con.fetch(cont)
                title = doc['title']
                wiki = doc['body']
                html = wp.to_html(wiki)
                text = wiki_template.format(title=title,body=html)
                self.write_message(json.dumps({'cmd': 'text', 'content': {'tid': cont, 'title': title, 'html': text}}))
            except Exception as e:
                print(e)
        elif cmd == 'link':
            id = con.link(cont)
            print(id)
            if id is not None:
                doc = con.fetch(id)
                title = doc['title']
                wiki = doc['body']
                html = wp.to_html(wiki)
                text = wiki_template.format(title=title,body=html)
                self.write_message(json.dumps({'cmd': 'text', 'content': {'tid': id, 'title': title, 'html': text}}))

# tornado content handlers
class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", EditorHandler),
            (r"/tidbit", TidbitHandler)
        ]
        settings = dict(
            app_name=u"Tidbit Editor",
            template_path="templates",
            static_path="static",
            xsrf_cookies=True,
        )
        tornado.web.Application.__init__(self, handlers, debug=True, **settings)

# create server
application = Application()
application.listen(args.port)
tornado.ioloop.IOLoop.current().start()

