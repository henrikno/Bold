#! /usr/bin/python
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

from elf.BinArray import BinArray
from elf.constants import *
from elf.elf import Elf64, Elf64_Phdr, TextSegment, DataSegment, Dynamic, Interpreter
import struct, sys

infiles = [Elf64(n) for n in sys.argv[1:]]
for i in infiles:
  i.resolve_names()
  i.find_symbols()

#h = infile.header
#print "Class:                             %s" % h.e_ident.ei_class
#print "Data:                              %s" % h.e_ident.ei_data
#print "Version:                           %s" % h.e_ident.ei_version
#print "OS/ABI:                            %s" % h.e_ident.ei_osabi
#print "ABI Version:                       %s" % h.e_ident.ei_abiversion
#print "Type:                              %s" % h.e_type
#print "Machine:                           %s" % h.e_machine
#print "Version:                           %s" % h.e_version
#print "Entry point address:               0x%x" % h.e_entry
#print "Start of program headers:          %i (bytes into file)" % h.e_phoff
#print "Start of section headers:          %i (bytes into file)" % h.e_shoff
#print "Flags:                             0x%x" % h.e_flags
#print "Size of this header:               %i (bytes)" % h.e_ehsize
#print "Size of program headers:           %i (bytes)" % h.e_phentsize
#print "Number of program headers:         %i" % h.e_phnum
#print "Size of section headers:           %i (bytes)" % h.e_shentsize
#print "Number of section headers:         %i" % h.e_shnum

#print "Section header string table index: %s" % h.e_shstrndx

#print

#print "Section Headers:"
#for sh in infile.shdrs:
  #print "[%2i] %-16s  %-16s %016x  %08x" % (sh.index, sh.name, sh.sh_type,
    #sh.sh_addr, sh.sh_offset)
  #print "     %016x  %016x  %-5s %4i  %4i  %4i" % (sh.sh_size, sh.sh_entsize,
    #sh.sh_flags, sh.sh_link, sh.sh_info, sh.sh_addralign)
#print

#for sh in infile.shdrs :
  #if sh.sh_type == SHT_STRTAB:
    ##print "Section %i is a string table with entries :" % sh.index
    ##for i, name in sh.content.iteritems():
    ##  print "%4i %s" % (i, name)
    #print
  #elif sh.sh_type == SHT_SYMTAB:
    #print "Section %i is a symbol table with entries :" % sh.index
    #print "   Num:    Value          Size Type    Bind   Vis      Ndx Name"
    #for i, sym in enumerate(sh.content.symtab):
      #print "%6i: %016x %5s %-7s %-6s %-7s %4s %s" % (i,
        #sym.st_value, sym.st_size, sym.st_type, sym.st_binding,
        #sym.st_visibility, sym.st_shndx, sym.name)
    #print
  #elif sh.sh_type == SHT_RELA:
    #print "Section %s is a RELA that applies to %s:" % (sh.name, sh.target.name)
    #print "  Offset          Info           Type           Sym. Value    Sym. Name + Addend"
    #for i in sh.content.relatab:
      #print "%012x  %012x %-16s  %016x %s%s + %x" % (i.r_offset, i.r_info,
      #i.r_type, i.symbol.st_value, i.symbol.name,
      #sh.owner.shdrs[i.symbol.st_shndx].name,
      #i.r_addend)
    #print



outfile = Elf64()

text_segment = TextSegment()
data_segment = DataSegment(align=0x100000)

outfile.add_segment(text_segment)
outfile.add_segment(data_segment)


outfile.header.e_ident.make_default_amd64()
outfile.header.e_phoff = outfile.header.size
outfile.header.e_type = ET_EXEC
text_segment.add_content(outfile.header)

ph_text = Elf64_Phdr()
ph_text.p_type = PT_LOAD
ph_text.p_align = 0x100000
outfile.add_phdr(ph_text)
text_segment.add_content(ph_text)

ph_data = Elf64_Phdr()
ph_data.p_type = PT_LOAD
ph_data.p_align = 0x100000
outfile.add_phdr(ph_data)
text_segment.add_content(ph_data)

ph_dynamic = Elf64_Phdr()
ph_dynamic.p_type = PT_DYNAMIC
outfile.add_phdr(ph_dynamic)
text_segment.add_content(ph_dynamic)

ph_interp = Elf64_Phdr()
ph_interp.p_type = PT_INTERP
outfile.add_phdr(ph_interp)
text_segment.add_content(ph_interp)

interp = Interpreter()
text_segment.add_content(interp)

dynamic = Dynamic()
dynamic.add_shlib("libGL.so.1")
dynamic.add_shlib("libSDL-1.2.so.0")
dynamic.add_symtab(0)
dynamic.add_debug()
data_segment.add_content(dynamic)
text_segment.add_content(dynamic.strtab)


# Find interresting sections in input file
for i in infiles:
  for sh in i.shdrs:
    if (sh.sh_flags & SHF_ALLOC):
      if (sh.sh_flags & SHF_EXECINSTR):
        text_segment.add_content(sh.content)
      else: # No exec, it's for .data
        if (sh.sh_type == SHT_NOBITS):
          data_segment.add_nobits(sh.content)
        else:
          data_segment.add_content(sh.content)


outfile.layout(base_vaddr=0x400000)


# Set addresses, sizes, etc. where known
outfile.header.e_phnum = len(outfile.phdrs)
outfile.header.e_phoff = outfile.phdrs[0].file_offset

ph_text.p_offset = text_segment.file_offset
ph_text.p_vaddr = text_segment.virt_addr
ph_text.p_filesz = text_segment.physical_size
ph_text.p_memsz = text_segment.logical_size

ph_data.p_offset = data_segment.file_offset
ph_data.p_vaddr = data_segment.virt_addr
ph_data.p_filesz = data_segment.physical_size
ph_data.p_memsz = data_segment.logical_size

ph_interp.p_offset = interp.file_offset
ph_interp.p_vaddr = interp.virt_addr
ph_interp.p_filesz = interp.physical_size
ph_interp.p_memsz = interp.logical_size

ph_dynamic.p_offset = dynamic.file_offset
ph_dynamic.p_vaddr = dynamic.virt_addr
ph_dynamic.p_filesz = dynamic.physical_size
ph_dynamic.p_memsz = dynamic.logical_size

for i in infiles:
  outfile.undefined_symbols.extend(i.undefined_symbols)

dt_dbg = dynamic.dt_debug_address
outfile.global_symbols["_dt_debug"] = dt_dbg
outfile.global_symbols["_DYNAMIC"] = dynamic.virt_addr

# Take all globally declared symbols, and put them in outfile's dict
for i in infiles:
  for s in i.global_symbols:
    section_addr = i.global_symbols[s][0].content.virt_addr
    addr = section_addr + i.global_symbols[s][1]
    if s in outfile.global_symbols:
      print "Symbol '%s' defined more than once."
      exit(1)
    outfile.global_symbols[s] = addr

for i in infiles:
  i.apply_relocation(outfile.global_symbols)

_start = outfile.global_symbols["_start"]
outfile.header.e_entry = _start

# outfile.apply_global_relocation()

f = open("prout", "wb")
outfile.toBinArray().tofile(f)
f.close()



