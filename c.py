import sys, re, os
from itertools import zip_longest, islice
import cParser, ppParser

sys.setrecursionlimit(2000)

# Abbreviations:
#
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
# cPE = C Preprocessor Evaluator

class Debugger:
  class DebugLogger:
    def __init__(self, module, filepath):
      self.__dict__.update(locals())
      self.fp = open(filepath, 'w')
    
    def log( self, category, line ):
      self.fp.write( "[%s] %s\n" % (category, line) )
      # TODO close file in destructor
      self.fp.flush()
    
  
  def __init__(self, directory):
    self.__dict__.update(locals())
    self.loggers = {}
  
  def getLogger(self, module):
    filepath = os.path.join(self.directory, module)
    if module in self.loggers:
      logger = self.loggers[module]
    else:
      logger = self.DebugLogger(module, filepath)
      self.loggers[module] = logger
    return logger
  
  
class Token(cParser.Terminal):
  def __init__(self, id, terminal_str, source_string, lineno, colno):
    self.__dict__.update(locals())
  
  def getString(self):
    return self.source_string
  
  def getLine(self):
    return self.lineno
  
  def getColumn(self):
    return self.colno
  
  def __str__( self ):
    #return "'%s'" % (self.terminal_str.lower())
    return '%s (%s) [line %d, col %d]' % ( self.terminal_str.lower(), self.source_string, self.lineno, self.colno )
  

class TokenList(list):
  pass


# Also called 'source file' in ISO docs.
# Takes C source code, pre-processes, returns C tokens
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
  def __init__( self, cST, cPPL, cPPP, cL, cPE, logger = None ):
    self.__dict__.update(locals())
  
  def process( self ):
    # Phase 1: Replace trigraphs with single-character equivelants
    for (trigraph, replacement) in self.trigraphs.items():
      self.cST = self.cST.replace(trigraph, replacement)
    # Phase 3: Tokenize, preprocessing directives executed, macro invocations expanded, expand _Pragma
    self.cPPL.setString( self.cST )
    parsetree = cPPP.parse(self.cPPL, 'pp_file')
    ast = parsetree.toAst()
    if self.logger:
      try:
        self.logger.log('parsetree', str(parsetree))
        self.logger.log('ast', str(ast))
      except RuntimeError:
        pass
    ctokens = self.cPE.eval(ast)
    return ctokens
  

class cPreprocessorFunction:
  def __init__(self, name, params, body, logger = None):
    self.__dict__.update(locals())
  
  def run(self, params):
    if len(params) != len(self.params):
      raise Exception('Error: too %s parameters to function %s: %s' % ('many' if len(params) > len(self.params) else 'few', self.name, ', '.join([str(x) for x in params])))
    values = {self.params[i].lower(): params[i] for i in range(len(params))}
    nodes = []
    if not self.body:
      return nodes
    for node in self.body.getAttr('tokens'):
      if node.terminal_str.lower() == 'identifier' and node.getString().lower() in values:
        val = values[node.getString().lower()]
        if isinstance(val, list):
          nodes.extend(val)
        else:
          nodes.append(val)
      else:
        nodes.append(node)
    return nodes
  
  def __str__(self):
    return '[cPreprocessorFunction params=%s body=%s]' % (', '.join(self.params), str(self.body))
  

