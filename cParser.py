import sys
def parse( iterator, entry ):
  p = Parser()
  return p.parse(iterator, entry)
class DebugTracer:
  def __init__(self, func, symbol, rule, callDepth ):
    self.__dict__.update(locals())
    self.children = []
  def add(self, child):
    self.children.append(child)
  def __str__(self):
    s = '%s[%s, symbol: %s, rule: %s]\n' % (' '.join(['' for i in range(self.callDepth)]), self.func, self.symbol, str(self.rule))
    for child in self.children:
      s += str(child)
    return s
class Terminal:
  def __init__(self, id):
    self.id=id
    self.str=Parser.terminal_str[id]
  def getId(self):
    return self.id
  def toAst(self):
    return self
  def __str__(self):
    return self.str
class NonTerminal():
  def __init__(self, id, string):
    self.id = id
    self.string = string
    self.list = False
  def __str__(self):
    return self.string
class AstTransform:
  pass
class AstTransformSubstitution(AstTransform):
  def __init__( self, idx ):
    self.idx = idx
  def __repr__( self ):
    return '$' + str(self.idx)
class AstTransformNodeCreator(AstTransform):
  def __init__( self, name, parameters ):
    self.name = name
    self.parameters = parameters
  def __repr__( self ):
    return self.name + '( ' + ', '.join(['%s=$%s' % (k,str(v)) for k,v in self.parameters.items()]) + ' )' 
class AstList(list):
  def toAst(self):
    retval = []
    for ast in self:
      retval.append(ast.toAst())
    return retval
class ParseTree():
  def __init__(self, nonterminal, tracer = None):
    self.__dict__.update(locals())
    self.children = []
    self.astTransform = None
    self.isExpr = False
    self.list = False
  def add( self, tree ):
    self.children.append( tree )
  def toAst( self ):
    if self.list == 'slist' or self.list == 'nlist':
      if len(self.children) == 0:
        return AstList()
      offset = 1 if not isinstance(self.children[0], ParseTree) else 0
      r = AstList([self.children[offset].toAst()])
      r.extend(self.children[offset+1].toAst())
      return r
    elif self.list == 'tlist':
      if len(self.children) == 0:
        return []
      r = AstList([self.children[0].toAst()])
      r.extend(self.children[2].toAst())
      return r
    elif self.isExpr:
      if isinstance(self.astTransform, AstTransformSubstitution):
        return self.children[self.astTransform.idx].toAst()
      elif isinstance(self.astTransform, AstTransformNodeCreator):
        parameters = {}
        for name, idx in self.astTransform.parameters.items():
          if isinstance(self.children[idx], ParseTree):
            parameters[name] = self.children[idx].toAst()
          elif isinstance(self.children[idx], list):
            parameters[name] = [x.toAst() for x in self.children[idx]]
          else:
            parameters[name] = self.children[idx]
        return Ast(self.astTransform.name, parameters)
    else:
      if isinstance(self.astTransform, AstTransformSubstitution):
        return self.children[self.astTransform.idx].toAst()
      elif isinstance(self.astTransform, AstTransformNodeCreator):
        parameters = {name: self.children[idx].toAst() for name, idx in self.astTransform.parameters.items()}
        return Ast(self.astTransform.name, parameters)
      elif len(self.children):
        return self.children[0].toAst()
      else:
        return None
  def __str__( self ):
    children = []
    for child in self.children:
      if isinstance(child, list):
        children.append('[' + ', '.join([str(a) for a in child]) + ']')
      else:
        children.append(str(child))
    return '(' + str(self.nonterminal) + ': ' + ', '.join(children) + ')'
class Ast():
  def __init__(self, name, attributes):
    self.name = name
    self.attributes = attributes
  def getAttr(self, attr):
    return self.attributes[attr]
  def __str__(self):
    return '(%s: %s)' % (self.name, ', '.join('%s=%s'%(str(k), '[' + ', '.join([str(x) for x in v]) + ']' if isinstance(v, list) else str(v) ) for k,v in self.attributes.items()))
class SyntaxError(Exception):
  def __init__(self, message, tracer = None):
    self.__dict__.update(locals())
  def __str__(self):
    return self.message
class TokenRecorder:
  def __init__(self):
    self.stack = []
    self.awake = False
  def wake(self):
    self.awake = True
    self.stack = []
    return self
  def sleep(self):
    self.awake = False
    return self
  def record(self, s):
    self.stack.append(s)
    return self
  def tokens(self):
    return self.stack
