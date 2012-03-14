from cast.Token import Token, cToken
from cast.SourceCode import SourceCode

class Lexer:
  def __iter__(self):
    return self
  
  def __next__(self):
    raise StopIteration()

class StatelessPatternMatchingLexer(Lexer):
  def __init__(self, regex):
    self.__dict__.update(locals())
  def match(self, string, wholeStringOnly=False):
    for (regex, terminalId, function) in self.regex:
      match = regex.match(string)
      if match:
        sourceString = match.group(0)
        if wholeStringOnly and sourceString != string:
          continue
        return (sourceString, terminalId, function)
    return (None, None, None)

class PatternMatchingLexer(StatelessPatternMatchingLexer):
  def __init__(self, sourceCode, regex):
    self.__dict__.update(locals())
    self.string = sourceCode.getString()
    self.resource = sourceCode.getResource()
    self.colno = sourceCode.getColumn()
    self.lineno = sourceCode.getLine()
    self.cache = []
  
  def addToken(self, token):
    self.cache.append(token)
  
  def addTokens(self, tokens):
    self.cache.extend(tokens)
  
  def hasToken(self):
    return len(self.cache) > 0
  
  def nextToken(self):
    if not self.hasToken():
      return None
    token = self.cache[0]
    self.cache = self.cache[1:]
    return token

  def advance(self, string):
    self.string = self.string[len(string):]
    newlines = len(list(filter(lambda x: x == '\n', string)))
    self.lineno += newlines
    if newlines > 0:
      self.colno = len(string.split('\n')[-1]) + 1
    else:
      self.colno += len(string)

  def peek(self, n=1):
    # returns an n-item list of tuples: (terminalId, length)
    lookahead = list()
    loc = 0
    for i in range(n):
      current = self.string[loc:]
      if not len(current):
        return lookahead
      for (regex, terminalId, function) in self.regex:
        match = regex.match(current)
        if match:
          length = len(match.group(0))
          loc += length
          lookahead.append( (terminalId,match.group(0),) )
    return lookahead

  def nextMatch(self):
    activity = True
    while activity:
      activity = False
      if not len(self.string):
        raise StopIteration()
      (string, terminalId, function) = self.match(self.string)
      if string is not None:
        activity = True
        lineno = self.lineno
        colno = self.colno
        self.advance( string )
        if function:
          function(string, lineno, colno, terminalId, self)
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
