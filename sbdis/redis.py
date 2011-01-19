#!/usr/bin/env python
import struct
import cStringIO
import sys

nfa_names = {
  0x10: "TYPE_CONST",
  0x22: "TYPE_ACCEPT",
  0x23: "TYPE_PAREN_CLOSE",
  0x24: "TYPE_PAREN_OPEN",
  0x25: "TYPE_SPLIT",
  0x30: "TYPE_DOT",
  0x31: "TYPE_EPSILON_MOVE",
  0x32: "TYPE_LINE_BEGIN",
  0x33: "TYPE_LINE_END",
  0x34: "TYPE_IN_CCLASS",
  0x35: "TYPE_NOT_IN_CCLASS",

  0x100: "TYPE_RE",
}

class Graph:
  def __init__(self):
    self.nodes = set()
    self.edges = {}
    self.redges = {}
    self.tags = {}

  def setTag(self, u, tag):
    self.tags[u] = tag

  def getTag(self, u):
    return self.tags.get(u)

  def removeEdge(self, u, v):
    self.edges[u].remove(v)
    self.redges[v].remove(u)

  def removeNode(self, u):
    for v in self.redges[u]:
      self.edges[v].remove(u)

    for v in self.edges[u]:
      self.redges[v].remove(u)
 
    self.nodes.remove(u)
    del self.edges[u]
    del self.redges[u]

  def mergeIfPossible(self, u, v):
    if v not in self.edges[u]:
      #print 'Not adjacent'
      return False
    elif self.redges[v] != set([u]):
      #print 'v can be entered via node other than u'
      return False
    elif u not in self.tags or v not in self.tags:
      #print 'untagged nodes cannot be merged'
      return False
    elif self.tags[u][0] != 0x100 or self.tags[v][0] != 0x100:
      #print 'only RE nodes can be merged'
      return False
    else:
      self.edges[u] |= self.edges[v]

      self.nodes.remove(v)
      del self.edges[v]
      del self.redges[v]
      self.edges[u].remove(v)

      for v_next in self.redges:
        if v in self.redges[v_next]:
          self.redges[v_next].remove(v)
          self.redges[v_next].add(u)

      utag = self.getTag(u)
      vtag = self.getTag(v)
      self.setTag(u, (0x100, utag[1] + vtag[1]))

      return True

  def addEdge(self, u, v):
    self.nodes.add(u)
    if u not in self.edges:
      self.edges[u] = set()
    if u not in self.redges:
      self.redges[u] = set()

    self.nodes.add(v)
    if v not in self.edges:
      self.edges[v] = set()
    if v not in self.redges:
      self.redges[v] = set()

    self.edges[u].add(v)
    self.redges[v].add(u)

  def pprint(self):
    for u in self.nodes:
      id = u
      tag = self.getTag(u)
      dsts = list(self.edges[u])
      srcs = list(self.redges[u])
      print '%s: %r %s %s' % (id, tag, dsts, srcs)

def reToGraph(re):
  f = cStringIO.StringIO(re)
  header = struct.unpack('>IIIIII', f.read(4 * 6))
  nodes = [struct.unpack('>III', f.read(4 * 3))
           for n in range(header[1])]
  cclasses = [[struct.unpack('>I', f.read(4))[0]
               for span in range(struct.unpack('>I', f.read(4))[0])]
              for i in range(header[4])]
  f.close()

  g = Graph()
  for idx, (typ, next, arg) in enumerate(nodes):
      if typ == 0x10:
        g.addEdge(idx, next)
        g.setTag(idx, (0x100, chr(arg & 0xff)))
      elif typ == 0x22:
        g.setTag(idx, (typ, None))
      elif typ == 0x23:
        g.addEdge(idx, next)
        g.setTag(idx, (0x100, ')'))
      elif typ == 0x24:
        g.addEdge(idx, next)
        g.setTag(idx, (0x100, '('))
      elif typ == 0x25:
        g.addEdge(idx, next)
        g.addEdge(idx, arg)
        g.setTag(idx, (typ, None))
      elif typ == 0x30:
        g.addEdge(idx, next)
        g.setTag(idx, (0x100, '.'))
      elif typ == 0x31:
        g.addEdge(idx, next)
        g.setTag(idx, (typ, None))
      elif typ == 0x32:
        g.addEdge(idx, next)
        g.setTag(idx, (0x100, '^'))
      elif typ == 0x33:
        g.addEdge(idx, next)
        g.setTag(idx, (0x100, '$'))
      elif typ == 0x34 or typ == 0x35:
        rngs = ''
        if typ == 0x35: rngs = '^'
        for i in range(0, len(cclasses[arg]), 2):
          rngs += chr(cclasses[arg][i])
          if cclasses[arg][i] != cclasses[arg][i+1]:
            rngs += '-' + chr(cclasses[arg][i+1])
        g.addEdge(idx, next)
        g.setTag(idx, (0x100, '[' + rngs + ']'))
  return g

