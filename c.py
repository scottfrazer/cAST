import sys, re, pprint
import cParser, ppParser

class Token(cParser.Terminal):
  def __init__( self, id, terminal_str, source_string, lineno, colno):
    self.__dict__.update(locals())
  
  def getString(self):
    return self.source_string
  
  def __str__( self ):
    #return "'%s'" % (self.terminal_str.lower())
    return '%s (%s) [line %d, col %d]' % ( self.terminal_str.lower(), self.source_string, self.lineno, self.colno )
  
class TokenList(list):
  pass

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
  def __init__( self, cST, cPPL, cPPP, cL ):
    self.__dict__.update(locals())
  
  def process( self ):
    # Phase 1: Replace trigraphs with single-character equivelants
    for (trigraph, replacement) in self.trigraphs.items():
      self.cST.replace(trigraph, replacement)
    # Phase 2: Delete all instances of backslash followed by newline
    self.cST.replace('\\\n', '')
    # Phase 3: Tokenize, preprocessing directives executed, macro invocations expanded, expand _Pragma
    self.cPPL.setString(self.cST)
    parsetree = cPPP.parse(self.cPPL, 'pp_file')
    ast = parsetree.toAst()
    e = cPreprocessingEvaluator(self.cPPP, self.cL, cTokens())
    s = e.eval(ast)
    for t in s:
      print(t)
    sys.exit(-1)
    buf = ''
    for cPPT in self.cPPL:
      print(cPPT)
      if cPPT.terminal_str == 'CSOURCE':
        buf += '\n'+cPPT.source_string
    #print(buf)
    # Phase 4: Expand all #include tags with cPreprocessingFile.process, recursively.
    return buf
  
class cPreprocessorFunction:
  def __init__(self, params, body):
    self.__dict__.update(locals())
  
  def run(self, params):
    if len(params) != len(self.params):
      raise Exception('Error: too few parameters to function')
    values = {self.params[i].lower(): params[i] for i in range(len(params))}
    nodes = []
    for node in self.body.getAttr('tokens'):
      if node.terminal_str.lower() == 'identifier' and node.getString().lower() in values:
        nodes.append(values[node.getString().lower()])
      else:
        nodes.append(node)
    return nodes
  
  def __str__(self):
    return '[function params=%s body=%s]' % (', '.join(self.params), str(self.body))
  

