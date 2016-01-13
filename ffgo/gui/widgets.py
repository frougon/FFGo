# widgets.py --- Customized widgets
# -*- coding: utf-8 -*-
#
# Copyright (c) 2015, 2016  Florent Rougon
#
# This file is distributed under the terms of the DO WHAT THE FUCK YOU WANT TO
# PUBLIC LICENSE version 2, dated December 2004, by Sam Hocevar. You should
# have received a copy of this license along with this file. You can also find
# it at <http://www.wtfpl.net/>.

import enum
import tkinter as tk
from tkinter import ttk


class error(Exception):
    """Base class for exceptions raised in the 'widgets' module."""

class NoSuchItem(error):
    pass


# *****************************************************************************
# *                 Improved version of Ttk's Treeview widget                 *
# *****************************************************************************

class MyTreeview(ttk.Treeview):
    """Like Ttk's Treeview, but with better handling of keyboard events."""
    def __init__(self, *args, FFGoWrapItems=False, **kwargs):
        """Initialize a MyTreeview instance.

        Arguments are the same as for ttk.Treeview, except that:
          - the 'height' keyword argument *must* be given;
          - 'FFGoWrapItems' specifies if the Up/Down arrow keys and
            PageUp/PageDown present a wrapping behavior when trying to
            go before the first, or after the last item of the tree.
            It defaults to False, which means: no wrapping behavior.

        """
        ttk.Treeview.__init__(self, *args, **kwargs)

        assert "height" in kwargs, kwargs
        self._FFGoTreeHeight = kwargs["height"]
        self._FFGoWrapItems = FFGoWrapItems
        # We need this flag for special handling of navigation keys:
        # because the subsequent processing may take some time and such
        # keys may cause repeated events by simply being held down, it
        # may be beneficial to wait a bit before doing lengthy
        # processing in case the selected item is changed again within a
        # short delay. This way, Tk's main loop can have enough time to
        # update the interface, despite keyboard events arriving with
        # "high" frequency.
        self._FFGoRepeatableNavKeyHit = False

        self.bind('<KeyPress>', self._FFGoOnKeyPress)

    def _FFGoOnKeyPress(self, event):
        if event.keysym in ("Up", "Down", "Prior", "Next", "Home", "End"):
            self._FFGoHandleBrowsingKey(event.keysym)
            return "break"      # don't propagate the event to the parent

    # Must be called with an up-to-date 'self' object
    def _FFGoHandleBrowsingKey(self, keysym):
        assert keysym in ("Down", "Up", "Next", "Prior", "Home", "End"), keysym

        if keysym in ("Home", "End"):
            self._FFGoHandleBrowsingHomeEnd(keysym)
        else:
            if keysym in ("Down", "Up"):
                amplitude = 1
            elif keysym in ("Next", "Prior"):
                amplitude = self._FFGoTreeHeight

            sign = 1 if keysym in ("Down", "Next") else -1
            delta = sign*amplitude

            treeItems = self.get_children()
            if treeItems:
                currentSel = self.selection()
                if currentSel:
                    currentIdx = self.index(currentSel[0])
                    if self._FFGoWrapItems:
                        targetIdx = (currentIdx + delta) % len(treeItems)
                    else:
                        if delta > 0:
                            targetIdx = min(currentIdx + delta,
                                            len(treeItems) - 1)
                        else:
                            targetIdx = max(currentIdx + delta, 0)
                else:               # no item is selected
                    targetIdx = 0

                self._FFGoRepeatableNavKeyHit = True # set the flag
                self.FFGoGotoItemWithIndex(targetIdx, treeItems=treeItems)

    # Must be called with an up-to-date 'self' object
    def _FFGoHandleBrowsingHomeEnd(self, keysym):
        assert keysym in ("Home", "End"), keysym

        treeItems = self.get_children()
        if treeItems:
            targetIdx = len(treeItems) - 1 if keysym == "End" else 0
            self.FFGoGotoItemWithIndex(targetIdx, treeItems=treeItems)

    def FFGoGotoItem(self, item):
        self.selection(selop="set", items=(item,))
        self.see(item)

    def FFGoGotoItemWithIndex(self, index, treeItems=None):
        if treeItems is None:   # small optimization in case we already have it
            treeItems = self.get_children()

        targetItem = treeItems[index]
        self.selection(selop="set", items=(targetItem,))
        self.see(targetItem)

    def FFGoGotoItemWithValue(self, column, value):
        """Go to the first item having the specified value in 'column'.

        'value' is compared to values from Treeview items, and therefore
        should be a string.

        Raise NoSuchItem if no item with this value is found.

        """
        for item in self.get_children():
            if self.set(item, column) == value:
                 self.FFGoGotoItem(item)
                 break           # The item was found and selected
        else:
            raise NoSuchItem()


