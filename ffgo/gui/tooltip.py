# tooltip.py --- Tooltip classes for Tkinter
# -*- coding: utf-8 -*-
#
# Copyright (c) 2013-2014  Robert 'erobo' Leda
# Copyright (c) 2015       Florent Rougon
#
# This file is distributed under the terms of the DO WHAT THE FUCK YOU WANT TO
# PUBLIC LICENSE version 2, dated December 2004, by Sam Hocevar. You should
# have received a copy of this license along with this file. You can also find
# it at <http://www.wtfpl.net/>.

"""Tooltip classes."""


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
        # With some widgets as the master (e.g., Menu under Tk 8.6), the Motion
        # event may occur even if the mouse pointer is outside the widget area.
        # Therefore, we use a boolean to keep track of whether the pointer is
        # inside the widget or outside, and thus whether the tooltip can be
        # shown or not.
        self.canBeShown = False

    def postInit(self):
        self.create_window()
        self.bind_to_master()

    def bind_to_master(self):
        self.master.bind('<Enter>', self.onEnter)
        self.master.bind('<Motion>', self.onMotion)
        self.master.bind('<Leave>', self.onLeave)
        self.master.bind('<Button>', self.hide_tooltip)

    def schedule_tooltip(self, event=None):
        self.id = self.master.after(self.delay, self.prepareAndShow)

    def create_window(self):
        self.overrideredirect(True)
        self.createLabel().pack()
        self.withdraw()

    def prepareText(self):
        """Prepare the tooltip text.

        This is one of methods subclasses are likely to need to
        override, along with __init__() and createLabel().

        """
        # This means: don't show the tooltip this time
        return False

    def prepareAndShow(self):
        if self.prepareText():
            # The tooltip text is ready and we are “authorized” to show it
            self.show()

    def show(self):
        self.update()
        self.deiconify()

    def adjustPosition(self, event):
        # Last known position of the mouse pointer, relative to the
        # top-left corner of the widget.
        self.lastPos = (event.x, event.y)
        self.geometry('+{0}+{1}'.format(event.x_root + self.offsetx,
                                        event.y_root + self.offsetx))

    def hide_tooltip(self, event=None):
        self.withdraw()
        self.cancel_id()

    def cancel_id(self):
        if self.id is not None:
            self.master.after_cancel(self.id)
            self.id = None

    def onEnter(self, event=None):
        self.canBeShown = True
        self.adjustPosition(event)
        self.schedule_tooltip()

    def onMotion(self, event):
        self.hide_tooltip()
        if self.canBeShown:
            self.adjustPosition(event)
            self.schedule_tooltip()

    def onLeave(self, event=None):
        self.canBeShown = False
        self.hide_tooltip()


class ToolTip(ToolTipBase):
    """A static Tooltip widget.

    Display the same tooltip text at mouse position when the mouse
    pointer is over the master widget.

    Arguments are:
      master:   parent widget
      text:     message to display
      bgColor:  background color
      offsetx, offsety:  offset from cursor position
      delay:    delay in milliseconds

    Old note: ToolTip might not work properly with the Frame widget. It
    seems that '<Motion>' events have some problems with getting updated
    cursor position there.

    Update: this is probably worked around now since the addition of
    ToolTipBase.canBeShown in Oct 2015 for the Menu widget, which
    received Motion events even after the mouse pointer left the widget.

    """

    def __init__(self, master=None, text=None, **kwargs):
        kwargs['master'] = master
        ToolTipBase.__init__(self, **kwargs)
        self.text = text
        self.postInit()

    def createLabel(self):
        return Label(self, text=self.text, bg=self.bgColor, justify=LEFT)

    def prepareText(self):
        # Always show the toolip. The text was already prepared in
        # __init__() (it is always the same for this tooltip), so there
        # is nothing left to prepare.
        return True


class ListBoxToolTip(ToolTipBase):
    def __init__(self, master=None, itemTextFunc=lambda i: None, **kwargs):
        """Constructor for ListBoxToolTip instances.

        master       -- a Menu instance
        itemTextFunc -- a function taking one argument. When called, the
                        function will be passed the index of an item in
                        the ListBox (starting from 0). If it returns
                        None, no tooltip will be shown for this item;
                        otherwise, the return value should be a string
                        that will be used as the tooltip for this item.

        Additional keyword arguments are passed to ToolTipBase's
        constructor.

        """
        kwargs['master'] = master
        ToolTipBase.__init__(self, **kwargs)
        self.itemTextFunc = itemTextFunc
        self.textVar = StringVar()
        self.postInit()

    def createLabel(self):
        return Label(self, textvariable=self.textVar, bg=self.bgColor,
                     justify=LEFT)

    def prepareText(self):
        if self.lastPos is None:
            return False

        nearestIdx = self.master.nearest(self.lastPos[1])
        bbox = self.master.bbox(nearestIdx)
        if bbox is None:
            return False

        xOffset, yOffset, width, height = bbox
        # Is the mouse pointer on the row of an item?
        if not (yOffset <= self.lastPos[1] < yOffset + height):
            return False

        text = self.itemTextFunc(nearestIdx)
        if text is not None:
            self.textVar.set(text)
            return True
        else:
            return False

    def setItemTextFunc(self, itemTextFunc):
        self.itemTextFunc = itemTextFunc
