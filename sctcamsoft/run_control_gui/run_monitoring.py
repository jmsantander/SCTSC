import logging
import math
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
from PyQt5.QtCore import Qt
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import  QTableWidget,QTableWidgetItem
from sctcamsoft.lib_gui.camera_handler import CameraHandler


class RunManager(QObject):

    def __init__(self, window, camera):
        super().__init__()

        self._camera = camera
        self._camera.on_update.connect(self.on_update)

        self._run_id = 11111
        self.start_commanded_time: datetime = None
        self.elapsed_time = timedelta(0)
        self.planned_duration = timedelta(0)
        self.is_observing = False
        self.tableWidget = window.tableWidget
        self.define_run_button = window.define_run
        self.add_comments_button = window.add_comments
        self.elapsed_time_textbox = window.elapsed_time_textbox
        self.progress_bar = window.run_progress_bar

        # Set the progress bar to vary between 0 and 100
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)

        self.start_button = window.start_run_button
        self.start_button.clicked.connect(self.start_run)
        self.stop_button = window.stop_run_button
        self.stop_button.clicked.connect(self.stop_run)
        self.define_run_button.clicked.connect(self.define_run)


    def on_update(self, update, variable_cache):
        def _update_matches(device, variable):
            return (update.device == device) and (update.variable == variable)

        if _update_matches('target', 'run_id'):
            self.run_id = int(update.value)

        logging.debug('Run manager recieved a device update.')
        # TODO: Process updates and edit run_info to match. Then, notify listeners.

    def on_error(self, update):
        logging.error('Run manager recieved an error: %r', update)

    def start_run(self):
        logging.info('STARTING run; sending start_run command.')
        self._camera.send_command('start_run')
        self.start_commanded_time = datetime.now(timezone.utc)

    def stop_run(self):
        logging.warning('STOP RUN; not implemented.')

    def define_run(self):
        rowPosition = self.tableWidget.rowCount()
        comboBox1 = QtWidgets.QComboBox()
        comboBox2 = QtWidgets.QComboBox()
        wether_list=['A','B','C','D']
        run_type=['Observe','Rate scan','Flasher']
        comboBox1.addItems(wether_list)
        comboBox2.addItems(run_type)
        self.tableWidget.insertRow(rowPosition)
        item1=QTableWidgetItem("Not Start")
        item1.setFlags(item1.flags() ^ Qt.ItemIsEditable) #read only
        item2= QTableWidgetItem(str(self._run_id))
        self.tableWidget.setItem(rowPosition, 0, item1)
        self.tableWidget.setItem(rowPosition, 1,item2)
        self._run_id+=1
        self.tableWidget.setCellWidget(rowPosition, 3, comboBox1)
        self.tableWidget.setCellWidget(rowPosition, 5, comboBox2)
    @property
    def run_id(self):
        return self._run_id

    @run_id.setter
    def run_id(self, value):
        self._run_id = value
        self.run_id_updated.emit(value)


    @pyqtSlot(int)
    def on_run_id(self, run_id):
        self.run_id_indicator.display(run_id)

    @pyqtSlot(object, object)
    def on_elapsed_time(self, elapsed_time: timedelta, planned_duration: timedelta):
        # Update the elapsed time textbox
        total_seconds = elapsed_time.total_seconds()
        minutes, seconds = divmod(total_seconds, 60)
        int_minutes = int(minutes)
        int_seconds = math.ceil(seconds)
        self.elapsed_time_textbox.setText(f'{int_minutes}:{int_seconds:02}')

        # Update the progress bar
        try:
            completion = elapsed_time / planned_duration
            percentage = math.ceil(completion * 100)
        except ZeroDivisionError:
            percentage = 0
        finally:
            self.progress_bar.setValue(percentage)
