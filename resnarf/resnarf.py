#!/usr/bin/env python

import struct
import sys

if len(sys.argv) != 2:
  print 'usage:'
  print '    ./resnarf.py sandbox-profile.sb.bin'
  print
  print '    This will dump a sandbox-profile.sb.bin.ddd.re for each regex'
  print '    found in the binary profile.  ddd is replaced with the decimal'
  print '    index into the regex table.'
  sys.exit(-1)

f = open(sys.argv[1], 'rb')

re_table_offset = struct.unpack('<H', f.read(2))[0] * 8
re_count = struct.unpack('<H', f.read(2))[0]

re_table = []
f.seek(re_table_offset)
for i in range(re_count):
  re_table.append(struct.unpack('<H', f.read(2))[0] * 8)

for idx, offset in enumerate(re_table):
  f.seek(offset)
  re_length = struct.unpack('<I', f.read(4))[0]
  re = f.read(re_length)
  outf = open(sys.argv[1] + '.%03d.re' % (idx,), 'wb')
  outf.write(re)
  outf.close()  

f.close()
