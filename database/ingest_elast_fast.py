import re
import argparse
import html
from mectools.hyper import progress
import indexer_elast as ix

# parse input arguments
parser = argparse.ArgumentParser(description='Nemonic Server.')
parser.add_argument('fname', type=str, help='filename of wikipedia')
parser.add_argument('--index', type=str, default='wikipedia', help='name of elasticsearch index')
parser.add_argument('--per', type=int, default=100000, help='frequency to output progress')
parser.add_argument('--limit', type=int, default=None, help='number of articles to parse')
parser.add_argument('--reset', action='store_true', help='drop existing index')
args = parser.parse_args()

# revert html codes
def html_unescape(text):
    text = html.unescape(text)
    text = text.replace('\xa0', ' ')
    return text

# regularize to token list
def reduce_wiki(text):
    text = re.sub(r'([^\w ]|_)', ' ', text) # remove non-alphanumeric, unicode aware
    text = re.sub(r' {2,}', ' ', text) # compress spaces
    return text.lower().strip() # to lowercase and trim

# initialize/open database
con = ix.Connection(index=args.index)
con.create(reset=args.reset)
con.settings(refresh_interval=-1)

# parse wiki pages (this parser is bad and wrong)
def gen_articles():
    store = False
    in_txt = False
    for line in open(args.fname):
        ret = re.match(r'( *)<([^>]*?)>', line)
        if ret:
            ind, tag = ret.groups()
            ind = len(ind)
            body = line[ret.end():]
            ret = re.match(r'([^<]*?)</[^>]*?>', body)
            if ret:
                body, = ret.groups()
                oner = True
            else:
                oner = False
        else:
            tag = None
            if in_txt:
                if line.endswith('</text>\n'):
                    data['wiki'] += line[:-8]
                    in_txt = False
                else:
                    data['wiki'] += line
            continue

        if tag == 'page':
            store = True
            in_txt = False
            data = {}
        elif tag == '/page':
            if store:
                data['aid'] = int(data['aid'])
                data['rid'] = int(data['rid'])
                data['title'] = html_unescape(data['title'])
                data['wiki'] = html_unescape(data['wiki'])
                data['text'] = reduce_wiki(data['wiki'])
                yield data
                store = False

        if not store:
            continue

        if tag == 'ns':
            if body != '0':
                store = False
        elif tag.startswith('redirect'):
            store = False
        elif tag == 'id':
            if ind == 4:
                data['aid'] = body
            elif ind == 6:
                data['rid'] = body
        elif tag == 'title':
            data['title'] = body
        elif tag == 'timestamp':
            data['date'] = body
        elif tag.startswith('text'):
            data['wiki'] = body
            in_txt = not oner
        elif tag == '/text':
            in_txt = False

# bulk insert
nart, errs = con.bulk(progress(gen_articles(), per=args.per, limit=args.limit))

# start refresh again
con.settings(refresh_interval=None)

# close out
print(f'nart = {nart}, nerr = {len(errs)}')
