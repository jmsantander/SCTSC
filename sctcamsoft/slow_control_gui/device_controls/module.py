from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import pyqtSignal
import matplotlib
import matplotlib.patches as mpatches
from sctcamsoft.slow_control_gui.device_controls.device_controls import DeviceControls
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib import cm


class ModuleControls(DeviceControls):
    def __init__(self, widgets, update_signal,
                 timer_signal, send_command_slot):

        self.length=5
        self.width =5
        self.dpi = 105
        self.gView1 =widgets.graphicsView  #voltage
        self.gView2 =widgets.graphicsView_2 #current
        self.gView4 = widgets.graphicsView_4  #presence


        super().__init__('backplane', [],
                 widgets, 6, update_signal,timer_signal, send_command_slot)



    def draw(self):
        self._currents_update()
        self._voltage_update()
        self._presence_update()


    def _currents_update(self):
        c_threshold=1.5
        dr = Figure_Canvas(Figure(figsize=(self.length, self.width), dpi=self.dpi))
        # data1 = np.random.random(size=(5, 5))
        data1,_,_,= self._read_data()
        dr.display(data1,"A", c_threshold)
        graphicscene = QtWidgets.QGraphicsScene()
        graphicscene.addWidget(dr)
        self.gView1.setScene(graphicscene)
        self.gView1.show()

    def _voltage_update(self):
        v_threshold = 13
        dr = Figure_Canvas(Figure(figsize=(self.length, self.width), dpi=self.dpi))
        # data1 = np.random.random(size=(5, 5))
        _,data1, _, = self._read_data()
        dr.display(data1,"V",v_threshold)
        graphicscene = QtWidgets.QGraphicsScene()
        graphicscene.addWidget(dr)
        self.gView2.setScene(graphicscene)
        self.gView2.show()


    def _presence_update(self):
        p_threshold = 2
        dr = Figure_Canvas(Figure(figsize=(self.length, self.width), dpi=self.dpi))
        # data1 = np.random.random(size=(5, 5))
        _,_, data1 = self._read_data()
        dr.display(data1,"P",p_threshold)
        graphicscene = QtWidgets.QGraphicsScene()
        graphicscene.addWidget(dr)
        self.gView4.setScene(graphicscene)
        self.gView4.show()



    def _read_data(self):
        current = np.zeros(shape=(5, 5))
        voltage = np.zeros(shape=(5, 5))
        presence = np.zeros(shape=(5, 5))
        slot_dict = {2: (0,0), 3: (0,1), 1:(0,2), 5:(0,3), 4:(0,4),    #map FEE number to 2d array (https://confluence.slac.stanford.edu/display/CTA/Backplane-FEE+integration-at-Madison)
                    9: (1,0), 106: (1,1), 126:(1,2), 125:(1,3), 103:(1,4),
                    8: (2, 0), 121: (2, 1), 110: (2, 2), 108: (2, 3), 119: (2, 4),
                    7: (3, 0), 112: (3, 1), 124: (3, 2), 123: (3, 3), 115: (3, 4),
                    6: (4, 0), 107: (4, 1), 114: (4, 2), 111: (4, 3), 100: (4, 4),}

        _current = self.get_val('current')  # currents is a list of namedtuples
        _voltage = self.get_val('voltage')
        _presence = self.get_val('presence')

        
        try:
            for i in _current[:][:]:  # for each element in 2d list
                index1 = slot_dict[int(i.identifier)]  # i[0]: FEE number
                current[index1] = float(i.value)
            current = np.around(current, decimals=1)
        except Exception as e:
            # print(" current is not ready:", e)
            pass
        try:
            for i in _voltage[:][:]:  # for each element in 2d list
                index1 = slot_dict[int(i.identifier)]  # i[0]: FEE number
                voltage[index1] = float(i.value)
            voltage = np.around(voltage, decimals=1)
        except Exception as e:
            # print(" voltage is not ready:", e)
            pass
        try:
            for i in _presence[:][:]:  # for each element in 2d list
                index1 = slot_dict[int(i.identifier)]  # i[0]: FEE number
                presence[index1] = float(i.value)
            presence = np.around(presence, decimals=1)
        except Exception as e:
            # print(" presence is not ready:", e)
            pass
        return current, voltage , presence

class Figure_Canvas(FigureCanvas): #https://matplotlib.org/users/artists.html
   def __init__(self, fig):
        self.fig=fig
        FigureCanvas.__init__(self, self.fig)  # initialize father class
        self.axes = self.fig.add_subplot(1, 1,1)  # call add_subplot method in figure，(similiar to subplot method in matplotlib.pyplot)
        self.vmin=0
        self.vmax=0

   def find_map_range(self, data):
       self.vmin = np.amin(data)
       self.vmax = np.amax(data)

   def display(self,data, unit, threshold): #show 2-D data
       self.data = data
       self.unit = unit

       self.find_map_range(self.data)
       self.data1 = np.copy(self.data)



       #color bar
       if self.unit=="S":   #if it's the Module States panel
           cmap = cm.get_cmap('viridis', 7)  # 11 discrete colors
           self.im = self.axes.imshow(self.data1, cmap=cmap, interpolation='nearest',vmax=3,vmin=-3)  # #viridis
           divider = make_axes_locatable(self.axes)
           cax = divider.append_axes("right", size="5%", pad=0.05)
           self.cbar = self.fig.colorbar(self.im, cax=cax)
       else:
           self.data1[(self.data1 > threshold)] = self.vmax  # set threshold for alert, marked as red color
           self.im = self.axes.imshow(self.data1, cmap="rainbow", interpolation='nearest')  # #viridis
           divider = make_axes_locatable(self.axes)
           cax = divider.append_axes("right", size="5%", pad=0.05)
           self.cbar=self.fig.colorbar(self.im,cax=cax)
           self.axes.text(4, 0, self.unit, position=(4 + 0.5, 0 - 0.6), rotation=0)  # position: x: + go right - go left


       # create white grid.
       for edge, spine in self.axes.spines.items(): # hide edges
           spine.set_visible(False)
       self.axes.set_xticks(np.arange(5) - .5, minor=True) #set monor ticks for drawing gird
       self.axes.set_yticks(np.arange(5) - .5, minor=True)
       self.axes.grid(which="minor", color="w", linestyle='-', linewidth=6)
       self.axes.tick_params(which="both", bottom=False, left=False, labelbottom=False, labelleft=False) #hide the tick  (major and minor)
       #heat map: mapping all data to the image
       self.data2 = np.around(self.data, decimals=1)
       for i in range(5):
           for j in range(5):
               text = self.axes.text(i, j, self.data2[j, i],
                                     position=(i-0.1, j+0.2), color="white")
       # mapping all mudole IDs
       slot = np.array( [ [2, 3, 1 ,5 , 4],    #sky view, reflected on y axis
                                [9, 106, 126, 125, 103] ,
                                [8, 121, 110, 108, 119] ,
                                [7, 112, 124, 123, 115] ,
                                [6, 107, 114, 111, 100]   ]  )
       for i in range(5):
           for j in range(5):
               text = self.axes.text(i, j, slot[j,i],
                             position=(i-0.4,j-0.2), color="black")



