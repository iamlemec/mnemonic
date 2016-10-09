# pull in all wikipedia data

import re
import os
import sys
import argparse
import sqlite3
from lxml import etree
from html.parser import unescape
import networkx as nx
import graph_tool as gt
from itertools import chain
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
cur.execute('create table title_link (src text, dst text, pos int, frac real)')
cur.execute('create table page (id int, rev int, date text, type int, length int, title text)')
cur.execute('create table redirect (src text, dst text)')
page_chunker = ChunkInserter(con, table='page')
link_chunker = ChunkInserter(con, table='title_link')
redir_chunker = ChunkInserter(con, table='redirect')

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

# usual capitalization
def capitalize(s):
    return s[0].upper() + s[1:] if len(s) > 0 else ''

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
            yield (t, s)

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
    title = page.find(title_tag).text
    redir = page.find(redir_tag)
    revn = page.find(revn_tag)
    rid = revn.find(id_tag).text
    date = revn.find(date_tag).text
    body = revn.find(text_tag).text or ''

    length = len(body)

    if ns != 0:
        o += 1
        atype = 2
    elif redir is not None:
        r += 1
        atype = 1
        targ = redir.get('title')
        redir_chunker.insert(title, targ)
        page_chunker.insert(aid, rid, date, atype, length, title)
    else:
        a += 1
        atype = 0
        wiki = html_unescape(body)
        links = gen_links(wiki)
        link_chunker.insertmany([(title, capitalize(dst), pos, pos/length) for (dst, pos) in links])
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
               inner join page as src_page on (src = src_page.title)
               inner join page as dst_page on (dst = dst_page.title)""")
print('merging redirects into id graph')
cur.execute('create table id_redirect (src int, dst int)')
cur.execute("""insert into id_redirect select src_page.id,dst_page.id from redirect
               inner join page as src_page on (src = src_page.title)
               inner join page as dst_page on (dst = dst_page.title)""")
con.commit()

# resolve redirects - FIX FROM HERE
print('resolving redirects')
redir = cur.execute('select * from id_redirect where dst is not null').fetchall()
G = nx.DiGraph()
G.add_edges_from(redir)
finals = [x for (x, i) in G.out_degree_iter() if i == 0]
newred = list(chain.from_iterable(([(a, z) for a in nx.ancestors(G, z)] for z in finals)))
cur.execute('create table final_redirect (src int, dst int)')
cur.executemany('insert into final_redirect values (?,?)', newred)
con.commit()

# create final link graph
print('creating final link graph')
cur.execute('create table final_link (src int, dst0 int, dst int, frac real)')
cur.execute("""insert into final_link select id_link.src,id_link.dst,final_redirect.dst,frac from id_link
               left join final_redirect on (id_link.dst = final_redirect.src)""")
cur.execute('update final_link set dst=dst0 where dst is null')
con.commit()

# close up shop
con.close()

# how to load graph
# import graph_tool
# import graph_tool.centrality
#
# print(cur.execute('select max(_rowid_) from final_link limit 1').fetchone()[0])
#
# g = graph_tool.Graph()
# g.ep.weight = g.new_edge_property('double')
# g.vp.name = g.new_vertex_property('int64_t')
#
# i = 0
# for chunk in pd.read_sql('select src,dst,2/(1+3*frac) from final_link', con, chunksize=1000000):
#     i += chunk.shape[0]
#     print(i)
#     vp = g.add_edge_list(chunk.values,hashed=True,eprops=[g.ep.weight])
#     g.vp.name.a += vp.a.astype(np.int64)
#
# pr = graph_tool.centrality.pagerank(g,weight=g.edge_properties['weight'])
# spr = np.argsort(pr.a)
# stn = [ g.vp.name[x] for x in spr[-10:] ]
# cur.execute('select * from page where id in (%s)' % ', '.join(map(str,stn))).fetchall()