class cPreprocessingEvaluator:
  def __init__(self, cPPP, cL, cT):
    self.__dict__.update(locals())
  
  def eval( self, cPPAST ):
    self.symbols = dict()
    self.line = 1
    return self._eval(cPPAST)
  
  def newlines(self, number):
    return ''.join(['\n' for i in range(number)])
  
  def _eval( self, cPPAST ):
    rtokens = []
    if not cPPAST:
      return []
    elif isinstance(cPPAST, Token) and cPPAST.terminal_str.lower() == 'pp_number':
      return self.ppnumber(cPPAST)
    elif isinstance(cPPAST, Token) and cPPAST.terminal_str.lower() == 'identifier':
      if cPPAST.getString() not in self.symbols:
        raise Exception('Unknown Variable %s' (cPPAST.getString()))
      x = self.symbols[cPPAST.getString()]
      # TODO: there has got to be a better way to do this!
      self.cPPP.iterator = iter(x)
      self.cPPP.sym = self.cPPP.getsym()
      ast = self.cPPP.expr().toAst()
      return self._eval(ast)
    elif isinstance(cPPAST, Token) and cPPAST.terminal_str.lower() == 'csource':
      string = cPPAST.getString()
      tokens = []
      self.cL.setString(string)
      self.cL.setLine(self.line)
      self.cL.setColumn(1)
      for token in self.cL:
        next = [token]
        if token.terminal_str.lower() == 'identifier':
          if token.getString() in self.symbols:
            next = []
            for ntoken in self.symbols[token.getString()]:
              ntoken.colno = token.colno
              ntoken.lineno = token.lineno
              next.append(ntoken)
        tokens.extend(next)
      lines = len(list(filter(lambda x: x == '\n', string))) + 1
      self.line += lines
      return TokenList(tokens)
    elif isinstance(cPPAST, Token):
      return cPPAST
    elif isinstance(cPPAST, list):
      if cPPAST and len(cPPAST):
        for node in cPPAST:
          rtokens.extend( self._eval(node) )
      return rtokens
    else:
      if cPPAST.name == 'PPFile':
        nodes = cPPAST.getAttr('nodes')
        return self._eval(nodes)
      elif cPPAST.name == 'IfSection':
        self.line += 1
        value = self._eval(cPPAST.getAttr('if'))
        if value:
          rtokens.extend( value )
        for elseif in cPPAST.getAttr('elif'):
          self.line += 1
          if not value:
            value = self._eval(elseif)
            if value:
              rtokens.extend( value )
          else:
            self._eval(elseif) # Silent eval to count line numbers properly
        if cPPAST.getAttr('else') and not value:
          value = self._eval(cPPAST.getAttr('else'))
          rtokens.extend( value )
        self.line += 1
        return rtokens
      elif cPPAST.name == 'If':
        expr = cPPAST.getAttr('expr')
        nodes = cPPAST.getAttr('nodes')
        if self._eval(expr) != 0:
          return self._eval(nodes)
        else:
          self.line += self.countSourceLines(nodes)
        return None
      elif cPPAST.name == 'IfDef':
        ident = cPPAST.getAttr('ident').getString()
        nodes = cPPAST.getAttr('nodes')
        if ident in self.symbols:
          return self._eval(nodes)
        else:
          self.line += self.countSourceLines(nodes)
        return None
      elif cPPAST.name == 'IfNDef':
        ident = cPPAST.getAttr('ident').getString()
        nodes = cPPAST.getAttr('nodes')
        if ident not in self.symbols:
          return self._eval(nodes)
        else:
          self.line += self.countSourceLines(nodes)
        return None
      elif cPPAST.name == 'ElseIf':
        expr = cPPAST.getAttr('expr')
        nodes = cPPAST.getAttr('nodes')
        if self._eval(expr) != 0:
          return self._eval(nodes)
        else:
          self.line += self.countSourceLines(nodes)
        return None
      elif cPPAST.name == 'Else':
        nodes = cPPAST.getAttr('nodes')
        return self._eval(nodes)
      elif cPPAST.name == 'Include':
        cPPAST.getAttr('file')
        self.line += 1
      elif cPPAST.name == 'Define':
        ident = cPPAST.getAttr('ident')
        body = cPPAST.getAttr('body')
        self.symbols[ident.getString()] = self._eval(body)
        self.line += 1
      elif cPPAST.name == 'DefineFunction':
        ident = cPPAST.getAttr('ident')
        params = cPPAST.getAttr('params')
        body = cPPAST.getAttr('body')
        self.symbols[ident.getString()] = cPreprocessorFunction( [p.getString() for p in params], body )
        self.line += 1
      elif cPPAST.name == 'Pragma':
        cPPAST.getAttr('tokens')
        self.line += 1
      elif cPPAST.name == 'Error':
        cPPAST.getAttr('tokens')
        self.line += 1
      elif cPPAST.name == 'Undef':
        ident = cPPAST.getAttr('ident').getString()
        if ident in self.symbols:
          del self.symbols[ident]
        self.line += 1
      elif cPPAST.name == 'Line':
        cPPAST.getAttr('tokens')
        self.line += 1
      elif cPPAST.name == 'ReplacementList':
        tokens = cPPAST.getAttr('tokens')
        rtokens = []
        advance = 0
        newTokens = []
        for (index, token) in enumerate(tokens):
          if advance > 0:
            advance -= 1
            continue
          if token.terminal_str.lower() == 'identifier' and token.getString() in self.symbols:
            replacement = self.symbols[token.getString()]
            if isinstance(replacement, cPreprocessorFunction):
              advance = 2 # skip the identifier and lparen
              params = []
              for token in tokens[index + advance:]:
                if token.getString() == ')':
                  break
                if token.getString() != ',':
                  params.append(token)
                advance += 1
              result = replacement.run(params)
              newTokens.extend(result)
            else:
              newTokens.extend( self.symbols[token.getString()] )
          else:
            newTokens.append(token)
        return newTokens
      elif cPPAST.name == 'FuncCall':
        name = cPPAST.getAttr('name')
        params = cPPAST.getAttr('params')
      elif cPPAST.name == 'Add':
        return self.ppnumber(self._eval(cPPAST.getAttr('left'))) + self.ppnumber(self._eval(cPPAST.getAttr('right')))
      elif cPPAST.name == 'Sub':
        return self.ppnumber(self._eval(cPPAST.getAttr('left'))) - self.ppnumber(self._eval(cPPAST.getAttr('right')))
      elif cPPAST.name == 'LessThan':
        return int(self.ppnumber(self._eval(cPPAST.getAttr('left'))) < self.ppnumber(self._eval(cPPAST.getAttr('right'))))
      elif cPPAST.name == 'GreaterThan':
        return int(self.ppnumber(self._eval(cPPAST.getAttr('left'))) > self.ppnumber(self._eval(cPPAST.getAttr('right'))))
      elif cPPAST.name == 'LessThanEq':
        return int(self.ppnumber(self._eval(cPPAST.getAttr('left'))) <= self.ppnumber(self._eval(cPPAST.getAttr('right'))))
      elif cPPAST.name == 'GreaterThanEq':
        return int(self.ppnumber(self._eval(cPPAST.getAttr('left'))) >= self.ppnumber(self._eval(cPPAST.getAttr('right'))))
      elif cPPAST.name == 'Mul':
        return self.ppnumber(self._eval(cPPAST.getAttr('left'))) * self.ppnumber(self._eval(cPPAST.getAttr('right')))
      elif cPPAST.name == 'Div':
        return self.ppnumber(self._eval(cPPAST.getAttr('left'))) / self.ppnumber(self._eval(cPPAST.getAttr('right')))
      elif cPPAST.name == 'Mod':
        return self.ppnumber(self._eval(cPPAST.getAttr('left'))) % self.ppnumber(self._eval(cPPAST.getAttr('right')))
      elif cPPAST.name == 'Equals':
        return int(self.ppnumber(self._eval(cPPAST.getAttr('left'))) == self.ppnumber(self._eval(cPPAST.getAttr('right'))))
      elif cPPAST.name == 'NotEquals':
        return int(self.ppnumber(self._eval(cPPAST.getAttr('left'))) != self.ppnumber(self._eval(cPPAST.getAttr('right'))))
      elif cPPAST.name == 'Comma':
        self._eval(left)
        return self.ppnumber(self._eval(cPPAST.getAttr('right')))
      elif cPPAST.name == 'LeftShift':
        return self.ppnumber(self._eval(cPPAST.getAttr('left'))) << self.ppnumber(self._eval(cPPAST.getAttr('right')))
      elif cPPAST.name == 'RightShift':
        return self.ppnumber(self._eval(cPPAST.getAttr('left'))) >> self.ppnumber(self._eval(cPPAST.getAttr('right')))
      elif cPPAST.name == 'BitAND':
        return self.ppnumber(self._eval(cPPAST.getAttr('left'))) & self.ppnumber(self._eval(cPPAST.getAttr('right')))
      elif cPPAST.name == 'BitOR':
        return self.ppnumber(self._eval(cPPAST.getAttr('left'))) | self.ppnumber(self._eval(cPPAST.getAttr('right')))
      elif cPPAST.name == 'BitXOR':
        return self.ppnumber(self._eval(cPPAST.getAttr('left'))) ^ self.ppnumber(self._eval(cPPAST.getAttr('right')))
      elif cPPAST.name == 'TernaryOperator':
        cond = cPPAST.getAttr('cond')
        true = cPPAST.getAttr('true')
        false = cPPAST.getAttr('false')
        if self._eval(cond) != 0:
          return self._eval(true)
        else:
          return self._eval(false)
      else:
        raise Exception('Bad AST Node', str(cPPAST))
    return rtokens
  
  def ppnumber(self, element):
    if isinstance(element, Token):
      return int(element.getString())
    return int(element)
  
  def countSourceLines(self, cPPAST):
    lines = 0
    if not cPPAST:
      return 0
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
  

