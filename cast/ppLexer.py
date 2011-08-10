import re
from cast.Lexer import Lexer, PatternMatchingLexer
from cast.Token import ppToken
from cast.ppParser import Parser as ppParser

def parseDefine( match, string, lineno, colno, terminals ):
  identifier_regex = r'([a-zA-Z_]|\\[uU]([0-9a-fA-F]{4})([0-9a-fA-F]{4})?)([a-zA-Z_0-9]|\\[uU]([0-9a-fA-F]{4})([0-9a-fA-F]{4})?)*'
  if re.match(r'[ \t]+%s\(' % (identifier_regex), string):
    token = ppToken(terminals['DEFINE_FUNCTION'], 'DEFINE_FUNCTION', match, lineno, colno - len(match))
  else:
    token = ppToken(terminals['DEFINE'], 'DEFINE', match, lineno, colno - len(match))
  return ([token], 0)

def parseInclude( match, string, lineno, colno, terminals ):
  header_global = re.compile(r'[<][^\n>]+[>]')
  header_local = re.compile(r'["][^\n"]+["]')
  advance = len(re.compile(r'[\t ]*').match(string).group(0))
  string = string[advance:]
  tokens = [ppToken(terminals['INCLUDE'], 'INCLUDE', match, lineno, colno)]
  for (regex, token) in [(header_global, 'HEADER_GLOBAL'), (header_local, 'HEADER_LOCAL')]:
    rmatch = regex.match(string)
    if rmatch:
      rstring = rmatch.group(0)
      tokens.append( ppToken(terminals[token], token, rstring, lineno, colno + advance) )
      advance += len(rstring)
      break
  return (tokens, advance)

