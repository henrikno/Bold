# -*- coding: utf-8 -*-

# kate: space-indent on; indent-width 2; mixedindent off; indent-mode python;

# Copyright (C) 2009 Amand 'alrj' Tihon <amand.tihon@alrj.org>
#
# This file is part of bold, the Byte Optimized Linker.
# Heavily inspired by elf.h from the GNU C Library.
#
# You can redistribute this file and/or modify it under the terms of the
# GNU Lesser General Public License as published by the Free Software
# Foundation, version 2.1.

from array import array
import struct

class BinArray(array):
  """A specialized array that contains bytes"""
  def __new__(cls, data=None):
    if data:
      return array.__new__(BinArray, "B", data)
    else:
      return array.__new__(BinArray, "B")
