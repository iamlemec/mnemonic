# pull in all wikipedia data

import re
import os
import sys
import argparse
import sqlite3
from lxml import etree
from html.parser import unescape
from db_tools import ChunkInserter

# parse input arguments
parser = argparse.ArgumentParser(description='Wikipedia indexer.')
parser.add_argument('wiki_fname', type=str, help='filename of wikipedia')
parser.add_argument('db_fname', type=str, help='filename of database')
parser.add_argument('--limit', type=int, default=None, help='number of articles to parse')
args = parser.parse_args()

# database
con = sqlite3.connect(args.db_fname)
cur = con.cursor()
cur.execute('create table if not exists title_link (src text, dst text, pos int, frac real)')
cur.execute('create table if not exists page (id int, rev int, date text, length int, title text)')
page_chunker = ChunkInserter(con, 'insert into page values (?,?,?,?,?)', output=False)
link_chunker = ChunkInserter(con, 'insert into title_link values (?,?,?,?)', output=False)

# tag ids
namespace = '{http://www.mediawiki.org/xml/export-0.10/}'
page_tag = namespace + 'page'
id_tag = namespace + 'id'
ns_tag = namespace + 'ns'
title_tag = namespace + 'title'
revn_tag = namespace + 'revision'
text_tag = namespace + 'text'
date_tag = namespace + 'timestamp'

# revert html codes
def html_unescape(text):
    text = unescape(text)
    text = text.replace(u'\xa0',u' ')
    return text

# generate plain vanilla links
def gen_links(wiki):
    for m in re.finditer(r'\[\[([^\]]*)\]\]', wiki):
        t = m.groups()[0]
        x = t.find('|')
        if x >= 0:
            t = t[:x]
        y = t.find('#')
        if y >= 0:
            t = t[:y]
        if len(t) > 0:
            s = m.span()[0]
            yield (t.lower(), s)

# preserve memory
def clear(elem):
    elem.clear()
    while elem.getprevious() is not None:
        del elem.getparent()[0]

# parse wiki pages
i = 0
for (_,page) in etree.iterparse(args.wiki_fname, tag=page_tag, events=['end']):
    aid = int(page.find(id_tag).text)
    ns = int(page.find(ns_tag).text)
    title = page.find(title_tag).text.lower()
    revn = page.find(revn_tag)
    rid = revn.find(id_tag).text
    date = revn.find(date_tag).text
    body = revn.find(text_tag).text

    # only articles
    if ns != 0:
        continue

    # redirects
    if body is None or body.startswith('#'):
        continue

    wiki = html_unescape(body)
    length = len(wiki)
    links = gen_links(wiki)
    page_chunker.insert(aid, rid, date, length, title)
    link_chunker.insertmany([(title, dst, pos, pos/length) for (dst, pos) in links])

    clear(page)

    i += 1
    if i % 100 == 0:
        print('%d, %d: %s' % (i, page.sourceline, title))
    if args.limit and i >= args.limit:
        break

# close out
page_chunker.commit()
link_chunker.commit()
print(i)
print()

# merge into id graph
print('merging into id graph')
cur.execute('create table id_link (src int, dst int, frac real)')
cur.execute("""insert into id_link select src_page.id,dst_page.id,frac from title_link
               left outer join page as src_page on (src = src_page.title)
               left outer join page as dst_page on (dst = dst_page.title)""")
con.commit()
con.close()
