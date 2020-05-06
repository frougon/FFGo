# widgets.py --- Customized widgets
# -*- coding: utf-8 -*-
#
# Copyright (c) 2015, 2016  Florent Rougon
#
# This file is distributed under the terms of the DO WHAT THE FUCK YOU WANT TO
# PUBLIC LICENSE version 2, dated December 2004, by Sam Hocevar. You should
# have received a copy of this license along with this file. You can also find
# it at <http://www.wtfpl.net/>.

import abc
import enum
import tkinter as tk
from tkinter import ttk

from .. import misc
from .. import constants


class error(Exception):
    """Base class for exceptions raised in the 'widgets' module."""

class NoSuchItem(error):
    pass

class NoSelectedItem(error):
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
        try:
            self.selection(selop="set", items=(item,)) # for Python <= 3.7
        except TypeError:
            self.selection_set((item,))                # for Python >= 3.8
        self.see(item)

    def FFGoGotoItemWithIndex(self, index, treeItems=None):
        if treeItems is None:   # small optimization in case we already have it
            treeItems = self.get_children()

        targetItem = treeItems[index]
        try:
            self.selection(selop="set", items=(targetItem,)) # for Python <= 3.7
        except TypeError:
            self.selection_set((targetItem,))                # for Python >= 3.8
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
                        element of IncrementalChooser.treeData)
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


