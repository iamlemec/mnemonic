# indexer interface

import os
from elasticsearch import Elasticsearch, helpers

doc_article = 'article'

def make_actions(index, docs):
    for doc in docs:
        yield {
            '_index': index,
            '_type': doc_article,
            '_source': doc
        }

class Connection:
    def __init__(self, index='wikipedia', **kwargs):
        self.es = Elasticsearch(**kwargs)
        self.index = index

    def create(self, reset=False):
        if reset:
            if self.es.indices.exists(self.index):
                self.es.indices.delete(self.index)
        self.es.indices.create(self.index, body={
            'mappings' : {
                doc_article : {
                    'properties' : {
                        'aid': {
                            'type': 'integer'
                        },
                        'title': {
                            'type': 'text'
                        },
                        'rid': {
                            'type': 'integer'
                        },
                        'date': {
                            'type': 'date'
                        },
                        'text': {
                            'type': 'text'
                        },
                        'wiki': {
                            'type': 'text',
                            'index': False
                        }
                    }
                }
            }
        })

    def settings(self, **opts):
        return self.es.indices.put_settings(index=self.index, body=opts)

    def insert(self, doc):
        return self.es.index(index=self.index, doc_type=doc_article, body=doc)

    def bulk(self, docs, **kwargs):
        return helpers.bulk(self.es, make_actions(self.index, docs), **kwargs)

    def delete(self, id):
        return self.es.delete(index=self.index, doc_type=doc_article, id=id)

    def fetch(self, id):
        return self.es.get(index=self.index, doc_type=doc_article, id=id)['_source']

    def fetch_title(self, id):
        return self.es.get(index=self.index, doc_type=doc_article, id=id, _source=['title'])['_source']['title']

    def link(self, title):
        ret = self.es.search(index=self.index, doc_type=doc_article, body={
            'query': {
                'term': {'title': title}
            }
        }, _source=['id'])
        hits = ret['hits']
        if hits['total'] > 0:
            return hits['hits'][0]['_id']
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
