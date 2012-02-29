from cast.cParser import Parser as cParser
from cast.cParser import Ast 
from cast.ppParser import Parser as ppParser
from xtermcolor.ColorMap import XTermColorMap

class Token:
  def __init__(self, id, resource, terminal_str, source_string, lineno, colno):
    self.__dict__.update(locals())
  
  def getString(self):
    return self.source_string
  
  def getLine(self):
    return self.lineno
  
  def getColumn(self):
    return self.colno

  def getId(self):
    return self.id

  def getTerminalStr(self):
    return self.terminal_str

  def getResource(self):
    return self.resource

  def toAst(self):
    return self
  
  def __str__( self ):
    return self.toString()

  def toString( self, format='long' ):
    truncatedSourceString = self.source_string.replace('>', '&gt;')
    if len(truncatedSourceString) > 10:
      truncatedSourceString = truncatedSourceString[:10] + '...'
    return '<%s (%s) [%s line %d, col %d]>' % ( self.terminal_str.lower(), truncatedSourceString, self.resource, self.lineno, self.colno )

class ppToken(Token):
  type = 'pp'

# TODO: this takes ridiculous parameters.
# 1) should be able to imply terminal_str from id
# 2) lineno, colno, context should all be one Context object
class cToken(Token):
  type = 'c'
  fromPreprocessor = False

  def __init__(self, id, resource, terminal_str, source_string, lineno, colno, context):
    super().__init__(id, resource, terminal_str, source_string, lineno, colno)
    self.context = context

class Cursor:
  def __init__(self):
    self.string = ''
    self.lineno = 1
    self.colno = 1
    c = lambda x: cParser.terminals[x]
    self.insertSpaceAfter = {
      c('else')
    }

  def add(self, token):
    if token.lineno > self.lineno:
      self.string += ''.join('\n' for i in range(token.lineno - self.lineno))
      self.lineno = token.lineno
      self.colno = 1
    if token.colno > self.colno:
      self.string += ''.join(' ' for i in range(token.colno - self.colno))
      self.colno = token.colno
    self.string += token.source_string
    if token.fromPreprocessor or token.id in self.insertSpaceAfter:
      self.string += ' '
    self.colno += len(token.source_string)
  def __str__(self):
    return self.string

class SourceCodeWriter:
  def __init__(self, tokenList, parsetree=None, grammar=None, ast=None, theme=None, highlight=False):
    self.__dict__.update(locals())
    self.string = ''
    self.lineno = 1
    self.colno = 1
    self.ancestors = dict([(t, set()) for t in self.tokenList])
    self.parents = dict([(t, set()) for t in self.tokenList])
    self.getTokenAncestors(ast)
    self.termcolor = XTermColorMap()
    c = lambda x: cParser.terminals[x]
    self.insertSpaceAfter = {
      c('else')
    }

    # bah, cruft
    self.keywords = []

  def getTokenAncestors(self, ast):
    self.stack = []
    self._getTokenAncestors(ast)

  def _getTokenAncestors(self, ast):
    if not ast:
      return
    self.stack.append(ast.name)
    for (attr, obj) in ast.attributes.items():
      if isinstance(obj, cToken):
        self.ancestors[obj] = self.ancestors[obj].union(set(self.stack))
        self.parents[obj] = (self.stack[-1], attr)
      elif isinstance(obj, Ast):
        self._getTokenAncestors(obj)
      elif isinstance(obj, list):
        for x in obj:
          if isinstance(x, cToken):
            self.ancestors[x] = self.ancestors[x].union(set(self.stack))
            self.parents[x] = (self.stack[-1], attr)
          else:
            self._getTokenAncestors(x)
    self.stack.pop()

  def add(self, token):
    if token.lineno > self.lineno:
      self.string += ''.join('\n' for i in range(token.lineno - self.lineno))
      self.lineno = token.lineno
      self.colno = 1
    if token.colno > self.colno:
      self.string += ''.join(' ' for i in range(token.colno - self.colno))
      self.colno = token.colno

    self.string += self.doHighlight(token)

    if token.fromPreprocessor or token.id in self.insertSpaceAfter:
      self.string += ' '
    self.colno += len(token.source_string)

  def doHighlight(self, token):
    if not self.highlight:
      return token.source_string

    if token in self.parents and len(self.parents[token]):
      (parent, attr) = self.parents[token]
      if attr == 'declaration_specifiers':
        return self.termcolor.colorize(token.source_string, 0x0087ff)
      if parent == 'FuncCall' and attr == 'name':
        return self.termcolor.colorize(token.source_string, 0x8700ff)
      if parent == 'FunctionSignature' and attr == 'declarator':
        return self.termcolor.colorize(token.source_string, 0xff8700)
    if self.grammar:
      if not len(self.keywords):
        for rule in self.grammar.getRules():
          terminal = rule.isTokenAlias()
          if terminal and rule.nonterminal.string == 'keyword':
            self.keywords.append(terminal.string)
      if token.terminal_str in self.keywords:
        return self.termcolor.colorize(token.source_string, 0xffff00)
    if token.terminal_str == 'string_literal':
      return self.termcolor.colorize(token.source_string, 0xff0000)
    if token.terminal_str == 'identifier':
      return self.termcolor.colorize(token.source_string, 0x00ff00)

    return token.source_string

  def __str__(self):
    if not len(self.string):
      for token in self.tokenList:
        self.add(token)
    return self.string

class TokenList(list):
  def __init__(self, arg1=[]):
    super().__init__(arg1)
    self.isIter = False
  def __iter__(self):
    if self.isIter == False:
      self.index = 0
      isIter = True
    return self
  def __next__(self):
    try:
      rval = self[self.index]
      self.index += 1
      return rval
    except:
      raise StopIteration
  def reset(self):
    self.isIter = False
  def peek(self, whereto):
    try:
      return self[self.index + int(whereto)]
    except:
      return None
  def go(self, whereto):
    whereto = int(whereto)
    if self.index + whereto < 0 or self.index + whereto + 1 > len(self):
      raise Exception()
    self.index += whereto
    return self
  def check(self, whereto, ids):
    try:
      return self[self.index + int(whereto) - 1].id in ids
    except:
      return False
  def toString(self, parsetree=None, grammar=None, ast=None, theme=None, highlight=False):
    kwargs = locals()
    del kwargs['self']
    scw = SourceCodeWriter(self, **kwargs)
    return str(scw)
    cursor = Cursor()
    for token in self:
      cursor.add( token )
    return str(cursor)