class IncrementalChooser(metaclass=abc.ABCMeta):
    """Generic glue logic turning three widgets into a convenient chooser.

    Abstract class used to build a convenient chooser from three
    widgets: a MyTreeview instance displaying a list of available items
    (airports, aircraft...), an Entry widget allowing the user to enter
    a search query, and a Button to clear the Entry and display the full
    list of available items.

    The list displayed in the MyTreeview widget may have several
    columns, allow sorting by clicking on column headers, have
    item-specific tooltips, etc.
    """

    def __init__(self, master, config, outputVar,
                 treeData, columnsMetadata, initSortBy,
                 entryWidget, clearButton, treeWidget,
                 repeatableNavKeyApplyDelay, treeUpdatedCallback=None,
                 updateDelay=400, clearSearchOnInit=True):
        """Constructor for IncrementalChooser instances.

        Some of the terminology used here (e.g., “column identifier”,
        “symbolic column name”) comes from the documentation of the Ttk
        Treeview widget.

        master          -- Tk master object (“root”)
        config          -- Config instance
        outputVar       -- Arbitrary Python object that will be
                           automatically updated to reflect the current
                           selection in 'treeWidget'. This class has a
                           few abstract methods to tell precisely how to
                           manage 'outputVar'.
        treeData        -- sequence of tuples where each tuple has one
                           element per column displayed in 'treeWidget'.
                           This is the complete data set used to fill
                           'treeWidget'. The word “tuple” is used to
                           ease understanding here, but any sequence can
                           do.
        columnsMetadata -- mapping from symbolic column names for
                           'treeWidget' to Column instances
        initSortBy      -- symbolic name of the column used to initially
                           sort 'treeWidget'
        entryWidget     -- Ttk or Tk Entry widget: the search field
        clearButton     -- Ttk or Tk Button widget: the “Clear” button
        treeWidget      -- MyTreeview instance used as a multicolumn
                           list (in other words, a table). It can of
                           course have one column only if desired---this
                           is just a particular case.
        repeatableNavKeyApplyDelay
                        -- delay before the result of using a repeatable
                           navigation key (up or down arrow, Page Up or
                           Page Down) is propagated to 'outputVar'. This
                           is necessary when writing to 'outputVar'
                           triggers time-consuming callbacks, otherwise
                           the Tk main loop doesn't have enough time to
                           refresh the interface between two successive
                           keyboard events, and thus the interface
                           appears to be frozen (typically when holding
                           down one of the aforementioned navigation
                           keys).
        treeUpdatedCallback
                        -- function called after 'treeWidget' has been
                           updated (after every update of the widget
                           *contents*---whether the selected item has
                           changed is irrelevant). The function is
                           called without any argument.
        updateDelay     -- delay in milliseconds before starting to
                           update 'treeWidget' after each character
                           typed in the search field. This allows to
                           keep the Entry responsive when typing or
                           erasing faster than would otherwise be
                           allowed due to the time needed to find the
                           matching entries, sort them and replace the
                           existing contents of 'treeWidget' with this
                           new data.
        clearSearchOnInit
                        -- whether to clear the search field, and thus
                           update 'treeWidget', when this constructor is
                           run. In some cases, this is undesirable
                           because clearing the search field eventually
                           updates the selection, and thus 'outputVar'.
                           Such a case where clearing the search field
                           as part of the constructor work is
                           undesirable, is when 'treeWidget' is
                           initialized in two steps: first as an empty
                           tree with an empty 'treeData' sequence, that
                           is later filled with a call to setTreeData().
                           In such a case, the initial clearing of the
                           search field would nullify 'outputVar',
                           because there can't be any match for any
                           search query in an empty tree.

        The three widgets used by this class (Entry, Button and
        MyTreeview) must be created by the caller. This constructor
        takes care of connecting them with the appropriate methods or
        internally-used StringVar instances.

        """
        _attrs = ("master", "config", "outputVar", "treeData",
                  "columnsMetadata", "entryWidget", "clearButton",
                  "treeWidget", "repeatableNavKeyApplyDelay",
                  "treeUpdatedCallback", "updateDelay")
        for attr in _attrs:
            setattr(self, attr, locals()[attr])

        self.sortBy = initSortBy

        # List of item indices (into treeData) for the items found by
        # the last search.
        self.matches = []

        self.searchBufferVar = tk.StringVar()
        self.searchVar = misc.Observable('')
        self.searchUpdateCancelId = None
        # If True, the next update to self.searchBufferVar will immediately
        # affect self.searchVar instead of being delayed. Has “one shot”
        # behavior.
        self.immediateSearchUpdate = False
        self.searchBufferVar.trace("w", self.searchBufferVarWritten)
        self.searchVar.trace("w", self.updateList_callback)
        # Id obtained from self.master.after() when scheduling
        # self.applySelection() for delayed execution after a repeatable
        # navigation key has triggered a TreeviewSelect event (assuming
        # self.repeatableNavKeyApplyDelay is non-zero).
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

        if clearSearchOnInit:
            self.clearSearch(setFocusOnEntryWidget=False)

    @abc.abstractmethod
    def findMatches(self):
        """Find all matches corresponding to the contents of 'self.searchVar'.

        This is used to determine the set of items that will remain in
        'self.treeWidget' for a given search query. Return a list of
        indices into 'self.treeData'.

        This is an abstract method. It must be overridden by subclasses
        before they can be instantiated.

        """
        raise NotImplementedError()

    @abc.abstractmethod
    def decodedOutputVar(self):
        """Decode the value of 'self.outputVar'.

        It may be that 'self.outputVar' encodes state information in a
        way that is not practical to work with (for instance, encoding
        complex states in a Tk StringVar). This method should decode the
        value of 'self.outputVar' and return a representation that is
        convenient to work with.

        """
        raise NotImplementedError()

    @abc.abstractmethod
    def matchesOutputVar(self, item, decodedOutputVar):
        """Whether a tree item is an exact match for 'self.outputVar'."""
        raise NotImplementedError()

    @abc.abstractmethod
    def matchesSearchText(self, item, massagedSearchText):
        """Whether a tree item is an exact match for the search query.

        This is used to choose the item to select *after* list filtering
        based on the search query. Among the remaining items once the
        search filter has been applied, one will be selected. This
        method can give a hint about which one to choose.

        Note that “exact match” means “full match” here, but not
        necessarily “case-sensitive match”. For instance, considering a
        search on aircraft names, an item named 'A320neo' could be
        exactly matched by search query 'a320neo', but not by 'a320'.

        """
        raise NotImplementedError()

    @abc.abstractmethod
    def setOutputVarForItem(self, item):
        """Set 'self.outputVar' to reflect selection of tree item 'item'."""
        raise NotImplementedError()

    @abc.abstractmethod
    def setNullOutputVar(self):
        """Set 'self.outputVar' to reflect that no item is selected."""
        raise NotImplementedError()

    def selectDefaultItemForEmptySearch(self):
        """Default item selection when the search string is empty.

        Likely to be overridden in subclasses. This implementation
        selects the first item in the list.

        When reimplementing this method in a subclass, you can rely on
        the fact that it is only called in situtations where
        'self.treeWidget' is non-empty.

        """
        self.treeWidget.FFGoGotoItemWithIndex(0)

    # Accept any arguments to allow safe use as a Tkinter variable observer
    def searchBufferVarWritten(self, *args):
        """Method called when self.searchBufferVar.set() is called."""
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

    def setTreeData(self, treeData, clearSearch=False, preserveSelection=False):
        """Change the underlying data for 'self.treeWidget'.

        When 'clearSearch' is True, the search field is cleared at the
        same time and special care is taken to avoid updating
        'self.treeWidget' twice.

        If 'clearSearch' is True, 'preserveSelection' must be False
        (limitation due to how Tkinter variable observers are called).

        If 'preserveSelection' is True, the item of 'self.treeWidget'
        that was selected when this method is called will be selected
        again (if possible) after the tree is rebuilt, before this
        method returns.

        """
        if clearSearch and preserveSelection:
            # When 'clearSearch' is True, self.updateList() is called
            # indirectly as a consequence of self.clearSearch(...) (see below).
            # In this case, it is impossible to propagate the value of
            # 'preserveSelection'. Therefore, only the value of
            # 'preserveSelection' used in self.updateList_callback() will be
            # passed to self.updateList(), which is False at the time of this
            # writing.
            assert False, (
                "{}.setTreeData(): passing both 'clearSearch' and "
                "'preserveSelection' as True is not supported.".format(
                    type(self).__name__))

        self.treeData = treeData
        # This will force an update of 'self.treeWidget' by
        # self.updateList().
        self.matches = None
        if clearSearch:
            # This will cause self.updateList() to be called via the
            # chain of observers for self.searchBufferVar and self.searchVar.
            self.clearSearch(setFocusOnEntryWidget=False)
        else:
            self.updateList(preserveSelection=preserveSelection)

    # Accept any arguments to allow safe use as a Tkinter variable observer
    def updateList_callback(self, *args):
        # This method is supposed to be called by Tkinter when some variable is
        # changed. In such a case, it is unfortunately impossible, due to the
        # Tkinter observers API, to obtain 'preserveSelection' from the caller
        # without resorting to ugly hacks such as using an instance attribute
        # to pass the value. Since this is not needed in the current state of
        # FFGo, just hardcode the value to False.
        self.updateList(preserveSelection=False)

    def updateList(self, preserveSelection=False):
        """Update the list based on the search query in 'self.searchVar'.

        If 'preserveSelection' is True, the item of 'self.treeWidget'
        that was selected when this method is called will still be
        selected (if possible) when this method returns.

        """
        # Find all matches corresponding to the contents of 'self.searchVar'.
        # 'unsortedMatches' is a list of their indices in 'self.treeData'.
        unsortedMatches = self.findMatches()

        col = self.columnsMetadata[self.sortBy]
        treeData = self.treeData  # for performance
        dataIndex = col.dataIndex # ditto

        l = [ (treeData[i][dataIndex], i) for i in unsortedMatches ]
        if col.sortFunc is not None:
            keyFunc = lambda t, f=col.sortFunc: f(t[0])
        else:
            keyFunc = lambda t: t[0]

        l.sort(key=keyFunc, reverse=int(col.sortOrder))
        matches = [ t[1] for t in l ] # only keep the indices of matching items

        if self.matches != matches: # tree contents changed?
            self.matches = matches
            self._updateTreeWidget()

        # Select a suitable item in the updated MyTreeview widget
        self._autoUpdateTreeSelection(
            preserveSelection=preserveSelection)

    def _updateTreeWidget(self):
        """Update the contents of 'self.treeWidget' based on 'self.matches'."""
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
            for dataIndex in range(len(columns)):
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

        if self.treeUpdatedCallback is not None:
            self.treeUpdatedCallback()

    def _autoUpdateTreeSelection(self, preserveSelection=False):
        """Select a suitable item in self.treeWidget, if it is non-empty.

        This method indirectly updates self.outputVar to reflect the new
        selection (possibly empty, in which case self.setNullOutputVar()
        is called).

        'preserveSelection' determines whether to prefer selecting the
        previously selected item (according to 'self.outputVar') or the
        first item that matches the search text (according to
        self.matchesSearchText()).

        """
        if self.matches:
            tree = self.treeWidget
            decodedOutputVar = self.decodedOutputVar()
            uSearchText = self.searchVar.get().upper()
            found = {}

            for item in tree.get_children():
                if self.matchesOutputVar(item, decodedOutputVar):
                    found["current selection"] = item
                    if preserveSelection:
                        break
                elif self.matchesSearchText(item, uSearchText):
                    # This one, if available, is preferred over the current
                    # selection.
                    found["match of search text"] = item
                    if not preserveSelection:
                        break

            if preserveSelection:
                preferredChoice = "current selection"
                bestFallbackChoice = "match of search text"
            else:
                preferredChoice = "match of search text"
                bestFallbackChoice = "current selection"

            try:
                item = found[preferredChoice]
            except KeyError:
                try:
                    item = found[bestFallbackChoice]
                except KeyError:
                    if uSearchText:
                        # Select the first item in the list. This will set
                        # self.outputVar via the TreeviewSelect event handler.
                        tree.FFGoGotoItemWithIndex(0)
                    else:
                        # Special case when the search query is empty
                        self.selectDefaultItemForEmptySearch()
                else:
                    tree.FFGoGotoItem(item)
            else:
                tree.FFGoGotoItem(item)
        else:                   # empty tree, we can't select anything
            self.setNullOutputVar()

    def configColumn(self, col):
        """Configure column 'col' of 'self.treeWidget'."""
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

        # Sorting the tree is not supposed to change the selected item.
        self.updateList(preserveSelection=True) # repopulate 'self.treeWidget'

    def onTreeviewSelect(self, event=None):
        tree = self.treeWidget
        currentSel = tree.selection()

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

        # Set self.outputVar based on the first (and normally only) item of the
        # selection.
        if currentSel:
            self.setOutputVarForItem(currentSel[0])

    def applySelection(self):
        """Set 'self.outputVar' according to the currently selected item."""
        tree = self.treeWidget
        currentSel = tree.selection()
        if currentSel:
            self.setOutputVarForItem(currentSel[0])

    def getValue(self, columnName):
        """Get the selected item's value in column 'columnName'.

        Raise NoSelectedItem if the selection is empty.

        """
        tree = self.treeWidget
        currentSel = tree.selection()
        if currentSel:
            return tree.set(currentSel[0], columnName)
        else:
            raise NoSelectedItem()