class ppLexer(Lexer):
  regex = [
    ( re.compile(r'^[ \t]*#[ \t]*include_next(?![a-zA-Z])'), None, parseInclude, None ), # GCC extension
    ( re.compile(r'^[ \t]*#[ \t]*include(?![a-zA-Z])'), None, parseInclude, None ),
    ( re.compile(r'^[ \t]*#[ \t]*define(?![a-zA-Z])'), None, parseDefine, None ),
    ( re.compile(r'^[ \t]*#[ \t]*ifdef(?![a-zA-Z])'), 'IFDEF', None, None ),
    ( re.compile(r'^[ \t]*#[ \t]*ifndef(?![a-zA-Z])'), 'IFNDEF', None, None ),
    ( re.compile(r'^[ \t]*#[ \t]*if(?![a-zA-Z])'), 'IF', None, None ),
    ( re.compile(r'^[ \t]*#[ \t]*else(?![a-zA-Z])'), 'ELSE', None, None ),
    ( re.compile(r'^[ \t]*#[ \t]*elif(?![a-zA-Z])'), 'ELIF', None, None ),
    ( re.compile(r'^[ \t]*#[ \t]*pragma(?![a-zA-Z])'), 'PRAGMA', None, None ),
    ( re.compile(r'^[ \t]*#[ \t]*error(?![a-zA-Z])'), 'ERROR', None, None ),
    ( re.compile(r'^[ \t]*#[ \t]*warning(?![a-zA-Z])'), 'WARNING', None, None ),
    ( re.compile(r'^[ \t]*#[ \t]*line(?![a-zA-Z])'), 'LINE', None, None ),
    ( re.compile(r'^[ \t]*#[ \t]*undef(?![a-zA-Z])'), 'UNDEF', None, None ),
    ( re.compile(r'^[ \t]*#[ \t]*endif\s?.*'), 'ENDIF', None, None ),
    ( re.compile(r'defined'), 'DEFINED', None, None ),
    ( re.compile(r'\.\.\.'), 'ELIPSIS', None, None ),
    ( re.compile(r'[\.]?[0-9]([0-9]|[a-zA-Z_]|\\[uU]([0-9a-fA-F]{4})([0-9a-fA-F]{4})?|[eEpP][-+]|\.)*'), 'PP_NUMBER', None, None ),
    ( re.compile(r'([a-zA-Z_]|\\[uU]([0-9a-fA-F]{4})([0-9a-fA-F]{4})?)([a-zA-Z_0-9]|\\[uU]([0-9a-fA-F]{4})([0-9a-fA-F]{4})?)*'), 'IDENTIFIER', None, None ),
    ( re.compile(r"[L]?'([^\\'\n]|\\[\\\"\'nrbtfav\?]|\\[0-7]{1,3}|\\x[0-9a-fA-F]+|\\[uU]([0-9a-fA-F]{4})([0-9a-fA-F]{4})?)+'"), 'CHARACTER_CONSTANT', None, None ),
    ( re.compile(r'[L]?"([^\\\"\n]|\\[\\"\'nrbtfav\?]|\\[0-7]{1,3}|\\x[0-9a-fA-F]+|\\[uU]([0-9a-fA-F]{4})([0-9a-fA-F]{4})?)*"'), 'STRING_LITERAL', None, None ),
    ( re.compile(r'\['), 'LSQUARE', None, None ),
    ( re.compile(r'\]'), 'RSQUARE', None, None ),
    ( re.compile(r'\('), 'LPAREN', None, None ),
    ( re.compile(r'\)'), 'RPAREN', None, None ),
    ( re.compile(r'\{'), 'LBRACE', None, None ),
    ( re.compile(r'\}'), 'RBRACE', None, None ),
    ( re.compile(r'\.'), 'DOT', None, None ),
    ( re.compile(r'->'), 'ARROW', None, None ),
    ( re.compile(r'\+\+'), 'INCR', None, None ),
    ( re.compile(r'--'), 'DECR', None, None ),
    ( re.compile(r'\*='), 'MULEQ', None, None ),
    ( re.compile(r'\+='), 'ADDEQ', None, None ),
    ( re.compile(r'-='), 'SUBEQ', None, None ),
    ( re.compile(r'%='), 'MODEQ', None, None ),
    ( re.compile(r'&='), 'BITANDEQ', None, None ),
    ( re.compile(r'\|='), 'BITOREQ', None, None ),
    ( re.compile(r'\^='), 'BITXOREQ', None, None ),
    ( re.compile(r'<<='), 'LSHIFTEQ', None, None ),
    ( re.compile(r'>>='), 'RSHIFTEQ', None, None ),
    ( re.compile(r'&(?!&)'), 'BITAND', None, None ),
    ( re.compile(r'\*(?!=)'), 'MUL', None, None ),
    ( re.compile(r'\+(?!=)'), 'ADD', None, None ),
    ( re.compile(r'-(?!=)'), 'SUB', None, None ),
    ( re.compile(r'!(?!=)'), 'EXCLAMATION_POINT', None, None ),
    ( re.compile(r'%(?!=)'), 'MOD', None, None ),
    ( re.compile(r'<<(?!=)'), 'LSHIFT', None, None ),
    ( re.compile(r'>>(?!=)'), 'RSHIFT', None, None ),
    ( re.compile(r'<(?!=)'), 'LT', None, None ),
    ( re.compile(r'>(?!=)'), 'GT', None, None ),
    ( re.compile(r'<='), 'LTEQ', None, None ),
    ( re.compile(r'>='), 'GTEQ', None, None ),
    ( re.compile(r'=='), 'EQ', None, None ),
    ( re.compile(r'!='), 'NEQ', None, None ),
    ( re.compile(r'\^(?!=)'), 'BITXOR', None, None ),
    ( re.compile(r'\|(?!\|)'), 'BITOR', None, None ),
    ( re.compile(r'~'), 'BITNOT', None, None ),
    ( re.compile(r'&&'), 'AND', None, None ),
    ( re.compile(r'\|\|'), 'OR', None, None ),
    ( re.compile(r'='), 'ASSIGN', None, None ),
    ( re.compile(r'\?'), 'QUESTIONMARK', None, None ),
    ( re.compile(r':'), 'COLON', None, None ),
    ( re.compile(r';'), 'SEMI', None, None ),
    ( re.compile(r','), 'COMMA', None, None ),
    ( re.compile(r'##'), 'POUNDPOUND', None, None ),
    ( re.compile(r'#(?!#)'), 'POUND', None, None ),
    ( re.compile(r'[ \t]+', 0), None, None, None ),
    ( re.compile(r'/\*.*?\*/', re.S), None, None, None ),
    ( re.compile(r'//.*', 0), None, None, None ),
    ( re.compile(r'/='), 'DIVEQ', None, None ),
    ( re.compile(r'/'), 'DIV', None, None )
  ]
  def __init__(self, patternMatchingLexer, terminals, logger = None):
    self.__dict__.update(locals())
    self.patternMatchingLexer.setRegex(self.regex)
    self.patternMatchingLexer.setTerminals(terminals)
    self.tokenBuffer = []
    self.colno = 1
    self.lineno = 0
  
  def setString(self, cST):
    self.cST_lines = cST.split('\n')
    self.cST_lines_index = 0
    self.cST_current_line_offset = 0
  
  def setLine(self, lineno):
    self.lineno = lineno
  
  def setColumn(self, colno):
    self.colno = colno
  
  def matchString(self, string):
    token = self.patternMatchingLexer.matchString(string)
    return ppToken(token.id, token.terminal_str, token.source_string, token.lineno, token.colno)
  
  def _advance(self, lines):
    self.cST_lines = self.cST_lines[lines:]

  def _hasToken(self):
    return len(self.tokenBuffer) > 0
  
  def _popToken(self):
    token = self.tokenBuffer[0]
    self.tokenBuffer = self.tokenBuffer[1:]
    return token
  
  def _addToken(self, token):
    self.tokenBuffer.append(token)
  
  def __iter__(self):
    return self
  
  def __next__(self):
    if self._hasToken():
      token = self._popToken()
      return token

    if not len(self.cST_lines):
      raise StopIteration()

    buf = []
    buf_line = 0
    lines = 0
    token = None
    emit_separator = False
    emit_csource = False
    continuation = False
    comment = False
    advance = 0
    for index, line in enumerate(self.cST_lines):
      self.lineno += 1

      if self._isPreprocessingLine( line ) or continuation:
        continuation = False
        if len(buf):
          self.lineno -= 1
          emit_csource = True
          break
        if '/*' in line and '*/' not in line:
          line = re.sub('/\*.*$', '', line)
          try:
            i = index
            while True:
              i += 1
              lines += 1
              if '*/' in self.cST_lines[i]:
                line += re.sub('^.*\*/', '', self.cST_lines[i])
                break
          except IndexError:
            pass
        if line.strip() == '#':
          lines += 1
          continue
        if len(line) and line[-1] == '\\':
          line = line[:-1]
          continuation = True
        self.patternMatchingLexer.setString( line )
        self.patternMatchingLexer.setLine( self.lineno )
        self.patternMatchingLexer.setColumn( 1 )
        for cPPT in self.patternMatchingLexer:
          self._addToken(ppToken(cPPT.id, cPPT.terminal_str, cPPT.source_string, cPPT.lineno, cPPT.colno))
          if cPPT.terminal_str.upper() in ['INCLUDE', 'DEFINE', 'DEFINE_FUNCTION', 'PRAGMA', 'ERROR', 'WARNING', 'LINE', 'ENDIF', 'UNDEF']:
            emit_separator = True
        if continuation:
          lines += 1
          continue
        if emit_separator:
          self._addToken( ppToken(self.terminals['SEPARATOR'], 'SEPARATOR', '', self.lineno + 1, 1) )
        self._advance( lines + 1 )
        if self._hasToken():
          return self._popToken()
        raise Exception('Unexpected')
      else:
        emit_csource = True
        if not len(buf):
          buf_line = self.lineno
        buf.append(line)
        lines += 1

    self._advance(lines)
    if emit_csource:
      token = ppToken(self.terminals['CSOURCE'], 'CSOURCE', '\n'.join(buf), buf_line, 1)
      self._addToken( ppToken(self.terminals['SEPARATOR'], 'SEPARATOR', '', self.lineno, 1) )
      return token
    raise StopIteration()
  
  def _isPreprocessingLine(self, line):
    if not line: return False
    stripped_line = line.strip()
    if len(stripped_line) and stripped_line[0] == '#':
      return True
    return False

class Factory:
  def create( self, debug = False ):
    matchLogger = None
    lexLogger = None
    if debug:
      matchLogger = debugger.getLogger('ppmatch')
      lexLogger = debugger.getLogger('pplex')

    cPPP = ppParser()
    cPPL_TokenMap = { terminalString.upper(): cPPP.terminal(terminalString) for terminalString in cPPP.terminalNames() }
    cPPL_PatternMatchingLexer = PatternMatchingLexer(terminals=cPPL_TokenMap, logger=matchLogger)
    cPPL = ppLexer( cPPL_PatternMatchingLexer, cPPL_TokenMap, logger=lexLogger )
    return cPPL