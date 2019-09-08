import os
import sys
import re
import json
import sqlite3
import argparse
from datetime import datetime, timedelta
from urllib.parse import unquote

import tornado.ioloop
import tornado.web
import tornado.websocket
from tornado.template import Template
from tornado.escape import json_encode, json_decode

# parse input arguments
parser = argparse.ArgumentParser(description='Mnemonic Server.')
parser.add_argument('db_fname', type=str, help='filename of database')
parser.add_argument('--port', type=int, default=9001, help='port to serve on')
parser.add_argument('--utc-offset', type=int, default=-5, help='timezone offset (EST = -5)')
args = parser.parse_args()

# open database
con = sqlite3.connect(args.db_fname)
cur = con.cursor()
cur.execute('create table if not exists view (id integer primary key, lang text, timestamp real, title text)')

# time conversion
todate = lambda ts: timedelta(seconds=ts/1000) + datetime(1970,1,1) - timedelta(hours=args.utc_offset)
tfmt = '%Y-%m-%d %H:%M'

# code generation
view_template = Template("""
<h1>WikiNav</h1>

{% for x in data %}
<div class="entry">{{ x['time'] }}: <a href="{{ x['url'] }}">{{ x['title'] }}</a></div>
{% end %}
""".strip())

class ViewerHandler(tornado.web.RequestHandler):
    def get(self):
        cur = con.cursor()
        ret = cur.execute('select lang,timestamp,title from view order by timestamp desc limit 100')
        data = [{
            'time': todate(s).strftime(tfmt),
            'url': 'https://%s.wikipedia.org/wiki/%s' % (l, t),
            'title': unquote(t)
        } for (l, s, t) in ret]
        self.write(view_template.generate(data=data))

class StoreHandler(tornado.web.RequestHandler):
    def post(self):
        self.set_header("Content-Type", "text/plain")
        data = json_decode(self.request.body)
        ret = re.match('https?://([a-z]{2}).wikipedia.org/wiki/(.*)', data['url'])
        if ret:
            (lang, path) = ret.groups()

            ret = re.match('(^[#]*)#(.*)',path)
            if ret:
                (name,sub) = ret.groups()
            else:
                (name,sub) = (path, None)

            print("%f: %s" % (data['timestamp'], name))

            cur = con.cursor()
            cur.execute('insert into view values (?,?,?,?)', (None, lang, data['timestamp'], name))
            con.commit()

# tornado content handlers
class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", ViewerHandler),
            (r"/store", StoreHandler)
        ]
        settings = dict(
            app_name="WikiNav",
            xsrf_cookies=False,
        )
        tornado.web.Application.__init__(self, handlers, debug=True, **settings)

# create server
application = Application()
application.listen(args.port)
tornado.ioloop.IOLoop.current().start()