class cPreprocessingEvaluator:
  def __init__(self, cPPP, cL, logger = None):
    self.__dict__.update(locals())
  
  def eval( self, cPPAST ):
    self.symbols = dict()
    self.line = 1
    return self._eval(cPPAST)
  
  def newlines(self, number):
    return ''.join(['\n' for i in range(number)])
  
  def _parseExpr(self, tokens):
    self.cPPP.iterator = iter(tokens)
    self.cPPP.sym = self.cPPP.getsym()
    ast = self.cPPP.expr().toAst()
    value = self._eval(ast)
    return Token(cPPP.terminal('pp_number'), 'pp_number', value, 0, 0)
  
  def _debugStr(self, cPPAST):
    if isinstance(cPPAST, Token):
      string = 'Token (%s) [line %d, col %d]' % (cPPAST.terminal_str.lower(), cPPAST.lineno, cPPAST.colno)
      if cPPAST.terminal_str.lower() not in ['pp_number', 'identifier', 'csource']:
        string = '(unidentified) ' + string
      return string
    if isinstance(cPPAST, list):
      return 'List: [%s]' % (', '.join([self._debugStr(x) for x in cPPAST]))
    if isinstance(cPPAST, ppParser.Ast):
      return 'Ast: %s' % (cPPAST.name)
  
  def _eval( self, cPPAST ):
    rtokens = []
    if self.logger:
      self._log('eval', self._debugStr(cPPAST))
      for symbol, replacement in self.symbols.items():
        if isinstance(replacement, list):
          replacementList = '[%s]' % (', '.join([str(x) for x in replacement]))
        else:
          replacementList = str(replacement)
        self._log('symbol', '%s: %s' % (str(symbol), replacementList))
    if not cPPAST:
      return []
    elif isinstance(cPPAST, Token) and cPPAST.terminal_str.lower() == 'pp_number':
      return self.ppnumber(cPPAST)
    elif isinstance(cPPAST, Token) and cPPAST.terminal_str.lower() == 'identifier':
      x = 0
      if cPPAST.getString() in self.symbols:
        x = self.symbols[cPPAST.getString()]
      
      try:
        self._log('eval', 'evaluating expression for identifier %s' % (cPPAST.getString()))
        self._log('eval', 'expression tokens: [%s]' % (self._debugStr(x)))
        if len(x):
          return self._parseExpr( x )
      except TypeError:
        return x
    elif isinstance(cPPAST, Token) and cPPAST.terminal_str.lower() == 'csource':
      tokens = []
      params = []
      advance = 0
      self.cL.setString(cPPAST.getString())
      self.cL.setLine(cPPAST.getLine())
      self.cL.setColumn(cPPAST.getColumn())
      # token with lookahead
      cTokens = list(self.cL)
      cLexer = zip_longest(cTokens, cTokens[1:])
      for token, lookahead in cLexer:
        if token.terminal_str.lower() == 'identifier' and \
           token.getString() in self.symbols:
          replacement = self.symbols[token.getString()]
          if isinstance(replacement, cPreprocessorFunction):
            if lookahead.getString() != '(':
              tokens.extend(token)
              continue
            next(cLexer) # skip lparen
            lparen = 1
            buf = []
            params = []
            print('--')
            for paramToken, plookahead in cLexer:
              print('pp', paramToken)
              paramTokenStr = paramToken.terminal_str.lower()
              if paramTokenStr == 'lparen':
                lparen += 1
              if paramTokenStr == 'rparen':
                lparen -= 1
              if paramTokenStr in ['comma', 'rparen'] and lparen <= 1:
                params.append( buf )
                buf = []
              else:
                if paramTokenStr in ['integer_constant', 'decimal_floating_constant', 'hexadecimal_floating_constant']:
                  paramToken.id = self.cPPP.terminal('pp_number');
                  paramToken.terminal_str = 'pp_number'
                buf.append(paramToken)
              if paramTokenStr == 'rparen' and lparen <= 1:
                break
            print(', '.join([str(x) for x in buf]))
            result = replacement.run(params)
            tokens.extend(result)
          elif isinstance(replacement, list):
            tmp = []
            for ntoken in replacement:
              ntoken.colno = token.colno
              ntoken.lineno = token.lineno
              tmp.append(ntoken)
            tokens.extend(tmp)
            continue
          else:
            raise Exception('unknown macro replacement type')
        else:
          tokens.append(token)
      lines = len(list(filter(lambda x: x == '\n', cPPAST.getString()))) + 1
      self.line += lines
      return TokenList(tokens)
    elif isinstance(cPPAST, Token):
      return cPPAST
    elif isinstance(cPPAST, list):
      if cPPAST and len(cPPAST):
        for node in cPPAST:
          result = self._eval(node)
          if isinstance(result, list):
            rtokens.extend(result)
          else:
            rtokens.append(result)
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
        if cPPAST.getAttr('else'):
          elseEval = self._eval(cPPAST.getAttr('else'))
          self.line += 1
          if not value:
            value = elseEval
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
        self._log('DEFINE', str(body))
        self.symbols[ident.getString()] = self._eval(body)
        self.line += 1
      elif cPPAST.name == 'DefineFunction':
        ident = cPPAST.getAttr('ident')
        params = cPPAST.getAttr('params')
        body = cPPAST.getAttr('body')
        self.symbols[ident.getString()] = cPreprocessorFunction( ident, [p.getString() for p in params], body )
        self.line += 1
      elif cPPAST.name == 'Pragma':
        cPPAST.getAttr('tokens')
        self.line += 1
      elif cPPAST.name == 'Error':
        cPPAST.getAttr('tokens')
        self.line += 1
      elif cPPAST.name == 'Warning':
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
              if index >= len(tokens) - 1:
                newTokens.append(replacement)
              elif tokens[index + 1].getString() == '(':
                advance = 2 # skip the identifier and lparen
                params = []
                param_tokens = []
                lparen_count = 1
                for token in tokens[index + advance:]:
                  if token.getString() == '(':
                    lparen_count += 1
                  if token.getString() == ')':
                    if lparen_count == 1:
                      params.append( self._parseExpr( param_tokens ) )
                      break
                    lparen_count -= 1
                    param_tokens.append(token)
                  elif token.getString() == ',':
                    if len(param_tokens):
                      params.append( self._parseExpr( param_tokens ) )
                      param_tokens = []
                  else:
                    param_tokens.append(token)
                  advance += 1
                result = replacement.run(params)
                newTokens.extend(result)
              else:
                newTokens.append(token)
            else:
              newTokens.extend( self.symbols[token.getString()] )
          else:
            newTokens.append(token)
        return newTokens
      elif cPPAST.name == 'FuncCall':
        name = cPPAST.getAttr('name')
        params = cPPAST.getAttr('params')
      elif cPPAST.name == 'IsDefined':
        return cPPAST.getAttr('expr').getString() in self.symbols
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
      elif cPPAST.name == 'BitNOT':
        return ~self.ppnumber(self._eval(cPPAST.getAttr('expr')))
      elif cPPAST.name == 'And':
        return self.ppnumber(self._eval(cPPAST.getAttr('left'))) and self.ppnumber(self._eval(cPPAST.getAttr('right')))
      elif cPPAST.name == 'Or':
        return self.ppnumber(self._eval(cPPAST.getAttr('left'))) or self.ppnumber(self._eval(cPPAST.getAttr('right')))
      elif cPPAST.name == 'Not':
        return not self.ppnumber(self._eval(cPPAST.getAttr('expr')))
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
      numstr = element.getString()
      if isinstance(numstr, int) or isinstance(numstr, float):
        return numstr
      numstr = re.sub(r'[lLuU]', '', numstr)
      if 'e' in numstr or 'E' in numstr:
        numstr = numstr.split( 'e' if e in numstr else 'E' )
        num = int(numstr[0], self._base(numstr[0])) ** int(numstr[1], self._base(numstr[1]))
      elif 'p' in numstr or 'P' in numstr:
        numstr = numstr.split( 'p' if e in numstr else 'P' )
        num = int(numstr[0], self._base(numstr[0])) * (2 ** int(numstr[1], self._base(numstr[1])))
      else:
        num = int(numstr, self._base(numstr))
      return num
    return int(element)
  
  def _base(self, string):
    if string[:2] == '0x' or string[:2] == '0X':
      return 16
    elif string[0] == '0':
      return 8
    else:
      return 10
  
  def _log(self, category, message):
    if not self.logger:
      return
    self.logger.log(category, message)
  
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
  

