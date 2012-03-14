import re
from cast.Lexer import Lexer, PatternMatchingLexer
from cast.Token import ppToken
from cast.pp_Parser import pp_Parser
from cast.SourceCode import SourceCodeString
from cast.Logger import Factory as LoggerFactory

moduleLogger = LoggerFactory().getModuleLogger(__name__)

def parseDefine( match, lineno, colno, terminalId, lexer ):
  identifier_regex = r'([a-zA-Z_]|\\[uU]([0-9a-fA-F]{4})([0-9a-fA-F]{4})?)([a-zA-Z_0-9]|\\[uU]([0-9a-fA-F]{4})([0-9a-fA-F]{4})?)*'
  if re.match(r'[ \t]+%s\(' % (identifier_regex), lexer.string):
    terminalId = pp_Parser.TERMINAL_DEFINE_FUNCTION
  else:
    terminalId = pp_Parser.TERMINAL_DEFINE
  lexer.addToken(ppToken(terminalId, lexer.resource, pp_Parser.terminals[terminalId], match, lineno, colno))

def parseDefined( match, lineno, colno, terminalId, lexer ):
  separatorId = pp_Parser.TERMINAL_DEFINED_SEPARATOR
  lexer.addToken(ppToken(terminalId, lexer.resource, pp_Parser.terminals[terminalId], match, lineno, colno))
  lexer.addToken(ppToken(separatorId, lexer.resource, pp_Parser.terminals[separatorId], match, lineno, colno))

def parseInclude( match, lineno, colno, terminalId, lexer ):
  headerGlobal = re.compile(r'[<][^\n>]+[>]')
  headerLocal = re.compile(r'["][^\n"]+["]')
  leadingWhitespace = re.compile(r'[\t ]*')

  lexer.addToken(ppToken(terminalId, lexer.resource, pp_Parser.terminals[terminalId], match, lineno, colno))
  lexer.advance( leadingWhitespace.match(lexer.string).group(0) )

  regexes = {
    pp_Parser.TERMINAL_HEADER_GLOBAL: headerGlobal,
    pp_Parser.TERMINAL_HEADER_LOCAL: headerLocal
  }

  for terminalId, regex in regexes.items():
    rmatch = regex.match(lexer.string)
    if rmatch:
      rstring = rmatch.group(0)
      token = ppToken(terminalId, lexer.resource, pp_Parser.terminals[terminalId], rstring, lexer.lineno, lexer.colno)
      lexer.addToken(token)
      lexer.advance(rstring)
      break

def token(string, lineno, colno, terminalId, lexer):
  lexer.addToken(ppToken(terminalId, lexer.resource, pp_Parser.terminals[terminalId], string, lineno, colno))