# *****************************************************************************
# *                      Airport Chooser-related classes                      *
# *****************************************************************************


@enum.unique
class SortOrder(enum.Enum):
    """Enumeration describing sort order."""

    ascending = 0
    descending = 1

    def __int__(self):
        """Convert the enum member to an int.

        This is convenient for using an enum member as the value for the
        'reverse' keyword argument of Python's sort() methods.

        """
        return self.value

    def reverse(self):
        """Return the enum member for the opposite direction."""
        return type(self)(0 if self.value else 1)


class Column:
    """Column metadata for Treeview widgets."""

    def __init__(self, name, title, dataIndex, anchor, stretch,
                 widthKeyword="width", widthText=None, sortFunc=None,
                 formatFunc=None, columnKwargs=None,
                 sortOrder=SortOrder.ascending):
        """Constructor for Column instances.

        name         -- symbolic name for the column; should match the
                        symbolic name used when interacting with the
                        Treeview widget.
        title        -- text to display in the column header
        dataIndex    -- index (starting from 0) used to look up data for
                        this column in each record of the underlying
                        data model (e.g., index for use inside each
                        element of AirportChooser.treeData)
        anchor       -- 'anchor' parameter for use in
                        TreeWidget.column()
        stretch      -- 'stretch' parameter for use in
                        TreeWidget.column()
        widthKeyword -- 'width' or 'minwidth': keyword used in
                        TreeWidget.column() in conjunction with
                        'widthText'
        widthText    -- string used, along with the 'title' parameter,
                        to determine the width of a column
        sortFunc     -- function taking one argument, as the 'key'
                        parameter of Python's sort(), used to sort data
                        values from this column; if None, Python's
                        default sort order for the corresponding data
                        type will be used.
        formatFunc   -- function taking one argument and returning a
                        string; used to obtain the formatted version of
                        a data item for display in the Treeview; if
                        None, the data value is used as is and should
                        normally be a string
        columnKwargs -- additional keyword arguments to pass to
                        TreeWidget.column(); should be a mapping, as any
                        “kwargs” in Python
        sortOrder    -- SortOrder instance (i.e., a member of the
                        SortOrder enumeration) specifying if the column
                        must be sorted in ascending or descending order.

        """
        if columnKwargs is None:
            columnKwargs = {}

        self._attrs = ("name", "title", "dataIndex", "anchor", "stretch",
                       "widthKeyword", "widthText", "sortFunc", "formatFunc",
                       "columnKwargs", "sortOrder")
        for attr in self._attrs:
            setattr(self, attr, locals()[attr])


