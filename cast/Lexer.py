from cast.Token import Token
from cast.SourceCode import SourceCode

class Lexer:
  def __init__(self, sourceCode):
    self.__dict__.update(locals())
    if sourceCode:
      self.setSourceCode(sourceCode)

  def __iter__(self):
    return self
  
  def __next__(self):
    raise StopIteration()

  def setSourceCode(self, sourceCode):
    self.string = sourceCode.getString()
    self.resource = sourceCode.getResource()
    self.colno = sourceCode.getColumn()
    self.lineno = sourceCode.getLine()

  def setString(self, string):
    self.string = string

  def getString(self):
    return self.string

class PatternMatchingLexer(Lexer):
  def __init__(self, resource, regex = [], terminals = {}, logger = None):
    super().__init__(resource)
    self.setLogger(logger)
    self.setRegex(regex)
    self.setTerminals(terminals)
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
  
  def setRegex(self, regex):
    self.regex = regex
  
  def setTerminals(self, terminals):
    self.terminals = terminals
  
  def setLogger(self, logger):
    self.logger = logger
  
  def advance(self, i):
    self.string = self.string[i:]
  
  def nextMatch(self):
    activity = True
    while activity:
      activity = False
      for (regex, terminal, process_func, format_func) in self.regex:
        match = regex.match(self.string)
        if match:
          activity = True
          lineno = self.lineno
          colno = self.colno
          match_str = match.group(0)
          self.advance( len(match_str) )
          
          if terminal == None and len(self.string) == 0:
            raise StopIteration()

          newlines = len(list(filter(lambda x: x == '\n', match_str)))
          self.lineno += newlines
          if newlines > 0:
            self.colno = len(match_str.split('\n')[-1]) + 1
          else:
            self.colno += len(match_str)

          if process_func:
            (tokens, advancement) = process_func(match_str, self)
            for token in tokens:
              self.addToken(token)
            self.advance(advancement)
            return self.nextToken()
          else:
            if terminal != None:
              return Token(self.terminals[terminal], self.resource, terminal, match_str, lineno, colno)
    return None
  
  def matchString(self, string):
    for (regex, terminal, process_func, format_func) in self.regex:
      match = regex.match(string)
      if match:
        return Token(self.terminals[terminal], self.resource, terminal, match.group(0), 0, 0)
    return None
  
  def __iter__(self):
    return self
  
  def __next__(self):
    if self.hasToken():
      token = self.nextToken()
      self._log('token', '(queued) %s' % (self._debugToken(token)))
      return token
    if len(self.string.strip()) <= 0:
      self._log('info', 'StopIteration')
      raise StopIteration()
    token = self.nextMatch()
    if not token:
      error = 'Invalid character on line %d, col %d' % (self.lineno, self.colno)
      self._log('error', error)
      raise Exception(error)
    self._log('token', str(self._debugToken(token)))
    return token
  
  def _debugToken(self, token):
    return '[line %d, col %d] %s (%s)' % ( token.lineno, token.colno, token.terminal_str.lower(), token.source_string )
  
  def _log(self, category, message):
    if not self.logger:
      return
    self.logger.log(category, message)
