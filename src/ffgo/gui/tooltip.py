# tooltip.py --- Tooltip classes for Tkinter
# -*- coding: utf-8 -*-
#
# Copyright (c) 2013-2014  Robert 'erobo' Leda
# Copyright (c) 2015-2016  Florent Rougon
#
# This file is distributed under the terms of the DO WHAT THE FUCK YOU WANT TO
# PUBLIC LICENSE version 2, dated December 2004, by Sam Hocevar. You should
# have received a copy of this license along with this file. You can also find
# it at <http://www.wtfpl.net/>.

"""Tooltip classes."""


from tkinter import *

from .. import constants
from ..constants import TOOLTIP_BG_COL, TOOLTIP_DELAY


class ToolTipBase(Toplevel):
    def __init__(self, master, bgColor=TOOLTIP_BG_COL,
                 offsetx=10, offsety=10, delay=TOOLTIP_DELAY,
                 wraplength=0, autowrap=False):
        Toplevel.__init__(self, master)
        self.offsetx = offsetx
        self.offsety = offsety
        self.delay = delay
        self.id = None
        self.lastPos = None
        self.bgColor = bgColor

        if autowrap:
            self.wraplength = constants.AUTOWRAP_TOOLTIP_WIDTH
        else:
            self.wraplength = wraplength

        # With some widgets as the master (e.g., Menu under Tk 8.6), the Motion
        # event may occur even if the mouse pointer is outside the widget area.
        # Therefore, we use a boolean to keep track of whether the pointer is
        # inside the widget or outside, and thus whether the tooltip can be
        # shown or not.
        self.canBeShown = False

    def postInit(self):
        self.createWindow()
        self.bindToMaster()

    def bindToMaster(self):
        self.master.bind('<Enter>', self.onEnter)
        self.master.bind('<Motion>', self.onMotion)
        self.master.bind('<Leave>', self.onLeave)
        self.master.bind('<Button>', self.hide)
        # Without this, there would be a _tkinter.TclError during the
        # deiconify() call in self.show() if the window containing self.master
        # were closed and the tooltip tried to appear afterwards. This also
        # hides the tooltip when the user switches to another workspace.
        self.master.bind('<Unmap>', self.hide)

    def scheduleTooltip(self, event):
        self.id = self.master.after(self.delay, self.prepareAndShow, event)

    def createWindow(self):
        self.overrideredirect(True)
        self.createLabel().pack()
        self.withdraw()

    def prepareText(self, event):
        """Prepare the tooltip text.

        This is one of methods subclasses are likely to need to
        override, along with __init__() and createLabel().

        """
        # This means: don't show the tooltip this time
        return False

    def prepareAndShow(self, event):
        if self.prepareText(event):
            # The tooltip text is ready and we are “authorized” to show it
            self.show(event)

    def show(self, event):
        self.update()
        self.deiconify()

    def adjustPosition(self, event):
        # Last known position of the mouse pointer, relative to the
        # top-left corner of the widget.
        self.lastPos = (event.x, event.y)
        self.geometry('+{0}+{1}'.format(event.x_root + self.offsetx,
                                        event.y_root + self.offsetx))

    # Used as an event handler (requires the 'event' parameter) as well as from
    # other parts of the program (not necessarily with an event to pass as
    # argument).
    def hide(self, event=None):
        self.withdraw()
        self.cancelId()

    def cancelId(self):
        if self.id is not None:
            self.master.after_cancel(self.id)
            self.id = None

    def onEnter(self, event):
        self.canBeShown = True
        self.adjustPosition(event)
        self.scheduleTooltip(event)

    def onMotion(self, event):
        self.hide()
        if self.canBeShown:
            self.adjustPosition(event)
            self.scheduleTooltip(event)

    def onLeave(self, event):
        self.canBeShown = False
        self.hide()


