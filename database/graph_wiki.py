# pull in all wikipedia data

import re
import os
import sys
import argparse
import sqlite3
from lxml import etree
from html.parser import unescape
import graph_tool as gt
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
cur.execute('create table if not exists page (id int, rev int, date text, type int, length int, title text)')
cur.execute('create table if not exists redirect (src text, dst text)')
page_chunker = ChunkInserter(con, 'insert into page values (?,?,?,?,?,?)', output=False)
link_chunker = ChunkInserter(con, 'insert into title_link values (?,?,?,?)', output=False)
redir_chunker = ChunkInserter(con, 'insert into redirect values (?,?)', output=False)

# tag ids
namespace = '{http://www.mediawiki.org/xml/export-0.10/}'
page_tag = namespace + 'page'
id_tag = namespace + 'id'
ns_tag = namespace + 'ns'
title_tag = namespace + 'title'
redir_tag = namespace + 'redirect'
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
o = 0
r = 0
a = 0
for (_,page) in etree.iterparse(args.wiki_fname, tag=page_tag, events=['end']):
    aid = int(page.find(id_tag).text)
    ns = int(page.find(ns_tag).text)
    title = page.find(title_tag).text.lower()
    redir = page.find(redir_tag)
    revn = page.find(revn_tag)
    rid = revn.find(id_tag).text
    date = revn.find(date_tag).text
    body = revn.find(text_tag).text

    length = len(body)

    if ns != 0:
        o += 1
        atype = 2
    elif redir is not None:
        r += 1
        atype = 1
        targ = redir.get('title').lower()
        if title != targ:
            redir_chunker.insert(title, targ)
    else:
        a += 1
        atype = 0
        wiki = html_unescape(body)
        links = gen_links(wiki)
        link_chunker.insertmany([(title, dst, pos, pos/length) for (dst, pos) in links])

    page_chunker.insert(aid, rid, date, atype, length, title)

    clear(page)

    i += 1
    if i % 100 == 0:
        print('%12d: i = %8d, a = %8d, r = %8d, o = %8d, title = %s' % (page.sourceline, i, a, r, o, title))
    if args.limit and i >= args.limit:
        break

# close out
page_chunker.commit()
link_chunker.commit()
redir_chunker.commit()
print(i)
print()

# merge into id graph
print('merging pages into id graph')
cur.execute('create table id_link (src int, dst int, frac real)')
cur.execute("""insert into id_link select src_page.id,dst_page.id,frac from title_link
               left outer join page as src_page on (src = src_page.title)
               left outer join page as dst_page on (dst = dst_page.title)""")
print('merging redirects into id graph')
cur.execute('create table id_redirect (src int, dst int)')
cur.execute("""insert into id_redirect select src_page.id,dst_page.id from redirect
               left outer join page as src_page on (src = src_page.title)
               left outer join page as dst_page on (dst = dst_page.title)""")
con.commit()
con.close()
