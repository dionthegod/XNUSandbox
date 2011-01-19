#!/usr/bin/env python

import struct
import sys

print 'THIS IS CURRENTLY HARDCODED FOR iPhone1,2_4.2.1'
print
print 'You\'ll have to find your own offsets otherwise, sorry.'
print

class KernelCacheOffsets:
  def __init__(self, file_offset, names_offset, sbs_offset):
    self.foff = file_offset
    self.noff = names_offset
    self.sboff = sbs_offset

iPhone_12_421 = KernelCacheOffsets(0x80037000, 0x36D448, 0x36D4D8)

def extract_sbs(fn, kcos, outpath):
  f = open(fn, 'rb')
  f.seek(kcos.noff)
  name_ptrs = []
  while True:
    ptr = struct.unpack('<I', f.read(4))[0]
    if ptr == 0:
      break
    name_ptrs.append(ptr)

  profile_names = []
  for ptr in name_ptrs:
    f.seek(ptr - kcos.foff)
    name = f.read(0x40)
    name = name[:name.find('\x00')]
    profile_names.append(name)

  print profile_names

  f.seek(kcos.sboff)
  sbs_ptrs = []
  while True:
    ptr = struct.unpack('<I', f.read(4))[0]
    if ptr == 0:
      break
    sbs_ptrs.append(ptr)

  sbs = []
  for ptr in sbs_ptrs:
    f.seek(ptr - kcos.foff)
    sb_ptr, sb_length = struct.unpack('<II', f.read(0x8))
    sbs.append((sb_ptr, sb_length))

  for name, (sb_ptr, sb_length) in zip(profile_names, sbs):
    f.seek(sb_ptr - kcos.foff)
    outf = open(outpath + '/' + name + '.sb.bin', 'wb')
    outf.write(f.read(sb_length))
    outf.close()
    print '%s: %08x - %08x' % (name, sb_ptr, sb_ptr + sb_length)

extract_sbs(sys.argv[1], iPhone_12_421, sys.argv[2])
