import sys
import csv
import yaml
import pprint
import random

from enum import Enum, auto
from typing import NamedTuple
from dataclasses import dataclass, field
from math import floor
from pathlib import Path

from PyQt5.QtWidgets import *
from PyQt5.QtGui import QPainter, QColor, QFont, QBrush, QPen
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QRectF


class ModuleConf(NamedTuple):
    mod_id: int = None
    fpm_sector: int = None
    fpm_position: int = None
    enabled: bool = True
    state: str = ''
    masked_triggers: list = list()


class DisplayMode(Enum):
    STATUS = 'Status'
    TRIGGER_MASKS = 'Trigger Pixels'


class ModuleConfigurationDialog(QDialog):
    """Top-level dialog object for module configuration.
    
    Dialog window that holds the camera indicator widget, the view mode 
    selection spinner, a textedit for detailed module view, and the 
    trigger-pixel grid editor.

    This dialog needs a list of ModuleConf tuples to display information, which 
    can be changed by calling `set_module_conf()`. 

    Attributes:
        module_conf_changed: A pyqtSignal emitted whenever a module's ModuleConf
            is updated (in response to some client's interaction with the 
            ModuleConfigurationDialog GUI). Emitted with new ModuleConf tuple. 
    """

    module_conf_changed = pyqtSignal(ModuleConf)

    def __init__(self, module_conf):
        super().__init__()

        self.module_configurations = {mod.mod_id: mod for mod in module_conf}
        self.selected_mod = None

        self.current_view_mode = None

        self.main_hbox_layout = QHBoxLayout(self)

        self.camera_indicator = CameraIndicator(module_conf)
        self.camera_indicator.module_clicked.connect(self._on_module_clicked)
        self.camera_indicator.module_changed.connect(self._on_module_changed)
        self.main_hbox_layout.addWidget(self.camera_indicator)
        self.right_vbox_layout = QVBoxLayout()
        self.main_hbox_layout.addLayout(self.right_vbox_layout)

        self.loaded_trigger_pixel_file_path = None
        self.trigger_pixel_file_buttons = QHBoxLayout()
        self.load_trigger_pixel_file_button = QPushButton('Load') 
        self.load_trigger_pixel_file_button.setAutoDefault(False)
        self.load_trigger_pixel_file_button.clicked.connect(
            self._on_triggers_file_load)
        self.save_trigger_pixel_file_button = QPushButton('Save')
        self.save_trigger_pixel_file_button.setAutoDefault(False)
        self.save_trigger_pixel_file_button.clicked.connect(
            self._on_triggers_file_save)
        self.save_trigger_pixel_file_button.setDisabled(True)
        self.trigger_pixel_file_buttons.addWidget(QLabel('Triggers'))
        self.trigger_pixel_file_buttons.addWidget(
            self.load_trigger_pixel_file_button)
        self.trigger_pixel_file_buttons.addWidget(
            self.save_trigger_pixel_file_button)

        self.mode_sel_hbox_layout = QHBoxLayout()
        self.mode_spinner_label = QLabel("View Mode")
        self.mode_spinner_label.setSizePolicy(
            QSizePolicy.Maximum, QSizePolicy.Minimum)
        self.view_mode_spinner = QComboBox()
        for index, enum_meta in zip(range(0, len(DisplayMode)), DisplayMode):
            self.view_mode_spinner.insertItem(index, enum_meta.value)
        self.view_mode_spinner.currentIndexChanged.connect(
            self._view_mode_changed)
        self.mode_sel_hbox_layout.addWidget(self.mode_spinner_label)
        self.mode_sel_hbox_layout.addWidget(self.view_mode_spinner)

        self.module_conf_text = QTextBrowser()
        self.mask_indicator = TriggerPixelIndicator()
        self.mask_indicator.trigger_mask_changed.connect(
            self._on_triggers_change)
        self.right_vbox_layout.addLayout(self.mode_sel_hbox_layout)
        self.right_vbox_layout.addLayout(self.trigger_pixel_file_buttons)
        self.right_vbox_layout.addWidget(self.module_conf_text)
        self.right_vbox_layout.addWidget(self.mask_indicator)

        self.main_hbox_layout.setStretch(0, 3)
        self.main_hbox_layout.setStretch(1, 1)

        self._view_mode_changed(0)

    def set_module_conf(self, mod_conf):
        self.camera_indicator.set_module_conf(mod_conf)

    def _view_mode_changed(self, new_index):
        new_val = self.view_mode_spinner.itemText(new_index)
        self.current_view_mode = DisplayMode(new_val)
        self.camera_indicator.set_view_mode(self.current_view_mode)

    def _on_module_clicked(self, mod_conf):
        self.selected_mod = mod_conf
        self.module_conf_text.setText(str(mod_conf))
        self.mask_indicator.set_masked_ids(mod_conf.masked_triggers)

    def _on_triggers_file_load(self):
        # Open the file dialog
        file_path_string, _ = QFileDialog.getOpenFileName(
            self,
            'Load Masked Trigger Pixel File',
            '',
            'Yaml Files (*.yaml *.yml);;All Files (*)',
            None,
            QFileDialog.DontUseNativeDialog)

        # If the dialog was canceled, return early
        if not file_path_string:
            return

        file_path = Path(file_path_string)
        self.loaded_trigger_pixel_file_path = file_path.resolve()

        # First, grab the module trigger masks, to
        # be used while creating the module data
        with open(self.loaded_trigger_pixel_file_path, 'r') as trigger_mask_path:
            saved_trigger_masks = yaml.safe_load(trigger_mask_path)

        for mod_id in self.module_configurations:
            try:
                trigger_mask = saved_trigger_masks[mod_id]
            except KeyError:
                trigger_mask = []

            # Create a new module conf with the new trigger mask list
            old_conf = self.module_configurations[mod_id]
            new_conf = old_conf._replace(masked_triggers=trigger_mask) 
            self.set_module_conf(new_conf)
            self.module_configurations[mod_id] = new_conf

        self.save_trigger_pixel_file_button.setDisabled(False)
            
    def _on_triggers_file_save(self):
        # Collect the current trigger pixel state of each module into a dict
        masked_trigger_pixels = {}
        for mod_id, module_conf in self.module_configurations.items():
            masked_trigger_pixels[mod_id] = module_conf.masked_triggers

        with open(self.loaded_trigger_pixel_file_path, 'w') as outfile:
            yaml.dump(masked_trigger_pixels, outfile, default_flow_style=None)

    def _on_module_changed(self, mod_conf):
        self.module_configurations[mod_conf.mod_id] = mod_conf
        if (self.selected_mod is not None and
            self.selected_mod.mod_id == mod_conf.mod_id): 
            self.module_conf_text.setText(str(mod_conf))
        self.module_conf_changed.emit(mod_conf)

    def _on_triggers_change(self, new_trigs):
        if (self.selected_mod is not None):
            updated_mod = self.selected_mod._replace(masked_triggers=new_trigs)
            self._on_module_changed(updated_mod)
            self.set_module_conf(updated_mod)


