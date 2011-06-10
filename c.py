import sys, re, pprint
import cParser, ppParser

class Token(cParser.Terminal):
  def __init__( self, id, terminal_str, source_string, lineno, colno):
    self.__dict__.update(locals())
  
  def getString(self):
    return self.source_string
  
  def __str__( self ):
    return "'%s'" % (self.terminal_str.lower())
    return '%s (%s) [line %d, col %d]' % ( self.terminal_str.lower(), self.source_string, self.lineno, self.colno )
  
# cST = C Source Text
# cPF = C Pre-Processing File
# cPTU = C Preprocessing Translation Unit
# cTU = C Translation Unit
# cT = C Token
# cL = C Lexer
# cPPL = C Pre-Processor Lexer
# cP = C Parser
# cPPP = C Pre-Processor Parser
# cPPT = C Pre-Processing Token
# cPPAST = C Pre-Processing Abstract Syntax Tree
# cAST = C Abstract Syntax Tree
# cPT = C Parse Tree

# Also called 'source file' in ISO docs.  Takes C source code,
# and expands all #include directives
class cPreprocessingFile:
  
  trigraphs = {
    '??=': '#',
    '??(': '[',
    '??/': '\\',
    '??)': ']',
    '??\'': '^',
    '??<': '{',
    '??!': '|',
    '??>': '}',
    '??-': '~',
  }
  def __init__( self, cST, cPPL, cPPP ):
    self.__dict__.update(locals())
  
  def process( self ):
    # Phase 1: Replace trigraphs with single-character equivelants
    for (trigraph, replacement) in self.trigraphs.items():
      self.cST.replace(trigraph, replacement)
    # Phase 2: Delete all instances of backslash followed by newline
    self.cST.replace('\\\n', '')
    # Phase 3: Tokenize, preprocessing directives executed, macro invocations expanded, expand _Pragma
    self.cPPL.setString(self.cST)
    ast = cPPP.parse(self.cPPL, 'pp_file').toAst()
    e = cPreprocessingEvaluator()
    s = e.eval(ast)
    print(s)
    sys.exit(-1)
    buf = ''
    for cPPT in self.cPPL:
      print(cPPT)
      if cPPT.terminal_str == 'CSOURCE':
        buf += '\n'+cPPT.source_string
    #print(buf)
    # Phase 4: Expand all #include tags with cPreprocessingFile.process, recursively.
    return buf
  