class ToolTip(ToolTipBase):
    """A Tooltip widget.

    Display a tooltip text at mouse position when the mouse pointer is
    over the master widget.

    Arguments are:
      master:   parent widget
      text:     message to display, or None if using 'textvariable'.
                This is for static tooltips.
      textvariable: StringVar corresponding to a message to display, or
                None if using 'text'. This allows to easily change the
                tooltip text without having to create a new tooltip.
      wraplength: width for automatic wrapping of the label text (no
                automatic wrapping by default)
      autowrap: if True, set 'wraplength' to
                constants.AUTOWRAP_TOOLTIP_WIDTH to provide a standard
                width for automatically-wrapped tooltips
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

    def __init__(self, master, text=None, textvariable=None, **kwargs):
        ToolTipBase.__init__(self, master, **kwargs)
        self.text = text
        self.textvariable = textvariable

        self.postInit()

    def createLabel(self):
        if self.text is not None:
            kwargs = {"text": self.text}
        else:
            kwargs = {"textvariable": self.textvariable}

        return Label(self, bg=self.bgColor, justify=LEFT,
                     wraplength=self.wraplength, **kwargs)

    def prepareText(self, event):
        # Always show the toolip. The text was already prepared in
        # __init__() (it is always the same for this tooltip), so there
        # is nothing left to prepare.
        return True


class MapBasedToolTip(ToolTipBase):
    """Abstract base class for map-based tooltips.

    This means, tooltips whose text is obtained from a function that
    maps parts of the underlying widget to particular tooltip texts.
    Typically, the function ('itemTextFunc' below) will take a row,
    column or more generally item identifier as argument and choose the
    appropriate text to return (or None) depending on this information.

    """
    def __init__(self, master, itemTextFunc, **kwargs):
        """Constructor for MapBasedToolTip instances.

        master       -- a widget
        itemTextFunc -- a function whose signature may vary among
                        concrete subclasses of this class. Its
                        argument(s) should allow to determine an
                        appropriate tooltip text. If it returns None, no
                        tooltip will be shown; otherwise, the return
                        value should be a string that will be used as
                        tooltip text.

        Additional keyword arguments are passed to ToolTipBase's
        constructor.

        """
        ToolTipBase.__init__(self, master, **kwargs)
        self.itemTextFunc = itemTextFunc
        self.textVar = StringVar()
        self.postInit()

    def createLabel(self):
        return Label(self, textvariable=self.textVar, bg=self.bgColor,
                     justify=LEFT, wraplength=self.wraplength)

    def setItemTextFunc(self, itemTextFunc):
        """Replace the existing 'itemTextFunc' callback function."""
        self.itemTextFunc = itemTextFunc


class ListBoxToolTip(MapBasedToolTip):
    def __init__(self, master, itemTextFunc=lambda i: None, **kwargs):
        """Constructor for ListBoxToolTip instances.

        master       -- a ListBox instance
        itemTextFunc -- a function taking one argument. When called, the
                        function will be passed the index of an item in
                        the ListBox (starting from 0). If it returns
                        None, no tooltip will be shown for this item;
                        otherwise, the return value should be a string
                        that will be used as the tooltip for this item.

        Additional keyword arguments are passed to ToolTipBase's
        constructor.

        """
        MapBasedToolTip.__init__(self, master, itemTextFunc, **kwargs)

    def prepareText(self, event):
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


class MenuToolTip(MapBasedToolTip):
    def __init__(self, master, itemTextFunc=lambda i: None, **kwargs):
        """Constructor for MenuToolTip instances.

        master       -- the master widget; should be a Menu instance or
                        a compatible object
        itemTextFunc -- a function taking one argument. When called, the
                        function will be passed the index of an item in
                        the Menu (starting from 0). If it returns None,
                        no tooltip will be shown for this item;
                        otherwise, the return value should be a string
                        that will be used as the tooltip for this item.

        Additional keyword arguments are passed to ToolTipBase's
        constructor.

        """
        MapBasedToolTip.__init__(self, master, itemTextFunc, **kwargs)
        self.highlightedItemIndex = None

    def bindToMaster(self):
        ToolTipBase.bindToMaster(self)
        self.master.bind('<<MenuSelect>>', self.onMenuSelect)

    def onMenuSelect(self, event):
        # Set to None when the pointer leaves the Menu widget
        self.highlightedItemIndex = event.widget.index('active')

    def prepareText(self, event):
        if self.highlightedItemIndex is None:
            return False

        text = self.itemTextFunc(self.highlightedItemIndex)
        if text is not None:
            self.textVar.set(text) # set the tooltip text
            return True            # tell the caller the tooltip must be shown
        else:
            # There is no tooltip to show for this item.
            return False


class TreeviewToolTip(MapBasedToolTip):
    def __init__(self, master,
                 itemTextFunc=lambda region, itemID, column: None, **kwargs):
        """Constructor for TreeviewToolTip instances.

        master       -- a Treeview instance
        itemTextFunc -- a function taking three arguments. When called, the
                        function will be passed:
                          - the region of the Treeview widget, as
                            returned by Treeview.identify_region();
                          - the item identifier, as returned by
                            Treeview.identify_row();
                          - the data column identifier of the cell, as
                            returned by Treeview.identify_column().
                        If this function returns None, no tooltip will
                        be shown for this cell (or, more generally, area
                        of the Treeview widget); otherwise, the return
                        value should be a string that will be used as
                        tooltip text for this cell/area.

        Additional keyword arguments are passed to ToolTipBase's
        constructor.

        """
        MapBasedToolTip.__init__(self, master, itemTextFunc, **kwargs)

    def prepareText(self, event):
        if self.lastPos is None:
            return False

        region = self.master.identify_region(event.x, event.y)
        itemID = self.master.identify_row(event.y)
        column = self.master.identify_column(event.x)

        text = self.itemTextFunc(region, itemID, column)
        if text is not None:
            self.textVar.set(text)
            return True
        else:
            return False
