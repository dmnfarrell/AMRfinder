#!/usr/bin/env python

"""
    sequence viewer GUI
    Created June 2020
    Copyright (C) Damien Farrell

    This program is free software; you can redistribute it and/or
    modify it under the terms of the GNU General Public License
    as published by the Free Software Foundation; either version 3
    of the License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, write to the Free Software
    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

from __future__ import absolute_import, print_function
import sys,os,traceback,subprocess
import glob,platform,shutil
import pickle
import threading,time
from PySide2 import QtCore
from PySide2.QtWidgets import *
from PySide2.QtGui import *

import pandas as pd
import numpy as np
from Bio import SeqIO
from . import tools, app, widgets, tables

home = os.path.expanduser("~")
module_path = os.path.dirname(os.path.abspath(__file__))


def main():
    "Run the application"

    import sys, os
    from argparse import ArgumentParser
    parser = ArgumentParser(description='sequence viewer tool')
    parser.add_argument("-f", "--fasta", dest="filename",default=None,
                        help="input fasta file", metavar="FILE")
    args = vars(parser.parse_args())

    app = QApplication(sys.argv)
    sv = widgets.SequencesViewer(**args)
    if args['filename'] != None:
        sv.load_fasta(args['filename'])
    sv.show()
    app.exec_()

if __name__ == '__main__':
    main()
