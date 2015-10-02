"""Tooltip widget"""


from tkinter import *

from ..constants import MESSAGE_BG_COL, TOOLTIP_DELAY


class ToolTipBase(Toplevel):
    def __init__(self, master=None, bgColor=MESSAGE_BG_COL,
                 offsetx=10, offsety=10, delay=TOOLTIP_DELAY):
        Toplevel.__init__(self, master)
        self.offsetx = offsetx
        self.offsety = offsety
        self.delay = delay
        self.id = None
        self.lastPos = None
        self.bgColor = MESSAGE_BG_COL

    def postInit(self):
        self.create_window()
        self.bind_to_master()

    def bind_to_master(self):
        self.master.bind('<Enter>', self.schedule_tooltip)
        self.master.bind('<Motion>', self.set_position)
        self.master.bind('<Leave>', self.hide_tooltip)
        self.master.bind('<Button>', self.hide_tooltip)

    def schedule_tooltip(self, event=None):
        self.id = self.master.after(self.delay, self.show_tooltip)

    def create_window(self):
        self.overrideredirect(True)
        self.createLabel().pack()
        self.withdraw()

    def set_position(self, event):
        self.hide_tooltip()
        self.lastPos = (event.x, event.y)
        self.geometry('+{0}+{1}'.format(event.x_root + self.offsetx,
                                        event.y_root + self.offsetx))
        self.schedule_tooltip()

    def hide_tooltip(self, event=None):
        self.withdraw()
        self.cancel_id()

    def cancel_id(self):
        if self.id is not None:
            self.master.after_cancel(self.id)
            self.id = None


class ToolTip(ToolTipBase):
    """A Tooltip widget

    Display tooltip message at mouse cursor when it is over master
    widget.

    Arguments are:
      master:   parent widget
      text:     message to display
      bgColor:  background color
      offsetx, offsety:  offset from cursor position
      delay:    delay in milliseconds

    Warning: ToolTip does not work properly with Frame widget.
    It seems that '<Motion>' event have some problems with getting
    updated cursor position there.

    """

    def __init__(self, master=None, text=None, **kwargs):
        kwargs['master'] = master
        ToolTipBase.__init__(self, **kwargs)
        self.text = text
        self.postInit()

    def createLabel(self):
        return Label(self, text=self.text, bg=self.bgColor, justify=LEFT)

    def show_tooltip(self):
        try:
            self.update()
            self.deiconify()
        except AttributeError:
            self.hide_tooltip()


class ListBoxToolTip(ToolTipBase):
    def __init__(self, master=None, itemTextFunc=lambda i: "", **kwargs):
        kwargs['master'] = master
        ToolTipBase.__init__(self, **kwargs)
        self.itemTextFunc = itemTextFunc
        self.textVar = StringVar()
        self.postInit()

    def createLabel(self):
        return Label(self, textvariable=self.textVar, bg=self.bgColor,
                     justify=LEFT)

    def show_tooltip(self):
        if self.lastPos is None:
            return

        nearestIdx = self.master.nearest(self.lastPos[1])
        bbox = self.master.bbox(nearestIdx)
        if bbox is None:
            return

        xOffset, yOffset, width, height = bbox
        # Is the mouse pointer on the row of an item?
        if not (yOffset <= self.lastPos[1] < yOffset + height):
            return

        self.textVar.set(self.itemTextFunc(nearestIdx))

        try:
            self.update()
            self.deiconify()
        except AttributeError:
            self.hide_tooltip()

    def setItemTextFunc(self, itemTextFunc):
        self.itemTextFunc = itemTextFunc
