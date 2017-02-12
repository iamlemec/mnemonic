# pull in all wikipedia data

import re
import os
import sys
import argparse
from lxml import etree

try:
    from HTMLParser import HTMLParser
except ImportError:
    from html.parser import HTMLParser

import indexer as ix

# parse input arguments
parser = argparse.ArgumentParser(description='Mnemonic Server.')
parser.add_argument('wiki_fname',type=str,help='filename of wikipedia')
parser.add_argument('db_fname',type=str,help='filename of database')
parser.add_argument('--limit',type=int,default=None,help='number of articles to parse')
args = parser.parse_args()

# tag ids
namespace = '{http://www.mediawiki.org/xml/export-0.10/}'
page_tag = namespace + 'page'
id_tag = namespace + 'id'
title_tag = namespace + 'title'
revn_tag = namespace + 'revision'
text_tag = namespace + 'text'

# initialize/open database
ix.initialize(args.db_fname)
con = ix.connect(args.db_fname)

# revert html codes
hp = HTMLParser()
def html_unescape(text):
    text = hp.unescape(text)
    text = text.replace(u'\xa0',u' ')
    return text

# compiled regexes
re_punct = re.compile(r'[\.,-\/#!$%\^&\*;:{}=\-_`~()@\+\?><\[\]\+\'\"\|\n–]') # punctuation
re_templ = re.compile(r'{{.*?}}',flags=re.MULTILINE|re.DOTALL) # templates
re_nlink = re.compile(r'\[\[.*:.*\]\]') # named links
re_elink = re.compile(r'\[([^\[\]]*)\]') # external links
re_htmlo = re.compile(r'<[^>]*>') # html open
re_htmlc = re.compile(r'</[^>]*>') # html close

# quick and dirty extraction
def title_smash(text):
    text = re_punct.sub(r' ',text) # remove punctuation
    toks = text.lower().split() # tokenize
    toks = filter(lambda x: len(x)>3,toks) # remove short words
    return toks

def wiki_smash(text):
    text = re_templ.sub(r' ',text) # templates
    text = re_nlink.sub(r' ',text) # named links (includes images)
    text = re_elink.sub(r' ',text) # external links
    text = re_htmlo.sub(r' ',text) # html open
    text = re_htmlc.sub(r' ',text) # html close
    text = re_punct.sub(r' ',text) # remove punctuation
    toks = text.lower().split() # tokenize
    toks = filter(lambda x: len(x)>3,toks) # remove short words
    return toks

# preserve memory
def clear(elem):
    elem.clear()
    while elem.getprevious() is not None:
        del elem.getparent()[0]

# parse wiki pages
i = 0
for (_,page) in etree.iterparse(args.wiki_fname,tag=page_tag,events=['end']):
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
        title_words = title_smash(title)
        body_words = wiki_smash(wiki)
        doc = ix.Document(id=aid,title=title,body=wiki)
        con.insert(doc,title_tags=title_words,body_tags=body_words,commit=False)
    except KeyboardInterrupt as e:
        print('(i = %d) Exiting' % (i,))
        raise(e)
    except Exception as e:
        print('(i = %d) Failed on %s' % (i,title))
        raise(e)

    clear(page)

    i += 1
    if i % 1000 == 0:
        con.commit()
        print(i)
    if args.limit and i >= args.limit:
        break

# close out
con.commit()
print(i)

