# pull in all wikipedia data

import re
import argparse
from lxml import etree
from mectools.hyper import progress
import indexer_elast as ix
import wiki_parser as wp

# parse input arguments
parser = argparse.ArgumentParser(description='Nemonic Server.')
parser.add_argument('fname', type=str, help='filename of wikipedia')
parser.add_argument('--index', type=str, default='wikipedia', help='name of elasticsearch index')
parser.add_argument('--per', type=int, default=100000, help='frequency to output progress')
parser.add_argument('--limit', type=int, default=None, help='number of articles to parse')
parser.add_argument('--reset', action='store_true', help='drop existing index')
args = parser.parse_args()

# tag ids
namespace = '{http://www.mediawiki.org/xml/export-0.10/}'
page_tag = namespace + 'page'
ns_tag = namespace + 'ns'
id_tag = namespace + 'id'
title_tag = namespace + 'title'
revn_tag = namespace + 'revision'
date_tag = namespace + 'timestamp'
text_tag = namespace + 'text'

# initialize/open database
con = ix.Connection(index=args.index, timeout=600)
con.create(reset=args.reset)
con.settings(refresh_interval=-1)

# text tools
def reduce_text(text):
    text = re.sub(r'([^\w ]|_)', ' ', text) # remove non-alphanumeric, unicode aware
    text = re.sub(r'\n', ' ', text) # convert newlines to spaces
    text = re.sub(r' {2,}', ' ', text) # compress spaces
    return text.lower().strip()

# robust text extract
def get_text(parent, tag, default=''):
    child = parent.find(tag)
    return (child.text or default) if child is not None else default

# preserve memory
def clear(elem):
    elem.clear()
    while elem.getprevious() is not None:
        del elem.getparent()[0]

# parse wiki pages
def gen_articles():
    for _, page in etree.iterparse(args.fname, tag=page_tag, events=['end']):
        ns = int(get_text(page, ns_tag))
        aid = int(get_text(page, id_tag))
        title = get_text(page, title_tag)
        revn = page.find(revn_tag)
        wiki = get_text(revn, text_tag)
        rid = int(get_text(revn, id_tag))
        date = get_text(revn, date_tag)
        clear(page)

        if ns != 0:
            continue
        if wiki.startswith('#redirect') or wiki.startswith('#REDIRECT'):
            continue

        # text = wp.to_text(wiki)
        text = reduce_text(wiki)

        yield {'aid': aid, 'title': title, 'rid': rid, 'date': date, 'text': text, 'wiki': wiki}

# bulk insert
nart, errs = con.bulk(progress(gen_articles(), per=args.per, limit=args.limit), chunk_size=100)

# start refresh again
con.settings(refresh_interval=None)

# close out
print(f'nart = {nart}, nerr = {len(errs)}')