class AirportChooser(IncrementalChooser):
    """Glue logic turning three widgets into a convenient airport chooser."""

    def findMatches(self):
        """Find all matches corresponding to the contents of 'self.searchVar'.

        Return a list of indices into 'self.treeData'.

        """
        unsortedMatches = []
        text = self.searchVar.get().lower()

        for i, (icao, name, *rest) in enumerate(self.treeData):
            if icao.lower().startswith(text) or text in name.lower():
                unsortedMatches.append(i)

        return unsortedMatches

    def decodedOutputVar(self):
        return self.outputVar.get()

    def setOutputVarForItem(self, item):
        # This is in upper case.
        self.outputVar.set(self.treeWidget.set(item, "icao"))

    def setNullOutputVar(self):
        self.outputVar.set('')

    def matchesOutputVar(self, item, decodedOutputVar):
        # Both the tree data for column “icao” and 'decodedOutputVar' are in
        # upper case.
        return self.treeWidget.set(item, "icao") == decodedOutputVar

    def matchesSearchText(self, item, massagedSearchText):
        # Both the tree data for column “icao” and 'massagedSearchText' are in
        # upper case.
        return self.treeWidget.set(item, "icao") == massagedSearchText

    def updateItemData(self, icao, updateTree=True):
        """Refresh the data for the airport whose ICAO code is 'icao'.

        Fetch the relevant data from the underlying AirportStub instance,
        update self.treeData with this new data and refresh
        'self.treeWidget'.

        The current implementation simply rebuilds the whole MyTreeview
        widget unless the optional argument 'updateTree' is False. This
        can be slow if the amount of data in 'self.treeWidget' is large.

        """
        # Not very efficient...
        for i, (itemIcao, *rest) in enumerate(self.treeData):
            if itemIcao == icao:
                airport = self.config.airports[icao]
                self.treeData[i] = (airport.icao, airport.name,
                                    airport.useCountForShow)

                if updateTree:
                    # Update the tree, but don't change the selected item.
                    self.setTreeData(self.treeData, preserveSelection=True)
                break
        else:
            raise NoSuchItem(icao)


