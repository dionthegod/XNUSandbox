#!/usr/bin/env python

import re
import subprocess
import sys

symbol_re = re.compile('^([0-9a-f]{8}) (.) (.*)$')
symbols = []
symbols_by_name = {}

p = subprocess.Popen(["nm", "-arch", "i386", "/usr/lib/libsandbox.dylib"],
                     stdout=subprocess.PIPE)
while True:
  line = p.stdout.readline()
  if not line:
    break

  mo = symbol_re.match(line)
  if mo is not None:
    symbols.append(mo.groups())
    symbols_by_name[mo.group(3)] = mo.groups()

#print symbols
#print symbols_by_name['_scheme_init']

print 'struct symbol {'
print '  const char *name;'
print '  unsigned int offset;'
print '} symbols[] = {'

for addr, typ, name in symbols:
  if typ in ['T', 't', 's']:
    print '  { \"%s\", 0x%s },' % (name, addr)

print '};'
print
print 'unsigned int get_offset(const char *name) {'
print '  unsigned int curr;'
print '  unsigned int count = sizeof(symbols) / sizeof(struct symbol);'
print
print '  for(curr = 0; curr < count; ++curr) {'
print '    if (strcmp(name, symbols[curr].name) == 0) {'
print '      return symbols[curr].offset;'
print '    }'
print '  }'
print
print '  return 0;'
print '}'
print



