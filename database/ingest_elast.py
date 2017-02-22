# pull in all wikipedia data

import re
import os
import sys
import argparse
from lxml import etree
from html.parser import HTMLParser
import indexer_elast as ix

# parse input arguments
parser = argparse.ArgumentParser(description='Nemonic Server.')
parser.add_argument('wiki_fname', type=str, help='filename of wikipedia')
parser.add_argument('--index', type=str, default='wikipedia', help='name of elasticsearch index')
parser.add_argument('--limit', type=int, default=None, help='number of articles to parse')
parser.add_argument('--reset', action='store_true', help='drop existing index')
args = parser.parse_args()

# tag ids
namespace = '{http://www.mediawiki.org/xml/export-0.10/}'
page_tag = namespace + 'page'
id_tag = namespace + 'id'
title_tag = namespace + 'title'
revn_tag = namespace + 'revision'
text_tag = namespace + 'text'

# initialize/open database
con = ix.Connection(index=args.index)
con.create(reset=args.reset)

# revert html codes
hp = HTMLParser()
def html_unescape(text):
    text = hp.unescape(text)
    text = text.replace(u'\xa0', u' ')
    return text

# preserve memory
def clear(elem):
    elem.clear()
    while elem.getprevious() is not None:
        del elem.getparent()[0]

# parse wiki pages
i = 0
for (_,page) in etree.iterparse(args.wiki_fname, tag=page_tag, events=['end']):
    aid = int(page.find(id_tag).text)
    title = page.find(title_tag).text
    revn = page.find(revn_tag)
    body = revn.find(text_tag).text

    if body is None or body.startswith('#redirect') or body.startswith('#REDIRECT'):
        continue
    if title.startswith('Wikipedia') or title.startswith('Talk:') or \
       title.startswith('User:') or title.startswith('User talk:') or \
       title.startswith('Category:') or title.startswith('Category talk:') or \
       title.startswith('Template:') or title.startswith('File:'):
        continue

    try:
        wiki = html_unescape(body)
        con.insert(aid, title, wiki)
    except KeyboardInterrupt as e:
        print('(i = %d) Exiting' % (i,))
        raise(e)
    except Exception as e:
        print('(i = %d) Failed on %s' % (i, title))
        raise(e)

    clear(page)

    i += 1
    if i % 1000 == 0:
        print(i)
    if args.limit and i >= args.limit:
        break

# close out
print(i)

