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

import parser as ps
import indexer as ix

# options
block_size = 25 # result chunk size

# utils
tagsort = lambda x: sorted(x,key=str.lower)
quotes = re.compile(r'\"([^\"]*)\"')

# parse input arguments
parser = argparse.ArgumentParser(description='Mnemonic Server.')
parser.add_argument('db_fname', type=str, help='filename of database')
parser.add_argument('--port', type=int, default=9001, help='port to serve on')
args = parser.parse_args()

# initialize/open database
con = ix.connect(args.db_fname)

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
                self.results = con.search(cont)
                ids = self.results.fetchmany(block_size)
                block = [{'tid': i, 'title': con.fetch_title(i)} for i in ids]
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
            ids = self.results.fetchmany(block_size)
            block = [{'tid': i, 'title': con.fetch_title(i)} for i in ids]
            reset = False
            done = (len(block) < block_size)
            self.write_message(json.dumps({'cmd': 'results', 'content': {'reset': reset, 'done': done, 'results': block}}))
        elif cmd == 'text':
            try:
                doc = con.fetch(cont)
                html = ps.to_html(doc.body)
                text = wiki_template.format(title=doc.title,body=html)
                self.write_message(json.dumps({'cmd': 'text', 'content': text}))
            except Exception as e:
                print(e)
        elif cmd == 'link':
            id = con.link(cont)
            if id is not None:
                doc = con.fetch(id)
                text = wiki_template.format(title=doc.title,body=doc.body)
                self.write_message(json.dumps({'cmd': 'text', 'content': text}))

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
