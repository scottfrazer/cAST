import re
from cast.Lexer import PatternMatchingLexer
from cast.Token import cToken
from cast.cParser import Parser as cParser

def parseTypedef( match, lexer ):
  pass

class cLexer(PatternMatchingLexer):
  type_specifier = ['void', 'char', 'short', 'int', 'long', 'float', 'double', 'signed', 'unsigned', '_Bool', '_Complex']
  cRegex = [
      # Comments
      ( re.compile(r'/\*.*?\*/', re.S), None, None, None ),
      ( re.compile(r'//.*', 0), None, None, None ),

      # Keywords
      ( re.compile(r'auto(?=\s)'), 'AUTO', None, None ),
      ( re.compile(r'_Bool(?=[\s\)])'), 'BOOL', None, None ),
      ( re.compile(r'break(?=\s)'), 'BREAK', None, None ),
      ( re.compile(r'case(?=\s)'), 'CASE', None, None ),
      ( re.compile(r'char(?=[\s\)])'), 'CHAR', None, None ),
      ( re.compile(r'_Complex(?=[\s\)])'), 'COMPLEX', None, None ),
      ( re.compile(r'const(?=[\s\)])'), 'CONST', None, None ),
      ( re.compile(r'continue(?=\s)'), 'CONTINUE', None, None ),
      ( re.compile(r'default(?=\s)'), 'DEFAULT', None, None ),
      ( re.compile(r'do(?=\s)'), 'DO', None, None ),
      ( re.compile(r'double(?=[\s\)])'), 'DOUBLE', None, None ),
      ( re.compile(r'else(?=\s)'), 'ELSE', None, None ),
      ( re.compile(r'enum(?=\s)'), 'ENUM', None, None ),
      ( re.compile(r'extern(?=[\s\)])'), 'EXTERN', None, None ),
      ( re.compile(r'float(?=[\s\)])'), 'FLOAT', None, None ),
      ( re.compile(r'for(?=\s)'), 'FOR', None, None ),
      ( re.compile(r'goto(?=\s)'), 'GOTO', None, None ),
      ( re.compile(r'if(?=\s)'), 'IF', None, None ),
      ( re.compile(r'_Imaginary(?=\s)'), 'IMAGINARY', None, None ),
      ( re.compile(r'inline(?=\s)'), 'INLINE', None, None ),
      ( re.compile(r'int(?=[\s\)])'), 'INT', None, None ),
      ( re.compile(r'long(?=[\s\)])'), 'LONG', None, None ),
      ( re.compile(r'register(?=[\s\)])'), 'REGISTER', None, None ),
      ( re.compile(r'restrict(?=[\s\)])'), 'RESTRICT', None, None ),
      ( re.compile(r'return(?=\s)'), 'RETURN', None, None ),
      ( re.compile(r'short(?=[\s\)])'), 'SHORT', None, None ),
      ( re.compile(r'signed(?=[\s\)])'), 'SIGNED', None, None ),
      ( re.compile(r'sizeof(?=\s)'), 'SIZEOF', None, None ),
      ( re.compile(r'static(?=\s)'), 'STATIC', None, None ),
      ( re.compile(r'struct(?=\s)'), 'STRUCT', None, None ),
      ( re.compile(r'switch(?=\s)'), 'SWITCH', None, None ),
      ( re.compile(r'typedef(?=\s)'), None, parseTypedef, None ),
      ( re.compile(r'union(?=\s)'), 'UNION', None, None ),
      ( re.compile(r'unsigned(?=\s)'), 'UNSIGNED', None, None ),
      ( re.compile(r'void(?=[\s\)])'), 'VOID', None, None ),
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
      ( re.compile(r'\((?=' + '(' +'|'.join(type_specifier) + ')\s*\))'), 'LPAREN_CAST', None, None ),
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
  def __init__(self, sourceCode = None, terminals = None, logger = None):
    super().__init__(sourceCode)
    self.setTerminals(terminals)
    self.setRegex(self.cRegex)
    self.setLogger(logger)

  def setSourceCode(self, sourceCode):
    super().setSourceCode(sourceCode)
    self.setString(re.sub(r'\\\n', r'\n', self.getString()))
  
  def __next__(self):
    token = super().__next__()
    return cToken(token.id, self.resource, token.terminal_str, token.source_string, token.lineno, token.colno)

class Factory:
  def create( self, sourceCode = None, logger = None):
    cP = cParser()
    cL_TokenMap = { terminalString.upper(): cP.terminal(terminalString) for terminalString in cP.terminalNames() }
    cL = cLexer(sourceCode=sourceCode, terminals=cL_TokenMap, logger=logger)
    return cL
  
