import re
from cast.Lexer import PatternMatchingLexer
from cast.Token import cToken, TokenList
from cast.cParser import Parser as cParser

def parseIdentifier( string, lineno, colno, terminalId, lexer ):
  addedToken = token( string, lineno, colno, terminalId, lexer)
  if addedToken.source_string in lexer.typedefs:
    tId = cParser.TERMINAL_TYPEDEF_IDENTIFIER
    addedToken.id = tId
    addedToken.terminal_str = cParser.terminals[tId]
  else:
    lexer.lastIdentifier = addedToken

def parseLabelIdentifier( string, lineno, colno, terminalId, lexer ):
  hintId = cParser.TERMINAL_LABEL_HINT
  ctx = lexer.getContext()
  lexer.addToken(cToken(hintId, lexer.resource, cParser.terminals[hintId], '', lineno, colno, context=ctx))
  lexer.addToken(cToken(terminalId, lexer.resource, cParser.terminals[terminalId], string, lineno, colno, context=ctx))

def parseTypedef( string, lineno, colno, terminalId, lexer ):
  lexer.typedefBlocks = lexer.typedefBlocks.union({(lexer.braceLevel, lexer.parenLevel)})
  token( string, lineno, colno, terminalId, lexer )
  
def parseLbrace( string, lineno, colno, terminalId, lexer ):
  lexer.braceLevel += 1
  token( string, lineno, colno, terminalId, lexer )

def parseRbrace( string, lineno, colno, terminalId, lexer ):
  lexer.braceLevel -= 1
  token( string, lineno, colno, terminalId, lexer )
  if (cParser.TERMINAL_RBRACE, lexer.braceLevel) in lexer.endifTokens:
    lexer.endifTokens = lexer.endifTokens.difference({(cParser.TERMINAL_RBRACE, lexer.braceLevel)})
    token('', lineno, colno, cParser.TERMINAL_ENDIF, lexer)

def parseLparenCast( string, lineno, colno, terminalId, lexer ):
  lexer.parenLevel += 1
  if lexer.braceLevel == 0:
    token( string, lineno, colno, cParser.TERMINAL_LPAREN, lexer )
  else:
    token( string, lineno, colno, cParser.TERMINAL_LPAREN_CAST, lexer )

def parseLparen( string, lineno, colno, terminalId, lexer ):
  lexer.parenLevel += 1
  token( string, lineno, colno, terminalId, lexer )

def parseRparen( string, lineno, colno, terminalId, lexer ):
  lexer.parenLevel -= 1
  token( string, lineno, colno, terminalId, lexer )
  if lexer.isIf():
    lexer.addEndif()

def parseIf( string, lineno, colno, terminalId, lexer ):
  token( string, lineno, colno, terminalId, lexer )
  lexer.markIf()

def parseElse( string, lineno, colno, terminalId, lexer ):
  token( string, lineno, colno, terminalId, lexer )
  lexer.addEndif()

def parseSemi( string, lineno, colno, terminalId, lexer ):
  token( string, lineno, colno, terminalId, lexer )
  if (cParser.TERMINAL_SEMI, lexer.braceLevel,) in lexer.endifTokens:
    lexer.endifTokens = lexer.endifTokens.difference({(cParser.TERMINAL_SEMI, lexer.braceLevel)})
    token('', lineno, colno, cParser.TERMINAL_ENDIF, lexer)
  if (lexer.braceLevel, lexer.parenLevel) in lexer.typedefBlocks:
    lexer.typedefBlocks = lexer.typedefBlocks.difference({(lexer.braceLevel, lexer.parenLevel)})
    tId = cParser.TERMINAL_TYPEDEF_IDENTIFIER
    if lexer.lastIdentifier:
      lexer.typedefs[lexer.lastIdentifier.source_string] = cToken(tId, lexer.resource, cParser.terminals[tId], lexer.lastIdentifier.source_string, lineno, colno, lexer.getContext())
    else:
      raise Exception('no last identifier')

def parseComma( string, lineno, colno, terminalId, lexer ):
  token( string, lineno, colno, terminalId, lexer )
  if (lexer.braceLevel, lexer.parenLevel) in lexer.typedefBlocks:
    tId = cParser.TERMINAL_TYPEDEF_IDENTIFIER
    if lexer.lastIdentifier:
      lexer.typedefs[lexer.lastIdentifier.source_string] = cToken(tId, lexer.resource, cParser.terminals[tId], lexer.lastIdentifier.source_string, lineno, colno, lexer.getContext())
    else:
      raise Exception('no last identifier')