class CameraIndicator(QWidget):
    """Custom QWidget for displaying a grid of BackplaneIndicators.
    
    Accepts a list of ModuleConf objects (used to create and update the 
    displayed BackplaneIndicators) and emits signals when a ModuleConf is 
    updated by a BackplaneIndicator.s

    Attributes:
        module_clicked: A pyqtSignal emitted when one of CameraIndicator's
            contained BackplaneIndicators emits a `module_changed` signal.
        module_changed: A pyqtSignal emitted when one of CameraIndicator's
            contained BackplaneIndicators emits a `module_clicked` signal.
    """

    module_clicked = pyqtSignal(ModuleConf)
    module_changed = pyqtSignal(ModuleConf)

    def __init__(self, module_conf=list()):
        super().__init__()

        self.grid_layout = QGridLayout(self)
        self.grid_layout.setHorizontalSpacing(4)
        self.grid_layout.setVerticalSpacing(4)

        self.bp_indicators = {}

        modules_by_backplane = {}
        for module in module_conf:
            sector_num = module.fpm_sector
            if sector_num not in modules_by_backplane:
                modules_by_backplane[sector_num] = list()
            modules_by_backplane[sector_num].append(module)

        for sector_num, modules in modules_by_backplane.items():
            bp_indc = BackplaneIndicator(sector_num, modules)
            bp_indc.module_clicked.connect(self.module_clicked)
            bp_indc.module_changed.connect(self.module_changed)
            self.bp_indicators[sector_num] = bp_indc
            (row, col) = (floor((sector_num) / 3), (sector_num) % 3)
            self.grid_layout.addWidget(bp_indc, row, col)

    def set_view_mode(self, new_mode):
        for bp_indc in self.bp_indicators.values():
            bp_indc.set_view_mode(new_mode)

    def set_module_conf(self, mod_conf):
        bp_indc = self.bp_indicators[mod_conf.fpm_sector]
        bp_indc.set_module(mod_conf)


