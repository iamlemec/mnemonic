#!/usr/bin/env python3
# coding: UTF-8

import sys
import argparse
import urwid
from urwid import MetaSignals
import indexer_elast as ix
import wiki_parser as wp

# import logging
# logging.basicConfig(filename='debug.log',level=logging.DEBUG)

# parse command line
parser = argparse.ArgumentParser(description='Patent classifier tool.')
parser.add_argument('--index', type=str, default='wikipedia', help='name of elasticsearch index')
args = parser.parse_args()

# connect to elasticsearch
con = ix.Connection(index=args.index)

# user interface
class MainWindow(object):
    __metaclass__ = MetaSignals
    signals = ['quit', 'keypress']

    _palette = [
        ('bar', 'black', 'dark cyan', 'standout'),
        ('text', 'light gray', 'default'),
    ]

    # states
    SEARCH = 1
    DISPLAY = 2

    def __init__(self):
        self.state = self.DISPLAY

    def main(self):
        self.ui = urwid.raw_display.Screen()
        self.ui.register_palette(self._palette)
        self.build_interface()
        self.ui.run_wrapper(self.run)

    def run(self):
        def input_cb(key):
            self.keypress(self.size,key)
        self.size = self.ui.get_cols_rows()
        self.main_loop = urwid.MainLoop(self.context, screen=self.ui,
            handle_mouse=False, unhandled_input=input_cb)

        try:
            self.main_loop.run()
        except KeyboardInterrupt:
            self.quit()

    def quit(self, exit=True):
        urwid.emit_signal(self, 'quit')
        if exit:
            sys.exit(0)

    def build_interface(self):
        self.header = urwid.Text('')
        self.footer = urwid.Edit(('bar', 'search: '), '')

        self.walker = urwid.SimpleFocusListWalker([])
        self.body = urwid.ListBox(self.walker)

        self.header = urwid.AttrWrap(self.header, 'bar')
        self.footer = urwid.AttrWrap(self.footer, 'bar')
        self.body = urwid.AttrWrap(self.body, 'body')

        self.context = urwid.Frame(header=self.header, body=self.body, footer=self.footer, focus_part='footer')

    def keypress(self, size, key):
        urwid.emit_signal(self, 'keypress', size, key)

        if key in ('page up','page down', 'up', 'down', 'home', 'end'):
            self.body.keypress(size, key)
        elif key == 'window resize':
            self.size = self.ui.get_cols_rows()
        elif key == 'esc':
            self.quit()
        elif key == 'enter':
            if self.state == self.DISPLAY:
                query = self.get_footer()
                self.search(query)
                self.set_header('SEARCH')
                self.set_footer('')
                self.state = self.SEARCH
                self.context.set_focus('body')

    def draw_interface(self):
        self.main_loop.draw_screen()

    def search(self, query):
        def search_choose(button, data):
            self.display_article(data)
        self.results = con.search(query)
        self.walker[:] = [urwid.AttrMap(urwid.Button(t, on_press=search_choose, user_data=i), None, focus_map='reversed') for (i, t) in self.results]

    def display_article(self, id):
        art = con.fetch(id)
        title = art['title']
        wiki = art['body']
        text = '\n' + wp.to_text(wiki) + '\n'
        self.display_text(text)
        self.set_header(title)
        self.set_footer('')
        self.state = self.DISPLAY
        self.context.set_focus('footer')

    def set_header(self, text):
        self.header.set_text(('bar', text))

    def set_footer(self, text):
        self.footer.set_edit_text(text)

    def get_footer(self):
        (text, attr) = self.footer.get_text()
        return text

    def display_text(self,text):
        if not isinstance(text, urwid.Text):
            text = urwid.Text(text)
        self.walker[:] = [text]

# main event
main_window = MainWindow()
main_window.main()

