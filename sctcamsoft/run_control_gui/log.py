from logging import INFO, Formatter, Handler

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QFont

def create_logbox_log_adapter():
    """Instantiate a logbox handler that propagates GUI-suitable logs."""
    
    gui_log_formatter = Formatter(
        '%(asctime)s [%(levelname)7s] %(message)s',
        '%m-%d %H:%M:%S')
    handler = QtLogAdapter()
    handler.setFormatter(gui_log_formatter)
    handler.setLevel(INFO)

    return handler

class QtLogAdapter(QObject, Handler):
    """A custom logging handler that emits QT signals upon log events.

    This logging handler ties log events into the QT's event loop.
    The log event is added to the loop upon the Handler.emit call, 
    and listeners can connect a slot to the exposed "new_record"
    signal to recieve log messages in a thread-safe, event-based way.
    """

    new_record = pyqtSignal(object)

    def __init__(self):
        super().__init__()

    def emit(self, record):
        log_entry = self.format(record)
        self.new_record.emit(log_entry)

class LogControls(QObject):
    """A object encapsulating the GUI widgets for log display."""

    def __init__(self, window):
        super().__init__()

        self.text_browser = window.log_textbrowser

        logbox_font = QFont('Courier')
        logbox_font.setStyleHint(QFont.Monospace)
        logbox_font.setPointSize(13)
        self.text_browser.setFont(logbox_font)

    @pyqtSlot(object)
    def append_to_textbrowser(self, log):
        self.text_browser.append(log)
