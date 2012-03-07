import re
from cast.Lexer import PatternMatchingLexer
from cast.Token import cToken, TokenList
from cast.c_Parser import c_Parser

def parseIdentifier( string, lineno, colno, terminalId, lexer ):
  addedToken = token( string, lineno, colno, terminalId, lexer)
  if addedToken.source_string in lexer.typedefs:
    tId = c_Parser.TERMINAL_TYPEDEF_IDENTIFIER
    addedToken.id = tId
    addedToken.terminal_str = c_Parser.terminals[tId]
  else:
    lexer.lastIdentifier = addedToken

def parseLabelIdentifier( string, lineno, colno, terminalId, lexer ):
  hintId = c_Parser.TERMINAL_LABEL_HINT
  ctx = lexer.getContext()
  lexer.addToken(cToken(hintId, lexer.resource, c_Parser.terminals[hintId], '', lineno, colno, context=ctx))
  lexer.addToken(cToken(terminalId, lexer.resource, c_Parser.terminals[terminalId], string, lineno, colno, context=ctx))

def parseTypedef( string, lineno, colno, terminalId, lexer ):
  lexer.typedefBlocks = lexer.typedefBlocks.union({(lexer.braceLevel, lexer.parenLevel)})
  token( string, lineno, colno, terminalId, lexer )
  
def parseLbrace( string, lineno, colno, terminalId, lexer ):
  lexer.braceLevel += 1
  token( string, lineno, colno, terminalId, lexer )

def parseRbrace( string, lineno, colno, terminalId, lexer ):
  lexer.braceLevel -= 1
  token( string, lineno, colno, terminalId, lexer )
  if (c_Parser.TERMINAL_RBRACE, lexer.braceLevel) in lexer.endifTokens:
    lexer.endifTokens = lexer.endifTokens.difference({(c_Parser.TERMINAL_RBRACE, lexer.braceLevel)})
    token('', lineno, colno, c_Parser.TERMINAL_ENDIF, lexer)

def parseLparenCast( string, lineno, colno, terminalId, lexer ):
  lexer.parenLevel += 1
  if lexer.braceLevel == 0:
    token( string, lineno, colno, c_Parser.TERMINAL_LPAREN, lexer )
  else:
    token( string, lineno, colno, c_Parser.TERMINAL_LPAREN_CAST, lexer )

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
  if (c_Parser.TERMINAL_SEMI, lexer.braceLevel,) in lexer.endifTokens:
    lexer.endifTokens = lexer.endifTokens.difference({(c_Parser.TERMINAL_SEMI, lexer.braceLevel)})
    token('', lineno, colno, c_Parser.TERMINAL_ENDIF, lexer)
  if (lexer.braceLevel, lexer.parenLevel) in lexer.typedefBlocks:
    lexer.typedefBlocks = lexer.typedefBlocks.difference({(lexer.braceLevel, lexer.parenLevel)})
    tId = c_Parser.TERMINAL_TYPEDEF_IDENTIFIER
    if lexer.lastIdentifier:
      lexer.typedefs[lexer.lastIdentifier.source_string] = cToken(tId, lexer.resource, c_Parser.terminals[tId], lexer.lastIdentifier.source_string, lineno, colno, lexer.getContext())
    else:
      raise Exception('no last identifier')

def parseComma( string, lineno, colno, terminalId, lexer ):
  token( string, lineno, colno, terminalId, lexer )
  if (lexer.braceLevel, lexer.parenLevel) in lexer.typedefBlocks:
    tId = c_Parser.TERMINAL_TYPEDEF_IDENTIFIER
    if lexer.lastIdentifier:
      lexer.typedefs[lexer.lastIdentifier.source_string] = cToken(tId, lexer.resource, c_Parser.terminals[tId], lexer.lastIdentifier.source_string, lineno, colno, lexer.getContext())
    else:
      raise Exception('no last identifier')