# This is what can be tokenized and parsed as C code.
class cTranslationUnit:
  def __init__( self, cT, cP, logger = None ):
    self.__dict__.update(locals())
  
  def process( self ):
    for t in self.cT:
      pass#print(t)
    return cT
    parsetree = self.cP.parse( self.cT, 'translation_unit' )
    ast = parsetree.toAst()
    return ast
  

class Lexer:
  def __iter__(self):
    return self
  
  def __next__(self):
    raise StopIteration()
  

class PatternMatchingLexer(Lexer):
  def __init__(self, string = '', regex = [], terminals = {}, logger = None):
    self.setLogger(logger)
    self.setRegex(regex)
    self.setTerminals(terminals)
    self.setString(string)
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
    self._log('info', 'SetString: "%s"' %(string))
  
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
            (tokens, advancement) = process_func(match_str, self.string, self.lineno, self.colno, self.terminals)
            for token in tokens:
              self.addToken(token)
            self.advance(advancement)
            return self.nextToken()
          else:
            if terminal != None:
              return Token(self.terminals[terminal], terminal, match_str, lineno, colno)
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
  

def parseDefine( match, string, lineno, colno, terminals ):
  identifier_regex = r'([a-zA-Z_]|\\[uU]([0-9a-fA-F]{4})([0-9a-fA-F]{4})?)([a-zA-Z_0-9]|\\[uU]([0-9a-fA-F]{4})([0-9a-fA-F]{4})?)*'
  if re.match(r'[ \t]+%s\(' % (identifier_regex), string):
    token = Token(terminals['DEFINE_FUNCTION'], 'DEFINE_FUNCTION', match, lineno, colno - len(match))
  else:
    token = Token(terminals['DEFINE'], 'DEFINE', match, lineno, colno - len(match))
  return ([token], 0)

