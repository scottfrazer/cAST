from cast.cParser import Parser as cParser
from cast.ppParser import Parser as ppParser

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
    return 'id:' + self.id

  def getResource(self):
    return self.resource

  def toAst(self):
    return self
  
  def __str__( self ):
    #return "'%s'" % (self.source_string)
    #return "'%s'" % (self.terminal_str.lower())
    return '[%s:%d] %s (%s) [line %d, col %d]' % ( self.type, self.id, self.terminal_str.lower(), self.source_string, self.lineno, self.colno )
    #return '%s (%s)' % ( self.terminal_str.lower(), self.source_string )

  def toString( self, format = 'long' ):
    if format == 'tiny':
      return self.getString()
    elif format == 'type':
      return self.getTerminalStr()
    elif format == 'short':
      if len(self.getString()):
        return "%s ('%s')" % ( self.getTerminalStr(), self.getString() )
      else:
        return "%s" % ( self.getTerminalStr() )
    else:
      return '[%s:%d] %s (%s) [line %d, col %d]' % ( self.type, self.id, self.terminal_str.lower(), self.source_string, self.lineno, self.colno )

class ppToken(Token):
  type = 'pp'

  def getTerminalStr(self):
    return ppParser.terminal_str[self.getId()].lower()

class cToken(Token):
  type = 'c'

  def getTerminalStr(self):
    return cParser.terminal_str[self.getId()].lower()

class TokenList(list):
  def toString(self):
    class Cursor:
      string = ''
      lineno = 1
      colno = 1
      def add(self, token):
        if token.lineno > self.lineno:
          self.string += ''.join('\n' for i in range(token.lineno - self.lineno))
          self.lineno = token.lineno
          self.colno = 1
        if token.colno > self.colno:
          self.string += ''.join(' ' for i in range(token.colno - self.colno))
          self.colno = token.colno
        self.string += token.source_string
        self.colno += len(token.source_string)
      def __str__(self):
        return self.string
    cursor = Cursor()
    for token in self:
      cursor.add( token )
    return str(cursor)