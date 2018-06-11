import re
import html as hp
import mwparserfromhell as mw
import traceback

# revert html codes
def html_unescape(text):
    text = hp.unescape(text)
    text = text.replace('\xa0', ' ')
    return text

# make a normal url
def escape_link(text):
    return text.replace(' ', '_')

def normalize_text(text):
    lines = text.split('\n')
    lines = [s.strip() for s in lines]
    text = '\n'.join(lines)
    text = re.sub(r'\n{2,}', '\n\n', text)
    return text.strip()

def normalize_html(html):
    html = re.sub(r'(<br/>){2,}','<br/>', html)
    return html.strip()

# recursively extract text from nodes
class WikiParser:
    def __init__(self):
        pass

    def initialize(self):
        self.foot = 0
        self.inpar = False

    def parse_html(self, node):
        t = type(node)
        if t is mw.wikicode.Wikicode:
            return ''.join([self.parse_html(n) for n in node.nodes])
        elif t is mw.nodes.Template:
            name = node.name.strip()
            if name.startswith('cite'):
                self.foot += 1
                return f'<sup>{self.foot}</sup>'
                #return ' '.join([self.parse_html(node.get(f) if node.has(f) else '') for f in ['title','last1','last2']])
            else:
                return ''
        elif t is mw.nodes.Argument:
            return ''
        elif t is mw.nodes.Wikilink:
            if node.title.startswith('Image:') or node.title.startswith('Category:') or node.title.startswith('File:'):
                return ''
            else:
                title = self.parse_html(node.title)
                link = escape_link(title)
                return f'<a href="{link}" class="wikilink">{title}</a>'
        elif t is mw.nodes.Heading:
            self.sec = True
            title = self.parse_html(node.title)
            return f'<h3>{title}</h3>'
        elif t is mw.nodes.ExternalLink:
            url = node.url
            if node.title:
                title = self.parse_html(node.title)
                return f'<a href="{url}">{title}</a>'
            else:
                return f'<a href="{url}">{url}</a>'
        elif t is mw.nodes.extras.Parameter:
            return self.parse_html(node.value)
        elif t is mw.nodes.Tag:
            if node.tag == 'ref':
                # parse contents
                self.foot += 1
                return f'<sup>{self.foot}</sup>'
            elif node.tag in ('li', 'ol'):
                return f'<br/>\n{node}'
            elif node.contents is not None:
                return self.parse_html(node.contents)
            else:
                return ''
        elif t is mw.nodes.Comment:
            return ''
        elif t is mw.nodes.HTMLEntity:
            return node.normalize()
        elif t is mw.nodes.Text:
            return self.parse_html(node.value)
        elif t is str:
            if node.startswith('\n\n'):
                if self.inpar:
                    return '</p><p>' + node[2:]
                else:
                    self.inpar = True
                    return '<p>' + node[2:]
            elif node.endswith('\n\n'):
                self.inpar = False
                return node[:-2] + '</p>'
            else:
                if self.inpar:
                    return node.replace('\n\n', '<p></p>')
                else:
                    return node
        else:
            traceback.print_stack()
            raise(Exception(f'Unrecognized Type {t}: {node}'))

    def parse_text(self,node):
        t = type(node)
        if node is None:
            return ''
        elif t is mw.wikicode.Wikicode:
            return ''.join([self.parse_text(n) for n in node.nodes])
        elif t is mw.nodes.Template:
            return ''
        elif t is mw.nodes.Argument:
            return ''
        elif t is mw.nodes.Wikilink:
            if node.title.startswith('Image:') or node.title.startswith('Category:') or node.title.startswith('File:'):
                return ''
            else:
                return self.parse_text(node.title)
        elif t is mw.nodes.Heading:
            return self.parse_text(node.title)
        elif t is mw.nodes.ExternalLink:
            if node.title:
                return self.parse_text(node.title)
            else:
                return ''
        elif t is mw.nodes.extras.Parameter:
            return self.parse_text(node.value)
        elif t is mw.nodes.Tag:
            if node.tag in ('gallery','ref'):
                return ''
            else:
                return self.parse_text(node.contents)
        elif t is mw.nodes.Comment:
            return ''
        elif t is mw.nodes.HTMLEntity:
            return node.normalize()
        elif t is mw.nodes.Text:
            return self.parse_text(node.value)
        elif t is str:
            return node
        else:
            traceback.print_stack()
            raise(Exception(f'Unrecognized Type {t}: {node}'))

# instance
parser = WikiParser()

def to_html(wiki):
    wiki = html_unescape(wiki)
    tree = mw.parse(wiki)
    parser.initialize()
    html = parser.parse_html(tree)
    html = normalize_html(html)
    return html

def to_text(wiki):
    wiki = html_unescape(wiki)
    tree = mw.parse(wiki)
    parser.initialize()
    text = parser.parse_text(tree)
    text = normalize_text(text)
    return text

def to_both(wiki):
    wiki = html_unescape(wiki)
    tree = mw.parse(wiki)

    parser.initialize()
    text = parser.parse_text(tree)
    text = normalize_text(text)

    parser.initialize()
    html = parser.parse_html(tree)
    html = normalize_html(html)

    return text, html
