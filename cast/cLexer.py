import re
from cast.Lexer import PatternMatchingLexer
from cast.Token import cToken
from cast.cParser import Parser as cParser

def parseTypedef( string, lineno, colno, terminalId, lexer ):
  queue = []
  ident = None

  typedefId = cParser.TERMINAL_TYPEDEF
  token = cToken(typedefId, lexer.resource, cParser.terminal_str[typedefId], string, lexer.lineno, lexer.colno - len(match))
  lexer.addToken(token)
  for token in lexer:
    lexer.addToken(token)
    if token.id == cParser.TERMINAL_IDENTIFIER:
      ident = token
    if token.id == cParser.TERMINAL_SEMI:
      break
  if ident:
    ident.id = cParser.TERMINAL_TYPEDEF_IDENTIFIER
    ident.terminal_str = cParser.terminal_str[ident.id]

def parseLbrace( string, lineno, colno, terminalId, lexer ):
  lexer.braceLevel += 1
  token( string, lineno, colno, terminalId, lexer )

def parseRbrace( string, lineno, colno, terminalId, lexer ):
  lexer.braceLevel -= 1
  token( string, lineno, colno, terminalId, lexer )

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

decls = None
def declaration_specifiers():
  global decls
  if not decls:
    c = lambda x: cParser.str_terminal[x]
    decls = { 
      c('typedef'),  c('extern'), c('static'), c('auto'), \
      c('register'), c('void'), c('char'), c('short'), c('int'), \
      c('long'), c('float'), c('double'), c('signed'), c('unsigned'), \
      c('_bool'), c('_complex'), c('struct'), c('union'), c('enum'), \
      c('typedef_identifier'), c('const'), c('restrict'), c('volatile'), \
      c('inline')
    }
  return decls

def token(string, lineno, colno, terminalId, lexer):
  matchedToken = cToken(terminalId, lexer.resource, cParser.terminal_str[terminalId], string, lineno, colno)

  if lexer.lock:
    lexer.addToken(matchedToken)
    return

  if lexer.braceLevel == 0 and terminalId in declaration_specifiers():
    declarationSpecifiers = [matchedToken]
    tokens = []

    lexer.lock = True
    keepGoing = True
    collectDeclarationSpecifiers = True
    while keepGoing:
      keepGoing = funcFound = rparenFound = identFound = hintId = False
      queue = []
      for token in lexer:
        if token.id in declaration_specifiers() and collectDeclarationSpecifiers:
          declarationSpecifiers.append(token)
          continue
        else:
          collectDeclarationSpecifiers = False

        queue.append(token)

        if funcFound :
          if token.id == cParser.TERMINAL_LBRACE:
            hintId = cParser.TERMINAL_FUNCTION_DEFINITION_HINT
            break
          if token.id == cParser.TERMINAL_RPAREN:
            rparenFound = True
            continue
          if rparenFound and token.id in [cParser.TERMINAL_SEMI, cParser.TERMINAL_COMMA] and lexer.parenLevel == 0:
            hintId = cParser.TERMINAL_FUNCTION_PROTOTYPE_HINT
            if token.id == cParser.TERMINAL_COMMA:
              keepGoing = True
            break
          rparenFound = False
          continue
        if identFound and token.id == cParser.TERMINAL_LPAREN:
          funcFound = True
          continue
        if token.id == cParser.TERMINAL_IDENTIFIER and lexer.braceLevel == 0:
          identFound = True
          continue
        funcFound = False
        identFound = False

        if token.id in [cParser.TERMINAL_SEMI, cParser.TERMINAL_COMMA] and lexer.braceLevel == 0 and lexer.parenLevel == 0:
          hintId = cParser.TERMINAL_DECLARATOR_HINT
          if token.id == cParser.TERMINAL_COMMA:
            keepGoing = True
          break

      if hintId != False:
        hint = cToken(hintId, lexer.resource, cParser.terminal_str[hintId], '', lineno, colno)
        tokens.append(hint)
      tokens.extend(queue)
    # endwhile
    edHintId = cParser.TERMINAL_EXTERNAL_DECLARATION_HINT
    lexer.addToken(cToken(edHintId, lexer.resource, cParser.terminal_str[edHintId], '', lineno, colno))
    for token in declarationSpecifiers:
      lexer.addToken(token)
    for token in tokens:
      lexer.addToken(token)
    lexer.lock = False
  else:
    lexer.addToken(matchedToken)