class cPreprocessingEvaluator:
  def eval( self, cPPAST ):
    self.symbols = dict()
    a = self._eval(cPPAST)
    print(self.symbols)
    return a
  def _eval( self, cPPAST ):
    buf = ''
    if not cPPAST:
      return buf
    elif isinstance(cPPAST, Token):
      string = cPPAST.getString()
      for key, replacement in self.symbols.items():
        string = string.replace(key, replacement)
      return string + '\n'
    elif isinstance(cPPAST, list):
      if cPPAST and len(cPPAST):
        for node in cPPAST:
          buf += self._eval(node)
      return buf
    else:
      if cPPAST.name == 'PPFile':
        nodes = cPPAST.getAttr('nodes')
        return self._eval(nodes)
      elif cPPAST.name == 'IfSection':
        buf = '\n'
        value = self._eval(cPPAST.getAttr('if'))
        if value:
          buf += value
        for elseif in cPPAST.getAttr('elif'):
          buf += '\n'
          if not value:
            value = self._eval(elseif)
            if value:
              buf += value
        if cPPAST.getAttr('else') and not value:
          value = self._eval(cPPAST.getAttr('else'))
          buf += value
        buf += '\n'
        return buf
      elif cPPAST.name == 'If':
        expr = cPPAST.getAttr('expr')
        nodes = cPPAST.getAttr('nodes')
        return self._eval(nodes)
      elif cPPAST.name == 'IfDef':
        ident = cPPAST.getAttr('ident').getString()
        nodes = cPPAST.getAttr('nodes')
        if ident in self.symbols:
          return self._eval(nodes)
      elif cPPAST.name == 'IfNDef':
        ident = cPPAST.getAttr('ident')
        nodes = cPPAST.getAttr('nodes')
        return self._eval(nodes)
      elif cPPAST.name == 'ElseIf':
        expr = cPPAST.getAttr('expr')
        nodes = cPPAST.getAttr('nodes')
        return self._eval(nodes)
      elif cPPAST.name == 'Else':
        nodes = cPPAST.getAttr('nodes')
        return self._eval(nodes)
      elif cPPAST.name == 'Include':
        cPPAST.getAttr('file')
        return '\n'
      elif cPPAST.name == 'Define':
        ident = cPPAST.getAttr('ident')
        body = cPPAST.getAttr('body')
        self.symbols[ident.getString()] = str(int(body[0].getString())) if body else ''
        return '\n'
      elif cPPAST.name == 'Pragma':
        cPPAST.getAttr('tokens')
        return '\n'
      elif cPPAST.name == 'Error':
        cPPAST.getAttr('tokens')
        return '\n'
      elif cPPAST.name == 'Undef':
        ident = cPPAST.getAttr('ident').getString()
        if ident in self.symbols:
          del self.symbols[ident]
        return '\n'
      elif cPPAST.name == 'Line':
        cPPAST.getAttr('tokens')
        return '\n'
      else:
        raise Exception('Bad AST Node')
    return buf
  
  def countSourceLines(self, cPPAST):
    lines = 0
    if isinstance(cPPAST, Token):
      return len(cPPAST.source_string.split('\n'))
    if isinstance(cPPAST, list):
      for node in cPPAST:
        lines += self.countSourceLines(node)
    elif cPPAST.name in ['Line', 'Undef', 'Error', 'Pragma', 'Define', 'Include']:
      return 1
    elif cPPAST.name in ['If', 'IfDef', 'IfNDef', 'ElseIf', 'Else', 'PPFile']:
      nodes = cPPAST.getAttr('nodes')
      if nodes and len(nodes):
        for node in nodes:
          lines += self.countSourceLines(node)
      if cPPAST.name in ['If', 'IfDef', 'IfNDef', 'ElseIf', 'Else']:
        lines += 1
    elif cPPAST.name == 'IfSection':
      lines += 1 # endif
      lines += self.countSourceLines(cPPAST.getAttr('if'))
      nodes = cPPAST.getAttr('elif')
      if nodes and len(nodes):
        for node in nodes:
          lines += self.countSourceLines(node)
      if cPPAST.getAttr('else'):
        lines += self.countSourceLines(cPPAST.getAttr('else'))
    return lines
  

# This is what can be tokenized and parsed as C code.
class cTranslationUnit:
  def __init__( self, cPF, cL, cP ):
    self.__dict__.update(locals())
  
  def process( self ):
    # Returns (cParseTree, cAst)
    self.cL.setString(self.cPF.process())
    for cT in self.cL:
      print(cT)
    return self.cPF
  

class cParseTree:
  pass

class Lexer:
  def __iter__(self):
    return self
  
  def __next__(self):
    raise StopIteration()
  

class PatternMatchingLexer(Lexer):
  def __init__(self, string = '', regex = [], terminals = {}):
    self.setString(string)
    self.setRegex(regex)
    self.setTerminals(terminals)
  
  def setString(self, string):
    self.string = string
    self.colno = 1
    self.lineno = 1
  
  def setRegex(self, regex):
    self.regex = regex
  
  def setTerminals(self, terminals):
    self.terminals = terminals
  
  def advance(self, i):
    self.string = self.string[i:]
  
  def nextMatch(self):
    activity = True
    while activity:
      activity = False
      for (regex, terminal, function) in self.regex:
        match = regex.match(self.string)
        if match:
          activity = True
          if terminal != None:
            token = Token(self.terminals[terminal], terminal, match.group(0), self.lineno, self.colno)
          self.advance( len(match.group(0)) )
          newlines = len(list(filter(lambda x: x == '\n', match.group(0))))
          self.lineno += newlines
          if newlines > 0:
            self.colno = len(match.group(0).split('\n')[-1])
          else:
            self.colno += len(match.group(0))
          if terminal != None:
            return token
    return None
  
  def __iter__(self):
    return self
  
  def __next__(self):
    if len(self.string.strip()) <= 0:
      raise StopIteration()
    token = self.nextMatch()
    if not token:
      raise Exception('Invalid character on line %d, col %d' % (self.lineno, self.colno))
    return token
  