def graphToRegEx(g):
  # Merge adjacents and pattern match for RE ops
  done = False
  while not done:
    done = True
    for u, adjs in g.edges.items():
      utag = g.getTag(u)

      # Get rid of "ACCEPT" nodes
      if utag is not None and utag[0] == 0x22:
        g.removeNode(u)
        done = False
        break

      # Try to match *
      if utag is not None and utag[0] == 0x25 and len(adjs) == 2:
        v_left = list(adjs)[0]
        v_right = list(adjs)[1]
        v_lefttag = g.getTag(v_left)
        v_righttag = g.getTag(v_right)

        if v_lefttag is not None and v_lefttag[0] == 0x100:
          if g.edges[v_left] == set([u]) and g.redges[v_left] == set([u]):       
            g.removeEdge(u, v_left)
            g.removeNode(v_left)
            g.setTag(u, (0x100, '(' + v_lefttag[1] + ')*'))
            done = False
            break
          elif u in g.edges[v_left] and len(g.redges[v_left]) == 2 and \
               u in g.redges[v_left]:
            entry = list(g.redges[v_left] - set([u]))[0]
            g.removeEdge(entry, v_left)
            g.removeEdge(u, v_left)
            g.removeNode(v_left)
            g.addEdge(entry, u)
            g.setTag(u, (0x100, '(' + v_lefttag[1] + ')+'))
            done = False
            break
          
        if v_righttag is not None and v_righttag[0] == 0x100:
          if g.edges[v_right] == set([u]) and g.redges[v_right] == set([u]):
            g.removeEdge(u, v_right)
            g.removeNode(v_right)
            g.setTag(u, (0x100, '(' + v_righttag[1] + ')*'))
            done = False
            break
          elif u in g.edges[v_right] and len(g.redges[v_right]) == 2 and \
               u in g.redges[v_right]:
            entry = list(g.redges[v_right] - set([u]))[0]
            g.removeEdge(entry, v_right)
            g.removeEdge(u, v_right)
            g.removeNode(v_right)
            g.addEdge(entry, u)
            g.setTag(u, (0x100, '(' + v_righttag[1] + ')+'))
            done = False
            break

      # Try to match |
      if utag is not None and utag[0] == 0x25 and len(adjs) == 2:
        v_left = list(adjs)[0]
        v_right = list(adjs)[1]
        v_lefttag = g.getTag(v_left)
        v_righttag = g.getTag(v_right)

        if v_lefttag is not None and v_lefttag[0] == 0x100 and \
           v_righttag is not None and v_righttag[0] == 0x100:
          vl_next = g.edges[v_left]
          vr_next = g.edges[v_right]
          if len(vl_next) <= 1 and len(vr_next) <= 1 and \
             vl_next == vr_next:
            g.removeEdge(u, v_left)
            g.removeEdge(u, v_right)
            if len(vl_next) == 1:
              join_node = list(vl_next)[0]
              g.addEdge(u, join_node)
            g.removeNode(v_left)
            g.removeNode(v_right)
            g.setTag(u, (0x100, v_lefttag[1] + '|' + v_righttag[1]))
            done = False
            break

      if utag is not None and utag[0] == 0x31:
        for v in g.edges[u]:
          for uu in g.redges[u]:
            g.addEdge(uu, v)
        g.removeNode(u)
        done = False
        break

      # Merge constants if possible
      for v in adjs:
        if g.mergeIfPossible(u, v):
          done = False
          break
      if not done:
        break

  if len(g.nodes) == 1:
    return g.getTag(list(g.nodes)[0])[1]
  else:
    return None

if __name__ == '__main__':
  f = open(sys.argv[1], 'rb')
  s = f.read()
  f.close()

  g = reToGraph(s)
  re = graphToRegEx(g)

  print re