class AirportChooser:
    """Glue logic turning three widgets into a convenient airport chooser."""

    def __init__(self, master, config,
                 icaoVar, treeData, columnsMetadata, initSortBy,
                 entryWidget, clearButton, treeWidget,
                 repeatableNavKeyApplyDelay, treeUpdatedCallback=None,
                 updateDelay=400):
        """Constructor for AirportChooser instances.

        master          -- Tk master object (“root”)
        config          -- Config instance
        icaoVar         -- StringVar instance that will be automatically
                           updated to reflect the currently selected
                           airport (currently selected in the Treeview
                           widget)
        treeData        -- sequence of tuples where each tuple has one
                           element per column displayed in the Treeview.
                           This is the complete data set used to fill
                           the Treeview. The word “tuple” is used to
                           ease understanding here, but any sequence
                           can do.
        columnsMetadata -- mapping from symbolic column names for the
                           Ttk Treeview widget to Column instances
        initSortBy      -- symbolic name of the column used to initially
                           sort the Treeview widget
        entryWidget     -- Ttk or Tk Entry widget: the search field
        clearButton     -- Ttk or Tk Button widget: the “Clear” button
        treeWidget      -- Ttk Treeview widget used as a multicolumn
                           list (in other words, a table)
        repeatableNavKeyApplyDelay
                        -- delay before the result of using a repeatable
                           navigation key (up or down arrow, Page Up or
                           Page Down) is propagated to 'icaoVar'. This
                           is necessary when writing to 'icaoVar'
                           triggers time-consuming callbacks, otherwise
                           the Tk main loop doesn't have enough time to
                           refresh the interface between two successive
                           keyboard events, and thus the interface
                           appears to be frozen (typically when holding
                           down one of the aforementioned navigation
                           keys).
        treeUpdatedCallback
                        -- function called after the Treeview widget has
                           been updated (after every update of the
                           Treeview widget contents). The function is
                           called without any argument.
        updateDelay     --
          delay in milliseconds before starting to update the Treeview
          after each character typed in the search field. This allows to
          keep the Entry responsive when typing or erasing faster than
          would otherwise be allowed due to the time needed to find the
          matching entries, sort them and replace the existing contents
          of the Treeview with this new data.

        The 'icaoVar' StringVar instance and the three widgets used by
        this class (Entry, Button and Treeview) must be created by the
        caller. However, this constructor takes care of connecting them
        with the appropriate methods or internally-used StringVar
        instances.

        """
        _attrs = ("master", "config", "icaoVar", "treeData", "columnsMetadata",
                  "entryWidget", "clearButton", "treeWidget",
                  "repeatableNavKeyApplyDelay", "treeUpdatedCallback",
                  "updateDelay")
        for attr in _attrs:
            setattr(self, attr, locals()[attr])

        self.sortBy = initSortBy

        # List of item indices (into treeData) for the airports found by
        # the last search.
        self.matches = []

        self.searchBufferVar = tk.StringVar()
        self.searchVar = tk.StringVar()
        self.searchUpdateCancelId = None
        # If True, the next update to self.searchBufferVar will immediately
        # affect self.searchVar instead of being delayed. Has “one shot”
        # behavior.
        self.immediateSearchUpdate = False
        # When False, self.searchBufferVarWritten() returns immediately without
        # doing its normal work.
        self.searchUpdateEnabled = True
        self.searchBufferVar.trace("w", self.searchBufferVarWritten)
        self.searchVar.trace("w", self.updateAirportList)
        self._applyNavKeyCancelId = None

        entryWidget.config(textvariable=self.searchBufferVar)
        clearButton.config(command=self.clearSearch)

        columnMapping = {}
        for col in self.columnsMetadata.values():
            self.configColumn(col)
            columnMapping[col.dataIndex] = col

        # Column instances in the order of their dataIndex
        self.columns = [ columnMapping[i]
                         for i in sorted(columnMapping.keys()) ]
        for i, col in enumerate(self.columns):
            assert i == col.dataIndex, (i, col.dataIndex)

        self.treeWidget.bind('<<TreeviewSelect>>', self.onTreeviewSelect)
        self.clearSearch(setFocusOnEntryWidget=False)

    # Accept any arguments to allow safe use as a Tkinter variable observer
    def searchBufferVarWritten(self, *args):
        if not self.searchUpdateEnabled:
            return

        if self.searchUpdateCancelId is not None:
            self.master.after_cancel(self.searchUpdateCancelId)

        if self.immediateSearchUpdate:
            self.immediateSearchUpdate = False # one shot
            self.searchVar.set(self.searchBufferVar.get())
        else:
            self.searchUpdateCancelId = self.master.after(
                self.updateDelay, self.updateSearchVar)

    def updateSearchVar(self):
        self.searchVar.set(self.searchBufferVar.get())

    def clearSearch(self, setFocusOnEntryWidget=True):
        self.immediateSearchUpdate = True
        self.searchBufferVar.set("")
        if setFocusOnEntryWidget:
            self.entryWidget.focus_set()

    def setTreeData(self, treeData, clearSearch=False):
        """Change the underlying data for the Treeview widget.

        When 'clearSearch' is True, the search field is cleared at the
        same time and special care is taken to avoid updating the
        airport list twice.

        """
        self.treeData = treeData
        # This will force an update of the Treeview widget.
        self.matches = None
        if clearSearch:
            # This will cause self.updateAirportList() to be called via the
            # chain of observers for self.searchBufferVar and self.searchVar.
            self.clearSearch(setFocusOnEntryWidget=False)
        else:
            self.updateAirportList()

    # Accept any arguments to allow safe use as a Tkinter variable observer
    def updateAirportList(self, *args):
        unsortedMatches = []
        text = self.searchVar.get().lower()

        for i, (icao, name, *rest) in enumerate(self.treeData):
            if icao.lower().startswith(text) or text in name.lower():
                unsortedMatches.append(i)

        col = self.columnsMetadata[self.sortBy]
        treeData = self.treeData  # for performance
        dataIndex = col.dataIndex # ditto

        l = [ (treeData[i][dataIndex], i) for i in unsortedMatches ]
        if col.sortFunc is not None:
            keyFunc = lambda t: col.sortFunc(t[0])
        else:
            keyFunc = lambda t: t[0]

        l.sort(key=keyFunc, reverse=int(col.sortOrder))
        matches = [ t[1] for t in l ]

        if self.matches != matches:
            self.matches = matches
            self._updateTreeWidget()

    def _updateTreeWidget(self):
        curIcao = self.icaoVar.get()
        tree = self.treeWidget
        # Delete all children of the root element. Even when the elements just
        # need to be put in a different order, it is much faster this way than
        # using tree.move() for each element.
        tree.delete(*tree.get_children())

        hasSpecialFormatter = any(
            ( col.formatFunc is not None for col in self.columns ))

        if hasSpecialFormatter:
            columns = self.columns

            formatter = []
            identity = lambda x: x
            for dataIndex in range(len(self.columns)):
                f = columns[dataIndex].formatFunc
                formatter.append(identity if f is None else f)

            for idx in self.matches:
                rawValues = self.treeData[idx]
                values = [ formatter[dataIndex](rawValue)
                           for dataIndex, rawValue in enumerate(rawValues) ]
                tree.insert("", "end", values=values)
        else:
            # Optimize the case where no column has a formatter function
            for idx in self.matches:
                tree.insert("", "end", values=self.treeData[idx])

        # Select a suitable item in the repopulated tree, if it is non-empty.
        if self.matches:
            uSearchText = self.searchVar.get().upper()
            found = {}
            for item in tree.get_children():
                itemIcao = tree.set(item, "icao")
                if itemIcao == curIcao:
                    found["current airport"] = item
                elif itemIcao == uSearchText:
                    # This one, if available, is preferred over the current
                    # airport.
                    found["exact match of search text"] = item
                    break

            try:
                # Is there an airport whose ICAO is the search text?
                item = found["exact match of search text"]
            except KeyError:
                try:
                    # Is the previously-selected airport in the list?
                    item = found["current airport"]
                except KeyError:
                    # Select the first airport in the tree. This will set
                    # self.icaoVar via the TreeviewSelect event handler.
                    tree.FFGoGotoItemWithIndex(0)
                else:
                    tree.FFGoGotoItem(item)
            else:
                tree.FFGoGotoItem(item)
        else:                   # empty tree, we can't select anything
            self.icaoVar.set('')

        if self.treeUpdatedCallback is not None:
            self.treeUpdatedCallback()

    def configColumn(self, col):
        measure = self.config.treeviewHeadingFont.measure
        if col.widthText is not None:
            width = max(map(measure, (col.widthText + "  ", col.title + "  ")))
        else:
            width = measure(col.title + "  ")

        kwargs = col.columnKwargs.copy()
        kwargs[col.widthKeyword] = width

        self.treeWidget.column(
            col.name, anchor=col.anchor, stretch=col.stretch, **kwargs)

        def sortFunc(col=col):
            self.sortTree(col)
        self.treeWidget.heading(col.name, text=col.title, command=sortFunc)

    def sortTree(self, col):
        """Sort tree contents when a column header is clicked on."""
        if self.sortBy == col.name:
            col.sortOrder = col.sortOrder.reverse()
        else:
            self.sortBy = col.name
            col.sortOrder = SortOrder.ascending

        self.updateAirportList() # repopulate the Treeview

    def onTreeviewSelect(self, event=None):
        tree = self.treeWidget
        currentSel = tree.selection()
        assert currentSel, "Unexpected empty selection in TreeviewSelect event"

        if tree._FFGoRepeatableNavKeyHit:
            # We are presumably here because of a repeatable navigation
            # key (up or down arrow, Page Up or Page Down).
            tree._FFGoRepeatableNavKeyHit = False # clear the flag

            if self._applyNavKeyCancelId is not None:
                self.master.after_cancel(self._applyNavKeyCancelId)

            if self.repeatableNavKeyApplyDelay: # non-zero delay
                self._applyNavKeyCancelId = self.master.after(
                    self.repeatableNavKeyApplyDelay, self.applySelection)
                return

        self.icaoVar.set(tree.set(currentSel[0], "icao"))

    def applySelection(self):
        """Set 'self.icaoVar' according to the currently selected item."""
        tree = self.treeWidget
        currentSel = tree.selection()
        if currentSel:
            self.icaoVar.set(tree.set(currentSel[0], "icao"))