class cTokens:
  def __init__(self):
    self.tokens = []
  def __iter__(self):
    return iter(self.token)
  def addTokens(self, tokens):
    self.tokens.extend(tokens)
  def addToken(self, token):
    self.tokens.append(token)

# This is what can be tokenized and parsed as C code.
class cTranslationUnit:
  def __init__( self, cT, cP ):
    self.__dict__.update(locals())
  
  def process( self ):
    # Returns (cParseTree, cAst)
    for token in self.cT:
      print(token)
  

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
  
  def setString(self, string):
    self.string = string
    self.colno = 1
    self.lineno = 1
  
  def setLine(self, lineno):
    self.lineno = lineno
  
  def setColumn(self, colno):
    self.colno = colno
  
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
      for (regex, terminal, process_func, format_func) in self.regex:
        match = regex.match(self.string)
        if match:
          activity = True
          lineno = self.lineno
          colno = self.colno
          
          self.advance( len(match.group(0)) )
          newlines = len(list(filter(lambda x: x == '\n', match.group(0))))
          self.lineno += newlines
          if newlines > 0:
            self.colno = len(match.group(0).split('\n')[-1]) + 1
          else:
            self.colno += len(match.group(0))

          if process_func:
            tokens = process_func(self.string)
            for token in tokens:
              self.addToken(Token(self.terminals[token], token, match.group(0), lineno, colno))
            return self.nextToken()
          else:
            if terminal != None:
              return Token(self.terminals[terminal], terminal, match.group(0), lineno, colno)
    return None
  
  def __iter__(self):
    return self
  
  def __next__(self):
    if self.hasToken():
      return self.nextToken()
    if len(self.string.strip()) <= 0:
      raise StopIteration()
    token = self.nextMatch()
    if not token:
      raise Exception('Invalid character on line %d, col %d' % (self.lineno, self.colno))
    return token
  