class BlankWidget(QWidget):
    def __init__(self):
        super().__init__()


class BackplaneIndicator(QWidget):
    """Custom QWidget for a Camera sector ("Backplane") composed of modules.

    BackplaneIndicator displays a (maximum) 5x5 grid of ModuleIndicator 
    widgets according to a list of ModuleConf objects.

    Attributes: 
        module_clicked: A pyqtSignal emitted when this QWidget recieves a
            `module_clicked` signal from a constituent ModuleIndicator.
        module_changed: A pyqtSignal emitted when this QWidget recieves a 
            `module_changed` signal from a constituent ModuleIndicator. 
    """

    NUM_ROWS = 5
    NUM_COLS = 5

    module_clicked = pyqtSignal(ModuleConf)
    module_changed = pyqtSignal(ModuleConf)

    def __init__(self, sector: int, module_conf: list):
        super().__init__()

        self.sector = sector
        self.module_grid = QGridLayout(self)
        self.module_grid.setContentsMargins(2, 2, 2, 2)
        self.module_grid.setHorizontalSpacing(2)
        self.module_grid.setVerticalSpacing(2)
        self.mod_indicators = {}

        # Fill the layout with spacers
        for i in range(0, 5):
            for j in range(0, 5):
                self.module_grid.addWidget(BlankWidget(), i, j)

        for mod in module_conf:
            (row, col) = BackplaneIndicator.fpm_pos_to_rowcol(mod.fpm_position)

            item = self.module_grid.itemAtPosition(row, col).widget()
            module = ModuleIndicator(mod)
            module.module_clicked.connect(self.module_clicked)
            module.disable_status_changed.connect(self.module_changed)
            self.mod_indicators[mod.mod_id] = module
            module.set_mouseover_highlight(True)
            self.module_grid.addWidget(module, row, col, 1, 1)

        # Fill the empty grid spots with blank widgets
        for row in range(0, BackplaneIndicator.NUM_ROWS):
            for col in range(0, BackplaneIndicator.NUM_COLS):
                at_pos = self.module_grid.itemAtPosition(row, col)
                if (not at_pos):
                    self.module_grid.addWidget(BlankWidget(), row, col, 1, 1)

        self.setMinimumSize(
            BackplaneIndicator.NUM_ROWS * 45,
            BackplaneIndicator.NUM_COLS * 45)

    def set_module(self, mod_conf):
        self.mod_indicators[mod_conf.mod_id].set_config(mod_conf)

    def set_view_mode(self, view_mode):
        for module in self.mod_indicators.values():
            module.set_view_mode(view_mode)

    @staticmethod
    def fpm_pos_to_rowcol(fpm_position):
        """Translates fpm_position to on-screen location in 5x5 grid.
        
        A static method used to convert an `fpm_position` into a 
        Qt grid-compatible row-column location.
        """

        row = 4 - floor((fpm_position) / 5)
        col = (fpm_position) % 5
        return (row, col)


