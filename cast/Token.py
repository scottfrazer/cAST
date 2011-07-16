class Token:
  def __init__(self, id, terminal_str, source_string, lineno, colno):
    self.__dict__.update(locals())
  
  def getString(self):
    return self.source_string
  
  def getLine(self):
    return self.lineno
  
  def getColumn(self):
    return self.colno

  def getId(self):
    return self.id

  def toAst(self):
    return self
  
  def __str__( self ):
    #return "'%s'" % (self.source_string)
    #return "'%s'" % (self.terminal_str.lower())
    return '[%s:%d] %s (%s) [line %d, col %d]' % ( self.type, self.id, self.terminal_str.lower(), self.source_string, self.lineno, self.colno )
    #return '%s (%s)' % ( self.terminal_str.lower(), self.source_string )
  
class ppToken(Token):
  type = 'pp'

class cToken(Token):
  type = 'c'

class TokenList(list):
  pass