class cLexer(PatternMatchingLexer):
  type_specifier = ['void', 'char', 'short', 'int', 'long', 'float', 'double', 'signed', 'unsigned', '_Bool', '_Complex']
  cRegex = [
      # Comments
      ( re.compile(r'/\*.*?\*/', re.S), None, None ),
      ( re.compile(r'//.*', 0), None, None ),

      # Keywords
      ( re.compile(r'auto(?=[^a-zA-Z])'), cParser.TERMINAL_AUTO, token ),
      ( re.compile(r'_Bool(?=[^a-zA-Z])'), cParser.TERMINAL_BOOL, token ),
      ( re.compile(r'break(?=[^a-zA-Z])'), cParser.TERMINAL_BREAK, token ),
      ( re.compile(r'case(?=[^a-zA-Z])'), cParser.TERMINAL_CASE, token ),
      ( re.compile(r'char(?=[^a-zA-Z])'), cParser.TERMINAL_CHAR, token ),
      ( re.compile(r'_Complex(?=[^a-zA-Z])'), cParser.TERMINAL_COMPLEX, token ),
      ( re.compile(r'const(?=[^a-zA-Z])'), cParser.TERMINAL_CONST, token ),
      ( re.compile(r'continue(?=[^a-zA-Z])'), cParser.TERMINAL_CONTINUE, token ),
      ( re.compile(r'default(?=[^a-zA-Z])'), cParser.TERMINAL_DEFAULT, token ),
      ( re.compile(r'do(?=[^a-zA-Z])'), cParser.TERMINAL_DO, token ),
      ( re.compile(r'double(?=[^a-zA-Z])'), cParser.TERMINAL_DOUBLE, token ),
      ( re.compile(r'else(?=[^a-zA-Z])'), cParser.TERMINAL_ELSE, token ),
      ( re.compile(r'enum(?=[^a-zA-Z])'), cParser.TERMINAL_ENUM, token ),
      ( re.compile(r'extern(?=[^a-zA-Z])'), cParser.TERMINAL_EXTERN, token ),
      ( re.compile(r'float(?=[^a-zA-Z])'), cParser.TERMINAL_FLOAT, token ),
      ( re.compile(r'for(?=[^a-zA-Z])'), cParser.TERMINAL_FOR, token ),
      ( re.compile(r'goto(?=[^a-zA-Z])'), cParser.TERMINAL_GOTO, token ),
      ( re.compile(r'if(?=[^a-zA-Z])'), cParser.TERMINAL_IF, token ),
      ( re.compile(r'_Imaginary(?=[^a-zA-Z])'), cParser.TERMINAL_IMAGINARY, token ),
      ( re.compile(r'inline(?=[^a-zA-Z])'), cParser.TERMINAL_INLINE, token ),
      ( re.compile(r'int(?=[^a-zA-Z])'), cParser.TERMINAL_INT, token ),
      ( re.compile(r'long(?=[^a-zA-Z])'), cParser.TERMINAL_LONG, token ),
      ( re.compile(r'register(?=[^a-zA-Z])'), cParser.TERMINAL_REGISTER, token ),
      ( re.compile(r'restrict(?=[^a-zA-Z])'), cParser.TERMINAL_RESTRICT, token ),
      ( re.compile(r'return(?=[^a-zA-Z])'), cParser.TERMINAL_RETURN, token ),
      ( re.compile(r'short(?=[^a-zA-Z])'), cParser.TERMINAL_SHORT, token ),
      ( re.compile(r'signed(?=[^a-zA-Z])'), cParser.TERMINAL_SIGNED, token ),
      ( re.compile(r'sizeof(?=[^a-zA-Z])'), cParser.TERMINAL_SIZEOF, token ),
      ( re.compile(r'static(?=[^a-zA-Z])'), cParser.TERMINAL_STATIC, token ),
      ( re.compile(r'struct(?=[^a-zA-Z])'), cParser.TERMINAL_STRUCT, token ),
      ( re.compile(r'switch(?=[^a-zA-Z])'), cParser.TERMINAL_SWITCH, token ),
      ( re.compile(r'typedef(?=[^a-zA-Z])'), cParser.TERMINAL_TYPEDEF, parseTypedef ),
      ( re.compile(r'union(?=[^a-zA-Z])'), cParser.TERMINAL_UNION, token ),
      ( re.compile(r'unsigned(?=[^a-zA-Z])'), cParser.TERMINAL_UNSIGNED, token ),
      ( re.compile(r'void(?=[^a-zA-Z])'), cParser.TERMINAL_VOID, token ),
      ( re.compile(r'volatile(?=[^a-zA-Z])'), cParser.TERMINAL_VOLATILE, token ),
      ( re.compile(r'while(?=[^a-zA-Z])'), cParser.TERMINAL_WHILE, token ),

      # Identifiers
      ( re.compile(r'([a-zA-Z_]|\\[uU]([0-9a-fA-F]{4})([0-9a-fA-F]{4})?)([a-zA-Z_0-9]|\\[uU]([0-9a-fA-F]{4})([0-9a-fA-F]{4})?)*'), cParser.TERMINAL_IDENTIFIER, token ),

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
      ( re.compile(r'\((?=\s*' + '(' +'|'.join(type_specifier) + ')[\*\s]*\))'), cParser.TERMINAL_LPAREN_CAST, parseLparenCast ),
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
      ( re.compile(r';'), cParser.TERMINAL_SEMI, token ),
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
      ( re.compile(r','), cParser.TERMINAL_COMMA, token ),
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

  def __init__(self, sourceCode):
    super().__init__(sourceCode, self.cRegex)
    self.braceLevel = 0
    self.parenLevel = 0
    self.lock = False

  def __next__(self):
    token = super().__next__()
    return cToken(token.id, self.resource, token.terminal_str, token.source_string, token.lineno, token.colno)

  def getContext(self):
    return (self.braceLevel, self.parenLevel, self.lock)

  def setContext(self, context):
    self.braceLevel = context[0]
    self.parenLevel = context[1]
    self.lock = context[2]
