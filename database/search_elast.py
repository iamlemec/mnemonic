from elasticsearch import Elasticsearch

idx = 'wikipedia'

es = Elasticsearch()

def search(query):
    ret = es.search(index=idx, body={'query': query})['hits']['hits']
    return [h['_source'] for h in ret]

def search_field(field, terms):
    return search({'match': {field: terms}})

def search_title(terms):
    return search_field('title', terms)

def get_by_id(aid):
    ret = search_field('aid', aid)
    if len(ret) == 0:
        return
    else:
        return ret[0]

def get_by_title(title):
    ret = search_field('title', title)
    if len(ret) == 0:
        return
    else:
        return ret[0]
