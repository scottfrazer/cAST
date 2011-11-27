from cast.Token import Token
from cast.SourceCode import SourceCode

class Lexer:
  def __init__(self, sourceCode):
    self.__dict__.update(locals())
    self.string = sourceCode.getString()
    self.resource = sourceCode.getResource()
    self.colno = sourceCode.getColumn()
    self.lineno = sourceCode.getLine()

  def __iter__(self):
    return self
  
  def __next__(self):
    raise StopIteration()

  def setString(self, string):
    self.string = string

  def getString(self):
    return self.string

class PatternMatchingLexer(Lexer):
  def __init__(self, sourceCode, regex):
    self.__dict__.update(locals())
    super().__init__(sourceCode)
    self.cache = []
  
  def addToken(self, token):
    self.cache.append(token)
  
  def hasToken(self):
    return len(self.cache) > 0
  
  def nextToken(self):
    if not self.hasToken():
      return None
    token = self.cache[0]
    self.cache = self.cache[1:]
    return token
  
  def setLine(self, lineno):
    self.lineno = lineno
  
  def setColumn(self, colno):
    self.colno = colno
  
  def advance(self, string):
    self.string = self.string[len(string):]
    newlines = len(list(filter(lambda x: x == '\n', string)))
    self.lineno += newlines
    if newlines > 0:
      self.colno = len(string.split('\n')[-1]) + 1
    else:
      self.colno += len(string)

  def peek(self):
    activity = True
    while activity:
      activity = False
      if not len(self.string):
        raise StopIteration()
      for (regex, terminalId, function) in self.regex:
        match = regex.match(self.string)
        if match:
          return Token(terminalId, self.resource, 'peek', match.group(0), self.lineno, self.colno)

  def nextMatch(self):
    activity = True
    while activity:
      activity = False
      if not len(self.string):
        raise StopIteration()
      for (regex, terminalId, function) in self.regex:
        match = regex.match(self.string)
        if match:
          activity = True
          lineno = self.lineno
          colno = self.colno
          sourceString = match.group(0)
          self.advance( sourceString )
          if function:
            function(sourceString, lineno, colno, terminalId, self)
            return self.nextToken()
    return None
  
  def __iter__(self):
    return self
  
  def __next__(self):
    if self.hasToken():
      token = self.nextToken()
      return token
    if len(self.string.strip()) <= 0:
      raise StopIteration()
    token = self.nextMatch()
    if not token:
      error = 'Invalid character on line %d, col %d' % (self.lineno, self.colno)
      raise Exception(error)
    return token