decls = None
def declaration_specifiers():
  global decls
  if not decls:
    c = lambda x: c_Parser.terminals[x]
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
  matchedToken = cToken(terminalId, lexer.resource, c_Parser.terminals[terminalId], string, lineno, colno, lexer.getContext())
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
      ( re.compile(r'auto(?=[^a-zA-Z_])'), c_Parser.TERMINAL_AUTO, token ),
      ( re.compile(r'_Bool(?=[^a-zA-Z_])'), c_Parser.TERMINAL_BOOL, token ),
      ( re.compile(r'break(?=[^a-zA-Z_])'), c_Parser.TERMINAL_BREAK, token ),
      ( re.compile(r'case(?=[^a-zA-Z_])'), c_Parser.TERMINAL_CASE, token ),
      ( re.compile(r'char(?=[^a-zA-Z_])'), c_Parser.TERMINAL_CHAR, token ),
      ( re.compile(r'_Complex(?=[^a-zA-Z_])'), c_Parser.TERMINAL_COMPLEX, token ),
      ( re.compile(r'const(?=[^a-zA-Z_])'), c_Parser.TERMINAL_CONST, token ),
      ( re.compile(r'continue(?=[^a-zA-Z_])'), c_Parser.TERMINAL_CONTINUE, token ),
      ( re.compile(r'default(?=[^a-zA-Z_])'), c_Parser.TERMINAL_DEFAULT, token ),
      ( re.compile(r'do(?=[^a-zA-Z_])'), c_Parser.TERMINAL_DO, token ),
      ( re.compile(r'double(?=[^a-zA-Z_])'), c_Parser.TERMINAL_DOUBLE, token ),
      ( re.compile(r'else\s+if(?=[^a-zA-Z_])'), c_Parser.TERMINAL_ELSE_IF, parseIf ),
      ( re.compile(r'else(?=[^a-zA-Z_])'), c_Parser.TERMINAL_ELSE, parseElse ),
      ( re.compile(r'enum(?=[^a-zA-Z_])'), c_Parser.TERMINAL_ENUM, token ),
      ( re.compile(r'extern(?=[^a-zA-Z_])'), c_Parser.TERMINAL_EXTERN, token ),
      ( re.compile(r'float(?=[^a-zA-Z_])'), c_Parser.TERMINAL_FLOAT, token ),
      ( re.compile(r'for(?=[^a-zA-Z_])'), c_Parser.TERMINAL_FOR, token ),
      ( re.compile(r'goto(?=[^a-zA-Z_])'), c_Parser.TERMINAL_GOTO, token ),
      ( re.compile(r'if(?=[^a-zA-Z_])'), c_Parser.TERMINAL_IF, parseIf ),
      ( re.compile(r'_Imaginary(?=[^a-zA-Z_])'), c_Parser.TERMINAL_IMAGINARY, token ),
      ( re.compile(r'inline(?=[^a-zA-Z_])'), c_Parser.TERMINAL_INLINE, token ),
      ( re.compile(r'int(?=[^a-zA-Z_])'), c_Parser.TERMINAL_INT, token ),
      ( re.compile(r'long(?=[^a-zA-Z_])'), c_Parser.TERMINAL_LONG, token ),
      ( re.compile(r'register(?=[^a-zA-Z_])'), c_Parser.TERMINAL_REGISTER, token ),
      ( re.compile(r'restrict(?=[^a-zA-Z_])'), c_Parser.TERMINAL_RESTRICT, token ),
      ( re.compile(r'return(?=[^a-zA-Z_])'), c_Parser.TERMINAL_RETURN, token ),
      ( re.compile(r'short(?=[^a-zA-Z_])'), c_Parser.TERMINAL_SHORT, token ),
      ( re.compile(r'signed(?=[^a-zA-Z_])'), c_Parser.TERMINAL_SIGNED, token ),
      ( re.compile(r'sizeof(?=[^a-zA-Z_])'), c_Parser.TERMINAL_SIZEOF, token ),
      ( re.compile(r'static(?=[^a-zA-Z_])'), c_Parser.TERMINAL_STATIC, token ),
      ( re.compile(r'struct(?=[^a-zA-Z_])'), c_Parser.TERMINAL_STRUCT, token ),
      ( re.compile(r'switch(?=[^a-zA-Z_])'), c_Parser.TERMINAL_SWITCH, token ),
      ( re.compile(r'typedef(?=[^a-zA-Z_])'), c_Parser.TERMINAL_TYPEDEF, parseTypedef ),
      ( re.compile(r'union(?=[^a-zA-Z_])'), c_Parser.TERMINAL_UNION, token ),
      ( re.compile(r'unsigned(?=[^a-zA-Z_])'), c_Parser.TERMINAL_UNSIGNED, token ),
      ( re.compile(r'void(?=[^a-zA-Z_])'), c_Parser.TERMINAL_VOID, token ),
      ( re.compile(r'volatile(?=[^a-zA-Z_])'), c_Parser.TERMINAL_VOLATILE, token ),
      ( re.compile(r'while(?=[^a-zA-Z_])'), c_Parser.TERMINAL_WHILE, token ),

      # Identifiers
      ( re.compile('%s(?=\s*:)' % (identifierRegex)), c_Parser.TERMINAL_IDENTIFIER, parseLabelIdentifier ),
      ( re.compile(identifierRegex), c_Parser.TERMINAL_IDENTIFIER, parseIdentifier ),

      # Unicode Characters
      ( re.compile(r'\\[uU]([0-9a-fA-F]{4})([0-9a-fA-F]{4})?'), c_Parser.TERMINAL_UNIVERSAL_CHARACTER_NAME, token ),

      # Digraphs
      ( re.compile(r'<%'), c_Parser.TERMINAL_LBRACE, token ),
      ( re.compile(r'%>'), c_Parser.TERMINAL_RBRACE, token ),
      ( re.compile(r'<:'), c_Parser.TERMINAL_LSQUARE, token ),
      ( re.compile(r':>'), c_Parser.TERMINAL_RSQUARE, token ),
      ( re.compile(r'%:%:'), c_Parser.TERMINAL_POUNDPOUND, token ),
      ( re.compile(r'%:'), c_Parser.TERMINAL_POUND, token ),

      # Punctuators
      ( re.compile(r'\['), c_Parser.TERMINAL_LSQUARE, token ),
      ( re.compile(r'\]'), c_Parser.TERMINAL_RSQUARE, token ),
      ( re.compile(r'\((?=\s*' + 'void[\s]*\))'), c_Parser.TERMINAL_LPAREN, parseLparen ),
      #( re.compile(r'\((?=\s*' + '(' +'|'.join(type_specifier) + ')[\*\s]*\))'), c_Parser.TERMINAL_LPAREN_CAST, parseLparenCast ),
      ( re.compile(r'\('), c_Parser.TERMINAL_LPAREN, parseLparen ),
      ( re.compile(r'\)'), c_Parser.TERMINAL_RPAREN, parseRparen ),
      ( re.compile(r'\{'), c_Parser.TERMINAL_LBRACE, parseLbrace ),
      ( re.compile(r'\}'), c_Parser.TERMINAL_RBRACE, parseRbrace ),
      ( re.compile(r'\.\.\.'), c_Parser.TERMINAL_ELIPSIS, token ),
      ( re.compile(r'\.'), c_Parser.TERMINAL_DOT, token ),
      ( re.compile(r'->'), c_Parser.TERMINAL_ARROW, token ),
      ( re.compile(r'\+\+'), c_Parser.TERMINAL_INCR, token ),
      ( re.compile(r'--'), c_Parser.TERMINAL_DECR, token ),
      ( re.compile(r'&(?!&)'), c_Parser.TERMINAL_BITAND, token ),
      ( re.compile(r'\*(?!=)'), c_Parser.TERMINAL_ASTERISK, token ),
      ( re.compile(r'\+(?!=)'), c_Parser.TERMINAL_ADD, token ),
      ( re.compile(r'-(?!=)'), c_Parser.TERMINAL_SUB, token ),
      ( re.compile(r'~'), c_Parser.TERMINAL_TILDE, token ),
      ( re.compile(r'!(?!=)'), c_Parser.TERMINAL_EXCLAMATION_POINT, token ),
      ( re.compile(r'/(?!=)'), c_Parser.TERMINAL_DIV, token ),
      ( re.compile(r'%(?!=)'), c_Parser.TERMINAL_MOD, token ),
      ( re.compile(r'<<(?!=)'), c_Parser.TERMINAL_LSHIFT, token ),
      ( re.compile(r'>>(?!=)'), c_Parser.TERMINAL_RSHIFT, token ),
      ( re.compile(r'<(?!=)'), c_Parser.TERMINAL_LT, token ),
      ( re.compile(r'>(?!=)'), c_Parser.TERMINAL_GT, token ),
      ( re.compile(r'<='), c_Parser.TERMINAL_LTEQ, token ),
      ( re.compile(r'>='), c_Parser.TERMINAL_GTEQ, token ),
      ( re.compile(r'=='), c_Parser.TERMINAL_EQ, token ),
      ( re.compile(r'!='), c_Parser.TERMINAL_NEQ, token ),
      ( re.compile(r'\^(?!=)'), c_Parser.TERMINAL_BITXOR, token ),
      ( re.compile(r'\|(?!\|)'), c_Parser.TERMINAL_BITOR, token ),
      ( re.compile(r'&&'), c_Parser.TERMINAL_AND, token ),
      ( re.compile(r'\|\|'), c_Parser.TERMINAL_OR, token ),
      ( re.compile(r'\?'), c_Parser.TERMINAL_QUESTIONMARK, token ),
      ( re.compile(r':'), c_Parser.TERMINAL_COLON, token ),
      ( re.compile(r';'), c_Parser.TERMINAL_SEMI, parseSemi ),
      ( re.compile(r'=(?!=)'), c_Parser.TERMINAL_ASSIGN, token ),
      ( re.compile(r'\*='), c_Parser.TERMINAL_MULEQ, token ),
      ( re.compile(r'/='), c_Parser.TERMINAL_DIVEQ, token ),
      ( re.compile(r'%='), c_Parser.TERMINAL_MODEQ, token ),
      ( re.compile(r'\+='), c_Parser.TERMINAL_ADDEQ, token ),
      ( re.compile(r'-='), c_Parser.TERMINAL_SUBEQ, token ),
      ( re.compile(r'<<='), c_Parser.TERMINAL_LSHIFTEQ, token ),
      ( re.compile(r'>>='), c_Parser.TERMINAL_RSHIFTEQ, token ),
      ( re.compile(r'&='), c_Parser.TERMINAL_BITANDEQ, token ),
      ( re.compile(r'\^='), c_Parser.TERMINAL_BITXOREQ, token ),
      ( re.compile(r'\|='), c_Parser.TERMINAL_BITOREQ, token ),
      ( re.compile(r',(?=\s*})'), c_Parser.TERMINAL_TRAILING_COMMA, token ),
      ( re.compile(r',(?=\s*\.\.\.)'), c_Parser.TERMINAL_COMMA_VA_ARGS, token ),
      ( re.compile(r','), c_Parser.TERMINAL_COMMA, parseComma ),
      ( re.compile(r'##'), c_Parser.TERMINAL_POUNDPOUND, token ),
      ( re.compile(r'#(?!#)'), c_Parser.TERMINAL_POUND, token ),

      # Constants, Literals
      ( re.compile(r'(([0-9]+)?\.([0-9]+)|[0-9]+\.)([eE][-+]?[0-9]+)?[flFL]?'), c_Parser.TERMINAL_DECIMAL_FLOATING_CONSTANT, token ),
      ( re.compile(r'[L]?"([^\\\"\n]|\\[\\"\'nrbtfav\?]|\\[0-7]{1,3}|\\x[0-9a-fA-F]+|\\[uU]([0-9a-fA-F]{4})([0-9a-fA-F]{4})?)*"'), c_Parser.TERMINAL_STRING_LITERAL, token ),
      ( re.compile(r'([1-9][0-9]*|0[xX][0-9a-fA-F]+|0[0-7]*)([uU](ll|LL)|[uU][lL]?|(ll|LL)[uU]?|[lL][uU])?'), c_Parser.TERMINAL_INTEGER_CONSTANT, token ),
      ( re.compile(r'0[xX](([0-9a-fA-F]+)?\.([0-9a-fA-F]+)|[0-9a-fA-F]+\.)[pP][-+]?[0-9]+[flFL]?'), c_Parser.TERMINAL_HEXADECIMAL_FLOATING_CONSTANT, token ),
      ( re.compile(r"[L]?'([^\\'\n]|\\[\\\"\'nrbtfav\?]|\\[0-7]{1,3}|\\x[0-9a-fA-F]+|\\[uU]([0-9a-fA-F]{4})([0-9a-fA-F]{4})?)+'"), c_Parser.TERMINAL_CHARACTER_CONSTANT, token ),

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
      self.hint_structDecl = set()
      self.hint_lock = False
    super().__init__(sourceCode, self.cRegex)

    mtokens = list(self)
    if pp_expander:
      mtokens = pp_expander(mtokens)
    mtokens = self.addParserHints(TokenList(mtokens))
    self.addTokens(mtokens)

  def update_hint_context(self, token):
    if token.id == c_Parser.TERMINAL_LPAREN:
      self.hint_parenLevel += 1
    elif token.id == c_Parser.TERMINAL_RPAREN:
      self.hint_parenLevel -= 1
    elif token.id == c_Parser.TERMINAL_LBRACE:
      self.hint_braceLevel += 1
    elif token.id == c_Parser.TERMINAL_RBRACE:
      self.hint_braceLevel -= 1

  def parse_parameter_list(self, tokenIterator):
    param = []
    params = []
    hint = c_Parser.TERMINAL_ABSTRACT_PARAMETER_HINT
    startParenLevel = self.hint_parenLevel
    start = True
    while True:
      try:
        token = next(tokenIterator)
        self.update_hint_context(token)
      except StopIteration:
        break

      if start and token.id == c_Parser.TERMINAL_RPAREN:
        return [token]
      start = False

      if token.id == c_Parser.TERMINAL_LPAREN and \
         ( tokenIterator.check('+1', declaration_specifiers()) or \
           tokenIterator.check('+1', [c_Parser.TERMINAL_RPAREN]) ):
        param.append(token)
        param.extend(self.parse_parameter_list(tokenIterator))
        continue
      elif (token.id == c_Parser.TERMINAL_COMMA) or \
           (token.id == c_Parser.TERMINAL_RPAREN and self.hint_parenLevel == startParenLevel - 1):
        params.append(cToken(hint, self.resource, c_Parser.terminals[hint], '', param[0].lineno, param[0].colno, self.getContext()))
        params.extend(param)
        params.append(token)
        param = []
        hint = c_Parser.TERMINAL_ABSTRACT_PARAMETER_HINT
        if token.id == c_Parser.TERMINAL_RPAREN:
          break
        continue
      else:
        param.append(token)
        if token.id == c_Parser.TERMINAL_IDENTIFIER:
          hint = c_Parser.TERMINAL_NAMED_PARAMETER_HINT

    if len(param):
      params.append(cToken(hint, self.resource, c_Parser.terminals[hint], '', param[0].lineno, param[0].colno, self.getContext()))
      params.extend(param)
      params.append(token)

    return params

  def parse_until(self, tokenIterator, terminal_id):
    tokens = []
    while True:
      try:
        n = next(tokenIterator)
        self.update_hint_context(n)
        tokens.append(n)
        if n.id == terminal_id:
          break
      except StopIteration:
        break
    return tokens

  def parse_parameters(self, tokenIterator):
    tokens = []
    hintId = False

    if not tokenIterator.check('+1', [c_Parser.TERMINAL_IDENTIFIER]):
      tokens.extend( self.parse_parameter_list(tokenIterator) )
    else:
      tokens.extend( self.parse_until(tokenIterator, c_Parser.TERMINAL_RPAREN) )

    return tokens
      

  def parseExternalDeclaration(self, tokenIterator):
    # returns as soon as a hint is determined or token stream ends
    ytokens = []
    xtokens = []
    self.lock = True
    self.keepGoing = True
    collectDeclarationSpecifiers = True

    while self.keepGoing:
      self.keepGoing = parseParams = funcFound = rparenFound = identFound = parametersParsed = False
      hintId = False
      ztokens = []
      declarationSpecifiers = []

      while True:
        try:
          token2 = next(tokenIterator)
        except StopIteration:
          break

        self.update_hint_context(token2)

        if collectDeclarationSpecifiers:

          if self.hint_braceLevel in self.hint_structDecl:
            declarationSpecifiers.append(token2)

            if parseParams and token2.id == c_Parser.TERMINAL_LPAREN and \
               ( tokenIterator.check('+1', declaration_specifiers()) or \
                 tokenIterator.check('+1', [c_Parser.TERMINAL_RPAREN, c_Parser.TERMINAL_IDENTIFIER]) ):
              paramTokens =  self.parse_parameters(tokenIterator)
              declarationSpecifiers.extend(paramTokens)
              parseParams = False
            if token2.id == c_Parser.TERMINAL_RBRACE:
              self.hint_structDecl = self.hint_structDecl.difference({self.hint_braceLevel})
            if token2.id == c_Parser.TERMINAL_IDENTIFIER and self.hint_parenLevel > 0:
              parseParams = True
              continue
            if len(self.hint_structDecl) == 0:
              collectDeclarationSpecifiers = False
            continue

          elif token2.id in {c_Parser.TERMINAL_STRUCT, c_Parser.TERMINAL_UNION}:
            declarationSpecifiers.append(token2)
            while True:
              try:
                n = next(tokenIterator)
                self.update_hint_context(n)
                declarationSpecifiers.append(n)
                if n.id == c_Parser.TERMINAL_LBRACE:
                  break
              except StopIteration:
                break
            self.hint_structDecl = self.hint_structDecl.union({self.hint_braceLevel})
            continue
          else:
            declarationSpecifiers.append(token2)
          if not tokenIterator.check('+1', declaration_specifiers()):
            collectDeclarationSpecifiers = False
          continue

        ztokens.append(token2)

        if self.hint_braceLevel == 0 and \
           token2.id == c_Parser.TERMINAL_IDENTIFIER and \
           (self.hint_parenLevel > 0 or tokenIterator.check('+1', [c_Parser.TERMINAL_LPAREN])):
          parseParams = True
          if tokenIterator.check('+1', [c_Parser.TERMINAL_LPAREN]):
            funcFound = True
          continue

        if parseParams and token2.id == c_Parser.TERMINAL_LPAREN and \
           ( tokenIterator.check('+1', declaration_specifiers()) or \
             tokenIterator.check('+1', [c_Parser.TERMINAL_RPAREN, c_Parser.TERMINAL_IDENTIFIER]) ):
          paramTokens = self.parse_parameters(tokenIterator)
          ztokens.extend(paramTokens)

          if tokenIterator.check('+1', [c_Parser.TERMINAL_LBRACE]):
            hintId = c_Parser.TERMINAL_FUNCTION_DEFINITION_HINT
          elif tokenIterator.check('+1', declaration_specifiers()):
            hintId = c_Parser.TERMINAL_FUNCTION_DEFINITION_HINT
            ztokens.extend( self.parse_until(tokenIterator, c_Parser.TERMINAL_LBRACE) )

          if funcFound and hintId:
            break
          continue

        if token2.id in [c_Parser.TERMINAL_SEMI, c_Parser.TERMINAL_COMMA]:
          if self.hint_braceLevel == 0 and self.hint_parenLevel == 0:
            if funcFound:
              hintId = c_Parser.TERMINAL_FUNCTION_PROTOTYPE_HINT
            else:
              hintId = c_Parser.TERMINAL_DECLARATOR_HINT

            if token2.id == c_Parser.TERMINAL_COMMA:
              self.keepGoing = True
            break

      ytokens.extend(declarationSpecifiers)
      if hintId != False:
        first = declarationSpecifiers[0] if len(declarationSpecifiers) else ztokens[0]
        hint = cToken(hintId, self.resource, c_Parser.terminals[hintId], '', first.lineno, first.colno, self.getContext())
        ytokens.append(hint)
      ytokens.extend(ztokens)
    # endwhile


    first = ytokens[0] if len(ytokens) else ztokens[0]
    edHintId = c_Parser.TERMINAL_EXTERNAL_DECLARATION_HINT
    edHint = cToken(edHintId, self.resource, c_Parser.terminals[edHintId], '', first.lineno, first.colno, self.getContext());
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
    if c_Parser.TERMINAL_LBRACE in nextTokens:
      t = {(c_Parser.TERMINAL_RBRACE, self.braceLevel,)}
    elif not len(nextTokens.intersection({c_Parser.TERMINAL_FOR, c_Parser.TERMINAL_IF, c_Parser.TERMINAL_WHILE, c_Parser.TERMINAL_DO})):
      t = {(c_Parser.TERMINAL_SEMI, self.braceLevel,)}
    else:
      self.markIf()
    self.endifTokens = self.endifTokens.union(t)

  def __next__(self):
    token = super().__next__()
    return cToken(token.id, self.resource, token.terminal_str, token.source_string, token.lineno, token.colno, context=self.getContext())

  def getContext(self):
    return self.__dict__