decls = None
def declaration_specifiers():
  global decls
  if not decls:
    c = lambda x: cParser.terminals[x]
    # decls = set(map(c, ['typedef','extern','static','auto','register','void','char','short','int','long','float','double','signed','unsigned','bool','complex','imaginary','struct','union','enum','typedef_identifier','const','restrict','volatile','inline']))
    decls = { 
      c('typedef'),  c('extern'), c('static'), c('auto'), \
      c('register'), c('void'), c('char'), c('short'), c('int'), \
      c('long'), c('float'), c('double'), c('signed'), c('unsigned'), \
      c('bool'), c('complex'), c('imaginary'), c('struct'), c('union'), c('enum'), \
      c('typedef_identifier'), c('const'), c('restrict'), c('volatile'), \
      c('inline')
    }
  return decls

def token(string, lineno, colno, terminalId, lexer):
  matchedToken = cToken(terminalId, lexer.resource, cParser.terminals[terminalId], string, lineno, colno, lexer.getContext())
  lexer.addToken(matchedToken)
  return matchedToken

identifierRegex = r'([a-zA-Z_]|\\[uU]([0-9a-fA-F]{4})([0-9a-fA-F]{4})?)([a-zA-Z_0-9]|\\[uU]([0-9a-fA-F]{4})([0-9a-fA-F]{4})?)*'

