import sys, re, os
from itertools import zip_longest, islice
from copy import copy, deepcopy
from cast.cParser import Parser as cParser
from cast.ppParser import Parser as ppParser
from cast.ppParser import Ast as ppAst
from cast.cLexer import cLexer
from cast.ppLexer import ppLexer
from cast.Token import Token, cToken, ppToken, TokenList
from cast.SourceCode import SourceCode, SourceCodeString, SourceCodeEmpty

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
    return None
    filepath = os.path.join(self.directory, module)
    if module in self.loggers:
      logger = self.loggers[module]
    else:
      logger = self.DebugLogger(module, filepath)
      self.loggers[module] = logger
    return logger

class Factory:
  def create(self, includePathGlobal = ['.'], includePathLocal = ['.']):
    cPPP = ppParser()
    cP = cParser()
    cPE = cPreprocessingEvaluator( cPPP, cP, self, includePathGlobal, includePathLocal )
    return PreProcessor( cPPP, cPE )

# Also called 'source file' in ISO docs.
# Takes C source code, pre-processes, returns C tokens
class PreProcessor:  
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
  def __init__( self, cPPP, cPE ):
    self.__dict__.update(locals())
  
  def process( self, sourceCode, symbols = {}, lineno = 1, skipIncludes=False ):
    # Phase 1: Replace trigraphs with single-character equivalents
    for (trigraph, replacement) in self.trigraphs.items():
      sourceCode.sourceCode = sourceCode.sourceCode.replace(trigraph, replacement)
    # Phase 3: Tokenize, preprocessing directives executed, macro invocations expanded, expand _Pragma
    parsetree = self.cPPP.parse( ppLexer(sourceCode) )
    ast = parsetree.toAst()
    self.cPE.skipIncludes = skipIncludes
    ctokens = self.cPE.eval(ast, symbols)
    return (ctokens, self.cPE.getSymbolTable())
  

#cPFF
class cPreprocessorFunctionFactory:
  class cPreprocessorFunction:
    def __init__(self, name, params, body, cP, cPE, logger = None):
      self.__dict__.update(locals())
    
    def run(self, params, lineno, colno):
      if len(params) != len(self.params) and self.params[-1] != '...':
        raise Exception('Error: too %s parameters to function %s: %s' % ('many' if len(params) > len(self.params) else 'few', self.name, ', '.join([str(x) for x in params])))
      paramValues = dict()
      for (index, param) in enumerate(self.params):
        if param == '...':
          if index != (len(self.params) - 1):
            raise Exception('Error: ellipsis must be the last parameter in parameter list')
          paramValues['__VA_ARGS__'] = []
          for va_arg_rlist, next in zip_longest(params[index:], params[index+1:]):
            paramValues['__VA_ARGS__'].extend(va_arg_rlist)
            if next:
              paramValues['__VA_ARGS__'].append(cToken(self.cP.terminal('comma'), '<stream>', 'comma', ',', 0, 0, None))
        else:
          paramValues[param] = params[index]
      nodes = []
      if not self.body:
        return nodes
      for node in self.body.getAttr('tokens'):
        if node.terminal_str.lower() == 'identifier' and node.getString() in paramValues:
          val = paramValues[node.getString()]
          if isinstance(val, list):
            nodes.extend(deepcopy(val))
          else:
            nodes.append(copy(val))
        else:
          newNode = copy(node)
          nodes.append(newNode)
      nodes = self.cPE._eval(ppAst('ReplacementList', {'tokens': nodes}))
      for node in nodes:
        node.lineno = lineno
        node.colno = colno

      return nodes
    
    def __str__(self):
      return '[cPreprocessorFunction params=%s body=%s]' % (', '.join(self.params), str(self.body))
    

  def __init__(self, cP, cPE, logger = None):
    self.__dict__.update(locals())
  
  def create(self, name, params, body):
    return self.cPreprocessorFunction(name, params, body, self.cP, self.cPE, self.logger)
  