def disambiguateDefine( string ):
  identifier_regex = r'([a-zA-Z_]|\\[uU]([0-9a-fA-F]{4})([0-9a-fA-F]{4})?)([a-zA-Z_0-9]|\\[uU]([0-9a-fA-F]{4})([0-9a-fA-F]{4})?)*'
  if re.match(r'[ \t]+%s\(' % (identifier_regex), string):
    return ['DEFINE_FUNCTION']
  else:
    return ['DEFINE']


class cPreprocessingLexer(Lexer):
  
  regex = [
    ( re.compile(r'#[ \t]*include'), 'INCLUDE', None, None ),
    ( re.compile(r'#[ \t]*define'), None, disambiguateDefine, None ),
    ( re.compile(r'#[ \t]*ifdef'), 'IFDEF', None, None ),
    ( re.compile(r'#[ \t]*ifndef'), 'IFNDEF', None, None ),
    ( re.compile(r'#[ \t]*if'), 'IF', None, None ),
    ( re.compile(r'#[ \t]*elif'), 'ELIF', None, None ),
    ( re.compile(r'#[ \t]*pragma'), 'PRAGMA', None, None ),
    ( re.compile(r'#[ \t]*error'), 'ERROR', None, None ),
    ( re.compile(r'#[ \t]*line'), 'LINE', None, None ),
    ( re.compile(r'#[ \t]*undef'), 'UNDEF', None, None ),
    ( re.compile(r'#[ \t]*endif'), 'ENDIF', None, None ),
    ( re.compile(r'[<][^\n>]+[>]'), 'HEADER_GLOBAL', None, None ),
    ( re.compile(r'["][^\n"]+["]'), 'HEADER_LOCAL', None, None ),
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
    ( re.compile(r'&(?!&)'), 'BITAND', None, None ),
    ( re.compile(r'\*(?!=)'), 'MUL', None, None ),
    ( re.compile(r'\+(?!=)'), 'ADD', None, None ),
    ( re.compile(r'-(?!=)'), 'SUB', None, None ),
    ( re.compile(r'~'), 'TILDE', None, None ),
    ( re.compile(r'!(?!=)'), 'EXCLAMATION_POINT', None, None ),
    ( re.compile(r'/(?!=)'), 'DIV', None, None ),
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
    ( re.compile(r'&&'), 'AND', None, None ),
    ( re.compile(r'\|\|'), 'OR', None, None ),
    ( re.compile(r'\?'), 'QUESTIONMARK', None, None ),
    ( re.compile(r':'), 'COLON', None, None ),
    ( re.compile(r';'), 'SEMI', None, None ),
    ( re.compile(r'\.\.\.'), 'ELIPSIS', None, None ),
    ( re.compile(r','), 'COMMA', None, None ),
    ( re.compile(r'##'), 'POUNDPOUND', None, None ),
    ( re.compile(r'#(?!#)'), 'POUND', None, None ),
    ( re.compile(r'[ \t]+', 0), None, None, None )
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
  
  def setLine(self, lineno):
    self.lineno = lineno
  
  def setColumn(self, colno):
    self.colno = colno
  
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
          if cPPT.terminal_str.upper() in ['INCLUDE', 'DEFINE', 'DEFINE_FUNCTION', 'PRAGMA', 'ERROR', 'LINE', 'ENDIF', 'UNDEF']:
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
    self.cache = []
    self.setTerminals(terminals)
    self.setString(string)
    self.setRegex ([
      # Comments
      ( re.compile(r'/\*.*?\*/', re.S), None, None, None ),
      ( re.compile(r'//.*', 0), None, None, None ),

      # Keywords
      ( re.compile(r'auto(?=\s)'), 'AUTO', None, None ),
      ( re.compile(r'_Bool(?=\s)'), 'BOOL', None, None ),
      ( re.compile(r'break(?=\s)'), 'BREAK', None, None ),
      ( re.compile(r'case(?=\s)'), 'CASE', None, None ),
      ( re.compile(r'char(?=\s)'), 'CHAR', None, None ),
      ( re.compile(r'_Complex(?=\s)'), 'COMPLEX', None, None ),
      ( re.compile(r'const(?=\s)'), 'CONST', None, None ),
      ( re.compile(r'continue(?=\s)'), 'CONTINUE', None, None ),
      ( re.compile(r'default(?=\s)'), 'DEFAULT', None, None ),
      ( re.compile(r'do(?=\s)'), 'DO', None, None ),
      ( re.compile(r'double(?=\s)'), 'DOUBLE', None, None ),
      ( re.compile(r'else(?=\s)'), 'ELSE', None, None ),
      ( re.compile(r'enum(?=\s)'), 'ENUM', None, None ),
      ( re.compile(r'extern(?=\s)'), 'EXTERN', None, None ),
      ( re.compile(r'float(?=\s)'), 'FLOAT', None, None ),
      ( re.compile(r'for(?=\s)'), 'FOR', None, None ),
      ( re.compile(r'goto(?=\s)'), 'GOTO', None, None ),
      ( re.compile(r'if(?=\s)'), 'IF', None, None ),
      ( re.compile(r'_Imaginary(?=\s)'), 'IMAGINARY', None, None ),
      ( re.compile(r'inline(?=\s)'), 'INLINE', None, None ),
      ( re.compile(r'int(?=\s)'), 'INT', None, None ),
      ( re.compile(r'long(?=\s)'), 'LONG', None, None ),
      ( re.compile(r'register(?=\s)'), 'REGISTER', None, None ),
      ( re.compile(r'restrict(?=\s)'), 'RESTRICT', None, None ),
      ( re.compile(r'return(?=\s)'), 'RETURN', None, None ),
      ( re.compile(r'short(?=\s)'), 'SHORT', None, None ),
      ( re.compile(r'signed(?=\s)'), 'SIGNED', None, None ),
      ( re.compile(r'sizeof(?=\s)'), 'SIZEOF', None, None ),
      ( re.compile(r'static(?=\s)'), 'STATIC', None, None ),
      ( re.compile(r'struct(?=\s)'), 'STRUCT', None, None ),
      ( re.compile(r'switch(?=\s)'), 'SWITCH', None, None ),
      ( re.compile(r'typedef(?=\s)'), 'TYPEDEF', None, None ),
      ( re.compile(r'union(?=\s)'), 'UNION', None, None ),
      ( re.compile(r'unsigned(?=\s)'), 'UNSIGNED', None, None ),
      ( re.compile(r'void(?=\s)'), 'VOID', None, None ),
      ( re.compile(r'volatile(?=\s)'), 'VOLATILE', None, None ),
      ( re.compile(r'while(?=\s)'), 'WHILE', None, None ),

      # Identifiers
      ( re.compile(r'([a-zA-Z_]|\\[uU]([0-9a-fA-F]{4})([0-9a-fA-F]{4})?)([a-zA-Z_0-9]|\\[uU]([0-9a-fA-F]{4})([0-9a-fA-F]{4})?)*'), 'IDENTIFIER', None, None ),

      # Unicode Characters
      ( re.compile(r'\\[uU]([0-9a-fA-F]{4})([0-9a-fA-F]{4})?'), 'UNIVERSAL_CHARACTER_NAME', None, None ),

      # Digraphs
      ( re.compile(r'<%'), 'LBRACE', None, None ),
      ( re.compile(r'%>'), 'RBRACE', None, None ),
      ( re.compile(r'<:'), 'LSQUARE', None, None ),
      ( re.compile(r':>'), 'RSQUARE', None, None ),
      ( re.compile(r'%:%:'), 'POUNDPOUND', None, None ),
      ( re.compile(r'%:'), 'POUND', None, None ),

      # Punctuators
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
      ( re.compile(r'&(?!&)'), 'BITAND', None, None ),
      ( re.compile(r'\*(?!=)'), 'MUL', None, None ),
      ( re.compile(r'\+(?!=)'), 'ADD', None, None ),
      ( re.compile(r'-(?!=)'), 'SUB', None, None ),
      ( re.compile(r'~'), 'TILDE', None, None ),
      ( re.compile(r'!(?!=)'), 'EXCLAMATION_POINT', None, None ),
      ( re.compile(r'/(?!=)'), 'DIV', None, None ),
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
      ( re.compile(r'&&'), 'AND', None, None ),
      ( re.compile(r'\|\|'), 'OR', None, None ),
      ( re.compile(r'\?'), 'QUESTIONMARK', None, None ),
      ( re.compile(r':'), 'COLON', None, None ),
      ( re.compile(r';'), 'SEMI', None, None ),
      ( re.compile(r'\.\.\.'), 'ELIPSIS', None, None ),
      ( re.compile(r'=(?!=)'), 'ASSIGN', None, None ),
      ( re.compile(r'\*='), 'MULEQ', None, None ),
      ( re.compile(r'/='), 'DIVEQ', None, None ),
      ( re.compile(r'%='), 'MODEQ', None, None ),
      ( re.compile(r'\+='), 'ADDEQ', None, None ),
      ( re.compile(r'-='), 'SUBEQ', None, None ),
      ( re.compile(r'<<='), 'LSHIFTEQ', None, None ),
      ( re.compile(r'>>='), 'RSHIFTEQ', None, None ),
      ( re.compile(r'&='), 'BITANDEQ', None, None ),
      ( re.compile(r'\^='), 'BITXOREQ', None, None ),
      ( re.compile(r'\|='), 'BITOREQ', None, None ),
      ( re.compile(r','), 'COMMA', None, None ),
      ( re.compile(r'##'), 'POUNDPOUND', None, None ),
      ( re.compile(r'#(?!#)'), 'POUND', None, None ),

      # Constants, Literals
      ( re.compile(r'(([0-9]+)?\.([0-9]+)|[0-9]+\.)([eE][-+]?[0-9]+)?[flFL]?'), 'DECIMAL_FLOATING_CONSTANT', None, None ),
      ( re.compile(r'[L]?"([^\\\"\n]|\\[\\"\'nrbtfav\?]|\\[0-7]{1,3}|\\x[0-9a-fA-F]+|\\[uU]([0-9a-fA-F]{4})([0-9a-fA-F]{4})?)*"'), 'STRING_LITERAL', None, None ),
      ( re.compile(r'([1-9][0-9]*|0[xX][0-9a-fA-F]+|0[0-7]*)([uU](ll|LL)|[uU][lL]?|(ll|LL)[uU]?|[lL][uU])?'), 'INTEGER_CONSTANT', None, None ),
      ( re.compile(r'0[xX](([0-9a-fA-F]+)?\.([0-9a-fA-F]+)|[0-9a-fA-F]+\.)[pP][-+]?[0-9]+[flFL]?'), 'HEXADECIMAL_FLOATING_CONSTANT', None, None ),
      ( re.compile(r"[L]?'([^\\'\n]|\\[\\\"\'nrbtfav\?]|\\[0-7]{1,3}|\\x[0-9a-fA-F]+|\\[uU]([0-9a-fA-F]{4})([0-9a-fA-F]{4})?)+'"), 'CHARACTER_CONSTANT', None, None ),

      # Whitespace
      ( re.compile(r'\s+', 0), None, None, None )
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

  cPF = cPreprocessingFile(open(filename).read(), cPPL, cPPP, cL)
  cT = cPF.process()
  cTU = cTranslationUnit(cT, cP)
  cTU.process()
