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

    tokenConvert = ['ADD', 'ADDEQ', 'AMPERSAND', 'AND', 'ARROW', 'ASSIGN', 'BITAND', 'BITANDEQ', 'BITNOT', 'BITOR', 'BITOREQ', 'BITXOR', 'BITXOREQ', 'CHARACTER_CONSTANT', 'COLON', 'COMMA', 'DECR', 'DEFINED', 'DEFINED_SEPARATOR', 'DIV', 'DOT', 'ELIPSIS', 'EQ', 'EXCLAMATION_POINT', 'GT', 'GTEQ', 'IDENTIFIER', 'INCR', 'LBRACE', 'LPAREN', 'LSHIFT', 'LSHIFTEQ', 'LSQUARE', 'LT', 'LTEQ', 'MOD', 'MODEQ', 'MUL', 'MULEQ', 'NEQ', 'OR', 'POUND', 'POUNDPOUND', 'PP_NUMBER', 'QUESTIONMARK', 'RBRACE', 'RPAREN', 'RSHIFT', 'RSHIFTEQ', 'RSQUARE', 'SEMI', 'STRING_LITERAL', 'SUB', 'SUBEQ', 'TILDE']
    tokenMap = dict(zip(tokenConvert, tokenConvert))
    tokenMap['MUL'] = 'ASTERISK'
    tokenMap['PP_NUMBER'] = 'INTEGER_CONSTANT'
    self.cPPTtocT = dict()
    self.cTtocPPT = dict()
    for pp_token, c_token in tokenMap.items():
      ppVarName = 'TERMINAL_' + pp_token
      cVarName = 'TERMINAL_' + c_token
      self.cPPTtocT[ppParser.__dict__[ppVarName]] = cParser.__dict__[cVarName]
      self.cTtocPPT[cParser.__dict__[cVarName]] = ppParser.__dict__[ppVarName]

  def eval( self, cPPAST, symbols = {} ):
    self.symbols = symbols
    self.line = 1
    return self._eval(cPPAST)

  def getSymbolTable(self):
    return self.symbols
  
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
  
  def _getCSourceMacroFunctionParams(self, cLexer):
    lparen = 0
    buf = []
    params = []

    for token, plookahead in cLexer:

      if token.id == cParser.TERMINAL_LPAREN:
        lparen += 1
        if lparen == 1:
          continue

      if token.id == cParser.TERMINAL_RPAREN:
        lparen -= 1

      if (token.id == cParser.TERMINAL_RPAREN and lparen == 0) or (token.id == cParser.TERMINAL_COMMA and lparen == 1):
        params.append( buf )
        buf = []
      else:
        token = ppLexer(SourceCodeEmpty(token.getResource())).matchString(token.getString())
        token.fromPreprocessor = True
        buf.append(token)

      if token.id == cParser.TERMINAL_RPAREN and lparen == 0:
        break

    return params
  
  def _tokenToCToken(self, token):
    if token.type == 'c':
      return copy(token)
    newId = self.cPPTtocT[token.id]
    return cToken( newId, token.resource, cParser.terminal_str[newId], token.source_string, token.lineno, token.colno, None )
 
  def evalInt( self, tree, attr ):
    return int(self.ppnumber(self._eval(tree.getAttr(attr))))

  def _eval( self, cPPAST ):
    if self.logger:
      for symbol, replacement in self.symbols.items():
        if isinstance(replacement, list):
          replacementList = '[%s]' % (', '.join([str(x) for x in replacement]))
        else:
          replacementList = str(replacement)

    tokenActions = {
      ppParser.TERMINAL_PP_NUMBER: self.eval_ppNumber,
      ppParser.TERMINAL_IDENTIFIER: self.eval_identifier,
      ppParser.TERMINAL_CSOURCE: self.eval_cSource
    }

    astActions = {
      'PPFile': self.eval_PPFile,
      'IfSection': self.eval_IfSection,
      'If': self.eval_If,
      'IfDef': self.eval_IfDef,
      'IfNDef': self.eval_IfNDef,
      'ElseIf': self.eval_ElseIf,
      'Else': self.eval_Else,
      'Include': self.eval_Include,
      'Define': self.eval_Define,
      'DefineFunction': self.eval_DefineFunction,
      'Pragma': self.eval_Pragma,
      'Error': self.eval_Error,
      'Warning': self.eval_Warning,
      'Undef': self.eval_Undef,
      'Line': self.eval_Line,
      'ReplacementList': self.eval_ReplacementList,
      'identifier': self.eval_identifier,
      'FuncCall': self.eval_FuncCall,
      'IsDefined': self.eval_IsDefined,
      'Add': self.eval_Add,
      'Sub': self.eval_Sub,
      'LessThan': self.eval_LessThan,
      'GreaterThan': self.eval_GreaterThan,
      'LessThanEq': self.eval_LessThanEq,
      'GreaterThanEq': self.eval_GreaterThanEq,
      'Mul': self.eval_Mul,
      'Div': self.eval_Div,
      'Mod': self.eval_Mod,
      'Equals': self.eval_Equals,
      'NotEquals': self.eval_NotEquals,
      'Comma': self.eval_Comma,
      'LeftShift': self.eval_LeftShift,
      'RightShift': self.eval_RightShift,
      'BitAND': self.eval_BitAND,
      'BitOR': self.eval_BitOR,
      'BitXOR': self.eval_BitXOR,
      'BitNOT': self.eval_BitNOT,
      'And': self.eval_And,
      'Or': self.eval_Or,
      'Not': self.eval_Not,
      'TernaryOperator': self.eval_TernaryOperator
    }

    if not cPPAST:
      return []

    if isinstance(cPPAST, Token):
      try:
        actionFunction = tokenActions[cPPAST.id]
      except KeyError:
        raise Exception('Bad AST Node')
      return actionFunction(cPPAST)

    elif isinstance(cPPAST, list):
      rtokens = TokenList()
      if cPPAST and len(cPPAST):
        for node in cPPAST:
          result = self._eval(node)
          if isinstance(result, list):
            rtokens.extend(result)
          elif result:
            rtokens.append(result)
      return rtokens

    elif isinstance(cPPAST, ppAst):
      try:
        actionFunction = astActions[cPPAST.name]
      except KeyError:
        raise Exception('Bad AST Node')
      return actionFunction(cPPAST)
    else:
      raise Exception('Bad AST Node')

  def eval_ppNumber(self, cPPAST):
    return self.ppnumber(cPPAST)

  def eval_identifier(self, cPPAST):
    replacementList = TokenList()
    if cPPAST.getString() in self.symbols:
      replacementList = self.symbols[cPPAST.getString()]
   
    def tokenize(token):
      tId = self.cTtocPPT[token.id]
      return ppToken(tId, token.resource, ppParser.terminal_str[tId], token.source_string, token.lineno, token.colno)

    return self._parseExpr( list(map(tokenize, replacementList)) )

  def eval_cSource(self, cPPAST):
    tokens = TokenList()

    cLex = cLexer(SourceCodeString(cPPAST.getResource(), cPPAST.getString(), cPPAST.getLine(), cPPAST.getColumn()))
    if self.cLexerContext:
      cLex.setContext(self.cLexerContext)
    cTokens = list(cLex)
    self.cLexerContext = cLex.getContext()
    cLexerWithLookahead = zip_longest(cTokens, cTokens[1:])

    for token, lookahead in cLexerWithLookahead:
      if token.id == cParser.TERMINAL_IDENTIFIER and token.getString() in self.symbols:
        replacement = self.symbols[token.getString()]
        if isinstance(replacement, self.cPFF.cPreprocessorFunction):
          if lookahead.id != cParser.TERMINAL_LPAREN:
            tokens.append(token)
            continue
          else:
            params = self._getCSourceMacroFunctionParams(cLexerWithLookahead)
            result = replacement.run(params, token.lineno, token.colno)
            tokens.extend(result)
        elif isinstance(replacement, list):
          tmp = []
          for (rtoken, next_rtoken) in zip_longest(replacement, replacement[1:]):
            if not next_rtoken:
              if isinstance(rtoken, self.cPFF.cPreprocessorFunction) and lookahead.id == cParser.TERMINAL_LPAREN:
                 params = self._getCSourceMacroFunctionParams(cLexerWithLookahead)
                 result = rtoken.run(params, token.lineno, token.colno)
                 tmp.extend(result)
                 break
            new_token = self._tokenToCToken(rtoken)
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

    self.line += len(list(filter(lambda x: x == '\n', cPPAST.getString()))) + 1
    return tokens
  
  def eval_PPFile(self, cPPAST):
    nodes = cPPAST.getAttr('nodes')
    return self._eval(nodes)

  def eval_IfSection(self, cPPAST):
    rtokens = TokenList()
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

  def eval_If(self, cPPAST):
    expr = cPPAST.getAttr('expr')
    nodes = cPPAST.getAttr('nodes')
    if self._eval(expr) != 0:
      return self._eval(nodes)
    else:
      self.line += self.countSourceLines(nodes)
    return None

  def eval_IfDef(self, cPPAST):
    ident = cPPAST.getAttr('ident').getString()
    nodes = cPPAST.getAttr('nodes')
    if ident in self.symbols:
      return self._eval(nodes)
    else:
      self.line += self.countSourceLines(nodes)
    return None

  def eval_IfNDef(self, cPPAST):
    ident = cPPAST.getAttr('ident').getString()
    nodes = cPPAST.getAttr('nodes')
    if ident not in self.symbols:
      return self._eval(nodes)
    else:
      self.line += self.countSourceLines(nodes)
    return None

  def eval_ElseIf(self, cPPAST):
    expr = cPPAST.getAttr('expr')
    nodes = cPPAST.getAttr('nodes')
    if self._eval(expr) != 0:
      return self._eval(nodes)
    else:
      self.line += self.countSourceLines(nodes)
    return None

  def eval_Else(self, cPPAST):
    nodes = cPPAST.getAttr('nodes')
    return self._eval(nodes)

  def eval_Include(self, cPPAST):
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

  def eval_Define(self, cPPAST):
    ident = cPPAST.getAttr('ident')
    body = cPPAST.getAttr('body')
    self.symbols[ident.getString()] = self._eval(body)
    self.line += 1

  def eval_DefineFunction(self, cPPAST):
    ident = cPPAST.getAttr('ident')
    params = cPPAST.getAttr('params')
    body = cPPAST.getAttr('body')
    self.symbols[ident.getString()] = self.cPFF.create( ident, [p.getString() for p in params], body )
    self.line += 1

  def eval_Pragma(self, cPPAST):
    # TODO: implement
    cPPAST.getAttr('tokens')
    self.line += 1

  def eval_Error(self, cPPAST):
    # TODO: implement
    cPPAST.getAttr('tokens')
    self.line += 1

  def eval_Warning(self, cPPAST):
    # TODO: implement
    cPPAST.getAttr('tokens')
    self.line += 1

  def eval_Undef(self, cPPAST):
    ident = cPPAST.getAttr('ident').getString()
    if ident in self.symbols:
      del self.symbols[ident]
    self.line += 1

  def eval_Line(self, cPPAST):
    cPPAST.getAttr('tokens')
    self.line += 1

  def eval_ReplacementList(self, cPPAST):
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

  def eval_FuncCall(self, cPPAST):
    name = cPPAST.getAttr('name')
    params = cPPAST.getAttr('params')

  def eval_IsDefined(self, cPPAST):
    return cPPAST.getAttr('expr').getString() in self.symbols

  def eval_Add(self, cPPAST):
    return self.evalInt(cPPAST, 'left') + self.evalInt(cPPAST, 'right')

  def eval_Sub(self, cPPAST):
    return self.evalInt(cPPAST, 'left') - self.evalInt(cPPAST, 'right')

  def eval_LessThan(self, cPPAST):
    return self.evalInt(cPPAST, 'left') < self.evalInt(cPPAST, 'right')

  def eval_GreaterThan(self, cPPAST):
    return self.evalInt(cPPAST, 'left') > self.evalInt(cPPAST, 'right')

  def eval_LessThanEq(self, cPPAST):
    return self.evalInt(cPPAST, 'left') <= self.evalInt(cPPAST, 'right')

  def eval_GreaterThanEq(self, cPPAST):
    return self.evalInt(cPPAST, 'left') >= self.evalInt(cPPAST, 'right')

  def eval_Mul(self, cPPAST):
    return self.evalInt(cPPAST, 'left') * self.evalInt(cPPAST, 'right')

  def eval_Div(self, cPPAST):
    return self.evalInt(cPPAST, 'left') / self.evalInt(cPPAST, 'right')

  def eval_Mod(self, cPPAST):
    return self.evalInt(cPPAST, 'left') % self.evalInt(cPPAST, 'right')

  def eval_Equals(self, cPPAST):
    return self.evalInt(cPPAST, 'left') == self.evalInt(cPPAST, 'right')

  def eval_NotEquals(self, cPPAST):
    return self.evalInt(cPPAST, 'left') != self.evalInt(cPPAST, 'right')

  def eval_Comma(self, cPPAST):
    self._eval(left)
    return self.evalInt(cPPAST, 'right')

  def eval_LeftShift(self, cPPAST):
    return self.evalInt(cPPAST, 'left') << self.evalInt(cPPAST, 'right')

  def eval_RightShift(self, cPPAST):
    return self.evalInt(cPPAST, 'left') >> self.evalInt(cPPAST, 'right')

  def eval_BitAND(self, cPPAST):
    return self.evalInt(cPPAST, 'left') & self.evalInt(cPPAST, 'right')

  def eval_BitOR(self, cPPAST):
    return self.evalInt(cPPAST, 'left') | self.evalInt(cPPAST, 'right')

  def eval_BitXOR(self, cPPAST):
    return self.evalInt(cPPAST, 'left') ^ self.evalInt(cPPAST, 'right')

  def eval_BitNOT(self, cPPAST):
    return ~self.evalInt(cPPAST, 'expr')

  def eval_And(self, cPPAST):
    return self.evalInt(cPPAST, 'left') and self.evalInt(cPPAST, 'right')

  def eval_Or(self, cPPAST):
    return self.evalInt(cPPAST, 'left') or self.evalInt(cPPAST, 'right')

  def eval_Not(self, cPPAST):
    return not self.evalInt(cPPAST, 'expr')

  def eval_TernaryOperator(self, cPPAST):
    if self.evalInt(cPPAST, 'cond'):
      return self.evalInt(cPPAST, 'true')
    else:
      return self.evalInt(cPPAST, 'false')

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