class ModuleIndicator(QWidget):
    """Custom QWidget for an individual module.

    ModuleIndicator is a rectangular box that can display information about a 
    Camera module's current configuration and status. All displayed information 
    is captured in a ModuleConf tuple. Which of that information is displayed is
    set by ModuleIndicator's `view_mode`. 

    If `view_mode` is DisplayMode.STATUS, then ModuleIndicator displays
    enabled/disabled state and connected state. If it is 
    DisplayMode.TRIGGER_MASKS, then ModuleIndicator displays that module's
    trigger mask.

    ModuleIndicator also can redraw when moused-over, growing slightly in size
    to indicate clickability. Finally, no matter the `view_mode`, the
    `module_id` associated with this indicator is displayed in the top-left
    corner of the widget.

    Attributes:
        module_clicked: A pyqtSignal emitted when this ModuleIndicator 
            is clicked.
        disable_status_changed: A pyqtSignal emitted when this ModuleIndicator's
            ModuleConf is updated with a new enabled/disabled status (in
            response to an action by the user).
    """

    BG_COLOR = QColor('#cfd8dc')
    DARK_COLOR = QColor("#1b1b1b")  # Widget bounding box color, etc
    CONNECTED_COLOR = QColor('#8aacc8')

    module_clicked = pyqtSignal(ModuleConf)
    disable_status_changed = pyqtSignal(ModuleConf)

    def __init__(self, module_conf=ModuleConf()):
        super().__init__()

        self.module_conf = module_conf
        self.view_mode = None

        self.trigger_grid = TriggerPixelGrid()

        self.setMinimumSize(15, 15)

        self.setContextMenuPolicy(Qt.ActionsContextMenu)

        self.show_is_connected = True

        self.enable_disable_action = QAction(self)
        self.enable_disable_action.triggered.connect(self.toggle_enabled)
        self.addAction(self.enable_disable_action)

        self.set_enabled(module_conf.enabled)

    def set_config(self, conf: ModuleConf):
        self.module_conf = conf
        self.update()

    def toggle_enabled(self, checked=False):
        self.set_enabled(not self.module_conf.enabled)
        self.disable_status_changed.emit(self.module_conf)

    def set_enabled(self, enabled):
        self.module_conf = self.module_conf._replace(enabled=enabled)

        self.unhighlight()
        if (self.module_conf.enabled):
            self.enable_disable_action.setText("Remove from Config")
        else:
            self.enable_disable_action.setText("Add to Config")

        self.update()

    def set_view_mode(self, new_view_mode):
        self.view_mode = new_view_mode
        self.update()

    def enterEvent(self, event):
        if (self.highlight_on_mouseover):
            self.highlight()

    def leaveEvent(self, event):
        if (self.highlight_on_mouseover):
            self.unhighlight()

    def mouseReleaseEvent(self, event):
        self.module_clicked.emit(self.module_conf)

    def highlight(self):
        ADD_SIZE = 5
        self.raise_()
        self.last_pos = (self.x(), self.y())
        self.last_size = (self.width(), self.height())
        self.resize(self.width() + ADD_SIZE, self.height() + ADD_SIZE)
        self.move(self.x() - (ADD_SIZE / 2), self.y() - (ADD_SIZE / 2))

    def unhighlight(self):
        try:
            self.resize(self.last_size[0], self.last_size[1])
            self.move(self.last_pos[0], self.last_pos[1])
        except AttributeError:
            pass

    def set_show_connec_state(self, show_connected):
        self.show_is_connected = show_connected
        self.update()

    def set_mouseover_highlight(self, show_highlight):
        self.highlight_on_mouseover = show_highlight
        self.unhighlight()
        self.update()

    def paintEvent(self, painter):
        painter = QPainter()
        painter.begin(self)

        # Draw background
        background = QRectF(1, 1, self.width() - 2, self.height() - 2)
        bg_brush = QBrush(ModuleIndicator.BG_COLOR)
        if ((self.view_mode is DisplayMode.STATUS) and not self.module_conf.enabled):
            bg_brush.setColor(ModuleIndicator.DARK_COLOR)
            bg_brush.setStyle(Qt.Dense4Pattern)
        bg_pen = QPen(ModuleIndicator.DARK_COLOR)
        bg_pen.setWidth(1.5)
        painter.setBrush(bg_brush)
        painter.setPen(bg_pen)
        painter.drawRoundedRect(background, 4, 4)

        if (self.view_mode is DisplayMode.STATUS):
            self._paint_status(painter)
        if (self.view_mode is DisplayMode.TRIGGER_MASKS):
            self.trigger_grid.paint(painter,
                                    self.height(),
                                    self.width(),
                                    self.module_conf.masked_triggers,
                                    draw_background=False,
                                    show_labels=False,
                                    show_major_grid=False,
                                    show_minor_grid=False)

        # Draw module id
        top_left_quad = QRectF(1, 1, self.width() / 2, self.height() / 2)
        module_id_font = QFont('Courier')
        module_id_font.setStyleHint(QFont.Monospace)
        module_id_font.setPointSize(15)
        painter.setFont(module_id_font)
        painter.drawText(top_left_quad, Qt.AlignCenter,
                         str(self.module_conf.mod_id))

        painter.end()

    def _paint_status(self, painter):
        # Draw connected status color (in quadrant III)
        top_left_quad = QRectF(1, 1, self.width() / 2, self.height() / 2)
        if (self.module_conf.enabled and self.show_is_connected):
            # If this module is in a "connected-like" state, color it accordingly
            if (self.module_conf.state in ['Safe', 'Pre-sync', 'Ready']):
                bg_brush = QBrush(ModuleIndicator.CONNECTED_COLOR)
                bg_pen = QPen(ModuleIndicator.DARK_COLOR)
                bg_pen.setWidth(1.5)
                painter.setBrush(bg_brush)
                painter.setPen(bg_pen)
                painter.drawRoundedRect(top_left_quad, 2, 2)
            else:
                bg_brush = QBrush()
                bg_brush.setStyle(Qt.BDiagPattern)
                bg_pen = QPen(ModuleIndicator.DARK_COLOR)
                bg_pen.setWidth(1.5)
                painter.setBrush(bg_brush)
                painter.setPen(bg_pen)
                painter.drawRoundedRect(top_left_quad, 2, 2)


