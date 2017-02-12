# indexer interface

import os
from elasticsearch import Elasticsearch

doc_article = 'article'

class Connection:
    def __init__(self, index='wikipedia'):
        self.es = Elasticsearch()
        self.index = index

    def insert(self, id, title, body):
        return self.es.index(index=self.index, doc_type=doc_article, id=id, body={
            'title': title,
            'body': body
        })

    def delete(self, id):
        return self.es.delete(index=self.index, doc_type=doc_article, id=id)

    def fetch(self, id):
        return self.es.get(index=self.index, doc_type=doc_article, id=id)['_source']

    def fetch_title(self, id):
        return self.es.get(index=self.index, doc_type=doc_article, id=id, _source=['title'])['_source']['title']

    def link(self, title):
        ret = self.es.get(index=self.index, doc_type=doc_article, body={
            'query': {
                'term': {'title': title}
            }
        }, _source=['id'])
        hits = ret['hits']
        if hits['total'] > 0:
            return hits['hits'][0]
        else:
            return None

    def search(self, query, base=0, size=10, raw=False):
        ret = self.es.search(index=self.index, doc_type=doc_article, body={
            'query': {
                'dis_max': {
                    'queries': [
                        { 'match': { 'title': query } },
                        { 'match': { 'body': query } }
                    ]
                }
            },
            'from': base,
            'size': size
        }, _source=['id', 'title'])
        hits = [ (d['_id'], d['_source']['title']) for d in ret['hits']['hits'] ]
        if raw:
            return hits
        else:
            return Results(self, query, base, size, hits)

class Results:
    def __init__(self, con, query, base, size, res):
        self.con = con
        self.query = query
        self.base = base
        self.size = size
        self.res = res

    def __iter__(self):
        return iter(self.res)

    def next(self, n=10):
        self.base += self.size
        self.size = n
        self.res = self.con.search(self.query, base=self.base, size=self.size, raw=True)