class AircraftChooser(IncrementalChooser):
    """Glue logic turning three widgets into a convenient aircraft chooser."""

    acNameTranslationMap = str.maketrans("", "", " -_.,;:!?")

    def __init__(self, *args, **kwargs):
        # Mapping for removing the listed characters from aircraft names
        # using str.translate(). Must be set before calling
        # IncrementalChooser's constructor.
        IncrementalChooser.__init__(self, *args, **kwargs)

    @classmethod
    def aircraftNameMatchKey(cls, acName):
        """Return the match key corresponding to a given aircraft name."""
        return acName.translate(cls.acNameTranslationMap).lower()

    def findMatches(self):
        """Find all matches corresponding to the contents of 'self.searchVar'.

        Return a list of indices into 'self.treeData'.

        """
        unsortedMatches = []
        text = self.searchVar.get().translate(
            self.acNameTranslationMap).lower()

        for i, (matchKey, *rest) in enumerate(self.treeData):
            if text in matchKey:
                unsortedMatches.append(i)

        return unsortedMatches

    def decodedOutputVar(self):
        return self.outputVar.get()

    def setOutputVarForItem(self, item):
        d = self.treeWidget.set(item)
        self.outputVar.set((d["name"], d["directory"]))

    def matchesOutputVar(self, item, decodedOutputVar):
        d = self.treeWidget.set(item)
        return (d["name"], d["directory"]) == decodedOutputVar

    def matchesSearchText(self, item, massagedSearchText):
        return self.treeWidget.set(item, "name").upper() == massagedSearchText

    def setNullOutputVar(self):
        self.outputVar.set(('', ''))

    def selectDefaultItemForEmptySearch(self):
        """Default aircraft selection when the search string is empty.

        This method is called in situtations where 'self.treeWidget' is
        non-empty.

        """
        try:
            self.treeWidget.FFGoGotoItemWithValue(
                "name", constants.DEFAULT_AIRCRAFT)
        except NoSuchItem:
            self.treeWidget.FFGoGotoItemWithIndex(0)

    def updateItemData(self, aircraftId, updateTree=True):
        """Refresh the data for the aircraft identified by 'aircraftId'.

        'aircraftId' should be a tuple (or, more generally, an iterable)
        of the form (aircraftName, aircraftDir). Fetch the relevant data
        from the underlying Aircraft instance, update self.treeData with
        this new data and refresh 'self.treeWidget'.

        The current implementation simply rebuilds the whole MyTreeview
        widget unless the optional argument 'updateTree' is False. This
        can be slow if the amount of data in 'self.treeWidget' is large.

        """
        # Not very efficient...
        for i, (matchKey, name, dir_, *rest) in enumerate(self.treeData):
            if (name, dir_) == aircraftId:
                aircraft = self.config.aircraftWithId(aircraftId)
                self.treeData[i] = (self.aircraftNameMatchKey(aircraft.name),
                                    aircraft.name,
                                    aircraft.dir,
                                    aircraft.useCountForShow)

                if updateTree:
                    # Update the tree, but don't change the selected item.
                    self.setTreeData(self.treeData, preserveSelection=True)
                break
        else:
            raise NoSuchItem(str(aircraftId))
