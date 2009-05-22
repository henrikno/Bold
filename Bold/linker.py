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

"""
Main entry point for the bold linker.
"""

from constants import *
from elf import Elf64, Elf64_Phdr, TextSegment, DataSegment, Dynamic, Interpreter
from errors import *
from ctypes.util import find_library

class BoldLinker(object):
  """A Linker object takes one or more objects files, optional shared libs,
  and arranges all this in an executable.

  Important note: the external functions from the libraries are NOT resolved.
  This import is left to the user, as it can be done more efficiently by hash.
  (http://www.linuxdemos.org/contentarticle/how_to_start_4k_introdev_with_ibh)
  For this, a very useful symbol is exported, : _dt_debug, the address of the
  DT_DEBUG's d_ptr.
  """

  def __init__(self):
    object.__init__(self)

    self.objs = []
    self.shlibs = []
    self.entry_point = "_start"
    self.output = Elf64()

  def add_object(self, filename):
    """Add a relocatable file as input."""
    obj = Elf64(filename)
    obj.resolve_names()
    obj.find_symbols()
    self.objs.append(obj)

  def add_shlib(self, libname):
    """Add a shared library to link against."""
    # Note : we use ctypes' find_library to find the real name
    fullname = find_library(libname)
    if not fullname:
      raise LibNotFound(libname)
    self.shlibs.append(fullname)

  def link(self):
    """Do the actual linking."""
    # Prepare two segments. One for .text, the other for .data + .bss
    self.text_segment = TextSegment()
    # .data will be mapped 0x100000 bytes further
    self.data_segment = DataSegment(align=0x100000)
    self.output.add_segment(self.text_segment)
    self.output.add_segment(self.data_segment)

    # Adjust the ELF header
    self.output.header.e_ident.make_default_amd64()
    self.output.header.e_phoff = self.output.header.size
    self.output.header.e_type = ET_EXEC
    # Elf header lies inside .text
    self.text_segment.add_content(self.output.header)

    # Create the four Program Headers. They'll be inside .text
    # The first Program Header defines .text
    ph_text = Elf64_Phdr()
    ph_text.p_type = PT_LOAD
    ph_text.p_align = 0x100000
    self.output.add_phdr(ph_text)
    self.text_segment.add_content(ph_text)

    # Second one defines .data + .bss
    ph_data = Elf64_Phdr()
    ph_data.p_type = PT_LOAD
    ph_data.p_align = 0x100000
    self.output.add_phdr(ph_data)
    self.text_segment.add_content(ph_data)

    # Third one is only there to define the DYNAMIC section
    ph_dynamic = Elf64_Phdr()
    ph_dynamic.p_type = PT_DYNAMIC
    self.output.add_phdr(ph_dynamic)
    self.text_segment.add_content(ph_dynamic)

    # Fourth one is for interp
    ph_interp = Elf64_Phdr()
    ph_interp.p_type = PT_INTERP
    self.output.add_phdr(ph_interp)
    self.text_segment.add_content(ph_interp)

    # We have all the needed program headers, update ELF header
    self.output.header.ph_num = len(self.output.phdrs)

    # Create the actual content for the interpreter section
    interp = Interpreter()
    self.text_segment.add_content(interp)

    # Then the Dynamic section
    dynamic = Dynamic()
    # for all the requested libs, add a reference in the Dynamic table
    for lib in self.shlibs:
      dynamic.add_shlib(lib)
    # Add an empty symtab, symbol resolution is not done.
    dynamic.add_symtab(0)
    # And we need a DT_DEBUG
    dynamic.add_debug()

    # This belongs to .data
    self.data_segment.add_content(dynamic)
    # The dynamic table links to a string table for the libs' names.
    self.text_segment.add_content(dynamic.strtab)

    # We can now add the interesting sections to the corresponding segments
    for i in self.objs:
      for sh in i.shdrs:
        # Only ALLOC sections are worth it.
        # This might require change in the future
        if not (sh.sh_flags & SHF_ALLOC):
          continue

        if (sh.sh_flags & SHF_EXECINSTR):
          self.text_segment.add_content(sh.content)
        else: # No exec, it's for .data or .bss
          if (sh.sh_type == SHT_NOBITS):
            self.data_segment.add_nobits(sh.content)
          else:
            self.data_segment.add_content(sh.content)

    # Now, everything is at its place.
    # Knowing the base address, we can determine where everyone will fall
    self.output.layout(base_vaddr=0x400000)

    # Knowing the addresses of all the parts, Program Headers can be filled
    # This will put the correct p_offset, p_vaddr, p_filesz and p_memsz
    ph_text.update_from_content(self.text_segment)
    ph_data.update_from_content(self.data_segment)
    ph_interp.update_from_content(interp)
    ph_dynamic.update_from_content(dynamic)


    # Gather the undefined symbols from all input files
    undefined_symbols = set()
    for i in self.objs:
      undefined_symbols.update(i.undefined_symbols)

    # Make a dict with all the symbols declared globally.
    # Key is the symbol name, value is the final virtual address
    global_symbols = {}

    for i in self.objs:
      for s in i.global_symbols:
        if s in global_symbols:
          raise RedefinedSymbol(s)
        # Final address is the section's base address + the symbol's offset
        addr = i.global_symbols[s][0].content.virt_addr
        addr += i.global_symbols[s][1]
        global_symbols[s] = addr

    # Add a few useful symbols
    global_symbols["_dt_debug"] = dynamic.dt_debug_address
    global_symbols["_DYNAMIC"] = dynamic.virt_addr

    # Find out which symbols aren't really defined anywhere
    undefined_symbols.difference_update(global_symbols)

    # For now, it's an error. Later, we could try to find them in the shared
    # libraries.
    if len(undefined_symbols):
      raise UndefinedSymbol(undefined_symbols.pop())



    # We can now do the actual relocation
    for i in self.objs:
      i.apply_relocation(global_symbols)

    # And update the ELF header with the entry point
    if not self.entry_point in global_symbols:
      raise UndefinedSymbol(self.entry_point)
    self.output.header.e_entry = global_symbols[self.entry_point]

    # DONE !


  def toBinArray(self):
    return self.output.toBinArray()

  def tofile(self, file_object):
    return self.output.toBinArray().tofile(file_object)

