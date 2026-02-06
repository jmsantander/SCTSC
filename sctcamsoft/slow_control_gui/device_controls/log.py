import sys
from PyQt5 import QtWidgets
import logging


class QTextEditLogger(logging.Handler):
    def __init__(self, widge):
        super().__init__()
        self.widge=widge
        self.widge.textBrowser.setReadOnly(True)


    def emit(self, record):
        msg = self.format(record)
        self.widge.textBrowser.append(msg)
