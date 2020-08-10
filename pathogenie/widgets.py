# -*- coding: utf-8 -*-

"""
    Qt widgets for pathogenie
    Created Nov 2019
    Copyright (C) Damien Farrell

    This program is free software; you can redistribute it and/or
    modify it under the terms of the GNU General Public License
    as published by the Free Software Foundation; either version 2
    of the License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, write to the Free Software
    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

from PySide2 import QtCore, QtGui
from PySide2.QtCore import QObject
from PySide2.QtWidgets import *
from PySide2.QtGui import *

import sys, os, io
import numpy as np
import pandas as pd
import string
from Bio.SeqRecord import SeqRecord
from Bio.Seq import Seq
from Bio import SeqIO

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s
from . import tools

def dialogFromOptions(parent, opts, sections=None,
                      sticky='news', wrap=2, section_wrap=2):
    """Get Qt widgets dialog from a dictionary of options"""

    sizepolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    sizepolicy.setHorizontalStretch(1)
    sizepolicy.setVerticalStretch(0)

    style = '''
    QLabel {
        font-size: 12px;
    }
    QWidget {
        max-width: 130px;
        min-width: 30px;
        font-size: 14px;
    }
    QPlainTextEdit {
        max-height: 80px;
    }

    '''

    if sections == None:
        sections = {'options': opts.keys()}

    widgets = {}
    dialog = QWidget(parent)
    dialog.setSizePolicy(sizepolicy)

    l = QGridLayout(dialog)
    l.setSpacing(2)
    l.setAlignment(QtCore.Qt.AlignLeft)
    scol=1
    srow=1
    for s in sections:
        row=1
        col=1
        f = QGroupBox()
        f.setSizePolicy(sizepolicy)
        f.setTitle(s)
        #f.resize(50,100)
        #f.sizeHint()
        l.addWidget(f,srow,scol)
        gl = QGridLayout(f)
        gl.setAlignment(QtCore.Qt.AlignTop)
        srow+=1
        #gl.setSpacing(10)
        for o in sections[s]:
            label = o
            val = None
            opt = opts[o]
            if 'label' in opt:
                label = opt['label']
            val = opt['default']
            t = opt['type']
            lbl = QLabel(label)
            gl.addWidget(lbl,row,col)
            lbl.setStyleSheet(style)
            if t == 'combobox':
                w = QComboBox()
                w.addItems(opt['items'])
                #w.view().setMinListWidth(100)
                try:
                    w.setCurrentIndex(opt['items'].index(str(opt['default'])))
                except:
                    w.setCurrentIndex(0)
            elif t == 'entry':
                w = QLineEdit()
                w.setText(str(val))
            elif t == 'textarea':
                w = QPlainTextEdit()
                #w.setSizePolicy(sizepolicy)
                w.insertPlainText(str(val))
            elif t == 'slider':
                w = QSlider(QtCore.Qt.Horizontal)
                s,e = opt['range']
                w.setTickInterval(opt['interval'])
                w.setSingleStep(opt['interval'])
                w.setMinimum(s)
                w.setMaximum(e)
                w.setTickPosition(QSlider.TicksBelow)
                w.setValue(val)
            elif t == 'spinbox':
                w = QSpinBox()
                w.setValue(val)
                if 'interval' in opt:
                    w.setSingleStep(opt['interval'])
            elif t == 'checkbox':
                w = QCheckBox()
                w.setChecked(val)
            elif t == 'font':
                w = QFontComboBox()
                w.resize(w.sizeHint())
                w.setCurrentIndex(1)
            col+=1
            gl.addWidget(w,row,col)
            w.setStyleSheet(style)
            widgets[o] = w
            #print (o, row, col)
            if col>=wrap:
                col=1
                row+=1
            else:
                col+=2
        if scol >= section_wrap:
            scol=1
        else:
            scol+=1
    return dialog, widgets

def getWidgetValues(widgets):
    """Get values back from a set of widgets"""

    kwds = {}
    for i in widgets:
        val = None
        if i in widgets:
            w = widgets[i]
            if type(w) is QLineEdit:
                try:
                    val = float(w.text())
                except:
                    val = w.text()
            elif type(w) is QPlainTextEdit:
                val = w.toPlainText()
            elif type(w) is QComboBox or type(w) is QFontComboBox:
                val = w.currentText()
            elif type(w) is QCheckBox:
                val = w.isChecked()
            elif type(w) is QSlider:
                val = w.value()
            elif type(w) is QSpinBox:
                val = w.value()
            if val != None:
                kwds[i] = val
    kwds = kwds
    return kwds

def setWidgetValues(widgets, values):
    """Set values for a set of widgets from a dict"""

    kwds = {}
    for i in values:
        val = values[i]
        if i in widgets:
            #print (i, val, type(val))
            w = widgets[i]
            if type(w) is QLineEdit:
                w.setText(str(val))
            elif type(w) is QPlainTextEdit:
                w.insertPlainText(str(val))
            elif type(w) is QComboBox or type(w) is QFontComboBox:
                w.setCurrentIndex(1)
            elif type(w) is QCheckBox:
                w.setChecked(val)
            elif type(w) is QSlider:
                w.setValue(val)
            elif type(w) is QSpinBox:
                w.setValue(val)
    return

class ToolBar(QWidget):
    """Toolbar class"""
    def __init__(self, table, parent=None):
        super(ToolBar, self).__init__(parent)
        self.parent = parent
        self.table = table
        self.layout = QVBoxLayout()
        self.layout.setAlignment(QtCore.Qt.AlignTop)
        self.layout.setContentsMargins(2,2,2,2)
        self.setLayout(self.layout)
        self.createButtons()
        self.setMaximumWidth(40)
        return

    def createButtons(self):

        funcs = {'load':self.table.load, 'save':self.table.save,
                 'importexcel': self.table.load,
                 'copy':self.table.copy, 'paste':self.table.paste,
                 'plot':self.table.plot,
                 'transpose':self.table.pivot,
                 'pivot':self.table.pivot}
        icons = {'load': 'document-new', 'save': 'document-save-as',
                 'importexcel': 'x-office-spreadsheet',
                 'copy': 'edit-copy', 'paste': 'edit-paste',
                 'plot':'insert-image',
                 'transpose':'object-rotate-right',
                 'pivot': 'edit-undo',
                 }
        for name in funcs:
            self.addButton(name, funcs[name], icons[name])

    def addButton(self, name, function, icon):

        layout=self.layout
        button = QPushButton(name)
        button.setGeometry(QtCore.QRect(30,40,30,40))
        button.setText('')
        iconw = QIcon.fromTheme(icon)
        button.setIcon(QIcon(iconw))
        button.setIconSize(QtCore.QSize(20,20))
        button.clicked.connect(function)
        button.setMinimumWidth(30)
        layout.addWidget(button)

class BaseOptions(object):
    """Class to generate widget dialog for dict of options"""
    def __init__(self, parent=None, opts={}, groups={}):
        """Setup variables"""

        self.parent = parent
        self.groups = groups
        self.opts = opts
        return

    def applyOptions(self):
        """Set the plot kwd arguments from the widgets"""

        self.kwds = getWidgetValues(self.widgets)
        return

    def apply(self):
        self.applyOptions()
        if self.callback != None:
            self.callback()
        return

    def showDialog(self, parent, wrap=2, section_wrap=2):
        """Auto create tk vars, widgets for corresponding options and
           and return the frame"""

        dialog, self.widgets = dialogFromOptions(parent, self.opts, self.groups,
                                wrap=wrap, section_wrap=section_wrap)
        return dialog

    def setWidgetValue(self, key, value):
        "Set a widget value"

        setWidgetValues(self.widgets, {key: value})
        self.applyOptions()
        return

    def increment(self, key, inc):
        """Increase the value of a widget"""

        new = self.kwds[key]+inc
        self.setWidgetValue(key, new)
        return

class DynamicDialog(QDialog):
    """Dynamic form using baseoptions"""

    def __init__(self, parent=None, options={}, groups=None, title='Dialog'):
        super(DynamicDialog, self).__init__(parent)
        self.setWindowTitle(title)
        layout = QVBoxLayout()
        self.setLayout(layout)
        self.opts = BaseOptions(self, options, groups)
        dialog = self.opts.showDialog(self, wrap=1, section_wrap=1)
        layout.addWidget(dialog)
        buttonbox = QDialogButtonBox(self)
        buttonbox.addButton("Cancel", QDialogButtonBox.RejectRole)
        buttonbox.addButton("Ok", QDialogButtonBox.AcceptRole)
        self.connect(buttonbox, QtCore.SIGNAL("accepted()"), self, QtCore.SLOT("accept()"))
        self.connect(buttonbox, QtCore.SIGNAL("rejected()"), self, QtCore.SLOT("reject()"))
        layout.addWidget(buttonbox)
        return

    def get_values():
        """Get the widget values"""

        kwds = self.opts.kwds
        return kwds

class Editor(QTextEdit):
    def __init__(self, parent=None, **kwargs):
        super(Editor, self).__init__(parent, **kwargs)

    def zoom(self, delta):
        if delta < 0:
            self.zoomOut(1)
        elif delta > 0:
            self.zoomIn(1)

    def contextMenuEvent(self, event):

        menu = QMenu(self)
        copyAction = menu.addAction("Copy")
        clearAction = menu.addAction("Clear")
        zoominAction = menu.addAction("Zoom In")
        zoomoutAction = menu.addAction("Zoom Out")
        action = menu.exec_(self.mapToGlobal(event.pos()))
        if action == copyAction:
            self.copy()
        elif action == clearAction:
            self.clear()
        elif action == zoominAction:
            self.zoom(1)
        elif action == zoomoutAction:
            self.zoom(-1)

class PlainTextEditor(QPlainTextEdit):
    def __init__(self, parent=None, **kwargs):
        super(PlainTextEditor, self).__init__(parent, **kwargs)
        font = QFont("Monospace")
        font.setPointSize(10)
        font.setStyleHint(QFont.TypeWriter)
        self.setFont(font)
        return

    def zoom(self, delta):
        if delta < 0:
            self.zoomOut(1)
        elif delta > 0:
            self.zoomIn(1)

    def contextMenuEvent(self, event):

        menu = QMenu(self)
        copyAction = menu.addAction("Copy")
        clearAction = menu.addAction("Clear")
        zoominAction = menu.addAction("Zoom In")
        zoomoutAction = menu.addAction("Zoom Out")
        action = menu.exec_(self.mapToGlobal(event.pos()))
        if action == copyAction:
            self.copy()
        elif action == clearAction:
            self.clear()
        elif action == zoominAction:
            self.zoom(1)
        elif action == zoomoutAction:
            self.zoom(-1)

class FileViewer(QDialog):
    """Sequence records features viewer"""
    def __init__(self, parent=None, filename=None):

        super(FileViewer, self).__init__(parent)
        self.ed = ed = QPlainTextEdit(self, readOnly=True)
        #ed.setStyleSheet("font-family: monospace; font-size: 14px;")
        font = QFont("Monospace")
        font.setPointSize(10)
        font.setStyleHint(QFont.TypeWriter)
        self.ed.setFont(font)
        self.setWindowTitle('sequence features')
        self.setGeometry(QtCore.QRect(200, 200, 800, 800))
        #self.setCentralWidget(ed)
        l = QVBoxLayout(self)
        self.setLayout(l)
        #w = self.recselect = QComboBox()
        #l.addWidget(QLabel('contig'))
        #l.addWidget(w)
        l.addWidget(ed)
        self.show()

    def show_records(self, recs, format='genbank'):

        from Bio import SeqIO
        recs = SeqIO.to_dict(recs)
        if format == 'genbank':
            for r in recs:
                self.ed.appendPlainText(recs[r].format('genbank'))
        elif format == 'gff':
            tools.save_gff(recs,'temp.gff')
            f = open('temp.gff','r')
            for l in f.readlines():
                self.ed.appendPlainText(l)
        recnames = list(recs.keys())
        #self.recselect.addItems(recnames)
        #self.recselect.setCurrentIndex(0)
        self.scroll_top()
        return

    def scroll_top(self):
        vScrollBar = self.ed.verticalScrollBar()
        vScrollBar.triggerAction(QScrollBar.SliderToMinimum)
        return

class AlignmentWidget(QWidget):
    """Widget for showing sequence alignments"""
    def __init__(self, parent=None):
        super(AlignmentWidget, self).__init__(parent)
        l = QHBoxLayout(self)
        self.setLayout(l)
        self.m = QSplitter(self)
        l.addWidget(self.m)
        self.left = PlainTextEditor(self.m, readOnly=True)
        self.right = PlainTextEditor(self.m, readOnly=True)
        self.left.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.right.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.m.setSizes([200,300])
        self.m.setStretchFactor(1,2)
        #connect scrollbars
        self.right.verticalScrollBar().sliderMoved.connect(self.left.verticalScrollBar().setValue)
        return

    def scroll_top(self):
        vScrollBar = self.right.verticalScrollBar()
        vScrollBar.triggerAction(QScrollBar.SliderToMinimum)
        return

    def draw_alignment(self, aln, format='color by residue'):
        """Show alignment with colored columns"""

        left = self.left
        right = self.right
        chunks=0
        offset=0
        diff = False

        left.clear()
        right.clear()
        self.scroll_top()

        colors = tools.get_protein_colors()
        format = QtGui.QTextCharFormat()
        format.setBackground(QtGui.QBrush(QtGui.QColor('white')))
        cursor = right.textCursor()

        ref = aln[0]
        l = len(aln[0])
        n=60
        s=[]
        if chunks > 0:
            chunks = [(i,i+n) for i in range(0, l, n)]
        else:
            chunks = [(0,l)]
        for c in chunks:
            start,end = c
            lbls = np.arange(start+1,end+1,10)-offset
            head = ''.join([('%-10s' %i) for i in lbls])
            #s = '%-25s %s' %('',head)
            #cursor.setCharFormat(format)
            cursor.insertText(head)
            right.insertPlainText('\n')
            left.appendPlainText(' ')
            for a in aln:
                name = a.id
                seq = a.seq[start:end]
                left.appendPlainText(name)
                line = ''
                for aa in seq:
                    c = colors[aa]
                    line += '<span style="background-color:%s;">%s</span>' %(c,aa)
                cursor.insertHtml(line)
                cursor.insertText('\n')
        #cursor.setCharFormat(format)
        left.appendPlainText('')
        return

class SequencesViewer(QMainWindow):
    """Viewer for sequences and alignments"""

    def __init__(self, parent=None, filename=None, title='Sequence Viewer'):
        super(SequencesViewer, self).__init__(parent)
        #QMainWindow.__init__(self, flags=QtCore.Qt.Window)
        self.setWindowTitle(title)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setGeometry(QtCore.QRect(200, 200, 1000, 600))
        self.setMinimumHeight(150)
        self.recs = None
        self.aln = None
        self.add_widgets()
        self.show()
        return

    def add_widgets(self):
        """Add widgets"""

        self.main = QWidget(self)
        self.setCentralWidget(self.main)
        l = QHBoxLayout(self.main)
        self.main.setLayout(l)
        self.tabs = QTabWidget(self.main)
        l.addWidget(self.tabs)

        self.ed = ed = PlainTextEditor(self, readOnly=True)
        self.ed.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.tabs.addTab(self.ed, 'fasta')

        self.alnview = AlignmentWidget(self.main)
        self.tabs.addTab(self.alnview, 'alignment')

        #import pylab as plt
        #from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
        #self.fig,self.ax = plt.subplots(1,1)
        #self.treeview = FigureCanvas(self.fig)
        #self.tabs.addTab(self.treeview, 'tree')

        sidebar = QWidget()
        sidebar.setFixedWidth(180)
        l.addWidget(sidebar)
        l2 = QVBoxLayout(sidebar)
        l2.setSpacing(5)
        l2.setAlignment(QtCore.Qt.AlignTop)
        #btn = QPushButton('Show Tree')
        #btn.clicked.connect(self.show_tree)
        #l2.addWidget(btn)
        btn = QPushButton()
        btn.clicked.connect(self.zoom_out)
        iconw = QIcon.fromTheme('zoom-out')
        btn.setIcon(QIcon(iconw))
        l2.addWidget(btn)
        btn = QPushButton()
        btn.clicked.connect(self.zoom_in)
        iconw = QIcon.fromTheme('zoom-in')
        btn.setIcon(QIcon(iconw))
        l2.addWidget(btn)
        lbl = QLabel('Format')
        l2.addWidget(lbl)
        w = QComboBox()
        w.addItems(['no color','color by residue','color by difference'])
        w.setCurrentIndex(1)
        w.activated.connect(self.show_alignment)
        self.formatchoice = w
        l2.addWidget(w)
        lbl = QLabel('Set Reference')
        l2.addWidget(lbl)
        w = QComboBox()
        w.activated.connect(self.set_reference)
        self.referencechoice = w
        l2.addWidget(w)
        lbl = QLabel('Aligner')
        l2.addWidget(lbl)
        w = QComboBox()
        w.setCurrentIndex(1)
        w.addItems(['clustal','muscle'])
        self.alignerchoice = w
        l2.addWidget(w)
        #lbl = QLabel('Width')
        #l2.addWidget(lbl)
        #w = QLineEdit()
        #l2.addWidget(w)
        self.create_menu()
        return

    def create_menu(self):
        """Create the menu bar for the application. """

        self.file_menu = QMenu('&File', self)
        self.menuBar().addMenu(self.file_menu)
        self.file_menu.addAction('&Load Fasta File', self.load_fasta,
                QtCore.Qt.CTRL + QtCore.Qt.Key_F)
        self.file_menu.addAction('&Save Alignment', self.save_alignment,
                QtCore.Qt.CTRL + QtCore.Qt.Key_S)
        return

    def scroll_top(self):
        vScrollBar = self.ed.verticalScrollBar()
        vScrollBar.triggerAction(QScrollBar.SliderToMinimum)
        return

    def zoom_out(self):
        self.ed.zoom(-1)
        self.alnview.left.zoom(-1)
        self.alnview.right.zoom(-1)
        return

    def zoom_in(self):
        self.ed.zoom(1)
        self.alnview.left.zoom(1)
        self.alnview.right.zoom(1)
        return

    def load_fasta(self, filename=None):
        """Load fasta file"""

        if filename == None:
            filename, _ = QFileDialog.getOpenFileName(self, 'Open File', './',
                            filter="Fasta Files(*.fa *.fna *.fasta);;All Files(*.*)")
        if not filename:
            return
        recs = list(SeqIO.parse(filename, 'fasta'))
        self.load_records(recs)
        return

    def load_records(self, recs):
        """Load seqrecords list"""

        self.recs = recs
        self.reference = self.recs[0]
        rdict = SeqIO.to_dict(recs)
        self.show_fasta()
        self.show_alignment()
        self.referencechoice.addItems(list(rdict.keys()))
        return

    def set_reference(self):
        ref = self.referencechoice.currentText()
        return

    def show_fasta(self):
        """Show records as fasta"""

        recs = self.recs
        if recs == None:
            return
        self.ed.clear()
        for rec in recs:
            s = rec.format('fasta')
            self.ed.insertPlainText(s)
        self.scroll_top()
        return

    def align(self):
        """Align current sequences"""

        if self.aln == None:
            outfile = 'temp.fa'
            SeqIO.write(self.recs, outfile, 'fasta')
            self.aln = tools.clustal_alignment(outfile)
        return

    def show_alignment(self):

        format = self.formatchoice.currentText()
        self.align()
        aln = self.aln
        self.alnview.draw_alignment(aln, format)
        return

    def save_alignment(self):

        filters = "clustal files (*.aln);;All files (*.*)"
        filename, _ = QFileDialog.getSaveFileName(self,"Save Alignment",
                                                  "",filters)
        if not filename:
            return
        SeqIO.write(self.aln,filename,format='clustal')
        return

class TreeBuilder(QMainWindow):
    """Interface to build trees from annotations using various methods"""

    def __init__(self, parent=None, title='Tree Builder'):
        super(TreeBuilder, self).__init__(parent)
        self.setWindowTitle(title)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setGeometry(QtCore.QRect(200, 200, 1000, 600))
        self.setMinimumHeight(150)
        self.add_widgets()
        self.show()
        return

    def add_widgets(self):
        """Add widgets"""

        self.main = QWidget(self)
        self.setCentralWidget(self.main)
        l = QHBoxLayout(self.main)
        self.main.setLayout(l)
        self.tabs = QTabWidget(self.main)
        l.addWidget(self.tabs)
        import pylab as plt
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
        self.fig,self.ax = plt.subplots(1,1)
        self.treeview = FigureCanvas(self.fig)
        self.tabs.addTab(self.treeview, 'tree')

        self.alnview = AlignmentWidget(self.main)
        self.tabs.addTab(self.alnview, 'alignment')

        sidebar = QWidget()
        sidebar.setFixedWidth(180)
        l.addWidget(sidebar)
        l2 = QVBoxLayout(sidebar)
        l2.setSpacing(5)
        l2.setAlignment(QtCore.Qt.AlignTop)
        btn = QPushButton('Build Tree')
        btn.clicked.connect(self.build_tree)
        l2.addWidget(btn)
        lbl = QLabel('Sequence Type')
        l2.addWidget(lbl)
        w = QComboBox()
        w.addItems(['protein','nucleotide'])
        self.seqtypechoice = w
        l2.addWidget(w)
        lbl = QLabel('Root On')
        l2.addWidget(lbl)
        w = QComboBox()
        l2.addWidget(w)
        w.addItems(['unrooted'])
        self.rootchoice = w
        lbl = QLabel('Genes')
        l2.addWidget(lbl)
        w = QListWidget()
        w.setSelectionMode(QAbstractItemView.MultiSelection)
        #w.setFixedHeight(200)
        self.genechoice = w
        l2.addWidget(w)

    def load_annotations(self, annotations):
        """Load annotations (lists of SeqRecord objects)"""

        self.annotations = annotations
        self.annot_df = tools.get_annotations_dataframe(annotations)
        genes = sorted(list(self.annot_df.gene.dropna().unique()))
        self.genechoice.addItems(genes)
        samples = list(self.annot_df['sample'].unique())
        self.rootchoice.addItems(samples)
        return

    def build_tree(self, seqtype='protein'):
        """Build tree from a set of selected genes"""

        df = self.annot_df
        annot = self.annotations
        samples = df['sample'].unique()
        genes = [i.text() for i in self.genechoice.selectedItems()]
        print (genes)
        seqtype = self.seqtypechoice.currentText()

        #get sequences for genes across all samples in order
        found = []
        for s in samples:
            seq = ''
            recs = SeqIO.to_dict(annot[s])
            for g in genes:
                rows = df[(df.gene==g) & (df['sample']==s)]
                if len(rows)==0:
                    continue
                row = rows.iloc[0]
                #print (row)
                if seqtype == 'protein':
                    seq += row.translation
                    #print (seq)
                else:
                    #get nucleotide sequence instead
                    rec = recs[row.id]
                    new = rec.seq[row.start:row.end]
                    #print (g)
                    if row.strand == -1:
                        new = new.reverse_complement()
                    seq += str(new)
                    #print (new)
                    #print (new.translate())

            #print (seq)
            rec = SeqRecord(Seq(seq),id=s)
            found.append(rec)

        #align
        outfile = 'temp.fa'
        SeqIO.write(found, outfile, 'fasta')
        aln = tools.muscle_alignment(outfile)
        dm, tree = tools.build_tree(aln)
        self.show_tree(tree)
        self.alnview.draw_alignment(aln)
        return

    def show_tree(self, tree):
        self.ax.cla()
        self.tree = tree
        tools.draw_tree(self.tree, ax=self.ax)
        self.fig.canvas.draw()
        return

class SeqFeaturesViewer(QDialog):
    """Sequence records features viewer using dna_features_viewer"""
    def __init__(self, parent=None, filename=None, title='features'):

        super(SeqFeaturesViewer, self).__init__(parent)
        self.setWindowTitle(title)
        self.setGeometry(QtCore.QRect(200, 200, 1000, 400))
        self.setMinimumHeight(150)
        self.add_widgets()
        self.color_map = {
            "rep_origin": "yellow",
            "CDS": "lightblue",
            "regulatory": "red",
            "misc_recomb": "darkblue",
            "misc_feature": "lightgreen",
            "tRNA": "orange"
        }
        return

    def add_widgets(self):
        """Add widgets"""

        l = QVBoxLayout(self)
        self.setLayout(l)
        val=0
        navpanel = QWidget()
        navpanel.setMaximumHeight(60)
        l.addWidget(navpanel)
        bl = QHBoxLayout(navpanel)
        slider = QSlider(QtCore.Qt.Horizontal)
        slider.setTickPosition(slider.TicksBothSides)
        slider.setTickInterval(1000)
        slider.setPageStep(200)
        slider.setValue(1)
        #slider.sliderReleased.connect(self.value_changed)
        slider.valueChanged.connect(self.value_changed)
        self.slider = slider
        bl.addWidget(slider)

        zoomoutbtn = QPushButton('-')
        zoomoutbtn.setMaximumWidth(50)
        bl.addWidget(zoomoutbtn)
        zoomoutbtn.clicked.connect(self.zoom_out)
        zoominbtn = QPushButton('+')
        zoominbtn.setMaximumWidth(50)
        bl.addWidget(zoominbtn)
        zoominbtn.clicked.connect(self.zoom_in)

        self.recselect = QComboBox()
        #recselect.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.recselect.currentIndexChanged.connect(self.update_record)
        bl.addWidget(self.recselect)

        from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
        import matplotlib.pyplot as plt
        fig,ax = plt.subplots(1,1,figsize=(15,2))
        self.canvas = FigureCanvas(fig)
        l.addWidget(self.canvas)
        self.ax = ax

        bottom = QWidget()
        bottom.setMaximumHeight(50)
        l.addWidget(bottom)
        bl2 = QHBoxLayout(bottom)
        self.loclbl = QLabel('')
        bl2.addWidget(self.loclbl)
        savebtn = QPushButton('Save Image')
        savebtn.clicked.connect(self.save_image)
        bl2.addWidget(savebtn)
        return

    def load_records(self, recs):
        """Load list of SeqRecord objects"""

        from Bio import SeqIO
        self.records = SeqIO.to_dict(recs)
        recnames = list(self.records.keys())
        self.rec = self.records[recnames[0]]
        length = len(self.rec.seq)
        self.recselect.addItems(recnames)
        self.recselect.setStyleSheet("QComboBox { combobox-popup: 0; }");
        self.recselect.setMaxVisibleItems(10)
        sl = self.slider
        sl.setMinimum(1)
        sl.setMaximum(length)
        sl.setTickInterval(length/20)
        return

    def set_record(self, recname):
        """Set the selected record which also updates the plot"""

        index = self.recselect.findText(recname)
        self.recselect.setCurrentIndex(index)
        return

    def update_record(self, recname=None):
        """Update after record selection changed"""

        #if recname == None:
        recname = self.recselect.currentText()
        #print ('name',recname)
        self.rec = self.records[recname]
        length = len(self.rec.seq)
        sl = self.slider
        sl.setMinimum(1)
        sl.setMaximum(length)
        sl.setTickInterval(length/20)
        self.redraw()
        return

    def value_changed(self):
        """Callback for widgets"""

        length = len(self.rec.seq)
        r = self.view_range
        start = int(self.slider.value())
        end = int(start+r)
        if end > length:
            return
        #print (start, end)
        self.redraw(start, end)
        return

    def zoom_in(self):
        """Zoom in"""

        length = len(self.rec.seq)
        fac = 1.2
        r = int(self.view_range/fac)
        start = int(self.slider.value())
        end = start + r
        if end > length:
            end=length
        self.redraw(start, end)
        return

    def zoom_out(self):
        """Zoom out"""

        length = len(self.rec.seq)
        fac = 1.2
        r = int(self.view_range*fac)
        start = int(self.slider.value())
        end = start + r
        if end > length:
            end=length
            start = start-r
        self.redraw(start, end)
        return

    def redraw(self, start=1, end=2000):
        """Plot the features"""

        import matplotlib
        import pylab as plt
        from dna_features_viewer import GraphicFeature, GraphicRecord
        from dna_features_viewer import BiopythonTranslator

        ax=self.ax
        ax.clear()
        rec = self.rec
        length = len(self.rec.seq)
        if start<0:
            start=1
        if end <= 0:
            end = start+2000
        if end-start > 100000:
            end = start+100000
        if end > length:
            end = length
        rec = self.rec
        translator = BiopythonTranslator(
            features_filters=(lambda f: f.type not in ["gene", "source"],),
            features_properties=lambda f: {"color": self.color_map.get(f.type, "white")},
        )
        #print (start, end, length)
        graphic_record = translator.translate_record(rec)
        cropped_record = graphic_record.crop((start, end))
        #print (len(cropped_record.features))
        cropped_record.plot( strand_in_label_threshold=7, ax=ax)
        if end-start < 150:
            cropped_record.plot_sequence(ax=ax, location=(start,end))
            cropped_record.plot_translation(ax=ax, location=(start,end),fontdict={'weight': 'bold'})
        plt.tight_layout()
        self.canvas.draw()
        self.view_range = end-start
        self.loclbl.setText(str(start)+'-'+str(end))
        return

    def save_image(self):

        filters = "png files (*.png);;svg files (*.svg);;jpg files (*.jpg);;All files (*.*)"
        filename, _ = QFileDialog.getSaveFileName(self,"Save Figure",
                                                  "",filters)
        if not filename:
            return
        self.ax.figure.savefig(filename, bbox_inches='tight')
        return

'''class AlignmentViewer(QDialog):
    """Alignment viewer"""
    def __init__(self, parent=None):
        super(AlignmentViewer, self).__init__(parent)
        self.setModal(False)
        self.setGeometry(QtCore.QRect(200, 200, 1000, 400))
        self.setWindowTitle('sequence alignment')
        l = QVBoxLayout(self)
        self.setLayout(l)
        self.tabs = QTabWidget(self)
        self.tabs.setTabsClosable(True)
        l.addWidget(self.tabs)
        self.show()

    def show_alignment(self, aln, name=''):

        from PySide2.QtWebEngineWidgets import QWebEngineView
        from . import viewers
        from bokeh.plotting import figure, output_file, save
        p = viewers.plot_sequence_alignment(aln)
        output_file("seqs.html")
        save(p)
        webview = QWebEngineView()
        path = os.path.abspath('seqs.html')
        webview.load( QtCore.QUrl.fromLocalFile(path) )
        self.tabs.addTab(webview,name)
        return'''

class PlotViewer(QDialog):
    def __init__(self, parent=None):
        super(PlotViewer, self).__init__(parent)
        from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar
        self.setGeometry(QtCore.QRect(200, 200, 600, 600))
        self.grid = QGridLayout()
        self.setLayout(self.grid)
        #self.show()
        #self.show_figure()
        return

    def show_figure(self, fig):

        from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
        import matplotlib.pyplot as plt

        #ax.plot(range(10))
        canvas = FigureCanvas(fig)
        self.grid.addWidget(canvas)
        self.fig = fig
        #self.ax = ax
        return
