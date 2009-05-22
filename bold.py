#! /usr/bin/python
# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 2; mixedindent off; indent-mode python;

# Copyright (C) 2009 Amand 'alrj' Tihon <amand.tihon@alrj.org>
#
# This file is part of bold, the Byte Optimized Linker.
#
# You can redistribute this file and/or modify it under the terms of the
# GNU Lesser General Public License as published by the Free Software
# Foundation, version 2.1.

#from bold.constants import *
#from bold.elf import Elf64, Elf64_Phdr, TextSegment, DataSegment, Dynamic, Interpreter

__author__ = "Amand Tihon <amand.tihon@alrj.org>"
__version__ = "0.0.1"


from Bold.linker import BoldLinker
from Bold.errors import *
from optparse import OptionParser
import os, sys

class BoldOptionParser(OptionParser):
  """Bold option parser."""
  global __version__
  _usage_message = "%prog [options] file..."
  _version_message = "%%prog version %s" % __version__
  _description_message = """A limited ELF linker for x86_64. It is
intended to create very small executables with the least possible overhead."""

  def __init__(self):
    OptionParser.__init__(self, usage=self._usage_message,
      version=self._version_message, description=self._description_message,
      add_help_option=True, prog="bold")

    self.set_defaults(entry="_start", outfile="a.out")

    self.add_option("-e", "--entry", action="store", dest="entry",
      metavar="SYMBOL", help="Set the entry point (default: _start)")
    self.add_option("-l", "--library", action="append", dest="shlibs",
      metavar="LIBNAME", help="Search for library LIBNAME")
    self.add_option("-o", "--output", action="store", dest="outfile",
      metavar="FILE", help="Set output file name (default: a.out)")


def main():
  parser = BoldOptionParser()
  options, args = parser.parse_args()

  linker = BoldLinker()

  if options.shlibs:
    for shlib in options.shlibs:
      try:
        linker.add_shlib(shlib)
      except LibNotFound, e:
        print >>sys.stderr, e
        return 1

  if not args:
    print >>sys.stderr, "No input files"
    return 1

  for infile in args:
    try:
      linker.add_object(infile)
    except UnsupportedObject, e:
      print >>sys.stderr, e
      return 1
    except IOError, e:
      print >>sys.stderr, e
      return 1

  linker.entry_point = options.entry

  try:
    linker.link()
  except UndefinedSymbol, e:
    print >>sys.stderr, e
    return 1
  except RedefinedSymbol, e:
    print >>sys.stderr, e
    return 1

  # Remove the file if it was present
  try:
    os.unlink(options.outfile)
  except os.error, e:
    if e.errno == 2: # No such file
      pass

  try:
    o = open(options.outfile, "wb")
  except IOError, e:
    print >>sys.stderr, e
    return 1

  linker.tofile(o)
  o.close()
  
  try:
    os.chmod(options.outfile, 0755)
  except IOError, e:
    print >>sys.stderr, e
    return 1

  return 0


if __name__ == "__main__":
  try:
    rcode = main()
  except Exception, e:
    raise
    print >>sys.stderr, "Unhandled error:", e
    rcode = 1

  exit(rcode)

