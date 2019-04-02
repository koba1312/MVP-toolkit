import requests
import jdcal
import datetime
import numpy as np
import matplotlib.pyplot as plt
import telnetlib
import re
from pprint import pprint
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.proj3d import proj_transform
from matplotlib.text import Annotation
from matplotlib import colors
from matplotlib import pyplot as plt
from pathlib import Path
import pickle
import tkinter
from tkinter.colorchooser import *
import operator
import csv
import configparser,ast

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.ticker import ScalarFormatter
# Implement the appearance Matplotlib key bindings.
from matplotlib.backend_bases import key_press_handler
from tkcalendar import DateEntry,Calendar
from tkinter import filedialog
# import io
# from PIL import Image

class celestial_artist:
    def __init__(self,id,orbit,pos,date,name,text):
        self.id = id
        self.orbit_artist = None
        self.position_artist = None
        self.annotation_artist = None
        self.orbit = orbit
        self.pos = pos
        self.date = date
        self.color = None
        self.name = name
        self.displayname = name
        self.info_text = text

class plot_application:
    def __init__(self, master):
        self.master = master
        self.index = 0
        self.kepler_dict = {}
        self.planet_positions = []
        self.position_coordinates = []
        self.HOST = 'horizons.jpl.nasa.gov'
        self.port = '6775'
        self.filename = 'DBNumbers'
        self.filename2 = 'smallbodies'
        self.cursor = 'tcross'
        self.turn_cursor = 'exchange'
        self.zoom_cursor = 'sizing'
        self.JPL_numbers = []
        self.orbit_colors = []
        self.equinox_artists = []
        self.list = []
        self.current_objects = []

        self.default_colors = ['#191919','#7f7f7f','#ffffff','#000000']
        self.resolution = 80
        self.set_default_colors()
        self.gridlinewidth = 0.2
        self.textsize = 8
        self.markersize = 7
        self.orbit_linewidth = 1
        self.refplane_linewidth = 0.3
        self.text_xoffset = 0
        self.text_yoffset = 4
        self.check_config()

        self.view_cid = None
        self.formatter = ScalarFormatter(useMathText=True,useOffset=True)
        self.dt = datetime.datetime.now()
        self.dates = []
        self.julian_date =  "'" + str(sum(jdcal.gcal2jd(self.dt.year, self.dt.month, self.dt.day))) + "'"
        self.order_of_keplers = ['excentricity','periapsis_distance','inclination','Omega','omega','Tp','n','mean_anomaly','true_anomaly','a','apoapsis_distance','sidereal_period']
        self.objects = ["'399'","'499'","'-143205'"] #earth,mars,Tesla roadster, ... ceres : ,"'5993'"
        self.batchfile = {"COMMAND": "'399'","CENTER": "'500@10'","MAKE_EPHEM": "'YES'","TABLE_TYPE": "'ELEMENTS'","TLIST":self.julian_date,"OUT_UNITS": "'AU-D'","REF_PLANE": "'ECLIPTIC'","REF_SYSTEM": "'J2000'","TP_TYPE": "'ABSOLUTE'","ELEM_LABELS": "'YES'","CSV_FORMAT": "'YES'","OBJ_DATA": "'YES'"}
        self.my_file = Path("./"+self.filename+'.pkl')
        self.my_file2 = Path("./"+self.filename2+'.csv')
        self.search_term = tkinter.StringVar()
        self.search_term.set('')
        self.search_term.trace("w", lambda name, index, mode: self.update_listbox())
        self.prog_var = tkinter.DoubleVar(value = 0)
        self.check_db()

        self.fig = plt.figure(facecolor = self.custom_color)
        self.fig.subplots_adjust(left=0.01, right=0.99, bottom=0.01, top=0.99)
        self.master.wm_title("JPL horizons DB visualisation")
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.master)  # A tk.DrawingArea.
        self.pick_event_cid = self.fig.canvas.mpl_connect('pick_event',self.clicked_on)
        self.canvas.get_tk_widget().bind('<ButtonPress-1>',self.canvas_mouseturn,add='+')
        self.canvas.get_tk_widget().bind('<ButtonPress-3>',self.canvas_mousezoom,add='+')
        self.canvas.get_tk_widget().bind('<ButtonRelease-3>',self.canvas_mouserelease,add='+')
        self.canvas.get_tk_widget().bind('<ButtonRelease-1>',self.canvas_mouserelease,add='+')

        self.canvas.get_tk_widget().config(cursor=self.cursor)

        plt.rcParams['savefig.facecolor']= self.custom_color
        plt.rcParams['grid.color'] = self.gridcolor
        plt.rcParams['grid.linewidth'] = self.gridlinewidth

        self.ax = self.fig.gca(projection = '3d',facecolor =  self.custom_color,proj_type = 'ortho')

        self.canvas.get_tk_widget().grid(row=0,column=0,columnspan=10,rowspan=10,sticky=tkinter.N+tkinter.W+tkinter.E+tkinter.S)
        self.viewbuttons_frame = tkinter.Frame(master= self.canvas.get_tk_widget())
        self.viewbuttons_frame.place(rely=1,relx=0,anchor=tkinter.SW)

        # self.equinox_cid = self.ax.callbacks.connect('xlim_changed',self.scale_equinox)

        self.menubar = tkinter.Menu(self.master)
        self.filemenu = tkinter.Menu(self.menubar,tearoff = 0)
        self.filemenu.add_command(label="save figure as", command=self.save_file_as)
        self.filemenu.add_command(label="preferences", command=self.preferences_menu)
        self.filemenu.add_separator()
        self.filemenu.add_command(label="Exit", command=self.master.quit)
        self.menubar.add_cascade(label='File',menu=self.filemenu)

        self.master.config(menu=self.menubar)

        self.button1 = tkinter.Button(master=self.master, text="new Plot", command=lambda : self.refresh_plot(True))
        self.button1.grid(row=3,column=11,columnspan=2,sticky=tkinter.N+tkinter.W+tkinter.E)
        self.button2  = tkinter.Button(master=self.master, text="add to Plot", command=lambda : self.refresh_plot(False))
        self.button2.grid(row=4,column=11,columnspan=2,sticky=tkinter.N+tkinter.W+tkinter.E)
        self.topview_button = tkinter.Button(master=self.viewbuttons_frame,text='TOP',borderwidth = 3, command=lambda:self.change_view('top'))
        self.topview_button.configure(width=3,height=1)
        self.topview_button.grid(row=0,column=0)
        self.rightview_button = tkinter.Button(master=self.viewbuttons_frame,text='XZ',borderwidth = 3, command=lambda:self.change_view('XZ'))
        self.rightview_button.configure(width=3,height=1)
        self.rightview_button.grid(row=0,column=1)
        self.xyzview_button = tkinter.Button(master=self.viewbuttons_frame,text='XYZ',borderwidth = 3,command=lambda:self.change_view('XYZ'))
        self.xyzview_button.configure(width=3,height=1)
        self.xyzview_button.grid(row=0,column=3)


        self.listbox = tkinter.Listbox(master=self.master,selectmode=tkinter.MULTIPLE,exportselection=False)
        self.listbox.grid(row=0,column=11,columnspan=2,sticky=tkinter.N+tkinter.W+tkinter.E+tkinter.S)
        tkinter.Label(master=self.master,text= 'type search term:').grid(row=1,column=11,sticky=tkinter.N+tkinter.W)
        self.search_box = tkinter.Entry(master=self.master, textvariable=self.search_term)
        self.search_box.grid(row=1,column=12,sticky=tkinter.N+tkinter.W)
        self.calendar_widget = Calendar(self.master,font="Arial 18", selectmode='day',cursor="hand1", year=self.dt.year, month=self.dt.month, day=self.dt.day)
        self.calendar_widget.grid(row=5,column=11,columnspan=2,sticky=tkinter.N+tkinter.W+tkinter.E+tkinter.S)
        self.refplane_var = tkinter.IntVar(value=0)
        self.annot_var = tkinter.IntVar(value=0)
        self.axis_var = tkinter.IntVar(value=1)
        self.proj_var = tkinter.IntVar(value=0)
        self.refplane_checkbutton = tkinter.Checkbutton(master=self.master,text='referenceplane lines',variable = self.refplane_var,command=self.redraw_current_objects).grid(row=6,column=11,sticky=tkinter.N+tkinter.W)
        self.annot_checkbutton = tkinter.Checkbutton(master=self.master,text='show date at objectposition',variable = self.annot_var,command=self.redraw_current_objects).grid(row=6,column=12,sticky=tkinter.N+tkinter.W)
        self.axis_checkbutton = tkinter.Checkbutton(master=self.master,text='show coordinate axis',variable = self.axis_var,command=self.toggle_axis).grid(row=7,column=11,sticky=tkinter.N+tkinter.W)
        self.proj_checkbutton = tkinter.Checkbutton(master=self.master,text='perspective projection',variable = self.proj_var,command=self.toggle_proj).grid(row=7,column=12,sticky=tkinter.N+tkinter.W)
        self.prog_bar = tkinter.ttk.Progressbar(self.master,orient='horizontal',length=200,mode='determinate')
        self.prog_bar.grid(row=8,column=11,columnspan=2,sticky=tkinter.S+tkinter.W+tkinter.E)
        for k,v in self.JPL_numbers.items():
            self.listbox.insert(tkinter.END,v)
        self.canvas.draw()

        self.nu = np.linspace(0,2*np.pi,self.resolution)
        orbits,positions = self.request_keplers(self.objects,self.batchfile)
        if orbits == False:
            pass
        else:
            # self.current_objects = {'orbits':orbits,'positions':positions}
            self.plot_orbits(self.ax,self.current_objects,refresh_canvas=True,refplane_var=self.refplane_var.get())
            # self.current_objects['dates'] = dates
            # self.current_objects['colors'] = colors
            # self.current_objects['artists'] = artists

        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

    class Annotation3D(Annotation):
        '''Annotate the point xyz with text s'''

        def __init__(self, s, xyz, *args, **kwargs):
            Annotation.__init__(self,s, xy=(0,0), *args, **kwargs)
            self._verts3d = xyz


        def draw(self, renderer):
            xs3d, ys3d, zs3d = self._verts3d
            xs, ys, zs = proj_transform(xs3d, ys3d, zs3d, renderer.M)
            self.xy=(xs,ys)
            Annotation.draw(self, renderer)

    def set_default_colors(self,redraw=False,buttons=None):
        '''sets colors to default, if buttons handed over: colors them accordingly'''
        self.custom_color =  self.default_colors[0]
        self.gridcolor = self.default_colors[1]
        self.text_color = self.default_colors[2]
        self.pane_color = self.default_colors[3]
        if redraw:
            self.redraw_current_objects()
            counter = 0
            for b in buttons:
                b.configure(bg=self.default_colors[counter])
                counter = counter + 1

    def check_config(self):
        '''check if config exists, makes default config if not'''
        file = Path("./config.ini")
        config = configparser.ConfigParser()
        if file.is_file():
            print('config found, reading from ./config.ini')
            config.read('config.ini')
            self.custom_color = config['appearance']['custom_color']
            self.gridcolor = config['appearance']['gridcolor']
            self.text_color = config['appearance']['text_color']
            self.pane_color = config['appearance']['pane_color']
            self.gridlinewidth = float(config['appearance']['gridlinewidth'])
            self.textsize = float(config['appearance']['textsize'])
            self.markersize = float(config['appearance']['markersize'])
            self.orbit_linewidth = float(config['appearance']['orbit_linewidth'])
            self.refplane_linewidth = float(config['appearance']['refplane_linewidth'])
            self.text_xoffset = float(config['appearance']['text_xoffset'])
            self.text_yoffset = float(config['appearance']['text_yoffset'])


        else:
            print('no config found, generating new ./config.ini')
            self.update_config()

    def update_config(self):
        '''update configfile with current memory variables'''
        config = configparser.ConfigParser()
        config['appearance'] = \
        {\
        'custom_color':str(self.custom_color), 'gridcolor':str(self.gridcolor),\
        'gridlinewidth':str(self.gridlinewidth), 'textsize':str(self.textsize), 'markersize':str(self.markersize),\
        'orbit_linewidth':str(self.orbit_linewidth), 'refplane_linewidth':str(self.refplane_linewidth),\
        'text_xoffset':str(self.text_xoffset), 'text_yoffset':str(self.text_yoffset), 'text_color':str(self.text_color),\
        'pane_color':str(self.pane_color)
        }
        with open('config.ini', 'w') as configfile:
            config.write(configfile)

    def canvas_mouseturn(self,event):
        self.canvas.get_tk_widget().config(cursor=self.turn_cursor)

    def canvas_mousezoom(self,event):
        self.canvas.get_tk_widget().config(cursor=self.zoom_cursor)

    def canvas_mouserelease(self,event):
        self.canvas.get_tk_widget().config(cursor=self.cursor)

    def hex_to_rgb(self,h,alpha=1):
        '''takes hex color code and returns rgb-alpha tuple'''
        h = h.strip('#')
        h = tuple(int(h[i:i+2], 16) for i in (0, 2 ,4))
        h = (h[0]/255,h[1]/255,h[2]/255,alpha)
        return h

    def save_file_as(self):
        '''saves figure (currently redraws figure and toggles visibility of axis to true)'''
        dir = filedialog.asksaveasfilename(defaultextension=".png")
        if dir == '' or dir == ():
            return
        print(dir)
        self.fig.canvas.mpl_disconnect(self.view_cid)
        plt.savefig(dir)
        # self.axis_visibility(None,'z',True)
        # self.axis_visibility(None,'y',True)

        '''does weird stuff with the image (atrifacts)'''
        # ps = self.canvas.get_tk_widget().postscript(colormode='color')
        # img = Image.open(io.BytesIO(ps.encode('utf-8')))
        # img.save(dir)

    def get_color(self,b):
        color=askcolor(b.cget('bg'))
        if None in color:
            return
        b.configure(bg=color[1])

    def preferences_menu(self):
        '''toplevel menu to adjust config file'''
        def validate(action, index, value_if_allowed,prior_value, text, validation_type, trigger_type, widget_name):
            if text in '0123456789.-+':
                try:
                    float(value_if_allowed)
                    return True
                except ValueError:
                    return False
            else:
                return False

        top = tkinter.Toplevel()

        x = root.winfo_x()
        y = root.winfo_y()
        top.geometry("+%d+%d" % (x + 10, y + 20))
        top.title("preferences")

        textsize_var = tkinter.StringVar()
        textsize_var.set(str(self.textsize))

        appearance_frame =  tkinter.LabelFrame(top, text= 'appearance')
        appearance_frame.grid(row=0,column= 0)

        button_frame = tkinter.Frame(top)
        button_frame.grid(row=1,column=0)

        vcmd = (appearance_frame.register(validate),'%d', '%i', '%P', '%s', '%S', '%v', '%V', '%W')

        tkinter.Label(appearance_frame,text='background color:').grid(row=0,column=0)
        custom_color_button = tkinter.Button(appearance_frame,text='',bg = self.custom_color ,command=lambda: self.get_color(custom_color_button), width=10)
        custom_color_button.grid(row=0,column=1,sticky=tkinter.E)
        tkinter.Label(appearance_frame,text='grid color:').grid(row=1,column=0)
        grid_color_button = tkinter.Button(appearance_frame,text='',bg = self.gridcolor ,command=lambda: self.get_color(grid_color_button), width=10)
        grid_color_button.grid(row=1,column=1,sticky=tkinter.E)
        tkinter.Label(appearance_frame,text='text color:').grid(row=2,column=0)
        text_color_button = tkinter.Button(appearance_frame,text='',bg = self.text_color ,command=lambda: self.get_color(text_color_button), width=10)
        text_color_button.grid(row=2,column=1,sticky=tkinter.E)
        tkinter.Label(appearance_frame,text='pane color:').grid(row=3,column=0)
        pane_color_button = tkinter.Button(appearance_frame,text='',bg = self.pane_color ,command=lambda: self.get_color(pane_color_button), width=10)
        pane_color_button.grid(row=3,column=1,sticky=tkinter.E)

        tkinter.Label(appearance_frame,text='textsize:').grid(row=4,column=0,sticky=tkinter.W)
        tkinter.Entry(appearance_frame, validate='key', validatecommand = vcmd,textvariable=textsize_var).grid(row=4,column=1,sticky=tkinter.E)

        dismiss_button = tkinter.Button(button_frame, text="cancel", command=top.destroy)
        dismiss_button.grid(row=0,column=0)
        accept_button = tkinter.Button(button_frame, text="save and apply", command = lambda: self.update_config_vars(custom_color_button,grid_color_button,text_color_button,pane_color_button,textsize_var.get()))
        accept_button.grid(row=0,column=1)
        default_button = tkinter.Button(button_frame, text='default colors', command = lambda: self.set_default_colors(redraw=True,buttons =[custom_color_button,grid_color_button,text_color_button,pane_color_button] ))
        default_button.grid(row=0,column=3)
        top.resizable(width=False,height=False)
        top.attributes('-topmost',1)

    def update_config_vars(self,custom_color_button,grid_color_button,text_color_button,pane_color_button,textsize_var):
        '''get colors of preference buttons, update config file and redraw figure with new colors'''
        self.custom_color = custom_color_button.cget('bg')
        self.gridcolor = grid_color_button.cget('bg')
        self.text_color = text_color_button.cget('bg')
        self.pane_color = pane_color_button.cget('bg')
        self.textsize = float(textsize_var)
        self.update_config()
        self.redraw_current_objects()

    def annotate3D(self,ax, s, *args, **kwargs):
        '''add anotation text s to to Axes3d ax'''

        tag = self.Annotation3D(s, *args, **kwargs)
        ax.add_artist(tag)
        return tag

    def rot_x(self,phi):
        '''returns rotational matrix around x, phi in rad'''
        return np.array([[1,0,0],[0,np.cos(phi),-np.sin(phi)],[0,np.sin(phi),np.cos(phi)]])
    def rot_z(self,rho):
        '''returns rotational matrix around z, rho in rad'''
        return np.array([[np.cos(rho),-np.sin(rho),0],[np.sin(rho),np.cos(rho),0],[0,0,1]])

    def change_view(self,view):
        '''sets the view angles of the plot and toggles visibility of the perpendicular axis to false until plot is moved/refreshed   '''
        if view == "top":
            self.axis_visibility(event = None,axis='z',visible=False) #produces clicking on artist beeing unresponsive
            self.ax.view_init(90,-90)
            self.view_cid = self.fig.canvas.mpl_connect('draw_event',lambda event: self.axis_visibility(event,axis='z',visible=True))
        elif view == "XZ":
            self.axis_visibility(event = None,axis='y',visible=False) #produces clicking on artist beeing unresponsives
            self.ax.view_init(0,-90)
            self.view_cid = self.fig.canvas.mpl_connect('draw_event',lambda event: self.axis_visibility(event,axis='y',visible=True))
        elif view == "XYZ":
            self.ax.view_init(45,-45)
        self.canvas.draw()


    def axis_visibility(self,event,axis,visible):
        if axis == 'z':
            self.ax.set_zticklabels(self.ax.get_zticklabels(),visible=visible)
            self.ax.set_zlabel(self.ax.get_zlabel(),visible=visible)
            # if visible:
            #     self.ax.tick_params(axis='z', colors=self.text_color)
            # else:
            #     self.ax.tick_params(axis='z', colors=self.custom_color)
        elif axis == 'y':
            self.ax.set_yticklabels(self.ax.get_yticklabels(),visible=visible)
            self.ax.set_ylabel(self.ax.get_ylabel(),visible=visible)
        elif axis == 'x':
            self.ax.set_xticklabels(self.ax.get_xticklabels(),visible=visible)
            self.ax.set_xlabel(self.ax.get_xlabel(),visible=visible)
        if self.view_cid != None:
            self.fig.canvas.mpl_disconnect(self.view_cid)


    def scale_equinox(self,event):
        '''function to draw a scaling vector-arrow on the x-axis(equinox)'''
        self.fig.canvas.mpl_disconnect(self.equinox_cid)
        if len(self.equinox_artists)>0:
            for i in range(0,len(self.equinox_artists)):
                if i == 3:
                    self.equinox_artists[i].remove()
                    continue
                self.equinox_artists[i][0].remove()
        self.equinox_artists = []
        xlim = self.ax.get_xlim()
        length = 0.15 *xlim[1]
        self.equinox_artists.append(self.ax.plot([0,length] , [0,0],[0,0],color=self.text_color,linewidth=self.refplane_linewidth))
        self.equinox_artists.append(self.ax.plot([length,0.7*length],[0,0.05*length],[0,0.05*length],color=self.text_color,linewidth=self.refplane_linewidth))
        self.equinox_artists.append(self.ax.plot([length,0.7*length],[0,-0.05*length],[0,-0.05*length],color=self.text_color,linewidth=self.refplane_linewidth))
        self.equinox_artists.append(self.annotate3D(self.ax, s='vernal equinox', xyz=[length,0,0], fontsize=self.textsize, xytext=(self.text_xoffset,-self.text_yoffset),textcoords='offset points', ha='center',va='top',color = self.text_color))
        self.equinox_cid = self.ax.callbacks.connect('xlim_changed',self.scale_equinox)

    def orbit_position(self,a,e,Omega,i,omega,true_anomaly=False):
        '''calculate orbit 3x1 radius vector'''
        if not(true_anomaly==False):
            p = a * (1-(e**2))
            r = p/(1+e*np.cos(true_anomaly))
            r = np.array([np.multiply(r,np.cos(true_anomaly)) , np.multiply(r,np.sin(true_anomaly)), np.zeros(len(true_anomaly))])
            r = np.matmul(self.rot_z(omega),r)
            r = np.matmul(self.rot_x(i),r)
            r = np.matmul(self.rot_z(Omega),r)
        elif e <=1:
            # e = 1 atually wrong, here just to prevent crash, exact excentricity of 1 should not happen
            p = a * (1-(e**2))
            r = p/(1+e*np.cos(self.nu))
            r = np.array([np.multiply(r,np.cos(self.nu)) , np.multiply(r,np.sin(self.nu)), np.zeros(len(self.nu))])
            r = np.matmul(self.rot_z(omega),r)
            r = np.matmul(self.rot_x(i),r)
            r = np.matmul(self.rot_z(Omega),r)
        elif e >1:
            if self.kepler_dict["true_anomaly"] > 2:
                plot_range = 3*np.pi/4
                if plot_range < np.abs(self.kepler_dict["true_anomaly"]):
                    plot_range = np.abs(self.kepler_dict["true_anomaly"])
            else:
                plot_range = 3/4 * np.pi -np.pi
                if plot_range > np.abs(self.kepler_dict["true_anomaly"]):
                    plot_range = np.abs(self.kepler_dict["true_anomaly"])
            nu = np.linspace(-plot_range,plot_range,self.resolution)
            p = a * (1-(e**2))
            r = p/(1+e*np.cos(nu))
            r = np.array([np.multiply(r,np.cos(nu)) , np.multiply(r,np.sin(nu)), np.zeros(len(nu))])
            r = np.matmul(self.rot_z(omega),r)
            r = np.matmul(self.rot_x(i),r)
            r = np.matmul(self.rot_z(Omega),r)
        return r

    def axisEqual3D(self,ax):
        '''fix for axis equal bug in 3D (z wont equal)'''
        extents = np.array([getattr(ax, 'get_{}lim'.format(dim))() for dim in 'xyz'])
        sz = extents[:,1] - extents[:,0]
        centers = np.mean(extents, axis=1)
        maxsize = max(abs(sz))
        r = maxsize/2
        for ctr, dim in zip(centers, 'xyz'):
            getattr(ax, 'set_{}lim'.format(dim))(ctr - r, ctr + r)

    def save_obj(self,obj, name ):
        with open('./'+ name + '.pkl', 'wb') as f:
            pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)

    def load_obj(self,name):
        with open('./' + name + '.pkl', 'rb') as f:
            return pickle.load(f)

    def _quit(self):
        self.master.quit()     # stops mainloop
        # root.destroy()  # this is necessary on Windows to prevent
                        # Fatal Python Error: PyEval_RestoreThread: NULL tstate

    def sort_vals(self,dictionary):
        '''sort dictionary values'''
        sorted_x = sorted(dictionary.items(), key=operator.itemgetter(1))
        return dict(sorted_x)

    def get_selected(self):
        '''get selected items from listbox'''
        user_choice = []
        index_list = map(int,self.listbox.curselection())
        for i in index_list:
            user_choice.append(self.listbox.get(i))
        return user_choice

    def refresh_plot(self,clear_axis = True):
        '''new plot, dismisses existing objects'''
        print('refreshing')
        if clear_axis:
            self.current_objects = []
            self.objects = []
        objects = self.get_selected()
        objects = [self.JPL_name2num[object] for object in objects]
        self.objects.extend(objects)
        orbits,positions = self.request_keplers(objects,self.batchfile)
        if orbits == False:
            pass
        else:
            self.plot_orbits(self.ax,self.current_objects,refresh_canvas = True,refplane_var=self.refplane_var.get())



    def plot_orbits(self,ax,objects,refresh_canvas=True,refplane_var = 1):
        '''plots orbits, positions and annotations'''

        self.ax.cla()

        plt.rcParams['savefig.facecolor']= self.custom_color
        plt.rcParams['grid.color'] = self.gridcolor
        plt.rcParams['grid.linewidth'] = self.gridlinewidth
        self.fig.set(facecolor = self.custom_color)
        self.ax.set(facecolor = self.custom_color)

        ax.scatter(0,0,0,marker='o',s = 20,color='yellow')
        self.annotate3D(ax, s='sun', xyz=[0,0,0], fontsize=self.textsize, xytext=(self.text_xoffset,self.text_yoffset),textcoords='offset points', ha='center',va='bottom',color ="white")
        ax.set_xlabel('X axis in AU')
        ax.set_ylabel('Y axis in AU')
        ax.set_zlabel('Z axis in AU')
        ax.xaxis.label.set_color(self.text_color)
        ax.yaxis.label.set_color(self.text_color)
        ax.zaxis.label.set_color(self.text_color)
        ax.tick_params(axis='x', colors=self.text_color)
        ax.tick_params(axis='y', colors=self.text_color)
        ax.tick_params(axis='z', colors=self.text_color)
        ax.w_xaxis.set_pane_color(self.hex_to_rgb(self.pane_color))
        ax.w_yaxis.set_pane_color(self.hex_to_rgb(self.pane_color))
        ax.w_zaxis.set_pane_color(self.hex_to_rgb(self.pane_color))

        for object in objects:
            if None in object.orbit:
                continue
            orbit = object.orbit
            pos = object.pos
            if object.color == None:
                object.orbit_artist = ax.plot(orbit[0],orbit[1],orbit[2],linewidth=self.orbit_linewidth,clip_on=False)
            else:
                object.orbit_artist = ax.plot(orbit[0],orbit[1],orbit[2],color=object.color,linewidth=self.orbit_linewidth,clip_on=False)
            if refplane_var == 1:
                     for x,y,z in zip(*object.orbit.tolist()):
                         ax.plot([x,x],[y,y],[z,0],'white',linewidth=self.refplane_linewidth,clip_on=False)

            color = object.orbit_artist[0].get_color()
            object.color = color

            object.position_artist = self.ax.plot(pos[0],pos[1],pos[2], marker='o', MarkerSize=self.markersize,MarkerFaceColor=color ,markeredgecolor = color ,clip_on=False,picker=5)
            object.annotation_artist = self.annotate3D(ax, s=object.displayname, xyz=[pos[0],pos[1],pos[2]], fontsize=self.textsize, xytext=(self.text_xoffset,self.text_yoffset),textcoords='offset points', ha='center',va='bottom',color = self.text_color,clip_on=False)
            if self.annot_var.get() == 1:
                self.annotate3D(ax, s=str(object.date), xyz=[pos[0],pos[1],pos[2]], fontsize=self.textsize, xytext=(self.text_xoffset,-self.text_yoffset),textcoords='offset points', ha='center',va='top',color = self.text_color,clip_on=False)

        # # # recompute the ax.dataLim
        # # ax.relim()
        # # # update ax.viewLim using the new dataLim
        # # ax.autoscale(True)
        #
        self.axisEqual3D(ax)
        ylim = np.max(np.abs(self.ax.get_ylim()))
        xlim = np.max(np.abs(self.ax.get_xlim()))
        zlim = np.max(np.abs(self.ax.get_zlim()))
        max = np.amax([ylim,xlim,zlim])
        self.ax.set_ylim([-max, max])
        self.ax.set_xlim([-max, max])
        self.ax.set_zlim([-max, max])

        # self.formatter.set_scientific(True)
        # self.ax.xaxis.set_major_formatter(self.formatter)
        # self.ax.yaxis.set_major_formatter(self.formatter)

        # self.scale_equinox(None)
        # ylim = self.ax.get_ylim()
        # xlim = self.ax.get_xlim()
        # self.ax.plot([20*xlim[0],20*xlim[1]],[0,0],[0,0],linewidth=0.3,clip_on=False,color='white')
        # self.ax.plot([0,0],[20*ylim[0],20*ylim[1]],[0,0],linewidth=0.3,clip_on=False,color='white')

        if self.axis_var.get() == 1:
            self.ax.set_axis_on()
        else:
            self.ax.set_axis_off()

        if refresh_canvas:
            self.canvas.draw()
        return # marker_artists,orbit_colors,dates

    def on_closing(self):
        if tkinter.messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.master.quit()

    def error_message(self,title,message):
        '''generates an error message-popup with generic title and message'''
        tkinter.messagebox.showerror(title,message)

    def request_keplers(self,objects,batchfile,errors=0):
        '''requests kepler elements from HORIZONS-batch-interface for objects'''
        print('requesting keplers for selected items')
        orbits = []
        positions = []

        self.prog_bar["maximum"] = len(objects)

        count = 0
        for object in objects:
            batchfile['COMMAND'] = object
            self.dt = self.calendar_widget.selection_get()
            batchfile['TLIST'] = "'" + str(sum(jdcal.gcal2jd(self.dt.year, self.dt.month, self.dt.day))) + "'"
            try:
                r = requests.get("https://ssd.jpl.nasa.gov/horizons_batch.cgi?batch=1", params = batchfile,timeout=2.0)
            except (requests.exceptions.ConnectionError,requests.exceptions.Timeout):
                print('connection failed, retrying...')
                if errors<=2:
                    return self.request_keplers(objects,batchfile,errors = errors+1)
                self.error_message('Connection Error','Could not reach the Server, please check your internet connection.')
                return False,False

            # print(r.text)
            count = count + 1
            self.prog_bar["value"] = count
            self.prog_bar.update()
            if 'No ephemeris for target' in r.text:
                print('No ephemeris for target{0} at date {1}'.format(self.JPL_numbers[object],self.dt))
                orbit = [None,None]
                position = [None,None]
                orbits.append([None,None])
                positions.append([None,None])
            elif 'is out of bounds, no action taken' in r.text:
                print('{0} is out of bounds, no action taken (couldnt find {1} in batch interface of JPL horizonss)'.format(self.JPL_numbers[object],object))
                orbit = [None,None]
                position = [None,None]
                orbits.append([None,None])
                positions.append([None,None])
            elif 'No such record, positive values only' in r.text:
                print('No record for {0}({1}), positive values only'.format(object,self.JPL_numbers[object]))
                orbit = [None,None]
                position = [None,None]
                orbits.append([None,None])
                positions.append([None,None])
            else:
                keplers = r.text.split('$$SOE')[1].split('$$EOE')[0].replace(' ','').split(',')
                del keplers[0:2]
                del keplers[-1]
                keplers = [float(element) for element in keplers]
                for i in range(len(keplers)):
                    self.kepler_dict[self.order_of_keplers[i]] = keplers[i]
                self.kepler_dict['Omega'] = np.deg2rad(self.kepler_dict['Omega'])
                self.kepler_dict['inclination'] = np.deg2rad(self.kepler_dict['inclination'])
                self.kepler_dict['omega'] = np.deg2rad(self.kepler_dict['omega'])
                self.kepler_dict['true_anomaly'] = np.deg2rad(self.kepler_dict['true_anomaly'])
                print('\n\n{0}:\n'.format(self.JPL_numbers[object]))
                pprint(self.kepler_dict)
                orbit = self.orbit_position(self.kepler_dict['a'],self.kepler_dict['excentricity'],self.kepler_dict['Omega'],self.kepler_dict['inclination'],self.kepler_dict['omega'])
                position = self.orbit_position(self.kepler_dict['a'],self.kepler_dict['excentricity'],self.kepler_dict['Omega'],self.kepler_dict['inclination'],self.kepler_dict['omega'],[self.kepler_dict['true_anomaly']])
                orbits.append(orbit)
                positions.append(position)

            '''celestial artist : def __init__(self,id,artist,orbit,pos,date,color,name):'''
            self.current_objects.append(celestial_artist(object,orbit,position,self.dt,self.JPL_numbers[object],r.text))
        return orbits,positions

    def update_listbox(self):
        '''update listbox according to search term'''
        search_term = self.search_term.get()
        selected_items = self.get_selected()
        self.listbox.delete(0,tkinter.END)
        for k,v in self.JPL_numbers.items():
            if search_term.lower() in v.lower() and not (search_term.lower() in selected_items):
                self.listbox.insert(tkinter.END,v)
        for item in selected_items:
            self.listbox.insert(0,item)
            self.listbox.selection_set(0)
        return True

    def toggle_axis(self):
        if self.axis_var.get() == 1:
            self.ax.set_axis_on()
            self.canvas.draw()
        else:
            self.ax.set_axis_off()
            self.canvas.draw()

    def redraw_current_objects(self):
        '''just redrawing the plot to accept user changes to appearance'''
        self.plot_orbits(self.ax,self.current_objects,refplane_var=self.refplane_var.get())

    def toggle_proj(self):
        if self.proj_var.get() == 1:
            self.ax.set_proj_type('persp')
        else:
            self.ax.set_proj_type('ortho')
        self.canvas.draw()

    def clicked_on(self,event):
        '''takes pick event of object'''
         # artist_dir = dir(event.artist)
         # pprint(arist_dir)
        for object in self.current_objects:
            if object.position_artist[0].get_label() == event.artist.get_label():
                name= object.name
                selected_object = object
                pprint('clicked {0}'.format(name))
        print(selected_object.info_text)
        for object in self.current_objects:
            object.position_artist[0].set_markeredgecolor(object.position_artist[0].get_markerfacecolor())
        selected_object.position_artist[0].set_markeredgecolor('white')
        self.canvas.draw()
        self.artist_menu(selected_object)

    def artist_menu(self,object):
        top = tkinter.Toplevel()

        x = root.winfo_x()
        y = root.winfo_y()
        top.geometry("+%d+%d" % (x + 10, y + 20))
        top.title("{0} parameters".format(object.displayname))

        displayname_var = tkinter.StringVar()
        displayname_var.set(str(object.displayname))
        settings_frame =  tkinter.LabelFrame(top, text= 'object parameters')
        settings_frame.grid(row=0,column= 0)

        button_frame = tkinter.Frame(top)
        button_frame.grid(row=1,column=0)

        tkinter.Label(settings_frame,text='object color:').grid(row=0,column=0,sticky=tkinter.W)
        artist_color_button = tkinter.Button(settings_frame,text='',bg = object.color ,command=lambda: self.get_color(artist_color_button), width=10)
        artist_color_button.grid(row=0,column=1,sticky=tkinter.E)

        tkinter.Label(settings_frame,text='displayname:').grid(row=2,column=0,sticky=tkinter.W)
        tkinter.Entry(settings_frame,textvariable=displayname_var).grid(row=2,column=1,sticky=tkinter.E)

        dismiss_button = tkinter.Button(button_frame, text="cancel", command=top.destroy)
        dismiss_button.grid(row=0,column=0)
        accept_button = tkinter.Button(button_frame, text="apply changes", command = lambda: self.update_artist(object,artist_color_button,displayname_var.get(),top))
        accept_button.grid(row=0,column=1)
        top.resizable(width=False,height=False)
        top.attributes('-topmost',1)

    def update_artist(self,object,artist_color_button,displayname,top):
        object.color = artist_color_button.cget('bg')
        object.displayname = displayname
        self.redraw_current_objects()
        top.destroy()

    def check_db(self):
        '''checks if DB file exists, if not, queries HORIZONS socket service to extract major bodies'''
        if not self.my_file.is_file():
            #telnet session to extract Major Bodies dict

            tn = telnetlib.Telnet(self.HOST,self.port)
            print('waiting for Horizons socket service')
            tn.read_until("Horizons>".encode('UTF-8'))
            print('Querying Major Bodies')
            tn.write('MB\n'.encode('UTF-8'))
            list = str(tn.read_until('0'.encode('UTF-8')))
            list = list[-2] + str(tn.read_until('Number'.encode('UTF-8')))[1:]
            tn.close()
            list = str(list)
            JPL_numbers = list.split()
            list = []
            ID = True
            safe_str = ''
            for s in JPL_numbers:
                if ID == True:
                    list.append(s)
                    ID = False
                elif not(s == '\\r\\n'):
                    safe_str = safe_str + ' ' + s
                else:
                    list.append(safe_str)
                    safe_str = ''
                    ID = True
            JPL_numbers = list
            del JPL_numbers[-1]
            JPL_numbers = dict(zip(JPL_numbers[::2],JPL_numbers[1::2]))
            self.JPL_numbers = dict(("'"+k.strip()+"'",v.strip()) for k,v in JPL_numbers.items())
            self.save_obj(self.JPL_numbers,self.filename)
        else:
            print('found .pckl file with DB IDs')
            self.JPL_numbers = self.load_obj(self.filename)
        if self.my_file2.is_file():
            print('{0} found! adding small bodies to list'.format(self.my_file2))
            with open('{0}'.format(self.my_file2),mode='r') as csvfile:
                small_bodies = csv.reader(csvfile)
                small_bodies = {"'"+row[0].strip()+";'":row [1].strip() for row in small_bodies}
        else:
            print('{0}'.format(self.my_file2))
            small_bodies = {}
        self.JPL_numbers.update(small_bodies)
        self.JPL_numbers = dict((k,v) for k,v in self.JPL_numbers.items() if not (v==''))
        self.JPL_numbers = self.sort_vals(self.JPL_numbers)
        self.JPL_name2num = dict((v,k) for k,v in self.JPL_numbers.items())

if __name__ == '__main__':
    root = tkinter.Tk()
    tkinter.Grid.rowconfigure(root, 0, weight=1)
    tkinter.Grid.columnconfigure(root, 0, weight=1)
    gui = plot_application(root)
    root.mainloop()