class TriggerPixelIndicator(QWidget):
    """A standalone custom widget for an editable grid of trigger pixels.

    TriggerPixelIndicator is a custom QWidget that displays a list of
    masked trigger pixel IDs as a grid of numbered pixels. Internally, it 
    uses the TriggerPixelGrid class for drawing grid and extends its
    painting logic with interactivity.

    A note on variable name and comment terminology for grid positions: 
        'POSITION' is from the top left.
        'ROW_COL' is from the top left.
        'ID' is internally independent of position.

    Attributes:
        trigger_mask_changed: A pyqtSignal emitted whenever the set of masked
            trigger pixels is changed by the user (from the GUI).
    """

    trigger_mask_changed = pyqtSignal(list)

    def __init__(self, masked_ids=list()):
        super().__init__()

        self.trigger_mask_grid = TriggerPixelGrid()
        self.set_masked_ids(masked_ids)
        self.mouseover_row_col = None

        self.trigger_grid = TriggerPixelGrid()

        self.setMinimumSize(15, 15)

        size_policy = QSizePolicy(
            QSizePolicy.Minimum, QSizePolicy.Minimum)
        size_policy.setHeightForWidth(True)
        self.setSizePolicy(size_policy)

        self.setMouseTracking(True)

    def heightForWidth(self, width):
        return width

    def sizeHint(self):
        return QSize(300, 300)

    def mouseMoveEvent(self, event):
        position = (event.pos().x(), event.pos().y())
        row_col = self.trigger_grid.xy_to_rowcol(position)

        if (self.mouseover_row_col != row_col):
            self.mouseover_row_col = row_col
            self.update()

    def mouseReleaseEvent(self, event):
        position = (event.pos().x(), event.pos().y())
        clicked_id = self.trigger_grid.xy_to_trig_id(position)

        # Toggle the clicked trigger
        try:
            self.masked_ids.remove(clicked_id)
        except ValueError:
            self.masked_ids.append(clicked_id)

        self.set_masked_ids(self.masked_ids)
        self.trigger_mask_changed.emit(self.masked_ids)

    def leaveEvent(self, event):
        self.mouseover_row_col = None
        self.update()

    def set_masked_ids(self, masked_ids):
        self.masked_ids = masked_ids
        self.update()

    def paintEvent(self, painter):
        painter = QPainter()
        painter.begin(self)

        self.trigger_grid.paint(painter, self.height(),
                                self.width(), self.masked_ids,
                                True, True, self.mouseover_row_col)

        painter.end()


