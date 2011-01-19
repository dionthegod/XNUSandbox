#!/usr/bin/env python

from __future__ import with_statement
import struct
import sys
import binascii
import pprint
import redis
import find_operations

# u2 re_table_offset (8-byte words from start of sb)
# u1 re_table_count (really just the low byte)
# u1 padding
# u2[] op_table (8-byte word offset)

def load_op_names_ios():
  global OP_TABLE_COUNT
  OP_TABLE_COUNT = 0x49
  f = open('ops.txt', 'r')
  ops = [s.strip() for s in f.readlines()]
  return ops[0:OP_TABLE_COUNT]

def load_op_names_osx():
  ops = find_operations.get_operations("/System/Library/Extensions/Sandbox.kext/Contents/MacOS/Sandbox")
  global OP_TABLE_COUNT
  OP_TABLE_COUNT = len(ops)
  return ops

def parse_filter(f, offset):
  f.seek(offset * 8)
  is_terminal = ord(f.read(1)) == 1
  if is_terminal:
    f.read(1) # padding
    result = ord(f.read(1))
    return (True, {0: 'allow', 1: 'deny', 2: 'allow-with-log', 3: 'deny-with-log'}[result])
  else:
    filter, filter_arg, match, unmatch = struct.unpack('<BHHH', f.read(7))
    return (False, (filter, filter_arg), parse_filter(f, match), parse_filter(f, unmatch))

def show_filter(typ, arg, re_table):
  if typ == 1:
    return 'path.match("%s")' % (re_table[arg],)
  elif typ == 3:
    return 'file-mode == %d' % (arg,)
  elif typ == 4:
    return 'mach-global.match("%s")' % (re_table[arg],)
  elif typ == 11:
    return 'iokit.match("%s")' % (re_table[arg],)
  elif typ == 12:
    return 'path_in_extensions'
  else:
    return 'filter(%d, %d)' % (typ, arg)

def usage():
  print 'usage:'
  print '    sbdis (ios | osx) binary.sb.bin'
  print
  print '    This will turn a binary sandbox profile into something human'
  print '    readable.  Be sure to specify OSX or iOS on the commandline'
  print '    to match the origin of the profile.'
  sys.exit(-1)

if len(sys.argv) != 3:
  usage()

if sys.argv[1] == 'ios':
  ops = load_op_names_ios()
elif sys.argv[1] == 'osx':
  ops = load_op_names_osx()
else:
  usage()

with open(sys.argv[2], 'rb') as f:
  re_table_offset, re_table_count = struct.unpack('<HH', f.read(4))
  op_table = struct.unpack('<%dH' % OP_TABLE_COUNT, f.read(2 * OP_TABLE_COUNT))
  f.seek(re_table_offset * 8)
  re_table = struct.unpack('<%dH' % re_table_count, f.read(2 * re_table_count))
  regex_table = []
  for offset in re_table:
    f.seek(offset * 8)
    re_count = struct.unpack('<I', f.read(4))[0]
    raw = f.read(re_count)
    g = redis.reToGraph(raw)
    re = redis.graphToRegEx(g)
    regex_table.append(re)
  #print regex_table

  op_bag = {}
  for i, op_offset in enumerate(op_table):
    if op_offset not in op_bag:
      op_bag[op_offset] = set()
    op_bag[op_offset].add(i)

  for i, op_offset in enumerate(op_table):
    # default is special case
    if i != 0 and op_offset == op_table[0]:
      continue

    if op_offset not in op_bag:
      continue

    if i != 0:
      op_list = list(op_bag[op_offset])
    else:
      op_list = [0]

    del op_bag[op_offset]

    filter = parse_filter(f, op_offset)
    #pprint.pprint(filter)

    def make_pfilter(filter):
      pfilter = []
      while filter is not None:
        if filter[0]:
          pfilter.append(filter[1])
          filter = None
        else:
          typ, arg = filter[1]
          true_filter = filter[2]
          false_filter = filter[3]

          if not true_filter[0] and \
             not false_filter[0]:
            pfilter.append(('if', show_filter(typ, arg, regex_table),
              make_pfilter(true_filter), make_pfilter(false_filter)))
            filter = None
          elif true_filter[0]:
            pfilter.append((true_filter[1], show_filter(typ, arg, regex_table)))
            filter = false_filter
          elif false_filter[0]:
            ff = 'true'
            if false_filter[1] == 'true':
              ff = 'false'
            pfilter.append((ff, show_filter(typ, arg, regex_table)))
            filter = true_filter
      return pfilter

    pfilter = ([ops[op] for op in op_list], make_pfilter(filter))
    pprint.pprint(pfilter)
