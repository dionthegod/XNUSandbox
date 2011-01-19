#!/usr/bin/env python

import re
import subprocess
import struct
import sys

def find_symbol(fn, sym, arch="i386"):
  symbol_re = re.compile('^([0-9a-f]{8}) (.) (.*)$')
  p = subprocess.Popen(["nm", "-arch", arch, fn],
                       stdout=subprocess.PIPE)
  while True:
    line = p.stdout.readline()
    if not line:
      break

    mo = symbol_re.match(line)
    if mo is not None:
      if mo.group(3) == sym:
        return mo.groups()

  return None

def get_loadmap(fn, arch="i386"):
  state = 0
  sects = []
  vm_addr = None
  vm_size = None
  file_offset = None
  sectname = None

  p = subprocess.Popen(["otool", "-arch", arch, "-l", fn],
                       stdout=subprocess.PIPE)
  while True:
    line = p.stdout.readline()
    if not line:
      break
    line = line.rstrip()

    if state == 0:
      if line.startswith("Section"):
        state = 1
    elif state == 1:
      if line.startswith("  sectname "):
        sectname = line[len("  sectname "):]
      elif line.startswith("      addr "):
        vm_addr = int(line[len("      addr "):], 16)
      elif line.startswith("      size "):
        vm_size = int(line[len("      size "):], 16)
      elif line.startswith("    offset "):
        file_offset = int(line[len("    offset "):], 10)
      elif line.startswith("Section"):
        sects.append((vm_addr, vm_size, file_offset, sectname))
      elif line.startswith("Load command"):
        sects.append((vm_addr, vm_size, file_offset, sectname))
        vm_addr = None
        vm_size = None
        file_offset = None
        sectname = None
        state = 0

  return sects

def get_address_offset(sects, addr):
  for vaddr, vsize, offset, sectname in sects:
    if addr >= vaddr and addr < (vaddr + vsize):
      return offset + (addr - vaddr)

  return None

def get_address_section(sects, addr):
  for vaddr, vsize, offset, sectname in sects:
    if addr >= vaddr and addr < (vaddr + vsize):
      return (vaddr, vsize, offset, sectname)
  return None

#fn = "/System/Library/Extensions/Sandbox.kext/Contents/MacOS/Sandbox"
def get_operations(fn):
  sym = find_symbol(fn, "_operation_names")
  addr = int(sym[0], 16)
  sects = get_loadmap(fn)
  offset = get_address_offset(sects, addr)

  curr = offset

  f = open(fn, 'rb')
  magic = struct.unpack('>I', f.read(4))[0]
  assert(magic == 0xcafebabe)

  fats = struct.unpack('>I', f.read(4))[0]

  fat_offset = None
  for idx in xrange(fats):
    ct, cst, mo_offset, mo_size, mo_align = struct.unpack('>IIIII', f.read(20))
    if ct == 7:
      fat_offset = mo_offset

  assert(fat_offset is not None) 

  operation_ptrs = []
  f.seek(fat_offset + curr)
  while True:
    ptr = struct.unpack('<I', f.read(4))[0]
    sect = get_address_section(sects, ptr)
    if sect[3] != '__cstring':
      break
    #print '0x%08x' % ptr
    operation_ptrs.append(ptr)

  operations = []
  for ptr in operation_ptrs:
    offset = get_address_offset(sects, ptr)
    f.seek(fat_offset + offset)
    s = f.read(32)
    s = s[:s.find('\x00')]
    operations.append(s)

  #print operations
  f.close()

  return operations