class TriggerPixelGrid():
    """Uses an injected QPainter to draws a grid of trigger pixels.
    
    TriggerPixelGrid is a generic class for painting a grid of large pixels
    according to a list of masked trigger pixel ids. Masked trigger pixels
    are filled, and unmasked pixels are left empty. The ID number of each pixel
    is printed in the top-left of the grid cell.
    
    The LOCATIONS class variable holds the mapping between trigger ID's (keys)
    to row-column grid locations (values).
    """

    LOCATIONS = {
        10: (0, 0), 11: (0, 1), 14: (0, 2), 15: (0, 3),
        8: (1, 0), 9: (1, 1), 12: (1, 2), 13: (1, 3),
        2: (2, 0), 3: (2, 1), 6: (2, 2), 7: (2, 3),
        0: (3, 0), 1: (3, 1), 4: (3, 2), 5: (3, 3)
    }

    BORDER_COLOR = QColor('#595959')
    MINOR_GRIDLINE_COLOR = QColor('#e1e1e1')
    UNMASKED_PIX = QColor('#eceff1')
    # MASKED_PIX = QColor('#FF8080')
    MASKED_PIX = QColor('#e53935')
    LABEL_COLOR_LIGHT = QColor('#FFFFFF')
    LABEL_COLOR_DARK = QColor('#000000')

    def __init__(self):

        self.height = None
        self.width = None

        # Create drawing resources
        self.bg_pen = QPen(TriggerPixelGrid.BORDER_COLOR)
        self.bg_pen.setWidth(1)
        self.bg_brush = QBrush(TriggerPixelGrid.UNMASKED_PIX)

        self.minor_gridline_pen = QPen(
            TriggerPixelGrid.MINOR_GRIDLINE_COLOR)
        self.minor_gridline_pen.setWidth(1)

        self.major_gridline_pen = QPen(TriggerPixelGrid.BORDER_COLOR)
        self.major_gridline_pen.setWidth(1)

        self.masked_trig_pen = Qt.NoPen
        self.masked_trig_brush = QBrush(TriggerPixelGrid.MASKED_PIX)

        self.highlighted_pen = QPen(TriggerPixelGrid.BORDER_COLOR)
        self.highlighted_pen.setWidth(2)

        self.light_label_pen = QPen(TriggerPixelGrid.LABEL_COLOR_LIGHT)
        self.dark_label_pen = QPen(TriggerPixelGrid.LABEL_COLOR_DARK)
        self.label_font = QFont('Courier')
        self.label_font.setStyleHint(QFont.Monospace)
        self.label_font.setPointSize(12)

    def xy_to_rowcol(self, pos):
        """Converts a pixel x-y position inside the widget to a grid location."""

        if (self.height is None or self.width is None):
            return None

        (x, y) = pos
        quarter_height = self.height / 4
        quarter_width = self.width / 4

        row = -1
        for row_index in range(0, 4):
            if (y < ((row_index + 1) * quarter_height)):
                row = row_index
                break

        col = -1
        for col_index in range(0, 4):
            if (x < ((col_index + 1) * quarter_width)):
                col = col_index
                break

        return (row, col)

    def xy_to_trig_id(self, pos):
        """Converts pixel location to trigger ID.
        
        Converts a pixel x-y position inside the widget to a 
        trigger ID associated with that grid location.
        """

        clicked_row_col = self.xy_to_rowcol(pos)

        for mod_id, mod_row_col in TriggerPixelGrid.LOCATIONS.items():
            if (mod_row_col == clicked_row_col):
                return mod_id

        return -1

    @staticmethod
    def _trigg_id_to_loc(mod_id):
        return TriggerPixelGrid.LOCATIONS[mod_id]

    def paint(self, painter, height, width,
              masked_ids: list,
              draw_background=True,
              show_labels=True,
              highlighted_rowcol: tuple = None,
              show_major_grid=True,
              show_minor_grid=True):

        self.height = height
        self.width = width

        masked_locations = \
            list(map(TriggerPixelGrid._trigg_id_to_loc, masked_ids))

        # Draw background
        background = QRectF(1, 1, width - 2, height - 2)
        painter.setBrush(self.bg_brush)
        painter.setPen(self.bg_pen)
        if (draw_background):
            painter.drawRoundedRect(background, 4, 4)

        # Draw trigger pixel grid
        height = height
        eighth_height = height / 8
        width = width
        eighth_width = width / 8
        minor_gridline = True

        # Draw minor gridlines
        painter.setPen(self.minor_gridline_pen)
        if (show_minor_grid):
            for index in {1, 3, 5, 7}:
                painter.drawLine(
                    eighth_width * index, self.bg_pen.width(),
                    eighth_width * index, height - self.bg_pen.width())
                painter.drawLine(
                    self.bg_pen.width(), eighth_height * index,
                    width - self.bg_pen.width(), eighth_height * index)

        # Draw masked pixels
        painter.setPen(self.masked_trig_pen)
        painter.setBrush(self.masked_trig_brush)
        quarter_width = width / 4
        quarter_height = height / 4
        for (row, col) in masked_locations:
            painter.drawRect(
                (col * quarter_width) + 1,
                (row * quarter_height) + 1,
                quarter_width,
                quarter_height)

        # Draw major gridlines
        painter.setPen(self.major_gridline_pen)
        if (show_major_grid):
            for index in {2, 4, 6}:
                painter.drawLine(eighth_width * index,
                                 self.bg_pen.width(), eighth_width * index, height)
                painter.drawLine(self.bg_pen.width(), eighth_height *
                                 index, width, eighth_height * index)

        # Draw highlighted trigger pixel
        painter.setBrush(Qt.NoBrush)
        if (highlighted_rowcol is not None):
            (row, col) = highlighted_rowcol
            painter.setPen(self.highlighted_pen)
            painter.drawRect(
                (col * quarter_width) + 1,
                (row * quarter_height) + 1,
                quarter_width,
                quarter_height)

        # Draw the trigger pixel label
        painter.setFont(self.label_font)
        if (show_labels):
            for trig_id, position in TriggerPixelGrid.LOCATIONS.items():
                if (position in masked_locations):
                    painter.setPen(self.light_label_pen)
                else:
                    painter.setPen(self.dark_label_pen)
                trig_pix_bbox = QRectF(
                    (position[1] * quarter_width),
                    (position[0] * quarter_height),
                    eighth_width,
                    eighth_height)
                painter.drawText(trig_pix_bbox, Qt.AlignCenter, str(trig_id))

        # Redraw the background's border
        background = QRectF(1, 1, width - 2, height - 2)
        painter.setPen(self.bg_pen)
        painter.drawRoundedRect(background, 4, 4)

def main():
    """Creates a standalone CameraIndicator in its own QApplication.
    
    This execution method was frequently used for testing. It does not
    serve much purpose now, as there is no listener for the 
    `module_conf_changed` signal.
    """

    app = QApplication(sys.argv)

    # Read FPM data and create module data
    fpm_config_data = '../../../data_taking/FPM_config.csv'
    module_conf = []
    with open(fpm_config_data) as csv_file:
        reader = csv.DictReader(csv_file)
        for fpm_config in reader:
            mod_id = int(fpm_config['module_id'])

            mod_data = ModuleConf(
                mod_id,
                int(fpm_config['fpm_sector']),
                int(fpm_config['fpm_position']),
                bool(random.randint(0, 4)),
                bool(random.randint(0, 2)),
                []
            )
            module_conf.append(mod_data)

    # Create the ModuleConfig dialog
    dialog = ModuleConfigurationDialog(module_conf)
    dialog.resize(600, 380)
    dialog.show()

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