class cPreprocessingEvaluator:
  def __init__(self, cPPP, cP, preProcessorFactory, includePathGlobal = ['.'], includePathLocal = ['.'], logger = None):
    self.__dict__.update(locals())
    self.cLexerContext = None
    self.skipIncludes = False
    self.cPFF = cPreprocessorFunctionFactory(self.cP, self, self.logger)
    self.cPPTtocT = {
      self.cPPP.TERMINAL_DEFINED : self.cP.TERMINAL_DEFINED ,
      self.cPPP.TERMINAL_DEFINED_SEPARATOR : self.cP.TERMINAL_DEFINED_SEPARATOR ,
      self.cPPP.TERMINAL_BITOREQ : self.cP.TERMINAL_BITOREQ ,
      self.cPPP.TERMINAL_OR : self.cP.TERMINAL_OR ,
      self.cPPP.TERMINAL_BITXOREQ : self.cP.TERMINAL_BITXOREQ ,
      self.cPPP.TERMINAL_DIV : self.cP.TERMINAL_DIV ,
      self.cPPP.TERMINAL_AND : self.cP.TERMINAL_AND ,
      self.cPPP.TERMINAL_ELIPSIS : self.cP.TERMINAL_ELIPSIS ,
      self.cPPP.TERMINAL_BITOR : self.cP.TERMINAL_BITOR ,
      self.cPPP.TERMINAL_LSHIFTEQ : self.cP.TERMINAL_LSHIFTEQ ,
      self.cPPP.TERMINAL_BITNOT : self.cP.TERMINAL_BITNOT ,
      self.cPPP.TERMINAL_BITXOR : self.cP.TERMINAL_BITXOR ,
      self.cPPP.TERMINAL_RSHIFTEQ : self.cP.TERMINAL_RSHIFTEQ ,
      self.cPPP.TERMINAL_ARROW : self.cP.TERMINAL_ARROW ,
      self.cPPP.TERMINAL_SUB : self.cP.TERMINAL_SUB ,
      self.cPPP.TERMINAL_RBRACE : self.cP.TERMINAL_RBRACE ,
      self.cPPP.TERMINAL_DOT : self.cP.TERMINAL_DOT ,
      self.cPPP.TERMINAL_LTEQ : self.cP.TERMINAL_LTEQ ,
      self.cPPP.TERMINAL_MODEQ : self.cP.TERMINAL_MODEQ ,
      self.cPPP.TERMINAL_ADDEQ : self.cP.TERMINAL_ADDEQ ,
      self.cPPP.TERMINAL_MULEQ : self.cP.TERMINAL_MULEQ ,
      self.cPPP.TERMINAL_GTEQ : self.cP.TERMINAL_GTEQ ,
      self.cPPP.TERMINAL_RPAREN : self.cP.TERMINAL_RPAREN ,
      self.cPPP.TERMINAL_LT : self.cP.TERMINAL_LT ,
      self.cPPP.TERMINAL_ASSIGN : self.cP.TERMINAL_ASSIGN ,
      self.cPPP.TERMINAL_NEQ : self.cP.TERMINAL_NEQ ,
      self.cPPP.TERMINAL_RSQUARE : self.cP.TERMINAL_RSQUARE ,
      self.cPPP.TERMINAL_LPAREN : self.cP.TERMINAL_LPAREN ,
      self.cPPP.TERMINAL_ADD : self.cP.TERMINAL_ADD ,
      self.cPPP.TERMINAL_POUND : self.cP.TERMINAL_POUND ,
      self.cPPP.TERMINAL_LSQUARE : self.cP.TERMINAL_LSQUARE ,
      self.cPPP.TERMINAL_RSHIFT : self.cP.TERMINAL_RSHIFT ,
      self.cPPP.TERMINAL_COMMA : self.cP.TERMINAL_COMMA ,
      self.cPPP.TERMINAL_EXCLAMATION_POINT : self.cP.TERMINAL_EXCLAMATION_POINT ,
      self.cPPP.TERMINAL_BITANDEQ : self.cP.TERMINAL_BITANDEQ ,
      self.cPPP.TERMINAL_SEMI : self.cP.TERMINAL_SEMI ,
      self.cPPP.TERMINAL_EQ : self.cP.TERMINAL_EQ ,
      self.cPPP.TERMINAL_MOD : self.cP.TERMINAL_MOD ,
      self.cPPP.TERMINAL_COLON : self.cP.TERMINAL_COLON ,
      self.cPPP.TERMINAL_QUESTIONMARK : self.cP.TERMINAL_QUESTIONMARK ,
      self.cPPP.TERMINAL_MUL : self.cP.TERMINAL_ASTERISK ,
      self.cPPP.TERMINAL_IDENTIFIER : self.cP.TERMINAL_IDENTIFIER ,
      self.cPPP.TERMINAL_GT : self.cP.TERMINAL_GT ,
      self.cPPP.TERMINAL_BITAND : self.cP.TERMINAL_BITAND ,
      self.cPPP.TERMINAL_PP_NUMBER : self.cP.TERMINAL_INTEGER_CONSTANT ,
      self.cPPP.TERMINAL_LSHIFT : self.cP.TERMINAL_LSHIFT ,
      self.cPPP.TERMINAL_CHARACTER_CONSTANT : self.cP.TERMINAL_CHARACTER_CONSTANT ,
      self.cPPP.TERMINAL_POUNDPOUND : self.cP.TERMINAL_POUNDPOUND ,
      self.cPPP.TERMINAL_DECR : self.cP.TERMINAL_DECR ,
      self.cPPP.TERMINAL_STRING_LITERAL : self.cP.TERMINAL_STRING_LITERAL ,
      self.cPPP.TERMINAL_SUBEQ : self.cP.TERMINAL_SUBEQ ,
      self.cPPP.TERMINAL_TILDE : self.cP.TERMINAL_TILDE ,
      self.cPPP.TERMINAL_AMPERSAND : self.cP.TERMINAL_AMPERSAND ,
      self.cPPP.TERMINAL_INCR : self.cP.TERMINAL_INCR ,
      self.cPPP.TERMINAL_LBRACE : self.cP.TERMINAL_LBRACE
    }
    self.cTtocPPT = {v: k for k, v in self.cPPTtocT.items()}

  def eval( self, cPPAST, symbols = {} ):
    self.symbols = symbols
    self.line = 1
    return self._eval(cPPAST)

  def getSymbolTable(self):
    return self.symbols

  def newlines(self, number):
    return ''.join(['\n' for i in range(number)])
  
  def _cT_to_cPPT(self, cT_list):
    tokens = []
    for token in cT_list:
      tokens.append(ppToken(self.cTtocPPT[token.id], token.resource, token.terminal_str, token.source_string, token.lineno, token.colno))
    return tokens
  
  def _parseExpr(self, tokens):
    self.cPPP.iterator = iter(tokens)
    self.cPPP.sym = self.cPPP.getsym()
    parsetree = self.cPPP.expr()
    ast = parsetree.toAst()
    value = self._eval(ast)
    if isinstance(value, Token):
      return value
    else:
      return ppToken(self.cPPP.terminal('pp_number'), None, 'pp_number', value, 0, 0)
  
  def _debugStr(self, cPPAST):
    if isinstance(cPPAST, Token):
      string = 'Token (%s) [line %d, col %d]' % (cPPAST.terminal_str.lower(), cPPAST.lineno, cPPAST.colno)
      if cPPAST.terminal_str.lower() not in ['pp_number', 'identifier', 'csource']:
        string = '(unidentified) ' + string
      return string
    if isinstance(cPPAST, list):
      return 'List: [%s]' % (', '.join([self._debugStr(x) for x in cPPAST]))
    if isinstance(cPPAST, ppAst):
      return 'Ast: %s' % (cPPAST.name)
  
  def _getCSourceMacroFunctionParams(self, cLexer):
    # returns PP tokens
    next(cLexer) # skip lparen
    lparen = 1
    buf = []
    params = []
    for paramToken, plookahead in cLexer:
      paramTokenStr = paramToken.terminal_str.lower()
      if paramTokenStr == 'lparen':
        lparen += 1
      if paramTokenStr == 'rparen':
        lparen -= 1
      if (paramTokenStr == 'rparen' and lparen == 0) or (paramTokenStr == 'comma' and lparen == 1):
        params.append( buf )
        buf = []
      else:
        # TODO: this line is kind of messy
        token = ppLexer(SourceCodeEmpty(paramToken.getResource())).matchString(paramToken.getString())
        token.fromPreprocessor = True
        buf.append(token)
      if paramTokenStr == 'rparen' and lparen == 0:
        break
    return params
  
  def _tokenToCToken(self, token):
    if token.type == 'c':
      return copy(token)
    newId = self.cPPTtocT[token.id]
    return cToken( newId, token.resource, cParser.terminal_str[newId], token.source_string, token.lineno, token.colno, None )
  
  def _eval( self, cPPAST ):
    rtokens = TokenList()
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
          return self._parseExpr( self._cT_to_cPPT(x) )
      except TypeError:
        return x
    elif isinstance(cPPAST, Token) and cPPAST.terminal_str.lower() == 'csource':
      tokens = []
      params = []
      advance = 0

      sourceCode = SourceCodeString( cPPAST.getResource(), cPPAST.getString(), cPPAST.getLine(), cPPAST.getColumn())

      cLex = cLexer(sourceCode)
      if self.cLexerContext:
        cLex.setContext(self.cLexerContext)
      cTokens = list(cLex)
      self.cLexerContext = cLex.getContext()
      cLexerWithLookahead = zip_longest(cTokens, cTokens[1:])

      for token, lookahead in cLexerWithLookahead:
        if token.terminal_str.lower() == 'identifier' and token.getString() in self.symbols:
          replacement = self.symbols[token.getString()]
          if isinstance(replacement, self.cPFF.cPreprocessorFunction):
            if lookahead.getString() != '(':
              if not isinstance(token, list):
                tmptoken = [token]
              else:
                tmptoken = token
              tokens.extend(tmptoken)
              continue
            else:
              params = self._getCSourceMacroFunctionParams(cLexerWithLookahead)
              result = replacement.run(params, token.lineno, token.colno)
              tokens.extend(result)
          elif isinstance(replacement, list):
            tmp = []
            for (replacement_token, next_token) in zip_longest(replacement, replacement[1:]):
              if not next_token:
                if isinstance(replacement_token, self.cPFF.cPreprocessorFunction) and \
                   lookahead.getString() == '(':
                   params = self._getCSourceMacroFunctionParams(cLexerWithLookahead)
                   result = replacement_token.run(params, token.lineno, token.colno)
                   tmp.extend(result)
                   break
              new_token = self._tokenToCToken(replacement_token)
              new_token.colno = token.colno
              new_token.lineno = token.lineno
              if new_token.id == ppParser.TERMINAL_PP_NUMBER:
                new_token.id = cParser.TERMINAL_INTEGER_CONSTANT
              tmp.append(new_token)
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
          self._log('IFDEF (true)', str(ident))
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
        if self.skipIncludes:
          return list()
        filename = cPPAST.getAttr('file').getString()
        if (filename[0], filename[-1]) == ('"', '"'):
          filename = filename.strip('"')
          for directory in self.includePathLocal:
            path = os.path.join( directory, filename )
            if os.path.isfile( path ):
              self.line += 1
              includePath = copy(self.includePathLocal)
              includePath.append( os.path.dirname(path) )
              preprocessor = self.preProcessorFactory.create(self.includePathGlobal, includePath)
              sourceCode = SourceCode( path, open(path) )
              (tokens, symbolTable) = preprocessor.process( sourceCode, self.symbols )
              self.symbols = symbolTable
              return tokens
          raise NameError(filename + ' not found in include path')
        elif (filename[0], filename[-1]) == ('<', '>'):
          filename = filename.strip('<>')
          for directory in self.includePathGlobal:
            path = os.path.join( directory, filename )
            if os.path.isfile( path ):
              self.line += 1
              includePath = copy(self.includePathLocal)
              includePath.append( os.path.dirname(path) )
              preprocessor = self.preProcessorFactory.create(self.includePathGlobal, includePath)
              sourceCode = SourceCode( path, open(path) )
              (tokens, symbolTable) = preprocessor.process( sourceCode, self.symbols )
              self.symbols = symbolTable
              return tokens
          raise NameError(filename + ' not found in include path')
        else:
          raise NameError('invalid include type')
      elif cPPAST.name == 'Define':
        ident = cPPAST.getAttr('ident')
        body = cPPAST.getAttr('body')
        self.symbols[ident.getString()] = self._eval(body)
        self.line += 1
      elif cPPAST.name == 'DefineFunction':
        ident = cPPAST.getAttr('ident')
        params = cPPAST.getAttr('params')
        body = cPPAST.getAttr('body')
        self.symbols[ident.getString()] = self.cPFF.create( ident, [p.getString() for p in params], body )
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
        # This means: return the replacement with macros replaced.
        # e.g. #define bar 2
        #      #define var 1 bar 3
        # eval( ReplacementList([1, bar, 3]) ) = ReplacementList([1, 2, 3])
        # input and output tokens are ctokens.
        
        # If tokens are not ctokens, convert them!
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
            if isinstance(replacement, self.cPFF.cPreprocessorFunction):
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
                      value = param_tokens
                      params.append(param_tokens)
                      break
                    lparen_count -= 1
                    param_tokens.append(self._tokenToCToken(token))
                  elif token.getString() == ',' and lparen_count == 1:
                    if len(param_tokens):
                      value = param_tokens
                      params.append(param_tokens)
                      param_tokens = []
                  else:
                    param_tokens.append(self._tokenToCToken(token))
                  advance += 1
                result = replacement.run(params, token.lineno, token.colno)
                newTokens.extend(result)
              else:
                newTokens.append(self._tokenToCToken(token))
            else:
              newTokens.extend( self.symbols[token.getString()] )
          else:
            newTokens.append(self._tokenToCToken(token))
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
        numstr = numstr.split( 'e' if 'e' in numstr else 'E' )
        num = int(numstr[0], self._base(numstr[0])) ** int(numstr[1], self._base(numstr[1]))
      elif 'p' in numstr or 'P' in numstr:
        numstr = numstr.split( 'p' if 'p' in numstr else 'P' )
        num = int(numstr[0], self._base(numstr[0])) * (2 ** int(numstr[1], self._base(numstr[1])))
      else:
        num = int(numstr, self._base(numstr))
      return num
    elif isinstance(element, list):
      if len(element):
        return int(element[0])
      return 0
    else:
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
    if self.logger:
      for t in self.cT:
        self.logger.log('token', str(t))
    return cT
    parsetree = self.cP.parse( self.cT, 'translation_unit' )
    ast = parsetree.toAst()
    return ast