class cLexer(PatternMatchingLexer):
  type_specifier = ['void', 'char', 'short', 'int', 'long', 'float', 'double', 'signed', 'unsigned', '_Bool', '_Complex']
  cRegex = [
      # Comments
      ( re.compile(r'/\*.*?\*/', re.S), None, None ),
      ( re.compile(r'//.*', 0), None, None ),

      # Keywords
      ( re.compile(r'auto(?=[^a-zA-Z_])'), cParser.TERMINAL_AUTO, token ),
      ( re.compile(r'_Bool(?=[^a-zA-Z_])'), cParser.TERMINAL_BOOL, token ),
      ( re.compile(r'break(?=[^a-zA-Z_])'), cParser.TERMINAL_BREAK, token ),
      ( re.compile(r'case(?=[^a-zA-Z_])'), cParser.TERMINAL_CASE, token ),
      ( re.compile(r'char(?=[^a-zA-Z_])'), cParser.TERMINAL_CHAR, token ),
      ( re.compile(r'_Complex(?=[^a-zA-Z_])'), cParser.TERMINAL_COMPLEX, token ),
      ( re.compile(r'const(?=[^a-zA-Z_])'), cParser.TERMINAL_CONST, token ),
      ( re.compile(r'continue(?=[^a-zA-Z_])'), cParser.TERMINAL_CONTINUE, token ),
      ( re.compile(r'default(?=[^a-zA-Z_])'), cParser.TERMINAL_DEFAULT, token ),
      ( re.compile(r'do(?=[^a-zA-Z_])'), cParser.TERMINAL_DO, token ),
      ( re.compile(r'double(?=[^a-zA-Z_])'), cParser.TERMINAL_DOUBLE, token ),
      ( re.compile(r'else\s+if(?=[^a-zA-Z_])'), cParser.TERMINAL_ELSE_IF, parseIf ),
      ( re.compile(r'else(?=[^a-zA-Z_])'), cParser.TERMINAL_ELSE, parseElse ),
      ( re.compile(r'enum(?=[^a-zA-Z_])'), cParser.TERMINAL_ENUM, token ),
      ( re.compile(r'extern(?=[^a-zA-Z_])'), cParser.TERMINAL_EXTERN, token ),
      ( re.compile(r'float(?=[^a-zA-Z_])'), cParser.TERMINAL_FLOAT, token ),
      ( re.compile(r'for(?=[^a-zA-Z_])'), cParser.TERMINAL_FOR, token ),
      ( re.compile(r'goto(?=[^a-zA-Z_])'), cParser.TERMINAL_GOTO, token ),
      ( re.compile(r'if(?=[^a-zA-Z_])'), cParser.TERMINAL_IF, parseIf ),
      ( re.compile(r'_Imaginary(?=[^a-zA-Z_])'), cParser.TERMINAL_IMAGINARY, token ),
      ( re.compile(r'inline(?=[^a-zA-Z_])'), cParser.TERMINAL_INLINE, token ),
      ( re.compile(r'int(?=[^a-zA-Z_])'), cParser.TERMINAL_INT, token ),
      ( re.compile(r'long(?=[^a-zA-Z_])'), cParser.TERMINAL_LONG, token ),
      ( re.compile(r'register(?=[^a-zA-Z_])'), cParser.TERMINAL_REGISTER, token ),
      ( re.compile(r'restrict(?=[^a-zA-Z_])'), cParser.TERMINAL_RESTRICT, token ),
      ( re.compile(r'return(?=[^a-zA-Z_])'), cParser.TERMINAL_RETURN, token ),
      ( re.compile(r'short(?=[^a-zA-Z_])'), cParser.TERMINAL_SHORT, token ),
      ( re.compile(r'signed(?=[^a-zA-Z_])'), cParser.TERMINAL_SIGNED, token ),
      ( re.compile(r'sizeof(?=[^a-zA-Z_])'), cParser.TERMINAL_SIZEOF, token ),
      ( re.compile(r'static(?=[^a-zA-Z_])'), cParser.TERMINAL_STATIC, token ),
      ( re.compile(r'struct(?=[^a-zA-Z_])'), cParser.TERMINAL_STRUCT, token ),
      ( re.compile(r'switch(?=[^a-zA-Z_])'), cParser.TERMINAL_SWITCH, token ),
      ( re.compile(r'typedef(?=[^a-zA-Z_])'), cParser.TERMINAL_TYPEDEF, parseTypedef ),
      ( re.compile(r'union(?=[^a-zA-Z_])'), cParser.TERMINAL_UNION, token ),
      ( re.compile(r'unsigned(?=[^a-zA-Z_])'), cParser.TERMINAL_UNSIGNED, token ),
      ( re.compile(r'void(?=[^a-zA-Z_])'), cParser.TERMINAL_VOID, token ),
      ( re.compile(r'volatile(?=[^a-zA-Z_])'), cParser.TERMINAL_VOLATILE, token ),
      ( re.compile(r'while(?=[^a-zA-Z_])'), cParser.TERMINAL_WHILE, token ),

      # Identifiers
      ( re.compile('%s(?=\s*:)' % (identifierRegex)), cParser.TERMINAL_IDENTIFIER, parseLabelIdentifier ),
      ( re.compile(identifierRegex), cParser.TERMINAL_IDENTIFIER, parseIdentifier ),

      # Unicode Characters
      ( re.compile(r'\\[uU]([0-9a-fA-F]{4})([0-9a-fA-F]{4})?'), cParser.TERMINAL_UNIVERSAL_CHARACTER_NAME, token ),

      # Digraphs
      ( re.compile(r'<%'), cParser.TERMINAL_LBRACE, token ),
      ( re.compile(r'%>'), cParser.TERMINAL_RBRACE, token ),
      ( re.compile(r'<:'), cParser.TERMINAL_LSQUARE, token ),
      ( re.compile(r':>'), cParser.TERMINAL_RSQUARE, token ),
      ( re.compile(r'%:%:'), cParser.TERMINAL_POUNDPOUND, token ),
      ( re.compile(r'%:'), cParser.TERMINAL_POUND, token ),

      # Punctuators
      ( re.compile(r'\['), cParser.TERMINAL_LSQUARE, token ),
      ( re.compile(r'\]'), cParser.TERMINAL_RSQUARE, token ),
      ( re.compile(r'\((?=\s*' + 'void[\s]*\))'), cParser.TERMINAL_LPAREN, parseLparen ),
      #( re.compile(r'\((?=\s*' + '(' +'|'.join(type_specifier) + ')[\*\s]*\))'), cParser.TERMINAL_LPAREN_CAST, parseLparenCast ),
      ( re.compile(r'\('), cParser.TERMINAL_LPAREN, parseLparen ),
      ( re.compile(r'\)'), cParser.TERMINAL_RPAREN, parseRparen ),
      ( re.compile(r'\{'), cParser.TERMINAL_LBRACE, parseLbrace ),
      ( re.compile(r'\}'), cParser.TERMINAL_RBRACE, parseRbrace ),
      ( re.compile(r'\.\.\.'), cParser.TERMINAL_ELIPSIS, token ),
      ( re.compile(r'\.'), cParser.TERMINAL_DOT, token ),
      ( re.compile(r'->'), cParser.TERMINAL_ARROW, token ),
      ( re.compile(r'\+\+'), cParser.TERMINAL_INCR, token ),
      ( re.compile(r'--'), cParser.TERMINAL_DECR, token ),
      ( re.compile(r'&(?!&)'), cParser.TERMINAL_BITAND, token ),
      ( re.compile(r'\*(?!=)'), cParser.TERMINAL_ASTERISK, token ),
      ( re.compile(r'\+(?!=)'), cParser.TERMINAL_ADD, token ),
      ( re.compile(r'-(?!=)'), cParser.TERMINAL_SUB, token ),
      ( re.compile(r'~'), cParser.TERMINAL_TILDE, token ),
      ( re.compile(r'!(?!=)'), cParser.TERMINAL_EXCLAMATION_POINT, token ),
      ( re.compile(r'/(?!=)'), cParser.TERMINAL_DIV, token ),
      ( re.compile(r'%(?!=)'), cParser.TERMINAL_MOD, token ),
      ( re.compile(r'<<(?!=)'), cParser.TERMINAL_LSHIFT, token ),
      ( re.compile(r'>>(?!=)'), cParser.TERMINAL_RSHIFT, token ),
      ( re.compile(r'<(?!=)'), cParser.TERMINAL_LT, token ),
      ( re.compile(r'>(?!=)'), cParser.TERMINAL_GT, token ),
      ( re.compile(r'<='), cParser.TERMINAL_LTEQ, token ),
      ( re.compile(r'>='), cParser.TERMINAL_GTEQ, token ),
      ( re.compile(r'=='), cParser.TERMINAL_EQ, token ),
      ( re.compile(r'!='), cParser.TERMINAL_NEQ, token ),
      ( re.compile(r'\^(?!=)'), cParser.TERMINAL_BITXOR, token ),
      ( re.compile(r'\|(?!\|)'), cParser.TERMINAL_BITOR, token ),
      ( re.compile(r'&&'), cParser.TERMINAL_AND, token ),
      ( re.compile(r'\|\|'), cParser.TERMINAL_OR, token ),
      ( re.compile(r'\?'), cParser.TERMINAL_QUESTIONMARK, token ),
      ( re.compile(r':'), cParser.TERMINAL_COLON, token ),
      ( re.compile(r';'), cParser.TERMINAL_SEMI, parseSemi ),
      ( re.compile(r'=(?!=)'), cParser.TERMINAL_ASSIGN, token ),
      ( re.compile(r'\*='), cParser.TERMINAL_MULEQ, token ),
      ( re.compile(r'/='), cParser.TERMINAL_DIVEQ, token ),
      ( re.compile(r'%='), cParser.TERMINAL_MODEQ, token ),
      ( re.compile(r'\+='), cParser.TERMINAL_ADDEQ, token ),
      ( re.compile(r'-='), cParser.TERMINAL_SUBEQ, token ),
      ( re.compile(r'<<='), cParser.TERMINAL_LSHIFTEQ, token ),
      ( re.compile(r'>>='), cParser.TERMINAL_RSHIFTEQ, token ),
      ( re.compile(r'&='), cParser.TERMINAL_BITANDEQ, token ),
      ( re.compile(r'\^='), cParser.TERMINAL_BITXOREQ, token ),
      ( re.compile(r'\|='), cParser.TERMINAL_BITOREQ, token ),
      ( re.compile(r',(?=\s*})'), cParser.TERMINAL_TRAILING_COMMA, token ),
      ( re.compile(r',(?=\s*\.\.\.)'), cParser.TERMINAL_COMMA_VA_ARGS, token ),
      ( re.compile(r','), cParser.TERMINAL_COMMA, parseComma ),
      ( re.compile(r'##'), cParser.TERMINAL_POUNDPOUND, token ),
      ( re.compile(r'#(?!#)'), cParser.TERMINAL_POUND, token ),

      # Constants, Literals
      ( re.compile(r'(([0-9]+)?\.([0-9]+)|[0-9]+\.)([eE][-+]?[0-9]+)?[flFL]?'), cParser.TERMINAL_DECIMAL_FLOATING_CONSTANT, token ),
      ( re.compile(r'[L]?"([^\\\"\n]|\\[\\"\'nrbtfav\?]|\\[0-7]{1,3}|\\x[0-9a-fA-F]+|\\[uU]([0-9a-fA-F]{4})([0-9a-fA-F]{4})?)*"'), cParser.TERMINAL_STRING_LITERAL, token ),
      ( re.compile(r'([1-9][0-9]*|0[xX][0-9a-fA-F]+|0[0-7]*)([uU](ll|LL)|[uU][lL]?|(ll|LL)[uU]?|[lL][uU])?'), cParser.TERMINAL_INTEGER_CONSTANT, token ),
      ( re.compile(r'0[xX](([0-9a-fA-F]+)?\.([0-9a-fA-F]+)|[0-9a-fA-F]+\.)[pP][-+]?[0-9]+[flFL]?'), cParser.TERMINAL_HEXADECIMAL_FLOATING_CONSTANT, token ),
      ( re.compile(r"[L]?'([^\\'\n]|\\[\\\"\'nrbtfav\?]|\\[0-7]{1,3}|\\x[0-9a-fA-F]+|\\[uU]([0-9a-fA-F]{4})([0-9a-fA-F]{4})?)+'"), cParser.TERMINAL_CHARACTER_CONSTANT, token ),

      # Whitespace
      ( re.compile(r'\s+', 0), None, None )
  ]

  def __init__(self, sourceCode, pp_expander=None, context=None):

    if context:
      self.__dict__ = context
    else:
      self.braceLevel = 0
      self.parenLevel = 0
      self.ifBlocks = set()
      self.typedefBlocks = set()
      self.typedefs = dict()
      self.lastIdentifier = None
      self.endifTokens = set()
      self.hint_braceLevel = 0
      self.hint_parenLevel = 0
      self.hint_structDecl = 0
      self.hint_lock = False
    super().__init__(sourceCode, self.cRegex)

    mtokens = list(self)
    if pp_expander:
      mtokens = pp_expander(mtokens)
    mtokens = self.addParserHints(TokenList(mtokens))
    self.addTokens(mtokens)

  def update_hint_context(self, token):
    if token.id == cParser.TERMINAL_LPAREN:
      self.hint_parenLevel += 1
    elif token.id == cParser.TERMINAL_RPAREN:
      self.hint_parenLevel -= 1
    elif token.id == cParser.TERMINAL_LBRACE:
      self.hint_braceLevel += 1
    elif token.id == cParser.TERMINAL_RBRACE:
      self.hint_braceLevel -= 1

  def parse_parameters(self, tokenIterator):
    param = []
    params = []
    hint = cParser.TERMINAL_ABSTRACT_PARAMETER_HINT
    startParenLevel = self.hint_parenLevel
    while True:
      try:
        token = next(tokenIterator)
        self.update_hint_context(token)
      except StopIteration:
        break

      if token.id == cParser.TERMINAL_LPAREN and tokenIterator.check('+1', declaration_specifiers()):
        param.append(token)
        param.extend(self.parse_parameters(tokenIterator))
        continue
      elif (token.id == cParser.TERMINAL_COMMA) or \
           (token.id == cParser.TERMINAL_RPAREN and self.hint_parenLevel == startParenLevel - 1):
        params.append(cToken(hint, self.resource, cParser.terminals[hint], '', param[0].lineno, param[0].colno, self.getContext()))
        params.extend(param)
        params.append(token)
        param = []
        hint = cParser.TERMINAL_ABSTRACT_PARAMETER_HINT
        if token.id == cParser.TERMINAL_RPAREN:
          break
        continue
      else:
        param.append(token)
        if token.id == cParser.TERMINAL_IDENTIFIER:
          hint = cParser.TERMINAL_NAMED_PARAMETER_HINT

    if len(param):
      params.append(cToken(hint, self.resource, cParser.terminals[hint], '', param[0].lineno, param[0].colno, self.getContext()))
      params.extend(param)
      params.append(token)

    return params

  def parseExternalDeclaration(self, tokenIterator):
    # returns as soon as a hint is determined or token stream ends
    ytokens = []
    xtokens = []
    self.lock = True
    keepGoing = True
    collectDeclarationSpecifiers = True

    while keepGoing:
      keepGoing = funcFound = rparenFound = identFound = parametersParsed = hintId = False
      ztokens = []
      declarationSpecifiers = []

      while True: #for token2 in tokenIterator:
        try:
          token2 = next(tokenIterator)
        except StopIteration:
          break

        self.update_hint_context(token2)

        if collectDeclarationSpecifiers:
          if self.hint_structDecl > 0:
            if token2.id == cParser.TERMINAL_RBRACE:
              self.hint_structDecl -= 1
            declarationSpecifiers.append(token2)
            if self.hint_structDecl == 0:
              collectDeclarationSpecifiers = False
            continue
          elif token2.id in {cParser.TERMINAL_STRUCT, cParser.TERMINAL_UNION}:
            self.hint_structDecl += 1
            declarationSpecifiers.append(token2)
            continue
          else:
            declarationSpecifiers.append(token2)
          if not tokenIterator.check('+1', declaration_specifiers()):
            collectDeclarationSpecifiers = False
          continue

        ztokens.append(token2)

        if self.hint_braceLevel == 0 and \
           token2.id == cParser.TERMINAL_IDENTIFIER and \
           (self.hint_parenLevel > 0 or tokenIterator.check('+1', [cParser.TERMINAL_LPAREN])):
          funcFound = True
          continue

        if funcFound:
          if token2.id == cParser.TERMINAL_LPAREN and tokenIterator.check('+1', declaration_specifiers()):
            ztokens.extend( self.parse_parameters(tokenIterator) )
            parametersParsed = True
            continue
          if token2.id == cParser.TERMINAL_RPAREN and self.hint_parenLevel == 0:
            parametersParsed = True
            continue
          if parametersParsed:
            if token2.id in [cParser.TERMINAL_SEMI, cParser.TERMINAL_COMMA] and self.hint_parenLevel == 0:
              hintId = cParser.TERMINAL_FUNCTION_PROTOTYPE_HINT
              if token2.id == cParser.TERMINAL_COMMA:
                keepGoing = True
            else:
              hintId = cParser.TERMINAL_FUNCTION_DEFINITION_HINT
              while token2.id != cParser.TERMINAL_LBRACE:
                try:
                  token2 = next(tokenIterator)
                  self.update_hint_context(token2)
                  ztokens.append(token2)
                except StopIteration:
                  break
            parametersParsed = False
            break
          continue

        if token2.id in [cParser.TERMINAL_SEMI, cParser.TERMINAL_COMMA] and \
           self.hint_braceLevel == 0 and self.hint_parenLevel == 0:
          hintId = cParser.TERMINAL_DECLARATOR_HINT
          if token2.id == cParser.TERMINAL_COMMA:
            keepGoing = True
          break

      ytokens.extend(declarationSpecifiers)
      if hintId != False:
        first = declarationSpecifiers[0] if len(declarationSpecifiers) else ztokens[0]
        hint = cToken(hintId, self.resource, cParser.terminals[hintId], '', first.lineno, first.colno, self.getContext())
        ytokens.append(hint)
      ytokens.extend(ztokens)
    # endwhile


    first = ytokens[0] if len(ytokens) else ztokens[0]
    edHintId = cParser.TERMINAL_EXTERNAL_DECLARATION_HINT
    edHint = cToken(edHintId, self.resource, cParser.terminals[edHintId], '', first.lineno, first.colno, self.getContext());
    xtokens.append(edHint)
    xtokens.extend(ytokens)
    self.hint_lock = False
    return xtokens

  def addParserHints(self, tokenIterator):
    xtokens = []
    tokenIterator = iter(tokenIterator)

    while True: #for token in tokenIterator:
      try:
        token = next(tokenIterator)
      except StopIteration:
        break

      if self.hint_lock:
        self.update_hint_context(token)
        xtokens.append(token)
      elif self.hint_braceLevel == 0 and token.id in declaration_specifiers():
        xtokens.extend(self.parseExternalDeclaration(tokenIterator.go('-1')))
      else:
        self.update_hint_context(token)
        xtokens.append(token)
    return xtokens

  def markIf(self):
    self.ifBlocks = self.ifBlocks.union({(self.braceLevel, self.parenLevel)})
  def unmarkIf(self):
    self.ifBlocks = self.ifBlocks.difference({(self.braceLevel, self.parenLevel)})
  def isIf(self):
    return (self.braceLevel, self.parenLevel) in self.ifBlocks
  def addEndif(self):
    self.unmarkIf()
    nextTokens = set(map(lambda x: x[0], self.peek(2)))
    t = set()
    if cParser.TERMINAL_LBRACE in nextTokens:
      t = {(cParser.TERMINAL_RBRACE, self.braceLevel,)}
    elif not len(nextTokens.intersection({cParser.TERMINAL_FOR, cParser.TERMINAL_IF, cParser.TERMINAL_WHILE, cParser.TERMINAL_DO})):
      t = {(cParser.TERMINAL_SEMI, self.braceLevel,)}
    else:
      self.markIf()
    self.endifTokens = self.endifTokens.union(t)

  def __next__(self):
    token = super().__next__()
    return cToken(token.id, self.resource, token.terminal_str, token.source_string, token.lineno, token.colno, context=self.getContext())

  def getContext(self):
    return self.__dict__
