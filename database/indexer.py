# indexer interface

import os
import sqlite3

# utils
def extract(arr,idx=0):
    return [x[idx] for x in arr]

def ensure_unicode(x):
    if type(x) is str:
        return x
    elif type(x) is bytes:
        return x.decode()
    else:
        raise str(x)

# initialize a db in a file
def initialize(fname):
    try:
        ret = os.stat(fname)
    except OSError:
        pass
    else:
        print('File exists.')
        return

    con = sqlite3.connect(fname)
    cur = con.cursor()

    cur.execute('create table document (id int, title text, body text)')
    cur.execute('create table feature (id int, type text, value text)')
    cur.execute('create index feat_id on document (id)')
    cur.execute('create index feat_val on feature (type,value)')

    con.close()

def connect(fname,create=True):
    try:
        ret = os.stat(fname)
    except OSError:
        print('File not found.')
        if create:
            print('Creating.')
            initialize(fname)
        else:
            print('Aborting.')
            return

    return Connection(fname)

class Connection:
    def __init__(self,fname):
        self.con = sqlite3.connect(fname)

    def __del__(self):
        self.con.close()

    def cursor(self):
        return self.con.cursor()

    def commit(self):
        self.con.commit()

    def insert(self,doc,title_tags=None,body_tags=None,commit=True):
        cur = self.cursor()
        cur.execute('insert into document values (?,?,?)',(doc.id,doc.title,doc.body))
        if title_tags:
            cur.executemany("insert into feature values (%d,'title',?)" % doc.id,zip(title_tags))
        if body_tags:
            cur.executemany("insert into feature values (%d,'body',?)" % doc.id,zip(body_tags))
        if commit:
            self.commit()

    def delete(self,id):
        cur = self.cursor()
        cur.execute('drop from document where id=?',(id,))
        cur.execute('drop from feature where id=?',(id,))

    def fetch(self,id):
        cur = self.cursor()
        ret = cur.execute('select title,body from document where id=?',(id,)).fetchone()
        if ret:
            (title,body) = ret
            return Document(id,title,body)

    def fetch_title(self,id):
        cur = self.cursor()
        ret = cur.execute('select title from document where id=?',(id,)).fetchone()
        if ret:
            return ret[0]

    def link(self,title):
        cur = self.cursor()
        ret = cur.execute('select id from document where title=?',(title,)).fetchone()
        if ret:
            return ret[0]

    def search(self,query='',sync=False):
        cur = self.cursor()
        if query == '':
            sql = 'select id from document'
        else:
            stack = []
            for term in query.split():
                if term.startswith('@'):
                    types = ['title']
                    term = term[1:]
                else:
                    types = ['title','body']
                for x in types:
                    stack.append("select id from feature where type='%s' and value like '%%%s%%'" % (x,term))
            sql = 'select distinct id from (\n' + '\nintersect\n'.join(stack) + '\n)'
        ret = cur.execute(sql)
        if sync:
            return extract(ret.fetchall())
        else:
            return Results(self,ret)

class Results:
    def __init__(self,con,res):
        self.con = con
        self.res = res

    def fetchone(self):
        ret = self.res.fetchone()
        if ret:
            return ret[0]

    def fetchmany(self,n):
        return extract(self.res.fetchmany(n))

class Document:
    def __init__(self,id,title,body):
        self.id = id
        self.title = title
        self.body = body

    def __repr__(self):
        return '%s (%d)\n\n%s' % (self.title,self.id,self.body)
