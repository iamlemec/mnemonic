###
### generate wikipedia word frequency series
###

# python3 tab_wikidiff.py ../categories/fields/field_diff.csv fields/wik_field_freq vocab=lit_freq/vocabulary.csv

import os
import re
import sqlite3
import argparse
import numpy as np
import pandas as pd
import sklearn.feature_extraction.text as fe
from collections import defaultdict
from itertools import product

# options
parser = argparse.ArgumentParser(description='Word frequency tabulator.')
parser.add_argument('dpath', type=str, help='filename of diffs')
parser.add_argument('outdir', type=str, help='directory to write to')
parser.add_argument('--vocab', type=str, default='../data/csv/vocab.csv', help='vocabulary file')
parser.add_argument('--chunk', type=int, default=1000000, help='chunk size to use')
args = parser.parse_args()

# constants
(ymin,ymax) = (2001,2016) # year range
months = list(product(range(ymin,ymax+1),range(1,12+1)))

# tools
slim = lambda x: np.asarray(x).squeeze()

# ensure output dir
if not os.path.isdir(args.outdir):
    os.mkdir(args.outdir)

# load in vocabulary
vocab = pd.read_csv(args.vocab, na_values=[], keep_default_na=False)['index']
nvoc = len(vocab)

# compute word counts over entire corpus
tfidf = fe.CountVectorizer(vocabulary=vocab)
counts = {'%d_%d' % ym: np.zeros(nvoc, dtype=np.int) for ym in months}
for fname in os.listdir(args.dpath):
    print(fname)
    fpath = '%s/%s' % (args.dpath, fname)
    for (i, chunk) in enumerate(pd.read_csv(fpath, chunksize=args.chunk, usecols=[2, 5], names=['time', 'words'])):
        print(i)

        date = chunk['time'].values
        toks = chunk['words'].fillna('').values

        # count words
        words = tfidf.fit_transform(toks)

        # monthly data
        info = pd.DataFrame({'date': pd.to_datetime(date)})
        info['year'] = info['date'].dt.year
        info['month'] = info['date'].dt.month

        # store in month bins
        for (y, m) in months:
            ms = '%d_%d' % (y, m)
            idx = list(info.query('year == %d and month == %d' % (y, m)).index)
            more = slim(words[idx,:].sum(axis=0))
            counts[ms] += more

# aggregate to higher levels
total = sum(counts.values())

# store data
print('storing frequency data')
pd.Series(tfidf.vocabulary_).to_csv('%s/vocabulary.csv' % args.outdir, index_label='token', header=['index'])
pd.Series(total).to_csv('%s/freq_total.csv' % args.outdir, index_label='token', header=['count'])
for (k, v) in counts.items():
    pd.Series(v).to_csv('%s/freq_%s.csv' % (args.outdir, k), index_label='token', header=['count'])