class cPreprocessingLexer(Lexer):
  regex = [
    (re.compile(r'#[ \t]*include'), 'INCLUDE', False),
    (re.compile(r'#[ \t]*define'), 'DEFINE', False),
    (re.compile(r'#[ \t]*ifdef'), 'IFDEF', False),
    (re.compile(r'#[ \t]*ifndef'), 'IFNDEF', False),
    (re.compile(r'#[ \t]*if'), 'IF', False),
    (re.compile(r'#[ \t]*elif'), 'ELIF', False),
    (re.compile(r'#[ \t]*pragma'), 'PRAGMA', False),
    (re.compile(r'#[ \t]*error'), 'ERROR', False),
    (re.compile(r'#[ \t]*line'), 'LINE', False),
    (re.compile(r'#[ \t]*undef'), 'UNDEF', False),
    (re.compile(r'#[ \t]*endif'), 'ENDIF', False),
    (re.compile(r'[<][^\n>]+[>]'), 'HEADER_GLOBAL', False),
    (re.compile(r'["][^\n"]+["]'), 'HEADER_LOCAL', False),
    (re.compile(r'[\.]?[0-9]([0-9]|[a-zA-Z_]|\\[uU]([0-9a-fA-F]{4})([0-9a-fA-F]{4})?|[eEpP][-+]|\.)*'), 'PP_NUMBER', None),
    (re.compile(r'([a-zA-Z_]|\\[uU]([0-9a-fA-F]{4})([0-9a-fA-F]{4})?)([a-zA-Z_0-9]|\\[uU]([0-9a-fA-F]{4})([0-9a-fA-F]{4})?)*'), 'IDENTIFIER', None),
    (re.compile(r"[L]?'([^\\'\n]|\\[\\\"\'nrbtfav\?]|\\[0-7]{1,3}|\\x[0-9a-fA-F]+|\\[uU]([0-9a-fA-F]{4})([0-9a-fA-F]{4})?)+'"), 'CHARACTER_CONSTANT', None),
    (re.compile(r'[L]?"([^\\\"\n]|\\[\\"\'nrbtfav\?]|\\[0-7]{1,3}|\\x[0-9a-fA-F]+|\\[uU]([0-9a-fA-F]{4})([0-9a-fA-F]{4})?)*"'), 'STRING_LITERAL', None),
    (re.compile(r'\((?<![ \t])'), 'LPAREN_SPECIAL', False),
    
    ( re.compile(r'\['), 'LSQUARE', None ),
    ( re.compile(r'\]'), 'RSQUARE', None ),
    ( re.compile(r'\('), 'LPAREN', None ),
    ( re.compile(r'\)'), 'RPAREN', None ),
    ( re.compile(r'\{'), 'LBRACE', None ),
    ( re.compile(r'\}'), 'RBRACE', None ),
    ( re.compile(r'\.'), 'DOT', None ),
    ( re.compile(r'->'), 'ARROW', None ),
    ( re.compile(r'\+\+'), 'INCR', None ),
    ( re.compile(r'--'), 'DECR', None ),
    ( re.compile(r'&(?!&)'), 'BITAND', None ),
    ( re.compile(r'\*(?!=)'), 'MUL', None ),
    ( re.compile(r'\+(?!=)'), 'ADD', None ),
    ( re.compile(r'-(?!=)'), 'SUB', None ),
    ( re.compile(r'~'), 'TILDE', None ),
    ( re.compile(r'!(?!=)'), 'EXCLAMATION_POINT', None ),
    ( re.compile(r'/(?!=)'), 'DIV', None ),
    ( re.compile(r'%(?!=)'), 'MOD', None ),
    ( re.compile(r'<<(?!=)'), 'LSHIFT', None ),
    ( re.compile(r'>>(?!=)'), 'RSHIFT', None ),
    ( re.compile(r'<(?!=)'), 'LT', None ),
    ( re.compile(r'>(?!=)'), 'GT', None ),
    ( re.compile(r'<='), 'LTEQ', None ),
    ( re.compile(r'>='), 'GTEQ', None ),
    ( re.compile(r'=='), 'EQ', None ),
    ( re.compile(r'!='), 'NEQ', None ),
    ( re.compile(r'\^(?!=)'), 'BITXOR', None ),
    ( re.compile(r'\|(?!\|)'), 'BITOR', None ),
    ( re.compile(r'&&'), 'AND', None ),
    ( re.compile(r'\|\|'), 'OR', None ),
    ( re.compile(r'\?'), 'QUESTIONMARK', None ),
    ( re.compile(r':'), 'COLON', None ),
    ( re.compile(r';'), 'SEMI', None ),
    ( re.compile(r'\.\.\.'), 'ELIPSIS', None ),
    ( re.compile(r'=(?!=)'), 'ASSIGN', None ),
    ( re.compile(r'\*='), 'MULEQ', None ),
    ( re.compile(r'/='), 'DIVEQ', None ),
    ( re.compile(r'%='), 'MODEQ', None ),
    ( re.compile(r'\+='), 'ADDEQ', None ),
    ( re.compile(r'-='), 'SUBEQ', None ),
    ( re.compile(r'<<='), 'LSHIFTEQ', None ),
    ( re.compile(r'>>='), 'RSHIFTEQ', None ),
    ( re.compile(r'&='), 'BITANDEQ', None ),
    ( re.compile(r'\^='), 'BITXOREQ', None ),
    ( re.compile(r'\|='), 'BITOREQ', None ),
    ( re.compile(r','), 'COMMA', None ),
    ( re.compile(r'##'), 'POUNDPOUND', None ),
    ( re.compile(r'#(?!#)'), 'POUND', None ),
    ( re.compile(r'[ \t]+', 0), None, None )
  ]
  def __init__(self, patternMatchingLexer, terminals, cST = ''):
    self.__dict__.update(locals())
    self.setString(cST)
    self.patternMatchingLexer.setRegex(self.regex)
    self.patternMatchingLexer.setTerminals(terminals)
    self.tokenBuffer = []
    self.colno = 1
    self.lineno = 0
  
  def setString(self, cST):
    self.cST_lines = cST.split('\n')
    self.cST_lines_index = 0
    self.cST_current_line_offset = 0
  
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
      token.lineno = self.lineno
      return token

    if not len(self.cST_lines):
      raise StopIteration()

    buf = []
    lines = 0
    token = None
    emit_separator = False
    for line in self.cST_lines:
      self.lineno += 1
      if self._isPreprocessingLine( line ):
        if line.strip() == '#':
          lines += 1
          continue
        if len(buf):
          token = Token(self.terminals['CSOURCE'], 'CSOURCE', '\n'.join(buf), self.lineno, 1)
          break
        self.patternMatchingLexer.setString( line )
        for cPPT in self.patternMatchingLexer:
          self._addToken(cPPT)
          if cPPT.terminal_str.upper() in ['INCLUDE', 'DEFINE', 'PRAGMA', 'ERROR', 'LINE', 'ENDIF', 'UNDEF']:
            emit_separator = True
        lines += 1
        if self._hasToken():
          token = self._popToken()
        break
      else:
        buf.append(line)
        lines += 1

    # Advance the number of consumed lines
    self.cST_lines = self.cST_lines[lines:]
    if not token and buf:
      token = Token(self.terminals['CSOURCE'], 'CSOURCE', '\n'.join(buf), self.lineno, 1)
    if (token and token.terminal_str.upper() == 'CSOURCE') or emit_separator:
      self._addToken( Token(self.terminals['SEPARATOR'], 'SEPARATOR', '', self.lineno, 1) )
    if token:
      token.lineno = self.lineno
      return token
    raise StopIteration()
  
  def _isPreprocessingLine(self, line):
    if not line: return False
    stripped_line = line.strip()
    if len(stripped_line) and stripped_line[0] == '#':
      return True
    return False
  