def parseInclude( match, string, lineno, colno, terminals ):
  header_global = re.compile(r'[<][^\n>]+[>]')
  header_local = re.compile(r'["][^\n"]+["]')
  advance = len(re.compile(r'[\t ]*').match(string).group(0))
  string = string[advance:]
  tokens = [Token(terminals['INCLUDE'], 'INCLUDE', match, lineno, colno)]
  for (regex, token) in [(header_global, 'HEADER_GLOBAL'), (header_local, 'HEADER_LOCAL')]:
    rmatch = regex.match(string)
    if rmatch:
      rstring = rmatch.group(0)
      tokens.append( Token(terminals[token], token, rstring, lineno, colno + advance) )
      advance += len(rstring)
      break
  return (tokens, advance)


class cPreprocessingLexer(Lexer):
  regex = [
    ( re.compile(r'#[ \t]*include(?=[ \t\n])'), None, parseInclude, None ),
    ( re.compile(r'#[ \t]*include_next(?=[ \t\n])'), None, parseInclude, None ), # GCC extension
    ( re.compile(r'#[ \t]*define(?=[ \t\n])'), None, parseDefine, None ),
    ( re.compile(r'#[ \t]*ifdef(?=[ \t\n])'), 'IFDEF', None, None ),
    ( re.compile(r'#[ \t]*ifndef(?=[ \t\n])'), 'IFNDEF', None, None ),
    ( re.compile(r'#[ \t]*if(?=[ \t\n])'), 'IF', None, None ),
    ( re.compile(r'#[ \t]*else'), 'ELSE', None, None ),
    ( re.compile(r'#[ \t]*elif(?=[ \t\n])'), 'ELIF', None, None ),
    ( re.compile(r'#[ \t]*pragma(?=[ \t\n])'), 'PRAGMA', None, None ),
    ( re.compile(r'#[ \t]*error(?=[ \t\n])'), 'ERROR', None, None ),
    ( re.compile(r'#[ \t]*warning(?=[ \t\n])'), 'WARNING', None, None ),
    ( re.compile(r'#[ \t]*line(?=[ \t\n])'), 'LINE', None, None ),
    ( re.compile(r'#[ \t]*undef(?=[ \t\n])'), 'UNDEF', None, None ),
    ( re.compile(r'#[ \t]*endif'), 'ENDIF', None, None ),
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
    self.comment_start = re.compile(r'/\*')
    self.comment_end = re.compile(r'\*/')
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
    for line in self.cST_lines:
      self.lineno += 1
      if not comment and (self._isPreprocessingLine( line ) or continuation):
        continuation = False
        if len(buf):
          self.lineno -= 1
          emit_csource = True
          break
        if line.strip() == '#':
          lines += 1
          continue
        if line[-1] == '\\':
          line = line[:-1]
          continuation = True
        self.patternMatchingLexer.setString( line )
        self.patternMatchingLexer.setLine( self.lineno )
        self.patternMatchingLexer.setColumn( 1 )
        for cPPT in self.patternMatchingLexer:
          self._addToken(cPPT)
          if cPPT.terminal_str.upper() in ['INCLUDE', 'DEFINE', 'DEFINE_FUNCTION', 'PRAGMA', 'ERROR', 'WARNING', 'LINE', 'ENDIF', 'UNDEF']:
            emit_separator = True
        if continuation:
          lines += 1
          continue
        if emit_separator:
          self._addToken( Token(self.terminals['SEPARATOR'], 'SEPARATOR', '', self.lineno + 1, 1) )
        self._advance( lines + 1 )
        if self._hasToken():
          return self._popToken()
        raise Exception('Unexpected')
      else:
        emit_csource = True
        if not len(buf):
          buf_line = self.lineno
        if self.comment_start.search(line) and not self.comment_end.search(line):
          comment = True
        elif not self.comment_start.search(line) and self.comment_end.search(line):
          comment = False
        buf.append(line)
        lines += 1

    self._advance(lines)
    if emit_csource:
      token = Token(self.terminals['CSOURCE'], 'CSOURCE', '\n'.join(buf), buf_line, 1)
      self._addToken( Token(self.terminals['SEPARATOR'], 'SEPARATOR', '', self.lineno, 1) )
      return token
    raise StopIteration()
  
  def _isPreprocessingLine(self, line):
    if not line: return False
    stripped_line = line.strip()
    if len(stripped_line) and stripped_line[0] == '#':
      return True
    return False
  

class cLexer(PatternMatchingLexer):
  cRegex = [
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
  ]
  def __init__(self, terminals, logger = None):
    self.cache = []
    self.setTerminals(terminals)
    self.setRegex(self.cRegex)
    self.setLogger(logger)
  

if len(sys.argv) < 2:
  print("missing C file(s)")
  sys.exit(-1)

for filename in sys.argv[1:]:
  debugger = Debugger('./debug')
  cP = cParser.Parser()
  cPPP = ppParser.Parser()
  
  cTokenMap = { terminalString.upper(): cP.terminal(terminalString) for terminalString in cP.terminalNames() }
  cL = cLexer(cTokenMap, logger=debugger.getLogger('cmatch'))

  cPPL_TokenMap = { terminalString.upper(): cPPP.terminal(terminalString) for terminalString in cPPP.terminalNames() }
  cPPL_PatternMatchingLexer = PatternMatchingLexer(terminals=cPPL_TokenMap, logger=debugger.getLogger('ppmatch'))
  cPPL = cPreprocessingLexer( cPPL_PatternMatchingLexer, cPPL_TokenMap, logger=debugger.getLogger('pplex') )
  cPE = cPreprocessingEvaluator(cPPP, cL, logger=debugger.getLogger('ppeval'))
  cPF = cPreprocessingFile(open(filename).read(), cPPL, cPPP, cL, cPE, logger=debugger.getLogger('ppfile'))
  
  try:
    cT = cPF.process()
    cTU = cTranslationUnit(cT, cP)
    cAST = cTU.process()
  except Exception as e:
    print(e, '\n', e.tracer)
    sys.exit(-1)
  sys.exit(0)
  print(cAST)
