"""Tooltip widget"""


from tkinter import *

from ..constants import MESSAGE_BG_COL, TOOLTIP_DELAY


class ToolTip(Toplevel):

    """A Tooltip widget

    displays tooltip message at mouse cursor when it is over master 
    widget.

    Arguments are:
      master:  parent widget
      text:  message to display
      bg:  background color
      offsetx, offsety:  offset from cursor position
      delay:  delay in milliseconds

    Warning: ToolTip does not work properly with Frame widget. 
    It seems that '<Motion>' event have some problems with getting 
    updated cursor position there.

    """

    def __init__(self, master=None, text=None, bg=MESSAGE_BG_COL,
                 offsetx=10, offsety=10, delay=TOOLTIP_DELAY):
        Toplevel.__init__(self, master)
        self.offsetx = offsetx
        self.offsety = offsety
        self.delay = delay
        self.id = None
        self.create_window(text, bg)
        self.bind_to_master()

    def bind_to_master(self):
        self.master.bind('<Enter>', self.shelude_tooltip)
        self.master.bind('<Motion>', self.set_position)
        self.master.bind('<Leave>', self.hide_tooltip)
        self.master.bind('<Button>', self.hide_tooltip)

    def shelude_tooltip(self, event=None):
        self.id = self.master.after(self.delay, self.show_tooltip)

    def create_window(self, text, bg):
        self.overrideredirect(True)
        label = Label(self, text=text, bg=bg, justify=LEFT)
        label.pack()
        self.withdraw()

    def show_tooltip(self):
        try:
            self.update()
            self.deiconify()
        except AttributeError:
            self.hide_tooltip()

    def set_position(self, event):
        self.geometry('+{0}+{1}'.format(event.x_root + self.offsetx,
                                        event.y_root + self.offsetx))

    def hide_tooltip(self, event=None):
        self.withdraw()
        self.cancel_id()

    def cancel_id(self):
        if self.id:
            self.master.after_cancel(self.id)
            self.id = None