class Parser:
  def __init__(self):
    self.iterator = None
    self.sym = None
    self.recorder = TokenRecorder()
    self.entry_points = {
      'translation_unit': self._TRANSLATION_UNIT,
    }
  TERMINAL_GT = 0
  TERMINAL_DECR = 1
  TERMINAL_VOLATILE = 2
  TERMINAL_BITNOT = 3
  TERMINAL_DO = 4
  TERMINAL_RSHIFTEQ = 5
  TERMINAL_RBRACE = 6
  TERMINAL_BREAK = 7
  TERMINAL_COMMA = 8
  TERMINAL__COMPLEX = 9
  TERMINAL_AND = 10
  TERMINAL_LONG = 11
  TERMINAL_BITOR = 12
  TERMINAL_IMAGINARY = 13
  TERMINAL_GOTO = 14
  TERMINAL_ADDEQ = 15
  TERMINAL_BITAND = 16
  TERMINAL_MOD = 17
  TERMINAL__IMAGINARY = 18
  TERMINAL_STATIC = 19
  TERMINAL_DOT = 20
  TERMINAL_BITOREQ = 21
  TERMINAL_WHILE = 22
  TERMINAL_POUNDPOUND = 23
  TERMINAL_MULEQ = 24
  TERMINAL_LBRACE = 25
  TERMINAL_OR = 26
  TERMINAL_INT = 27
  TERMINAL_COMPLEX = 28
  TERMINAL_CONST = 29
  TERMINAL_NOT = 30
  TERMINAL_DIV = 31
  TERMINAL_LTEQ = 32
  TERMINAL_ADD = 33
  TERMINAL_LPAREN = 34
  TERMINAL_LSHIFT = 35
  TERMINAL_REGISTER = 36
  TERMINAL_ASSIGN = 37
  TERMINAL_IF = 38
  TERMINAL_COLON = 39
  TERMINAL_RESTRICT = 40
  TERMINAL_PP_NUMBER = 41
  TERMINAL_STRING_LITERAL = 42
  TERMINAL_HEXADECIMAL_FLOATING_CONSTANT = 43
  TERMINAL_RSQUARE = 44
  TERMINAL_CONTINUE = 45
  TERMINAL_CASE = 46
  TERMINAL_BITXOR = 47
  TERMINAL_GTEQ = 48
  TERMINAL_TILDE = 49
  TERMINAL_SHORT = 50
  TERMINAL_UNIVERSAL_CHARACTER_NAME = 51
  TERMINAL_BOOL = 52
  TERMINAL_FLOAT = 53
  TERMINAL_AMPERSAND = 54
  TERMINAL_SIGNED = 55
  TERMINAL_HEADER_NAME = 56
  TERMINAL_VOID = 57
  TERMINAL_UNSIGNED = 58
  TERMINAL_SIZEOF = 59
  TERMINAL_BITXOREQ = 60
  TERMINAL__BOOL = 61
  TERMINAL_LT = 62
  TERMINAL_ELIPSIS = 63
  TERMINAL_IDENTIFIER = 64
  TERMINAL_AUTO = 65
  TERMINAL_INTEGER_CONSTANT = 66
  TERMINAL_SUBEQ = 67
  TERMINAL_RPAREN = 68
  TERMINAL_SEMI = 69
  TERMINAL_TYPEDEF = 70
  TERMINAL_NUMBER = 71
  TERMINAL_MUL = 72
  TERMINAL_DIVEQ = 73
  TERMINAL_DEFAULT = 74
  TERMINAL_EXCLAMATION_POINT = 75
  TERMINAL_SWITCH = 76
  TERMINAL_RSHIFT = 77
  TERMINAL_DECIMAL_FLOATING_CONSTANT = 78
  TERMINAL_EXTERN = 79
  TERMINAL_LSQUARE = 80
  TERMINAL_QUESTIONMARK = 81
  TERMINAL_INLINE = 82
  TERMINAL_FOR = 83
  TERMINAL_MODEQ = 84
  TERMINAL_UNION = 85
  TERMINAL_ARROW = 86
  TERMINAL_RETURN = 87
  TERMINAL_INCR = 88
  TERMINAL_CHARACTER_CONSTANT = 89
  TERMINAL_BITANDEQ = 90
  TERMINAL_ELSE = 91
  TERMINAL_STRUCT = 92
  TERMINAL_NEQ = 93
  TERMINAL_CHAR = 94
  TERMINAL_POUND = 95
  TERMINAL_SUB = 96
  TERMINAL_DOUBLE = 97
  TERMINAL_LSHIFTEQ = 98
  TERMINAL_ENUM = 99
  TERMINAL_EQ = 100
  terminal_str = {
    0: 'gt',
    1: 'decr',
    2: 'volatile',
    3: 'bitnot',
    4: 'do',
    5: 'rshifteq',
    6: 'rbrace',
    7: 'break',
    8: 'comma',
    9: '_complex',
    10: 'and',
    11: 'long',
    12: 'bitor',
    13: 'imaginary',
    14: 'goto',
    15: 'addeq',
    16: 'bitand',
    17: 'mod',
    18: '_imaginary',
    19: 'static',
    20: 'dot',
    21: 'bitoreq',
    22: 'while',
    23: 'poundpound',
    24: 'muleq',
    25: 'lbrace',
    26: 'or',
    27: 'int',
    28: 'complex',
    29: 'const',
    30: 'not',
    31: 'div',
    32: 'lteq',
    33: 'add',
    34: 'lparen',
    35: 'lshift',
    36: 'register',
    37: 'assign',
    38: 'if',
    39: 'colon',
    40: 'restrict',
    41: 'pp_number',
    42: 'string_literal',
    43: 'hexadecimal_floating_constant',
    44: 'rsquare',
    45: 'continue',
    46: 'case',
    47: 'bitxor',
    48: 'gteq',
    49: 'tilde',
    50: 'short',
    51: 'universal_character_name',
    52: 'bool',
    53: 'float',
    54: 'ampersand',
    55: 'signed',
    56: 'header_name',
    57: 'void',
    58: 'unsigned',
    59: 'sizeof',
    60: 'bitxoreq',
    61: '_bool',
    62: 'lt',
    63: 'elipsis',
    64: 'identifier',
    65: 'auto',
    66: 'integer_constant',
    67: 'subeq',
    68: 'rparen',
    69: 'semi',
    70: 'typedef',
    71: 'number',
    72: 'mul',
    73: 'diveq',
    74: 'default',
    75: 'exclamation_point',
    76: 'switch',
    77: 'rshift',
    78: 'decimal_floating_constant',
    79: 'extern',
    80: 'lsquare',
    81: 'questionmark',
    82: 'inline',
    83: 'for',
    84: 'modeq',
    85: 'union',
    86: 'arrow',
    87: 'return',
    88: 'incr',
    89: 'character_constant',
    90: 'bitandeq',
    91: 'else',
    92: 'struct',
    93: 'neq',
    94: 'char',
    95: 'pound',
    96: 'sub',
    97: 'double',
    98: 'lshifteq',
    99: 'enum',
    100: 'eq',
  }
  nonterminal_str = {
    101: '_expr',
    102: '_gen0',
    103: 'punctuator',
    104: '_gen1',
    105: 'token',
    106: 'keyword',
    107: 'terminals',
    108: 'type_qualifier',
    109: 'translation_unit',
    110: '_gen2',
    111: '_direct_declarator',
    112: 'constant',
  }
  str_terminal = {
    'gt': 0,
    'decr': 1,
    'volatile': 2,
    'bitnot': 3,
    'do': 4,
    'rshifteq': 5,
    'rbrace': 6,
    'break': 7,
    'comma': 8,
    '_complex': 9,
    'and': 10,
    'long': 11,
    'bitor': 12,
    'imaginary': 13,
    'goto': 14,
    'addeq': 15,
    'bitand': 16,
    'mod': 17,
    '_imaginary': 18,
    'static': 19,
    'dot': 20,
    'bitoreq': 21,
    'while': 22,
    'poundpound': 23,
    'muleq': 24,
    'lbrace': 25,
    'or': 26,
    'int': 27,
    'complex': 28,
    'const': 29,
    'not': 30,
    'div': 31,
    'lteq': 32,
    'add': 33,
    'lparen': 34,
    'lshift': 35,
    'register': 36,
    'assign': 37,
    'if': 38,
    'colon': 39,
    'restrict': 40,
    'pp_number': 41,
    'string_literal': 42,
    'hexadecimal_floating_constant': 43,
    'rsquare': 44,
    'continue': 45,
    'case': 46,
    'bitxor': 47,
    'gteq': 48,
    'tilde': 49,
    'short': 50,
    'universal_character_name': 51,
    'bool': 52,
    'float': 53,
    'ampersand': 54,
    'signed': 55,
    'header_name': 56,
    'void': 57,
    'unsigned': 58,
    'sizeof': 59,
    'bitxoreq': 60,
    '_bool': 61,
    'lt': 62,
    'elipsis': 63,
    'identifier': 64,
    'auto': 65,
    'integer_constant': 66,
    'subeq': 67,
    'rparen': 68,
    'semi': 69,
    'typedef': 70,
    'number': 71,
    'mul': 72,
    'diveq': 73,
    'default': 74,
    'exclamation_point': 75,
    'switch': 76,
    'rshift': 77,
    'decimal_floating_constant': 78,
    'extern': 79,
    'lsquare': 80,
    'questionmark': 81,
    'inline': 82,
    'for': 83,
    'modeq': 84,
    'union': 85,
    'arrow': 86,
    'return': 87,
    'incr': 88,
    'character_constant': 89,
    'bitandeq': 90,
    'else': 91,
    'struct': 92,
    'neq': 93,
    'char': 94,
    'pound': 95,
    'sub': 96,
    'double': 97,
    'lshifteq': 98,
    'enum': 99,
    'eq': 100,
  }
  str_nonterminal = {
    '_expr': 101,
    '_gen0': 102,
    'punctuator': 103,
    '_gen1': 104,
    'token': 105,
    'keyword': 106,
    'terminals': 107,
    'type_qualifier': 108,
    'translation_unit': 109,
    '_gen2': 110,
    '_direct_declarator': 111,
    'constant': 112,
  }
  terminal_count = 101
  nonterminal_count = 12
  parse_table = [
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [12, 148, -1, -1, -1, 3, 46, -1, 161, -1, 152, -1, 168, -1, -1, 77, -1, 131, -1, -1, 22, 0, -1, 63, 85, 34, 49, -1, -1, -1, -1, 108, 175, 176, 95, 8, -1, 82, -1, 89, -1, -1, -1, -1, 84, -1, -1, 106, 40, 44, -1, -1, -1, -1, 21, -1, -1, -1, -1, -1, 167, -1, 124, 146, -1, -1, -1, 91, 18, 31, -1, -1, 184, -1, -1, 181, -1, 110, -1, -1, 140, 117, -1, -1, 14, -1, 111, -1, 186, -1, 68, -1, -1, 16, -1, 133, 164, -1, 32, -1, 163],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [105, 105, 33, -1, 33, 105, 105, 33, 105, 33, 105, 33, 105, -1, 33, 105, -1, 105, 33, 33, 105, 105, 33, 105, 105, 105, 105, 33, -1, 33, -1, 105, 105, 105, 105, 105, 33, 105, 33, 105, 33, 159, 51, -1, 105, 33, 33, 105, 105, 105, 33, -1, -1, 33, 105, 33, -1, 33, 33, 33, 105, 33, 105, 105, 17, 33, -1, 105, 105, 105, 33, -1, 105, -1, 33, 105, 33, 105, -1, 33, 105, 105, 33, 33, 105, 33, 105, 33, 105, -1, 105, 33, 33, 105, 33, 105, 105, 33, 105, 33, 105],
  [-1, -1, 135, -1, 118, -1, -1, 177, -1, 114, -1, 53, -1, -1, 174, -1, -1, -1, 93, 100, -1, -1, 47, -1, -1, -1, -1, 28, -1, 127, -1, -1, -1, -1, -1, -1, 156, -1, 5, -1, 94, -1, -1, -1, -1, 189, 116, -1, -1, -1, 129, -1, -1, 66, -1, 183, -1, 38, 99, 136, -1, 59, -1, -1, -1, 103, -1, -1, -1, -1, 169, -1, -1, -1, 154, -1, 55, -1, -1, 187, -1, -1, 42, 120, -1, 73, -1, 39, -1, -1, -1, 67, 142, -1, 115, -1, -1, 9, -1, 153, -1],
  [112, 162, 166, -1, 54, 107, 2, 119, 178, -1, 90, 10, 149, 65, 75, 102, 20, 26, -1, 70, 50, 171, 158, 36, 6, 60, 4, 145, 74, 61, 109, 179, 30, 1, 147, 76, 19, 173, 56, 27, 101, -1, 13, 81, 48, 128, 157, 43, 160, 52, 37, 134, 29, 62, -1, 69, 172, 137, 122, 58, 123, -1, 141, 41, 45, 92, 155, 23, 87, 125, 98, 151, 113, 188, 185, 64, 138, 86, 11, 96, 15, 150, 83, 35, 7, 57, 71, 25, 182, 165, 97, 144, 79, 104, 143, 80, 121, 88, 139, 24, 130],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1]
  ]
  def terminal(self, str):
    return self.str_terminal[str]
  def terminalNames(self):
    return list(self.str_terminal.keys())
  def isTerminal(self, id):
    return 0 <= id <= 100
  def isNonTerminal(self, id):
    return 101 <= id <= 112
  def rewind(self, recorder):
    global tokens
    tokens = recorder.tokens().append(tokens)
  def binding_power(self, sym, bp):
    try:
      return bp[sym.getId()]
    except KeyError:
      return 0
    except AttributeError:
      return 0
  def getAtomString(self, id):
    if self.isTerminal(id):
      return self.terminal_str[id]
    elif self.isNonTerminal(id):
      return self.nonterminal_str[id]
    return ''
  def getsym(self):
    try:
      return next( self.iterator )
    except StopIteration:
      return None
  def parse(self, iterator, entry):
    self.iterator = iter(iterator)
    self.sym = self.getsym()
    tree = self.entry_points[entry]()
    if self.sym != None:
      raise SyntaxError('Syntax Error: Finished parsing without consuming all tokens.', tree.tracer)
    self.iterator = None
    self.sym = None
    return tree
  def next(self):
    self.sym = self.getsym()
    if self.sym is not None and not self.isTerminal(self.sym.getId()):
      self.sym = None
      raise SyntaxError('Invalid symbol ID: %d (%s)'%(self.sym.getId(), self.sym), None)
    if self.recorder.awake and self.sym is not None:
      self.recorder.record(self.sym)
    return self.sym
  def expect(self, s, tracer):
    if self.sym and s == self.sym.getId():
      symbol = self.sym
      self.sym = self.next()
      return symbol
    else:
      raise SyntaxError('Unexpected symbol.  Expected %s, got %s.' %(self.terminal_str[s], self.sym if self.sym else 'None'), tracer)
  def rule(self, n):
    if self.sym == None: return -1
    return self.parse_table[n - 101][self.sym.getId()]
  def call(self, nt_str):
    return getattr(self, nt_str)()
  def __GEN0(self, depth = 0):
    rule = self.rule(102)
    if depth is not False:
      tracer = DebugTracer("__GEN0", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(102, self.getAtomString(102)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PUNCTUATOR(self, depth = 0):
    rule = self.rule(103)
    if depth is not False:
      tracer = DebugTracer("_PUNCTUATOR", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(103, self.getAtomString(103)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 0:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITOREQ, tracer) )
      return tree
    elif rule == 3:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RSHIFTEQ, tracer) )
      return tree
    elif rule == 8:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LSHIFT, tracer) )
      return tree
    elif rule == 12:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_GT, tracer) )
      return tree
    elif rule == 14:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_MODEQ, tracer) )
      return tree
    elif rule == 16:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_NEQ, tracer) )
      return tree
    elif rule == 18:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RPAREN, tracer) )
      return tree
    elif rule == 21:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_AMPERSAND, tracer) )
      return tree
    elif rule == 22:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DOT, tracer) )
      return tree
    elif rule == 31:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SEMI, tracer) )
      return tree
    elif rule == 32:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LSHIFTEQ, tracer) )
      return tree
    elif rule == 34:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LBRACE, tracer) )
      return tree
    elif rule == 40:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_GTEQ, tracer) )
      return tree
    elif rule == 44:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_TILDE, tracer) )
      return tree
    elif rule == 46:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RBRACE, tracer) )
      return tree
    elif rule == 49:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_OR, tracer) )
      return tree
    elif rule == 63:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_POUNDPOUND, tracer) )
      return tree
    elif rule == 68:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITANDEQ, tracer) )
      return tree
    elif rule == 77:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ADDEQ, tracer) )
      return tree
    elif rule == 82:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ASSIGN, tracer) )
      return tree
    elif rule == 84:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RSQUARE, tracer) )
      return tree
    elif rule == 85:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_MULEQ, tracer) )
      return tree
    elif rule == 89:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_COLON, tracer) )
      return tree
    elif rule == 91:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SUBEQ, tracer) )
      return tree
    elif rule == 95:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LPAREN, tracer) )
      return tree
    elif rule == 106:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITXOR, tracer) )
      return tree
    elif rule == 108:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DIV, tracer) )
      return tree
    elif rule == 110:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RSHIFT, tracer) )
      return tree
    elif rule == 111:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ARROW, tracer) )
      return tree
    elif rule == 117:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_QUESTIONMARK, tracer) )
      return tree
    elif rule == 124:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LT, tracer) )
      return tree
    elif rule == 131:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_MOD, tracer) )
      return tree
    elif rule == 133:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_POUND, tracer) )
      return tree
    elif rule == 140:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LSQUARE, tracer) )
      return tree
    elif rule == 146:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ELIPSIS, tracer) )
      return tree
    elif rule == 148:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DECR, tracer) )
      return tree
    elif rule == 152:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_AND, tracer) )
      return tree
    elif rule == 161:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_COMMA, tracer) )
      return tree
    elif rule == 163:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_EQ, tracer) )
      return tree
    elif rule == 164:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SUB, tracer) )
      return tree
    elif rule == 167:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITXOREQ, tracer) )
      return tree
    elif rule == 168:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITOR, tracer) )
      return tree
    elif rule == 175:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LTEQ, tracer) )
      return tree
    elif rule == 176:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ADD, tracer) )
      return tree
    elif rule == 181:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_EXCLAMATION_POINT, tracer) )
      return tree
    elif rule == 184:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_MUL, tracer) )
      return tree
    elif rule == 186:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_INCR, tracer) )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN1(self, depth = 0):
    rule = self.rule(104)
    if depth is not False:
      tracer = DebugTracer("__GEN1", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(104, self.getAtomString(104)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _TOKEN(self, depth = 0):
    rule = self.rule(105)
    if depth is not False:
      tracer = DebugTracer("_TOKEN", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(105, self.getAtomString(105)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 17:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_IDENTIFIER, tracer) )
      return tree
    elif rule == 33:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._KEYWORD(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 51:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_STRING_LITERAL, tracer) )
      return tree
    elif rule == 105:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PUNCTUATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 159:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_PP_NUMBER, tracer) )
      return tree
    elif rule == 190:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._CONSTANT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _KEYWORD(self, depth = 0):
    rule = self.rule(106)
    if depth is not False:
      tracer = DebugTracer("_KEYWORD", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(106, self.getAtomString(106)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 5:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_IF, tracer) )
      return tree
    elif rule == 9:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DOUBLE, tracer) )
      return tree
    elif rule == 28:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_INT, tracer) )
      return tree
    elif rule == 38:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_VOID, tracer) )
      return tree
    elif rule == 39:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RETURN, tracer) )
      return tree
    elif rule == 42:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_INLINE, tracer) )
      return tree
    elif rule == 47:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_WHILE, tracer) )
      return tree
    elif rule == 53:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LONG, tracer) )
      return tree
    elif rule == 55:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SWITCH, tracer) )
      return tree
    elif rule == 59:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL__BOOL, tracer) )
      return tree
    elif rule == 66:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_FLOAT, tracer) )
      return tree
    elif rule == 67:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ELSE, tracer) )
      return tree
    elif rule == 73:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_UNION, tracer) )
      return tree
    elif rule == 93:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL__IMAGINARY, tracer) )
      return tree
    elif rule == 94:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RESTRICT, tracer) )
      return tree
    elif rule == 99:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_UNSIGNED, tracer) )
      return tree
    elif rule == 100:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_STATIC, tracer) )
      return tree
    elif rule == 103:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_AUTO, tracer) )
      return tree
    elif rule == 114:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL__COMPLEX, tracer) )
      return tree
    elif rule == 115:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_CHAR, tracer) )
      return tree
    elif rule == 116:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_CASE, tracer) )
      return tree
    elif rule == 118:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DO, tracer) )
      return tree
    elif rule == 120:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_FOR, tracer) )
      return tree
    elif rule == 127:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_CONST, tracer) )
      return tree
    elif rule == 129:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SHORT, tracer) )
      return tree
    elif rule == 135:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_VOLATILE, tracer) )
      return tree
    elif rule == 136:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SIZEOF, tracer) )
      return tree
    elif rule == 142:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_STRUCT, tracer) )
      return tree
    elif rule == 153:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ENUM, tracer) )
      return tree
    elif rule == 154:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DEFAULT, tracer) )
      return tree
    elif rule == 156:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_REGISTER, tracer) )
      return tree
    elif rule == 169:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_TYPEDEF, tracer) )
      return tree
    elif rule == 174:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_GOTO, tracer) )
      return tree
    elif rule == 177:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BREAK, tracer) )
      return tree
    elif rule == 183:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SIGNED, tracer) )
      return tree
    elif rule == 187:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_EXTERN, tracer) )
      return tree
    elif rule == 189:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_CONTINUE, tracer) )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _TERMINALS(self, depth = 0):
    rule = self.rule(107)
    if depth is not False:
      tracer = DebugTracer("_TERMINALS", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(107, self.getAtomString(107)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 1:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ADD, tracer) )
      return tree
    elif rule == 2:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RBRACE, tracer) )
      return tree
    elif rule == 4:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_OR, tracer) )
      return tree
    elif rule == 6:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_MULEQ, tracer) )
      return tree
    elif rule == 7:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_MODEQ, tracer) )
      return tree
    elif rule == 10:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LONG, tracer) )
      return tree
    elif rule == 11:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DECIMAL_FLOATING_CONSTANT, tracer) )
      return tree
    elif rule == 13:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_STRING_LITERAL, tracer) )
      return tree
    elif rule == 15:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LSQUARE, tracer) )
      return tree
    elif rule == 19:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_REGISTER, tracer) )
      return tree
    elif rule == 20:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITAND, tracer) )
      return tree
    elif rule == 23:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SUBEQ, tracer) )
      return tree
    elif rule == 24:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ENUM, tracer) )
      return tree
    elif rule == 25:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RETURN, tracer) )
      return tree
    elif rule == 26:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_MOD, tracer) )
      return tree
    elif rule == 27:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_COLON, tracer) )
      return tree
    elif rule == 29:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BOOL, tracer) )
      return tree
    elif rule == 30:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LTEQ, tracer) )
      return tree
    elif rule == 35:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_FOR, tracer) )
      return tree
    elif rule == 36:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_POUNDPOUND, tracer) )
      return tree
    elif rule == 37:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SHORT, tracer) )
      return tree
    elif rule == 41:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ELIPSIS, tracer) )
      return tree
    elif rule == 43:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITXOR, tracer) )
      return tree
    elif rule == 45:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_IDENTIFIER, tracer) )
      return tree
    elif rule == 48:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RSQUARE, tracer) )
      return tree
    elif rule == 50:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DOT, tracer) )
      return tree
    elif rule == 52:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_TILDE, tracer) )
      return tree
    elif rule == 54:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DO, tracer) )
      return tree
    elif rule == 56:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_IF, tracer) )
      return tree
    elif rule == 57:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_UNION, tracer) )
      return tree
    elif rule == 58:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SIZEOF, tracer) )
      return tree
    elif rule == 60:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LBRACE, tracer) )
      return tree
    elif rule == 61:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_CONST, tracer) )
      return tree
    elif rule == 62:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_FLOAT, tracer) )
      return tree
    elif rule == 64:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_EXCLAMATION_POINT, tracer) )
      return tree
    elif rule == 65:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_IMAGINARY, tracer) )
      return tree
    elif rule == 69:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SIGNED, tracer) )
      return tree
    elif rule == 70:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_STATIC, tracer) )
      return tree
    elif rule == 71:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ARROW, tracer) )
      return tree
    elif rule == 72:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LBRACE, tracer) )
      return tree
    elif rule == 74:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_COMPLEX, tracer) )
      return tree
    elif rule == 75:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_GOTO, tracer) )
      return tree
    elif rule == 76:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LSHIFT, tracer) )
      return tree
    elif rule == 78:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RSQUARE, tracer) )
      return tree
    elif rule == 79:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_STRUCT, tracer) )
      return tree
    elif rule == 80:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_POUND, tracer) )
      return tree
    elif rule == 81:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_HEXADECIMAL_FLOATING_CONSTANT, tracer) )
      return tree
    elif rule == 83:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_INLINE, tracer) )
      return tree
    elif rule == 86:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RSHIFT, tracer) )
      return tree
    elif rule == 87:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RPAREN, tracer) )
      return tree
    elif rule == 88:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DOUBLE, tracer) )
      return tree
    elif rule == 90:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_AND, tracer) )
      return tree
    elif rule == 92:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_AUTO, tracer) )
      return tree
    elif rule == 96:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_EXTERN, tracer) )
      return tree
    elif rule == 97:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITANDEQ, tracer) )
      return tree
    elif rule == 98:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_TYPEDEF, tracer) )
      return tree
    elif rule == 101:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RESTRICT, tracer) )
      return tree
    elif rule == 102:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ADDEQ, tracer) )
      return tree
    elif rule == 104:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_NEQ, tracer) )
      return tree
    elif rule == 107:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RSHIFTEQ, tracer) )
      return tree
    elif rule == 109:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_NOT, tracer) )
      return tree
    elif rule == 112:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_GT, tracer) )
      return tree
    elif rule == 113:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_MUL, tracer) )
      return tree
    elif rule == 119:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BREAK, tracer) )
      return tree
    elif rule == 121:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SUB, tracer) )
      return tree
    elif rule == 122:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_UNSIGNED, tracer) )
      return tree
    elif rule == 123:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITXOREQ, tracer) )
      return tree
    elif rule == 125:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SEMI, tracer) )
      return tree
    elif rule == 126:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RBRACE, tracer) )
      return tree
    elif rule == 128:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_CONTINUE, tracer) )
      return tree
    elif rule == 130:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_EQ, tracer) )
      return tree
    elif rule == 132:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_POUNDPOUND, tracer) )
      return tree
    elif rule == 134:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_UNIVERSAL_CHARACTER_NAME, tracer) )
      return tree
    elif rule == 137:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_VOID, tracer) )
      return tree
    elif rule == 138:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SWITCH, tracer) )
      return tree
    elif rule == 139:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LSHIFTEQ, tracer) )
      return tree
    elif rule == 141:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LT, tracer) )
      return tree
    elif rule == 143:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_CHAR, tracer) )
      return tree
    elif rule == 144:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ELSE, tracer) )
      return tree
    elif rule == 145:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_INT, tracer) )
      return tree
    elif rule == 147:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LPAREN, tracer) )
      return tree
    elif rule == 149:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITOR, tracer) )
      return tree
    elif rule == 150:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_QUESTIONMARK, tracer) )
      return tree
    elif rule == 151:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_NUMBER, tracer) )
      return tree
    elif rule == 155:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_INTEGER_CONSTANT, tracer) )
      return tree
    elif rule == 157:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_CASE, tracer) )
      return tree
    elif rule == 158:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_WHILE, tracer) )
      return tree
    elif rule == 160:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_GTEQ, tracer) )
      return tree
    elif rule == 162:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DECR, tracer) )
      return tree
    elif rule == 165:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_CHARACTER_CONSTANT, tracer) )
      return tree
    elif rule == 166:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_VOLATILE, tracer) )
      return tree
    elif rule == 170:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_POUND, tracer) )
      return tree
    elif rule == 171:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITOREQ, tracer) )
      return tree
    elif rule == 172:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_HEADER_NAME, tracer) )
      return tree
    elif rule == 173:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ASSIGN, tracer) )
      return tree
    elif rule == 178:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_COMMA, tracer) )
      return tree
    elif rule == 179:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DIV, tracer) )
      return tree
    elif rule == 180:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LSQUARE, tracer) )
      return tree
    elif rule == 182:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_INCR, tracer) )
      return tree
    elif rule == 185:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DEFAULT, tracer) )
      return tree
    elif rule == 188:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DIVEQ, tracer) )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _TYPE_QUALIFIER(self, depth = 0):
    rule = self.rule(108)
    if depth is not False:
      tracer = DebugTracer("_TYPE_QUALIFIER", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(108, self.getAtomString(108)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _TRANSLATION_UNIT(self, depth = 0):
    rule = self.rule(109)
    if depth is not False:
      tracer = DebugTracer("_TRANSLATION_UNIT", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(109, self.getAtomString(109)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN2(self, depth = 0):
    rule = self.rule(110)
    if depth is not False:
      tracer = DebugTracer("__GEN2", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(110, self.getAtomString(110)), tracer )
    tree.list = 'nlist'
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __DIRECT_DECLARATOR(self, depth = 0):
    rule = self.rule(111)
    if depth is not False:
      tracer = DebugTracer("__DIRECT_DECLARATOR", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(111, self.getAtomString(111)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _CONSTANT(self, depth = 0):
    rule = self.rule(112)
    if depth is not False:
      tracer = DebugTracer("_CONSTANT", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(112, self.getAtomString(112)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  bp0 = {
    0: 10000,
    1: 15000,
    5: 2000,
    8: 1000,
    10: 5000,
    12: 8000,
    15: 2000,
    16: 6000,
    17: 13000,
    20: 15000,
    21: 2000,
    24: 2000,
    26: 4000,
    31: 13000,
    32: 10000,
    33: 12000,
    34: 15000,
    35: 11000,
    37: 2000,
    47: 7000,
    48: 10000,
    60: 2000,
    62: 10000,
    67: 2000,
    72: 13000,
    73: 2000,
    77: 11000,
    80: 15000,
    81: 3000,
    84: 2000,
    86: 15000,
    88: 15000,
    90: 2000,
    93: 9000,
    96: 12000,
    98: 2000,
    100: 9000,
  }
  def expr(self):
    return self.__EXPR()
  def __EXPR( self, rbp = 0, depth = 0 ):
    t = self.sym
    if depth is not False:
      tracer = DebugTracer("(expr) __EXPR", str(self.sym), 'N/A', depth)
      depth = depth + 1
    else:
      tracer = None
    left = self.nud0(depth)
    if isinstance(left, ParseTree):
      tracer.add(left.tracer)
    while rbp < self.binding_power(self.sym, self.bp0):
      left = self.led0(left, depth)
      if isinstance(left, ParseTree):
        tracer.add(left.tracer)
    if left:
      left.isExpr = True
      left.tracer = tracer
    return left
  def nud0(self, tracer):
    tree = ParseTree( NonTerminal(self.str_nonterminal['_expr'], '_expr') )
    if self.sym.getId() == 64:
      return self.expect( 64, tracer )
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      return tree
    if self.sym.getId() == 16:
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(14000) )
      tree.astTransform = AstTransformNodeCreator('AddressOf', {'var': 1})
      return tree
    if self.sym.getId() == 34:
      tree.add( self.expect( 34, tracer ) ) #here?
      tree.add(self.__EXPR())
      tree.add( self.expect( 68, tracer ) ) #here?
      return tree
    if self.sym.getId() == 101:
      return tree
    if self.sym.getId() == 1:
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(14000) )
      tree.astTransform = AstTransformNodeCreator('PreDecr', {'var': 1})
      return tree
    if self.sym.getId() == 72:
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(14000) )
      tree.astTransform = AstTransformNodeCreator('Dereference', {'var': 1})
      return tree
    if self.sym.getId() == 42:
      return self.expect( 42, tracer )
      return tree
    if self.sym.getId() == 112:
      return self.expect( 112, tracer )
      return tree
    if self.sym.getId() == 88:
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(14000) )
      tree.astTransform = AstTransformNodeCreator('PreIncr', {'var': 1})
      return tree
  def led0(self, left, tracer):
    tree = ParseTree( NonTerminal(self.str_nonterminal['_expr'], '_expr') )
    if self.sym.getId() == 0:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(10000) )
      tree.astTransform = AstTransformNodeCreator('GreaterThan', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 1:
      if left:
        tree.add( left )
      tree.add( self.expect( 1, tracer ) )
      tree.astTransform = AstTransformNodeCreator('PostDecr', {'var': 0})
      return tree
    if self.sym.getId() == 5:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(1999) )
      tree.astTransform = AstTransformNodeCreator('RightShiftAssign', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 8:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(1000) )
      tree.astTransform = AstTransformNodeCreator('Comma', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 12:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(8000) )
      tree.astTransform = AstTransformNodeCreator('BitOR', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 15:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(1999) )
      tree.astTransform = AstTransformNodeCreator('AddAssign', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 16:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(6000) )
      tree.astTransform = AstTransformNodeCreator('BitAND', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 17:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(13000) )
      tree.astTransform = AstTransformNodeCreator('Mod', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 20:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(0) )
      tree.astTransform = AstTransformNodeCreator('MemberSelect', {'member': 2, 'object': 0})
      return tree
    if self.sym.getId() == 21:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(1999) )
      tree.astTransform = AstTransformNodeCreator('ORAssign', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 24:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(1999) )
      tree.astTransform = AstTransformNodeCreator('MultiplyAssign', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 31:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(13000) )
      tree.astTransform = AstTransformNodeCreator('Div', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 32:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(10000) )
      tree.astTransform = AstTransformNodeCreator('LessThanEq', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 33:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(12000) )
      tree.astTransform = AstTransformNodeCreator('Add', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 34:
      if left:
        tree.add( left )
      ls = AstList()
      tree.add( self.expect( 34, tracer ) )
      if self.sym.getId() != 68:
        while 1:
          ls.append( self.__EXPR() )
          if self.sym.getId() != 8:
            break
          self.expect( 8, tracer )
      tree.add( ls )
      tree.add( self.expect(68, tracer ) )
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      return tree
    if self.sym.getId() == 35:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(11000) )
      tree.astTransform = AstTransformNodeCreator('LeftShift', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 37:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(1999) )
      tree.astTransform = AstTransformNodeCreator('Assign', {'var': 0, 'value': 2})
      return tree
    if self.sym.getId() == 47:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(7000) )
      tree.astTransform = AstTransformNodeCreator('BitXOR', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 48:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(10000) )
      tree.astTransform = AstTransformNodeCreator('GreaterThanEq', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 60:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(1999) )
      tree.astTransform = AstTransformNodeCreator('XORAssign', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 62:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(10000) )
      tree.astTransform = AstTransformNodeCreator('LessThan', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 67:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(1999) )
      tree.astTransform = AstTransformNodeCreator('SubtractAssign', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 72:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(13000) )
      tree.astTransform = AstTransformNodeCreator('Mul', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 73:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(1999) )
      tree.astTransform = AstTransformNodeCreator('DivideAssign', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 77:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(11000) )
      tree.astTransform = AstTransformNodeCreator('RightShift', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 80:
      if left:
        tree.add( left )
      ls = AstList()
      tree.add( self.expect( 80, tracer ) )
      if self.sym.getId() != 44:
        while 1:
          ls.append( self.__EXPR() )
          if self.sym.getId() != 8:
            break
          self.expect( 8, tracer )
      tree.add( ls )
      tree.add( self.expect(44, tracer ) )
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      return tree
    if self.sym.getId() == 81:
      if left:
        tree.add( left )
      tree.add( self.expect( 81, tracer ) )
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      tree.add(self.__EXPR())
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      tree.add( self.expect( 39, tracer ) )
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      tree.add(self.__EXPR())
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      return tree
    if self.sym.getId() == 84:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(1999) )
      tree.astTransform = AstTransformNodeCreator('ModAssign', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 86:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(0) )
      tree.astTransform = AstTransformNodeCreator('DerefMemberSelect', {'member': 2, 'object': 0})
      return tree
    if self.sym.getId() == 88:
      if left:
        tree.add( left )
      tree.add( self.expect( 88, tracer ) )
      tree.astTransform = AstTransformNodeCreator('PostIncr', {'var': 0})
      return tree
    if self.sym.getId() == 90:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(1999) )
      tree.astTransform = AstTransformNodeCreator('ANDAssign', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 96:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(12000) )
      tree.astTransform = AstTransformNodeCreator('Sub', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 98:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(1999) )
      tree.astTransform = AstTransformNodeCreator('LeftShiftAssign', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 100:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(8999) )
      tree.astTransform = AstTransformNodeCreator('Equals', {'right': 2, 'left': 0})
      return tree
  bp1 = {
    80: 1000,
  }
  def direct_declarator(self):
    return self.__DIRECT_DECLARATOR()
  def __DIRECT_DECLARATOR( self, rbp = 0, depth = 0 ):
    t = self.sym
    if depth is not False:
      tracer = DebugTracer("(expr) __DIRECT_DECLARATOR", str(self.sym), 'N/A', depth)
      depth = depth + 1
    else:
      tracer = None
    left = self.nud1(depth)
    if isinstance(left, ParseTree):
      tracer.add(left.tracer)
    while rbp < self.binding_power(self.sym, self.bp1):
      left = self.led1(left, depth)
      if isinstance(left, ParseTree):
        tracer.add(left.tracer)
    if left:
      left.isExpr = True
      left.tracer = tracer
    return left
  def nud1(self, tracer):
    tree = ParseTree( NonTerminal(self.str_nonterminal['_direct_declarator'], '_direct_declarator') )
    if self.sym.getId() == 64:
      return self.expect( 64, tracer )
      return tree
    if self.sym.getId() == 111:
      return tree
  def led1(self, left, tracer):
    tree = ParseTree( NonTerminal(self.str_nonterminal['_expr'], '_expr') )
    if self.sym.getId() == 80:
      if left:
        tree.add( left )
      tree.add( self.expect( 80, tracer ) )
      tree.add( self.expect( 44, tracer ) )
      return tree
