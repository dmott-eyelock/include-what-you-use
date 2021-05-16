#!/usr/bin/env python

##===--- generate_qt_mappings.py ------------------------------------------===##
#
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.
#
##===----------------------------------------------------------------------===##

"""
This script generates the Qt mapping file according to given Qt include
directory

Example usage :

   $ ./generate_qt_mappings.py /usr/include/x86_64-linux-gnu/qt5 qt5_11.imp

"""

from __future__ import print_function
import argparse
import glob
import json
import os
import re
import sys


OUTFILEHDR = ("# Do not edit! This file was generated by the script %s." %
              os.path.basename(__file__))

QOBJECT_SYMBOLS = [
    "QObjectList",
    "qFindChildren",
    "qobject_cast",
    "QT_NO_NARROWING_CONVERSIONS_IN_CONNECT",
    "Q_CLASSINFO",
    "Q_DISABLE_COPY",
    "Q_DISABLE_COPY_MOVE",
    "Q_DISABLE_MOVE",
    "Q_EMIT",
    "Q_ENUM",
    "Q_ENUM_NS",
    "Q_FLAG",
    "Q_FLAG_NS",
    "Q_GADGET",
    "Q_INTERFACES",
    "Q_INVOKABLE",
    "Q_NAMESPACE",
    "Q_NAMESPACE_EXPORT",
    "Q_OBJECT",
    "Q_PROPERTY",
    "Q_REVISION",
    "Q_SET_OBJECT_NAME",
    "Q_SIGNAL",
    "Q_SIGNALS",
    "Q_SLOT",
    "Q_SLOTS",
    "emit",
    "slots",
    "signals",
    "SIGNAL",
    "SLOT",
]


class QtHeader(object):
    """ Carry data associated with a Qt header """
    def __init__(self, headername):
        self.headername = headername
        self.classname = os.path.basename(headername)
        self.modulename = os.path.basename(os.path.dirname(headername))
        self._private_headers = None

    def get_private_headers(self):
        """ Return a list of headernames included by this header """
        if self._private_headers is None:
            with open(self.headername, 'r') as headerfile:
                included = re.findall(r'#include "(.*)\.h"', headerfile.read())
            self._private_headers = list(included)
        return self._private_headers


def build_imp_lines(symbols_map, includes_map):
    """ Generate a big string containing the mappings in .imp format.

    This should ideally return a jsonable structure instead, and use json.dump
    to write it to the output file directly. But there doesn't seem to be a
    simple way to convince Python's json library to generate a "packed"
    formatting, it always prefers to wrap dicts onto multiple lines.

    Cheat, and use json.dumps for escaping and build a string instead.
    """
    root = []

    def jsonline(mapping):
        return "  " + json.dumps(mapping)

    for symbol, header in symbols_map:
        map_to = "<" + header + ">"
        root.append(jsonline({"symbol": [symbol, "private", map_to, "public"]}))

    for module, include, header in includes_map:
        # Use regex map-from to match both quoted and angled includes and
        # optional directory prefix (e.g. <QtCore/qnamespace.h> is equivalent to
        # "qnamespace.h").
        map_from = r'@["<](%s/)?%s\.h[">]' % (module, include)
        map_to = "<" + header + ">"
        root.append(jsonline({"include": [map_from, "private",
                                          map_to, "public"]}))

    lines = "[\n"
    lines += ",\n".join(root)
    lines += "\n]\n"
    return lines


def add_mapping_rules(header, symbols_map, includes_map):
    """ Add symbol and include mappings for a Qt module. """
    symbols_map += [(header.classname, header.classname)]
    for include in header.get_private_headers():
        includes_map += [(header.modulename, include, header.classname)]


def main(qt_include_dir, output_file):
    """ Entry point. """
    symbols_map = []
    includes_map = []
    deferred_headers = []

    # Add manual overrides.
    symbols_map += [("qDebug", "QtGlobal")]
    symbols_map += [(symbol, "QObject") for symbol in QOBJECT_SYMBOLS]
    includes_map += [("QtCore", "qnamespace", "Qt")]

    # Collect mapping information from Qt directory tree.
    headers = glob.glob(os.path.join(qt_include_dir, '**/*[!.h]'))
    for header in headers:
        if os.path.isdir(header):
            continue

        header = QtHeader(header)
        if header.classname == "QInternal":
            continue

        if header.classname == header.modulename:
            deferred_headers.append(header)
        else:
            add_mapping_rules(header, symbols_map, includes_map)

    for header in deferred_headers:
        add_mapping_rules(header, symbols_map, includes_map)

    # Transform to .imp-style format and write to output file.
    lines = build_imp_lines(symbols_map, includes_map)
    with open(output_file, 'w') as outfile:
        print(OUTFILEHDR, file=outfile)
        print(lines, file=outfile)

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("qt_include_dir", help="Qt include directoy")
    parser.add_argument("output_file", help="Generated output mapping file")
    args = parser.parse_args()
    sys.exit(main(args.qt_include_dir, args.output_file))