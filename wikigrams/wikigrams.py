import os
import sys
import re
import json
import argparse

import numpy as np
import pandas as pd

import tornado.ioloop
import tornado.web
import tornado.websocket

# parse input arguments
parser = argparse.ArgumentParser(description='Mnemonic Server.')
parser.add_argument('dpath', type=str, default='counts', help='path of word counts')
parser.add_argument('--index', type=str, default='token', help='name of index column')
parser.add_argument('--port', type=int, default=9454, help='port to serve on')
args = parser.parse_args()

# functions
norm = lambda x: x/np.sum(x)

# constants
month0 = (2001, 1)
month1 = (2016, 9)
def gen_months():
    (y, m) = month0
    yield (y, m)
    while True:
        m += 1
        if m == 13:
            y += 1
            m = 1
        yield (y, m)
        if (y, m) == month1:
            break
months = list(gen_months())
mstrs = ['%d_%d' % m for m in months]
tvec = ['%d-%02d-01' % m for m in months]
nmon = len(months)

# load in vocab
vpath = '%s/%s' % (args.dpath, 'vocabulary.csv')
voc = pd.read_csv(vpath, index_col=args.index)['index']
print('Loaded vocab.')

# load in counts
counts = pd.DataFrame({ms: pd.read_csv('%s/freq_%s.csv' % (args.dpath, ms), index_col=args.index)['count'] for ms in mstrs})
cumul = counts.cumsum(axis=1)
freqs = cumul.apply(norm)
del counts, cumul
print('Loaded counts.')

# frequency fetcher
def freq_series(tok):
    idx = voc.get(tok)
    if idx is None:
        ser = pd.Series(np.zeros(nmon), name=tok)
    else:
        ser = freqs.ix[idx]
    ser.index = pd.Index(tvec, name='date')
    return ser

class WikigramHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.set_header("Content-Type", 'text/csv')

    def get(self):
        toks = self.get_argument('token').split(',')
        datf = pd.DataFrame({t: freq_series(t.lower()) for t in toks})
        self.write(datf.to_csv(float_format='%.15f'))

    def options(self):
        # no body
        self.set_status(204)
        self.finish()

# tornado content handlers
class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/freq", WikigramHandler),
        ]
        settings = dict(
            app_name='Wikigram Server',
            xsrf_cookies=True,
        )
        tornado.web.Application.__init__(self, handlers, debug=True, **settings)

# create server
application = Application()
application.listen(args.port)
tornado.ioloop.IOLoop.current().start()