class ppLexer(Lexer):
  regex = [
    ( re.compile(r'^[ \t]*#[ \t]*include_next(?![a-zA-Z])'), pp_Parser.TERMINAL_INCLUDE, parseInclude ),
    ( re.compile(r'^[ \t]*#[ \t]*include(?![a-zA-Z])'), pp_Parser.TERMINAL_INCLUDE, parseInclude ),
    ( re.compile(r'^[ \t]*#[ \t]*define(?![a-zA-Z])'), pp_Parser.TERMINAL_DEFINE, parseDefine ),
    ( re.compile(r'^[ \t]*#[ \t]*ifdef(?![a-zA-Z])'), pp_Parser.TERMINAL_IFDEF, token ),
    ( re.compile(r'^[ \t]*#[ \t]*ifndef(?![a-zA-Z])'), pp_Parser.TERMINAL_IFNDEF, token ),
    ( re.compile(r'^[ \t]*#[ \t]*if(?![a-zA-Z])'), pp_Parser.TERMINAL_IF, token ),
    ( re.compile(r'^[ \t]*#[ \t]*else(?![a-zA-Z])'), pp_Parser.TERMINAL_ELSE, token ),
    ( re.compile(r'^[ \t]*#[ \t]*elif(?![a-zA-Z])'), pp_Parser.TERMINAL_ELIF, token ),
    ( re.compile(r'^[ \t]*#[ \t]*pragma(?![a-zA-Z])'), pp_Parser.TERMINAL_PRAGMA, token ),
    ( re.compile(r'^[ \t]*#[ \t]*error(?![a-zA-Z])'), pp_Parser.TERMINAL_ERROR, token ),
    ( re.compile(r'^[ \t]*#[ \t]*warning(?![a-zA-Z])'), pp_Parser.TERMINAL_WARNING, token ),
    ( re.compile(r'^[ \t]*#[ \t]*line(?![a-zA-Z])'), pp_Parser.TERMINAL_LINE, token ),
    ( re.compile(r'^[ \t]*#[ \t]*undef(?![a-zA-Z])'), pp_Parser.TERMINAL_UNDEF, token ),
    ( re.compile(r'^[ \t]*#[ \t]*endif\s?.*'), pp_Parser.TERMINAL_ENDIF, token ),
    ( re.compile(r'defined'), pp_Parser.TERMINAL_DEFINED, parseDefined ),
    ( re.compile(r'\.\.\.'), pp_Parser.TERMINAL_ELIPSIS, token ),
    ( re.compile(r'[\.]?[0-9]([0-9]|[a-zA-Z_]|\\[uU]([0-9a-fA-F]{4})([0-9a-fA-F]{4})?|[eEpP][-+]|\.)*'), pp_Parser.TERMINAL_PP_NUMBER, token ),
    ( re.compile(r'([a-zA-Z_]|\\[uU]([0-9a-fA-F]{4})([0-9a-fA-F]{4})?)([a-zA-Z_0-9]|\\[uU]([0-9a-fA-F]{4})([0-9a-fA-F]{4})?)*'), pp_Parser.TERMINAL_IDENTIFIER, token ),
    ( re.compile(r"[L]?'([^\\'\n]|\\[\\\"\'nrbtfav\?]|\\[0-7]{1,3}|\\x[0-9a-fA-F]+|\\[uU]([0-9a-fA-F]{4})([0-9a-fA-F]{4})?)+'"), pp_Parser.TERMINAL_CHARACTER_CONSTANT, token ),
    ( re.compile(r'[L]?"([^\\\"\n]|\\[\\"\'nrbtfav\?]|\\[0-7]{1,3}|\\x[0-9a-fA-F]+|\\[uU]([0-9a-fA-F]{4})([0-9a-fA-F]{4})?)*"'), pp_Parser.TERMINAL_STRING_LITERAL, token ),
    ( re.compile(r'\['), pp_Parser.TERMINAL_LSQUARE, token ),
    ( re.compile(r'\]'), pp_Parser.TERMINAL_RSQUARE, token ),
    ( re.compile(r'\('), pp_Parser.TERMINAL_LPAREN, token ),
    ( re.compile(r'\)'), pp_Parser.TERMINAL_RPAREN, token ),
    ( re.compile(r'\{'), pp_Parser.TERMINAL_LBRACE, token ),
    ( re.compile(r'\}'), pp_Parser.TERMINAL_RBRACE, token ),
    ( re.compile(r'\.'), pp_Parser.TERMINAL_DOT, token ),
    ( re.compile(r'->'), pp_Parser.TERMINAL_ARROW, token ),
    ( re.compile(r'\+\+'), pp_Parser.TERMINAL_INCR, token ),
    ( re.compile(r'--'), pp_Parser.TERMINAL_DECR, token ),
    ( re.compile(r'\*='), pp_Parser.TERMINAL_MULEQ, token ),
    ( re.compile(r'\+='), pp_Parser.TERMINAL_ADDEQ, token ),
    ( re.compile(r'-='), pp_Parser.TERMINAL_SUBEQ, token ),
    ( re.compile(r'%='), pp_Parser.TERMINAL_MODEQ, token ),
    ( re.compile(r'&='), pp_Parser.TERMINAL_BITANDEQ, token ),
    ( re.compile(r'\|='), pp_Parser.TERMINAL_BITOREQ, token ),
    ( re.compile(r'\^='), pp_Parser.TERMINAL_BITXOREQ, token ),
    ( re.compile(r'<<='), pp_Parser.TERMINAL_LSHIFTEQ, token ),
    ( re.compile(r'>>='), pp_Parser.TERMINAL_RSHIFTEQ, token ),
    ( re.compile(r'&(?!&)'), pp_Parser.TERMINAL_BITAND, token ),
    ( re.compile(r'\*(?!=)'), pp_Parser.TERMINAL_MUL, token ),
    ( re.compile(r'\+(?!=)'), pp_Parser.TERMINAL_ADD, token ),
    ( re.compile(r'-(?!=)'), pp_Parser.TERMINAL_SUB, token ),
    ( re.compile(r'!(?!=)'), pp_Parser.TERMINAL_EXCLAMATION_POINT, token ),
    ( re.compile(r'%(?!=)'), pp_Parser.TERMINAL_MOD, token ),
    ( re.compile(r'<<(?!=)'), pp_Parser.TERMINAL_LSHIFT, token ),
    ( re.compile(r'>>(?!=)'), pp_Parser.TERMINAL_RSHIFT, token ),
    ( re.compile(r'<(?!=)'), pp_Parser.TERMINAL_LT, token ),
    ( re.compile(r'>(?!=)'), pp_Parser.TERMINAL_GT, token ),
    ( re.compile(r'<='), pp_Parser.TERMINAL_LTEQ, token ),
    ( re.compile(r'>='), pp_Parser.TERMINAL_GTEQ, token ),
    ( re.compile(r'=='), pp_Parser.TERMINAL_EQ, token ),
    ( re.compile(r'!='), pp_Parser.TERMINAL_NEQ, token ),
    ( re.compile(r'\^(?!=)'), pp_Parser.TERMINAL_BITXOR, token ),
    ( re.compile(r'\|(?!\|)'), pp_Parser.TERMINAL_BITOR, token ),
    ( re.compile(r'~'), pp_Parser.TERMINAL_BITNOT, token ),
    ( re.compile(r'&&'), pp_Parser.TERMINAL_AND, token ),
    ( re.compile(r'\|\|'), pp_Parser.TERMINAL_OR, token ),
    ( re.compile(r'='), pp_Parser.TERMINAL_ASSIGN, token ),
    ( re.compile(r'\?'), pp_Parser.TERMINAL_QUESTIONMARK, token ),
    ( re.compile(r':'), pp_Parser.TERMINAL_COLON, token ),
    ( re.compile(r';'), pp_Parser.TERMINAL_SEMI, token ),
    ( re.compile(r','), pp_Parser.TERMINAL_COMMA, token ),
    ( re.compile(r'##'), pp_Parser.TERMINAL_POUNDPOUND, token ),
    ( re.compile(r'#(?!#)'), pp_Parser.TERMINAL_POUND, token ),
    ( re.compile(r'[ \t]+', 0), None, None ),
    ( re.compile(r'/\*.*?\*/', re.S), None, None ),
    ( re.compile(r'//.*', 0), None, None ),
    ( re.compile(r'/='), pp_Parser.TERMINAL_DIVEQ, token ),
    ( re.compile(r'/'), pp_Parser.TERMINAL_DIV, token )
  ]

  def __init__(self, sourceCode):
    self.__dict__.update(locals())
    self.string = sourceCode.getString()
    self.resource = sourceCode.getResource()
    self.colno = sourceCode.getColumn()
    self.lineno = sourceCode.getLine()
    self.cST_lines = self.string.split('\n')
    self.lineno -= 1
    self.logger = LoggerFactory().getClassLogger(__name__, self.__class__.__name__)
    self.tokenBuffer = []

  def matchString(self, string):
    for (regex, terminalId, function) in self.regex:
      match = regex.match(string)
      if match:
        return ppToken(terminalId, self.resource, pp_Parser.terminals[terminalId], match.group(0), 0, 0)
    return None
  
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
    advance = 0
    cComment = False
    for index, line in enumerate(self.cST_lines):
      self.lineno += 1

      if not cComment and (self._isPreprocessingLine( line ) or continuation):
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
              self.lineno += 1
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
        cPPL_PatternMatcher = PatternMatchingLexer( SourceCodeString(self.resource, line, self.lineno, 1), self.regex )
        for cPPT in cPPL_PatternMatcher:
          self._addToken(ppToken(cPPT.id, self.resource, cPPT.terminal_str, cPPT.source_string, cPPT.lineno, cPPT.colno))
          if cPPT.terminal_str.upper() in ['INCLUDE', 'DEFINE', 'DEFINE_FUNCTION', 'PRAGMA', 'ERROR', 'WARNING', 'LINE', 'ENDIF', 'UNDEF']:
            emit_separator = True
        if continuation:
          lines += 1
          continue
        if emit_separator:
          terminalId = pp_Parser.TERMINAL_SEPARATOR
          self._addToken( ppToken(terminalId, self.resource, pp_Parser.terminals[terminalId], '', self.lineno, 1) )
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
        if not cComment and '/*' in line and '*/' not in line:
          cComment = True
        if cComment and '*/' in line:
          cComment = False

    self._advance(lines)
    if emit_csource:
      csourceId = pp_Parser.TERMINAL_CSOURCE
      separatorId = pp_Parser.TERMINAL_SEPARATOR
      token = ppToken(csourceId, self.resource, pp_Parser.terminals[csourceId], '\n'.join(buf), buf_line, 1)
      self._addToken( ppToken(separatorId, self.resource, pp_Parser.terminals[separatorId], '', self.lineno, 1) )
      return token
    raise StopIteration()
  
  def _isPreprocessingLine(self, line):
    if not line: return False
    stripped_line = line.strip()
    if len(stripped_line) and stripped_line[0] == '#':
      return True
    return False
