
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import pyqtSignal
import matplotlib
import matplotlib.patches as mpatches
from sctcamsoft.slow_control_gui.device_controls.device_controls import DeviceControls
import os,sys
import glob
from pathlib import Path
from matplotlib import colors
import json
from mpl_toolkits.axes_grid1 import make_axes_locatable

class FeeTempControls(DeviceControls):
    def __init__(self,widgets, update_signal,
                 timer_signal, send_command_slot):

        self.length = 5
        self.width = 5
        self.dpi = 105
        self.gView3 = widgets.graphicsView_3

        super().__init__('fee_temperature', [],
                 widgets, 6, update_signal,
                 timer_signal, send_command_slot)

    def draw(self):
        self._temp_update()

    def _temp_update(self):
        dr = Figure_Canvas(Figure(figsize=(self.length, self.width), dpi=self.dpi))
        data,last_run_num = self._read_temp()

        dr.display(data,last_run_num)
        graphicscene = QtWidgets.QGraphicsScene()
        graphicscene.addWidget(dr)
        self.gView3.setScene(graphicscene)
        self.gView3.show()

    def _read_temp(self):
        data1= np.zeros(shape=(5, 5))
        slot_dict = {2: (0,0), 3: (0,1), 1:(0,2), 5:(0,3), 4:(0,4),    #map FEE number to 2d array (https://confluence.slac.stanford.edu/display/CTA/Backplane-FEE+integration-at-Madison)
                    9: (1,0), 106: (1,1), 126:(1,2), 125:(1,3), 103:(1,4),
                    8: (2, 0), 121: (2, 1), 110: (2, 2), 108: (2, 3), 119: (2, 4),
                    7: (3, 0), 112: (3, 1), 124: (3, 2), 123: (3, 3), 115: (3, 4),
                    6: (4, 0), 107: (4, 1), 114: (4, 2), 111: (4, 3), 100: (4, 4),}

        temperatures = self.get_val('temperature') # temperatures is a list of namedtuples
        last_run_number = self.get_val('last_run_num')
        try:
            for i in temperatures[:][:]:  # for each element in 2d list
                     index1=slot_dict[int(i.identifier)] #  i[0]: FEE number
                     data1[index1]=float(i.value)    #  i[1]: temp   how to format to 3 significant figures
            data1=np.around(data1, decimals=1)
        except Exception as e:
            #print("Temperature data is not ready:",e)
            pass
        return data1, last_run_number

class Figure_Canvas(FigureCanvas): #https://matplotlib.org/users/artists.html
   def __init__(self, fig):
        self.fig=fig
        FigureCanvas.__init__(self, self.fig)  # initialize father class
        self.axes = self.fig.add_subplot(1,1,1)  # call add_subplot method in figure，(similiar to subplot method in matplotlib.pyplot)
        self.vmin=0
        self.vmax=0
   def find_map_range(self,data):
       self.vmin=np.amin(data)
       self.vmax = np.amax(data)

   def display(self,data, run_id): #show 2-D data
       self.find_map_range(data)

       self.data1=np.copy(data)
       self.data1[(self.data1 > 41)] = self.vmax  # set threshold for alert, marked as red color

       self.im = self.axes.imshow(self.data1, cmap="rainbow", interpolation='nearest',vmin=self.vmin, vmax=self.vmax)# #viridis
       #color bar
       divider = make_axes_locatable(self.axes)
       cax = divider.append_axes("right", size="5%", pad=0.05)
       self.cbar=self.fig.colorbar(self.im,cax=cax)

       self.axes.text(4,0,"°C", position=(4+0.5,0-0.6),rotation=0)  # position: x: + go right - go left

       try:
           self.fig.suptitle("Last Run ID:"+run_id)  #if run_id is not NoneType
       except:
           self.fig.suptitle("Last Run ID:")

       #heat map: mapping all data to the image
       for i in range(5):
           for j in range(5):
               text = self.axes.text(i, j, data[j,i],
                                     position=(i - 0.1, j + 0.2), color="white")
       # mapping all mudole IDs

       ##to do: the value here is inconsistant with the actual color
       slot = np.array( [ [2, 3, 1 ,5 , 4],
                                [9, 106, 126, 125, 103] ,
                                [8, 121, 110, 108, 119] ,
                                [7, 112, 124, 123, 115] ,
                                [6, 107, 114, 111, 100]   ]  )
       for i in range(5):
           for j in range(5):
               text = self.axes.text(i,j, slot[j,i],
                             position=(i-0.4,j-0.2), color="black")   #position of text in each module

       #create white grid. https://matplotlib.org/3.1.0/gallery/images_contours_and_fields/image_annotated_heatmap.html#sphx-glr-gallery-images-contours-and-fields-image-annotated-heatmap-py
       for edge, spine in self.axes.spines.items(): # hide edges
           spine.set_visible(False)
       self.axes.set_xticks(np.arange(5) - .5, minor=True) #set monor ticks for drawing gird
       self.axes.set_yticks(np.arange(5) - .5, minor=True)
       self.axes.grid(which="minor", color="w", linestyle='-', linewidth=6)
       self.axes.tick_params(which="both", bottom=False, left=False,labelbottom=False, labelleft=False) #hide the tick