class cLexer(PatternMatchingLexer):
  def __init__(self, terminals, string = ''):
    self.setTerminals(terminals)
    self.setString(string)
    self.setRegex ([
      # Comments
      ( re.compile(r'/\*.*?\*/', re.S), None, None ),
      ( re.compile(r'//.*', 0), None, None ),

      # Keywords
      ( re.compile(r'auto(?=\s)'), 'AUTO', None ),
      ( re.compile(r'_Bool(?=\s)'), 'BOOL', None ),
      ( re.compile(r'break(?=\s)'), 'BREAK', None ),
      ( re.compile(r'case(?=\s)'), 'CASE', None ),
      ( re.compile(r'char(?=\s)'), 'CHAR', None ),
      ( re.compile(r'_Complex(?=\s)'), 'COMPLEX', None ),
      ( re.compile(r'const(?=\s)'), 'CONST', None ),
      ( re.compile(r'continue(?=\s)'), 'CONTINUE', None ),
      ( re.compile(r'default(?=\s)'), 'DEFAULT', None ),
      ( re.compile(r'do(?=\s)'), 'DO', None ),
      ( re.compile(r'double(?=\s)'), 'DOUBLE', None ),
      ( re.compile(r'else(?=\s)'), 'ELSE', None ),
      ( re.compile(r'enum(?=\s)'), 'ENUM', None ),
      ( re.compile(r'extern(?=\s)'), 'EXTERN', None ),
      ( re.compile(r'float(?=\s)'), 'FLOAT', None ),
      ( re.compile(r'for(?=\s)'), 'FOR', None ),
      ( re.compile(r'goto(?=\s)'), 'GOTO', None ),
      ( re.compile(r'if(?=\s)'), 'IF', None ),
      ( re.compile(r'_Imaginary(?=\s)'), 'IMAGINARY', None ),
      ( re.compile(r'inline(?=\s)'), 'INLINE', None ),
      ( re.compile(r'int(?=\s)'), 'INT', None ),
      ( re.compile(r'long(?=\s)'), 'LONG', None ),
      ( re.compile(r'register(?=\s)'), 'REGISTER', None ),
      ( re.compile(r'restrict(?=\s)'), 'RESTRICT', None ),
      ( re.compile(r'return(?=\s)'), 'RETURN', None ),
      ( re.compile(r'short(?=\s)'), 'SHORT', None ),
      ( re.compile(r'signed(?=\s)'), 'SIGNED', None ),
      ( re.compile(r'sizeof(?=\s)'), 'SIZEOF', None ),
      ( re.compile(r'static(?=\s)'), 'STATIC', None ),
      ( re.compile(r'struct(?=\s)'), 'STRUCT', None ),
      ( re.compile(r'switch(?=\s)'), 'SWITCH', None ),
      ( re.compile(r'typedef(?=\s)'), 'TYPEDEF', None ),
      ( re.compile(r'union(?=\s)'), 'UNION', None ),
      ( re.compile(r'unsigned(?=\s)'), 'UNSIGNED', None ),
      ( re.compile(r'void(?=\s)'), 'VOID', None ),
      ( re.compile(r'volatile(?=\s)'), 'VOLATILE', None ),
      ( re.compile(r'while(?=\s)'), 'WHILE', None ),

      # Identifiers
      ( re.compile(r'([a-zA-Z_]|\\[uU]([0-9a-fA-F]{4})([0-9a-fA-F]{4})?)([a-zA-Z_0-9]|\\[uU]([0-9a-fA-F]{4})([0-9a-fA-F]{4})?)*'), 'IDENTIFIER', None ),

      # Unicode Characters
      ( re.compile(r'\\[uU]([0-9a-fA-F]{4})([0-9a-fA-F]{4})?'), 'UNIVERSAL_CHARACTER_NAME', None ),

      # Digraphs
      ( re.compile(r'<%'), 'LBRACE', None ),
      ( re.compile(r'%>'), 'RBRACE', None ),
      ( re.compile(r'<:'), 'LSQUARE', None ),
      ( re.compile(r':>'), 'RSQUARE', None ),
      ( re.compile(r'%:%:'), 'POUNDPOUND', None ),
      ( re.compile(r'%:'), 'POUND', None ),

      # Punctuators
      ( re.compile(r'\['), 'LSQUARE', None ),
      ( re.compile(r'\]'), 'RSQUARE', None ),
      ( re.compile(r'\('), 'LPAREN', None ),
      ( re.compile(r'\)'), 'RPAREN', None ),
      ( re.compile(r'\{'), 'LBRACE', None ),
      ( re.compile(r'\}'), 'RBRACE', None ),
      ( re.compile(r'\.'), 'DOT', None ),
      ( re.compile(r'->'), 'ARROW', None ),
      ( re.compile(r'\+\+'), 'INCR', None ),
      ( re.compile(r'--'), 'DECR', None ),
      ( re.compile(r'&(?!&)'), 'BITAND', None ),
      ( re.compile(r'\*(?!=)'), 'MUL', None ),
      ( re.compile(r'\+(?!=)'), 'ADD', None ),
      ( re.compile(r'-(?!=)'), 'SUB', None ),
      ( re.compile(r'~'), 'TILDE', None ),
      ( re.compile(r'!(?!=)'), 'EXCLAMATION_POINT', None ),
      ( re.compile(r'/(?!=)'), 'DIV', None ),
      ( re.compile(r'%(?!=)'), 'MOD', None ),
      ( re.compile(r'<<(?!=)'), 'LSHIFT', None ),
      ( re.compile(r'>>(?!=)'), 'RSHIFT', None ),
      ( re.compile(r'<(?!=)'), 'LT', None ),
      ( re.compile(r'>(?!=)'), 'GT', None ),
      ( re.compile(r'<='), 'LTEQ', None ),
      ( re.compile(r'>='), 'GTEQ', None ),
      ( re.compile(r'=='), 'EQ', None ),
      ( re.compile(r'!='), 'NEQ', None ),
      ( re.compile(r'\^(?!=)'), 'BITXOR', None ),
      ( re.compile(r'\|(?!\|)'), 'BITOR', None ),
      ( re.compile(r'&&'), 'AND', None ),
      ( re.compile(r'\|\|'), 'OR', None ),
      ( re.compile(r'\?'), 'QUESTIONMARK', None ),
      ( re.compile(r':'), 'COLON', None ),
      ( re.compile(r';'), 'SEMI', None ),
      ( re.compile(r'\.\.\.'), 'ELIPSIS', None ),
      ( re.compile(r'=(?!=)'), 'ASSIGN', None ),
      ( re.compile(r'\*='), 'MULEQ', None ),
      ( re.compile(r'/='), 'DIVEQ', None ),
      ( re.compile(r'%='), 'MODEQ', None ),
      ( re.compile(r'\+='), 'ADDEQ', None ),
      ( re.compile(r'-='), 'SUBEQ', None ),
      ( re.compile(r'<<='), 'LSHIFTEQ', None ),
      ( re.compile(r'>>='), 'RSHIFTEQ', None ),
      ( re.compile(r'&='), 'BITANDEQ', None ),
      ( re.compile(r'\^='), 'BITXOREQ', None ),
      ( re.compile(r'\|='), 'BITOREQ', None ),
      ( re.compile(r','), 'COMMA', None ),
      ( re.compile(r'##'), 'POUNDPOUND', None ),
      ( re.compile(r'#(?!#)'), 'POUND', None ),

      # Constants, Literals
      ( re.compile(r'(([0-9]+)?\.([0-9]+)|[0-9]+\.)([eE][-+]?[0-9]+)?[flFL]?'), 'DECIMAL_FLOATING_CONSTANT', None ),
      ( re.compile(r'[L]?"([^\\\"\n]|\\[\\"\'nrbtfav\?]|\\[0-7]{1,3}|\\x[0-9a-fA-F]+|\\[uU]([0-9a-fA-F]{4})([0-9a-fA-F]{4})?)*"'), 'STRING_LITERAL', None ),
      ( re.compile(r'([1-9][0-9]*|0[xX][0-9a-fA-F]+|0[0-7]*)([uU](ll|LL)|[uU][lL]?|(ll|LL)[uU]?|[lL][uU])?'), 'INTEGER_CONSTANT', None ),
      ( re.compile(r'0[xX](([0-9a-fA-F]+)?\.([0-9a-fA-F]+)|[0-9a-fA-F]+\.)[pP][-+]?[0-9]+[flFL]?'), 'HEXADECIMAL_FLOATING_CONSTANT', None ),
      ( re.compile(r"[L]?'([^\\'\n]|\\[\\\"\'nrbtfav\?]|\\[0-7]{1,3}|\\x[0-9a-fA-F]+|\\[uU]([0-9a-fA-F]{4})([0-9a-fA-F]{4})?)+'"), 'CHARACTER_CONSTANT', None ),

      # Whitespace
      ( re.compile(r'\s+', 0), None, None )
    ])
  

if len(sys.argv) < 2:
  print("missing C file(s)")
  sys.exit(-1)

for filename in sys.argv[1:]:
  cP = cParser.Parser()
  cPPP = ppParser.Parser()
  
  cTokenMap = { terminalString.upper(): cP.terminal(terminalString) for terminalString in cP.terminalNames() }
  cL = cLexer(cTokenMap)

  ppTokenMap = { terminalString.upper(): cPPP.terminal(terminalString) for terminalString in cPPP.terminalNames() }
  cPPL = cPreprocessingLexer( PatternMatchingLexer(terminals=ppTokenMap), ppTokenMap )

  cTU = cTranslationUnit(cPreprocessingFile(open(filename).read(), cPPL, cPPP), cL, None)
  cTU.process()