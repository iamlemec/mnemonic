import re
import os
import argparse
import sqlite3
from collections import OrderedDict
from html import unescape
from unicodedata import normalize

# parse input arguments
parser = argparse.ArgumentParser(description='Tidbit Converter.')
parser.add_argument('db_fname', type=str, help='filename of database')
parser.add_argument('out_dir', type=str, help='directory to store files')
args = parser.parse_args()

# html tag stripper
def strip_tags(html):
    html = normalize('NFKD', unescape(html))
    html = re.sub(r'^<div>', '', html)
    html = re.sub(r'<div><br></div>', '\n', html)
    html = re.sub(r'</div>', '', html)
    html = re.sub(r'<br>', '\n', html)
    html = re.sub(r'<div ?.*?>', '\n', html)
    html = re.sub(r'<span ?.*?>', '', html)
    html = re.sub(r'</span>', '', html)
    return html.strip()

def title_smash(s):
    s = s.lower()
    s = re.sub(r'\W', '_', s)
    s = re.sub(r'_{2,}', '_', s)
    s = s.strip('_')
    return s

# load in data
con = sqlite3.connect(args.db_fname)
data = con.execute('select * from tidbit').fetchall()
con.close()

# group data by ids
info = OrderedDict()
for id, field, value in data:
    if id not in info:
        info[id] = {'tags': [], 'timestamp': 0}
    if field == 'tag':
        info[id]['tags'].append(value)
    elif field == 'timestamp':
        info[id]['timestamp'] = float(value)
    elif field in ['title', 'body']:
        info[id][field] = strip_tags(value)

# write to files
for block in  sorted(info.values(), key=lambda x: x['timestamp']):
    text = ''
    text += '!' + block['title'] + ' ' + ' '.join(['#'+t for t in block['tags']]) + '\n'
    text += '\n'
    text += block['body']

    fname = title_smash(block['title'])
    fpath = os.path.join(args.out_dir, fname)
    with open(fpath, 'w+') as fid:
        fid.write(text)

