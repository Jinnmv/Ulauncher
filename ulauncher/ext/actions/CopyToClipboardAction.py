import sys
import os
from gi.repository import Gtk, Gdk
from .BaseAction import BaseAction


class CopyToClipboardAction(BaseAction):

    def __init__(self, text):
        self.text = text

    def keep_app_open(self):
        return False

    def run(self):
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(self.text, -1)
        clipboard.store()
