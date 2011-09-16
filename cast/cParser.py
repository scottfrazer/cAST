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
  def toString(self, format):
    if format == 'type':
      return self.str
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
    self.isNud = False
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
          if idx == '$':
            child = self.children[0]
          elif isinstance(self.children[0], ParseTree) and self.children[0].isNud: # implies .isExpr
            if idx < len(self.children[0].children):
              child = self.children[0].children[idx]
            else:
              index = idx - len(self.children[0].children) + 1
              child = self.children[index]
          else:
            child = self.children[idx]
          if isinstance(child, ParseTree):
            parameters[name] = child.toAst()
          elif isinstance(child, list):
            parameters[name] = [x.toAst() for x in child]
          else:
            parameters[name] = child
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
class AstPrettyPrintable(Ast):
  def __init__(self, ast, tokenFormat='type'):
    self.__dict__.update(locals())
  def getAttr(self, attr):
    return self.ast.getAttr(attr)
  def __str__(self):
    return self._prettyPrint(self.ast, 0)
  def _prettyPrint(self, ast, indent = 0):
    indentStr = ''.join([' ' for x in range(indent)])
    if isinstance(ast, Ast):
      string = '%s(%s:\n' % (indentStr, ast.name)
      string += ',\n'.join([ \
        '%s  %s=%s' % (indentStr, name, self._prettyPrint(value, indent + 2).lstrip()) for name, value in ast.attributes.items() \
      ])
      string += '\n%s)' % (indentStr)
      return string
    elif isinstance(ast, list):
      if len(ast) == 0:
        return '%s[]' % (indentStr)
      string = '%s[\n' % (indentStr)
      string += ',\n'.join([self._prettyPrint(element, indent + 2) for element in ast])
      string += '\n%s]' % (indentStr)
      return string
    elif isinstance(ast, Terminal):
      return '%s%s' % (indentStr, ast.toString(self.tokenFormat))
    else:
      return '%s%s' % (indentStr, ast)
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
  TERMINAL_TILDE = 0
  TERMINAL_BOOL = 1
  TERMINAL_PP_NUMBER = 2
  TERMINAL_MODEQ = 3
  TERMINAL_ASSIGN = 4
  TERMINAL_DIVEQ = 5
  TERMINAL_SUB = 6
  TERMINAL_IMAGINARY = 7
  TERMINAL_DOUBLE = 8
  TERMINAL_AUTO = 9
  TERMINAL_MULEQ = 10
  TERMINAL_VOLATILE = 11
  TERMINAL_ADD = 12
  TERMINAL_BREAK = 13
  TERMINAL_INT = 14
  TERMINAL_COMMA = 15
  TERMINAL_WHILE = 16
  TERMINAL_MUL = 17
  TERMINAL_LT = 18
  TERMINAL_DO = 19
  TERMINAL_HEADER_NAME = 20
  TERMINAL_GT = 21
  TERMINAL_POUNDPOUND = 22
  TERMINAL_COMPLEX = 23
  TERMINAL__BOOL = 24
  TERMINAL_LSHIFT = 25
  TERMINAL_DIV = 26
  TERMINAL_HEXADECIMAL_FLOATING_CONSTANT = 27
  TERMINAL_CHAR = 28
  TERMINAL_POUND = 29
  TERMINAL_IF = 30
  TERMINAL_UNIVERSAL_CHARACTER_NAME = 31
  TERMINAL_AMPERSAND = 32
  TERMINAL_CASE = 33
  TERMINAL_CONST = 34
  TERMINAL_GOTO = 35
  TERMINAL_RESTRICT = 36
  TERMINAL_LTEQ = 37
  TERMINAL__IMAGINARY = 38
  TERMINAL_DECR = 39
  TERMINAL_VOID = 40
  TERMINAL_CONTINUE = 41
  TERMINAL_CHARACTER_CONSTANT = 42
  TERMINAL_LONG = 43
  TERMINAL_ARROW = 44
  TERMINAL_INLINE = 45
  TERMINAL_INCR = 46
  TERMINAL_SEMI = 47
  TERMINAL_DEFAULT = 48
  TERMINAL_FOR = 49
  TERMINAL_SHORT = 50
  TERMINAL_DOT = 51
  TERMINAL_OR = 52
  TERMINAL_RSQUARE = 53
  TERMINAL_QUESTIONMARK = 54
  TERMINAL_SIGNED = 55
  TERMINAL_RETURN = 56
  TERMINAL_LBRACE = 57
  TERMINAL_AND = 58
  TERMINAL_BITOREQ = 59
  TERMINAL_FLOAT = 60
  TERMINAL_DEFINED = 61
  TERMINAL_NEQ = 62
  TERMINAL_RBRACE = 63
  TERMINAL_BITOR = 64
  TERMINAL_BITXOREQ = 65
  TERMINAL_STATIC = 66
  TERMINAL_SIZEOF = 67
  TERMINAL_BITAND = 68
  TERMINAL_LSQUARE = 69
  TERMINAL_BITXOR = 70
  TERMINAL_DECIMAL_FLOATING_CONSTANT = 71
  TERMINAL_BITANDEQ = 72
  TERMINAL_UNSIGNED = 73
  TERMINAL_STRUCT = 74
  TERMINAL_ELIPSIS = 75
  TERMINAL_NUMBER = 76
  TERMINAL_RSHIFTEQ = 77
  TERMINAL_IDENTIFIER = 78
  TERMINAL_EXTERN = 79
  TERMINAL_SWITCH = 80
  TERMINAL_REGISTER = 81
  TERMINAL_LPAREN = 82
  TERMINAL_EQ = 83
  TERMINAL_INTEGER_CONSTANT = 84
  TERMINAL_COLON = 85
  TERMINAL_ENUM = 86
  TERMINAL_UNION = 87
  TERMINAL_TYPEDEF = 88
  TERMINAL_MOD = 89
  TERMINAL_RPAREN = 90
  TERMINAL_LSHIFTEQ = 91
  TERMINAL_STRING_LITERAL = 92
  TERMINAL__COMPLEX = 93
  TERMINAL_SUBEQ = 94
  TERMINAL_LPAREN_CAST = 95
  TERMINAL_BITNOT = 96
  TERMINAL_EXCLAMATION_POINT = 97
  TERMINAL_GTEQ = 98
  TERMINAL_ELSE = 99
  TERMINAL_NOT = 100
  TERMINAL_ADDEQ = 101
  TERMINAL_RSHIFT = 102
  terminal_str = {
    0: 'tilde',
    1: 'bool',
    2: 'pp_number',
    3: 'modeq',
    4: 'assign',
    5: 'diveq',
    6: 'sub',
    7: 'imaginary',
    8: 'double',
    9: 'auto',
    10: 'muleq',
    11: 'volatile',
    12: 'add',
    13: 'break',
    14: 'int',
    15: 'comma',
    16: 'while',
    17: 'mul',
    18: 'lt',
    19: 'do',
    20: 'header_name',
    21: 'gt',
    22: 'poundpound',
    23: 'complex',
    24: '_bool',
    25: 'lshift',
    26: 'div',
    27: 'hexadecimal_floating_constant',
    28: 'char',
    29: 'pound',
    30: 'if',
    31: 'universal_character_name',
    32: 'ampersand',
    33: 'case',
    34: 'const',
    35: 'goto',
    36: 'restrict',
    37: 'lteq',
    38: '_imaginary',
    39: 'decr',
    40: 'void',
    41: 'continue',
    42: 'character_constant',
    43: 'long',
    44: 'arrow',
    45: 'inline',
    46: 'incr',
    47: 'semi',
    48: 'default',
    49: 'for',
    50: 'short',
    51: 'dot',
    52: 'or',
    53: 'rsquare',
    54: 'questionmark',
    55: 'signed',
    56: 'return',
    57: 'lbrace',
    58: 'and',
    59: 'bitoreq',
    60: 'float',
    61: 'defined',
    62: 'neq',
    63: 'rbrace',
    64: 'bitor',
    65: 'bitxoreq',
    66: 'static',
    67: 'sizeof',
    68: 'bitand',
    69: 'lsquare',
    70: 'bitxor',
    71: 'decimal_floating_constant',
    72: 'bitandeq',
    73: 'unsigned',
    74: 'struct',
    75: 'elipsis',
    76: 'number',
    77: 'rshifteq',
    78: 'identifier',
    79: 'extern',
    80: 'switch',
    81: 'register',
    82: 'lparen',
    83: 'eq',
    84: 'integer_constant',
    85: 'colon',
    86: 'enum',
    87: 'union',
    88: 'typedef',
    89: 'mod',
    90: 'rparen',
    91: 'lshifteq',
    92: 'string_literal',
    93: '_complex',
    94: 'subeq',
    95: 'lparen_cast',
    96: 'bitnot',
    97: 'exclamation_point',
    98: 'gteq',
    99: 'else',
    100: 'not',
    101: 'addeq',
    102: 'rshift',
  }
  nonterminal_str = {
    103: 'translation_unit',
    104: 'type_qualifier',
    105: 'token',
    106: 'comma_opt',
    107: 'pp',
    108: '_direct_declarator',
    109: '_gen0',
    110: 'type_name',
    111: '_gen2',
    112: 'keyword',
    113: '_expr',
    114: '_gen1',
    115: 'terminals',
    116: '_gen4',
    117: 'initilizer_list_item',
    118: '_gen3',
    119: 'punctuator',
    120: 'constant',
  }
  str_terminal = {
    'tilde': 0,
    'bool': 1,
    'pp_number': 2,
    'modeq': 3,
    'assign': 4,
    'diveq': 5,
    'sub': 6,
    'imaginary': 7,
    'double': 8,
    'auto': 9,
    'muleq': 10,
    'volatile': 11,
    'add': 12,
    'break': 13,
    'int': 14,
    'comma': 15,
    'while': 16,
    'mul': 17,
    'lt': 18,
    'do': 19,
    'header_name': 20,
    'gt': 21,
    'poundpound': 22,
    'complex': 23,
    '_bool': 24,
    'lshift': 25,
    'div': 26,
    'hexadecimal_floating_constant': 27,
    'char': 28,
    'pound': 29,
    'if': 30,
    'universal_character_name': 31,
    'ampersand': 32,
    'case': 33,
    'const': 34,
    'goto': 35,
    'restrict': 36,
    'lteq': 37,
    '_imaginary': 38,
    'decr': 39,
    'void': 40,
    'continue': 41,
    'character_constant': 42,
    'long': 43,
    'arrow': 44,
    'inline': 45,
    'incr': 46,
    'semi': 47,
    'default': 48,
    'for': 49,
    'short': 50,
    'dot': 51,
    'or': 52,
    'rsquare': 53,
    'questionmark': 54,
    'signed': 55,
    'return': 56,
    'lbrace': 57,
    'and': 58,
    'bitoreq': 59,
    'float': 60,
    'defined': 61,
    'neq': 62,
    'rbrace': 63,
    'bitor': 64,
    'bitxoreq': 65,
    'static': 66,
    'sizeof': 67,
    'bitand': 68,
    'lsquare': 69,
    'bitxor': 70,
    'decimal_floating_constant': 71,
    'bitandeq': 72,
    'unsigned': 73,
    'struct': 74,
    'elipsis': 75,
    'number': 76,
    'rshifteq': 77,
    'identifier': 78,
    'extern': 79,
    'switch': 80,
    'register': 81,
    'lparen': 82,
    'eq': 83,
    'integer_constant': 84,
    'colon': 85,
    'enum': 86,
    'union': 87,
    'typedef': 88,
    'mod': 89,
    'rparen': 90,
    'lshifteq': 91,
    'string_literal': 92,
    '_complex': 93,
    'subeq': 94,
    'lparen_cast': 95,
    'bitnot': 96,
    'exclamation_point': 97,
    'gteq': 98,
    'else': 99,
    'not': 100,
    'addeq': 101,
    'rshift': 102,
  }
  str_nonterminal = {
    'translation_unit': 103,
    'type_qualifier': 104,
    'token': 105,
    'comma_opt': 106,
    'pp': 107,
    '_direct_declarator': 108,
    '_gen0': 109,
    'type_name': 110,
    '_gen2': 111,
    'keyword': 112,
    '_expr': 113,
    '_gen1': 114,
    'terminals': 115,
    '_gen4': 116,
    'initilizer_list_item': 117,
    '_gen3': 118,
    'punctuator': 119,
    'constant': 120,
  }
  terminal_count = 103
  nonterminal_count = 18
  parse_table = [
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [141, -1, 168, 141, 141, -1, 141, -1, 154, 154, 141, 154, 141, 154, 154, 141, 154, 141, 141, 154, -1, 141, 141, -1, 154, 141, 141, -1, 154, 141, 154, -1, 141, 154, 154, 154, 154, 141, 154, 141, 154, 154, -1, 154, 141, 154, 141, 141, 154, 154, 154, 141, 141, 141, 141, 154, 154, 141, 141, 141, 154, -1, 141, 141, 141, 141, 154, 154, -1, 141, 141, -1, 141, 154, 154, 141, -1, 141, 119, 154, 154, 154, 141, 141, -1, 141, 154, 154, 154, 141, 141, 141, 113, 154, 141, -1, -1, 141, 141, 154, -1, 141, 141],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 132, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, 31, 193, -1, 15, -1, 105, 90, -1, 34, -1, -1, 16, -1, -1, -1, -1, 136, -1, -1, -1, 148, -1, 164, -1, -1, 170, 108, 49, 123, -1, 42, -1, 5, 186, -1, 190, -1, 51, -1, -1, 4, 30, 98, -1, -1, -1, -1, 63, 71, -1, -1, -1, 12, -1, -1, -1, -1, -1, 147, 103, -1, -1, -1, -1, -1, 195, 68, -1, -1, -1, -1, 92, 25, 128, -1, -1, -1, -1, 191, 89, 134, -1, -1, -1, -1, 80, -1, -1, -1, -1, -1, 47, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [167, 10, -1, 84, 64, 69, 130, 58, 37, 194, 52, 59, 100, 22, 73, 117, 133, 23, 41, 96, 161, 56, 144, 67, -1, 24, 122, 137, 192, 140, 146, 158, -1, 76, 82, 104, 124, 21, -1, 83, 85, 17, 39, 7, 72, 196, 179, 75, 157, 115, 53, 79, 169, 101, 95, 70, 38, 19, 189, 78, 40, -1, 118, 6, 114, 66, 36, 88, 81, 110, 142, 125, 45, 180, 18, 57, 86, 106, 91, 50, 111, 197, 87, 20, 94, 127, 178, 93, 2, 77, 26, 152, 171, -1, 112, -1, -1, 32, 33, 156, 35, 14, 8],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 54, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [160, -1, -1, 176, 135, -1, 185, -1, -1, -1, 97, -1, 102, -1, -1, 143, -1, 187, 151, -1, -1, 150, 155, -1, -1, 120, 145, -1, -1, 177, -1, -1, 165, -1, -1, -1, -1, 27, -1, 182, -1, -1, -1, -1, 11, -1, 1, 99, -1, -1, -1, 173, 13, 139, 107, -1, -1, 166, 28, 3, -1, -1, 61, 62, 44, 172, -1, -1, -1, 131, 163, -1, 29, -1, -1, 55, -1, 126, -1, -1, -1, -1, 0, 9, -1, 129, -1, -1, -1, 121, 175, 138, -1, -1, 188, -1, -1, 46, 43, -1, -1, 183, 109],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1]
  ]
  def terminal(self, str):
    return self.str_terminal[str]
  def terminalNames(self):
    return list(self.str_terminal.keys())
  def isTerminal(self, id):
    return 0 <= id <= 102
  def isNonTerminal(self, id):
    return 103 <= id <= 120
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
    return self.parse_table[n - 103][self.sym.getId()]
  def call(self, nt_str):
    return getattr(self, nt_str)()
  def _TRANSLATION_UNIT(self, depth = 0):
    rule = self.rule(103)
    if depth is not False:
      tracer = DebugTracer("_TRANSLATION_UNIT", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(103, self.getAtomString(103)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _TYPE_QUALIFIER(self, depth = 0):
    rule = self.rule(104)
    if depth is not False:
      tracer = DebugTracer("_TYPE_QUALIFIER", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(104, self.getAtomString(104)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
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
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 65:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._CONSTANT(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 113:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(92, tracer) ) # string_literal
      return tree
    elif rule == 119:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(78, tracer) ) # identifier
      return tree
    elif rule == 141:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PUNCTUATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 154:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._KEYWORD(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 168:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(2, tracer) ) # pp_number
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _COMMA_OPT(self, depth = 0):
    rule = self.rule(106)
    if depth is not False:
      tracer = DebugTracer("_COMMA_OPT", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(106, self.getAtomString(106)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PP(self, depth = 0):
    rule = self.rule(107)
    if depth is not False:
      tracer = DebugTracer("_PP", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(107, self.getAtomString(107)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 132:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(61, tracer) ) # defined
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __DIRECT_DECLARATOR(self, depth = 0):
    rule = self.rule(108)
    if depth is not False:
      tracer = DebugTracer("__DIRECT_DECLARATOR", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(108, self.getAtomString(108)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN0(self, depth = 0):
    rule = self.rule(109)
    if depth is not False:
      tracer = DebugTracer("__GEN0", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(109, self.getAtomString(109)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _TYPE_NAME(self, depth = 0):
    rule = self.rule(110)
    if depth is not False:
      tracer = DebugTracer("_TYPE_NAME", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(110, self.getAtomString(110)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN2(self, depth = 0):
    rule = self.rule(111)
    if depth is not False:
      tracer = DebugTracer("__GEN2", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(111, self.getAtomString(111)), tracer )
    tree.list = 'slist'
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 162:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._INITILIZER_LIST_ITEM(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN3(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _KEYWORD(self, depth = 0):
    rule = self.rule(112)
    if depth is not False:
      tracer = DebugTracer("_KEYWORD", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(112, self.getAtomString(112)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 4:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(48, tracer) ) # default
      return tree
    elif rule == 5:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(40, tracer) ) # void
      return tree
    elif rule == 12:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(60, tracer) ) # float
      return tree
    elif rule == 15:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(11, tracer) ) # volatile
      return tree
    elif rule == 16:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(19, tracer) ) # do
      return tree
    elif rule == 25:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(80, tracer) ) # switch
      return tree
    elif rule == 30:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(49, tracer) ) # for
      return tree
    elif rule == 31:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(8, tracer) ) # double
      return tree
    elif rule == 34:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(16, tracer) ) # while
      return tree
    elif rule == 42:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(38, tracer) ) # _imaginary
      return tree
    elif rule == 47:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(99, tracer) ) # else
      return tree
    elif rule == 49:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(35, tracer) ) # goto
      return tree
    elif rule == 51:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(45, tracer) ) # inline
      return tree
    elif rule == 63:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(55, tracer) ) # signed
      return tree
    elif rule == 68:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(74, tracer) ) # struct
      return tree
    elif rule == 71:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(56, tracer) ) # return
      return tree
    elif rule == 80:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(93, tracer) ) # _complex
      return tree
    elif rule == 89:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(87, tracer) ) # union
      return tree
    elif rule == 90:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(14, tracer) ) # int
      return tree
    elif rule == 92:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(79, tracer) ) # extern
      return tree
    elif rule == 98:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(50, tracer) ) # short
      return tree
    elif rule == 103:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(67, tracer) ) # sizeof
      return tree
    elif rule == 105:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(13, tracer) ) # break
      return tree
    elif rule == 108:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(34, tracer) ) # const
      return tree
    elif rule == 123:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(36, tracer) ) # restrict
      return tree
    elif rule == 128:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(81, tracer) ) # register
      return tree
    elif rule == 134:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(88, tracer) ) # typedef
      return tree
    elif rule == 136:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(24, tracer) ) # _bool
      return tree
    elif rule == 147:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(66, tracer) ) # static
      return tree
    elif rule == 148:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(28, tracer) ) # char
      return tree
    elif rule == 164:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(30, tracer) ) # if
      return tree
    elif rule == 170:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(33, tracer) ) # case
      return tree
    elif rule == 186:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(41, tracer) ) # continue
      return tree
    elif rule == 190:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(43, tracer) ) # long
      return tree
    elif rule == 191:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(86, tracer) ) # enum
      return tree
    elif rule == 193:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(9, tracer) ) # auto
      return tree
    elif rule == 195:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(73, tracer) ) # unsigned
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN1(self, depth = 0):
    rule = self.rule(114)
    if depth is not False:
      tracer = DebugTracer("__GEN1", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(114, self.getAtomString(114)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _TERMINALS(self, depth = 0):
    rule = self.rule(115)
    if depth is not False:
      tracer = DebugTracer("_TERMINALS", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(115, self.getAtomString(115)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 2:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(88, tracer) ) # typedef
      return tree
    elif rule == 6:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(63, tracer) ) # rbrace
      return tree
    elif rule == 7:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(43, tracer) ) # long
      return tree
    elif rule == 8:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(102, tracer) ) # rshift
      return tree
    elif rule == 10:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(1, tracer) ) # bool
      return tree
    elif rule == 14:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(101, tracer) ) # addeq
      return tree
    elif rule == 17:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(41, tracer) ) # continue
      return tree
    elif rule == 18:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(74, tracer) ) # struct
      return tree
    elif rule == 19:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(57, tracer) ) # lbrace
      return tree
    elif rule == 20:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(83, tracer) ) # eq
      return tree
    elif rule == 21:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(37, tracer) ) # lteq
      return tree
    elif rule == 22:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(13, tracer) ) # break
      return tree
    elif rule == 23:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(17, tracer) ) # mul
      return tree
    elif rule == 24:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(25, tracer) ) # lshift
      return tree
    elif rule == 26:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(90, tracer) ) # rparen
      return tree
    elif rule == 32:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(97, tracer) ) # exclamation_point
      return tree
    elif rule == 33:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(98, tracer) ) # gteq
      return tree
    elif rule == 35:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(100, tracer) ) # not
      return tree
    elif rule == 36:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(66, tracer) ) # static
      return tree
    elif rule == 37:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(8, tracer) ) # double
      return tree
    elif rule == 38:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(56, tracer) ) # return
      return tree
    elif rule == 39:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(42, tracer) ) # character_constant
      return tree
    elif rule == 40:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(60, tracer) ) # float
      return tree
    elif rule == 41:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(18, tracer) ) # lt
      return tree
    elif rule == 45:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(72, tracer) ) # bitandeq
      return tree
    elif rule == 50:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(79, tracer) ) # extern
      return tree
    elif rule == 52:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(10, tracer) ) # muleq
      return tree
    elif rule == 53:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(50, tracer) ) # short
      return tree
    elif rule == 56:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(21, tracer) ) # gt
      return tree
    elif rule == 57:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(75, tracer) ) # elipsis
      return tree
    elif rule == 58:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(7, tracer) ) # imaginary
      return tree
    elif rule == 59:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(11, tracer) ) # volatile
      return tree
    elif rule == 64:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(4, tracer) ) # assign
      return tree
    elif rule == 66:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(65, tracer) ) # bitxoreq
      return tree
    elif rule == 67:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(23, tracer) ) # complex
      return tree
    elif rule == 69:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(5, tracer) ) # diveq
      return tree
    elif rule == 70:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(55, tracer) ) # signed
      return tree
    elif rule == 72:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(44, tracer) ) # arrow
      return tree
    elif rule == 73:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(14, tracer) ) # int
      return tree
    elif rule == 75:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(47, tracer) ) # semi
      return tree
    elif rule == 76:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(33, tracer) ) # case
      return tree
    elif rule == 77:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(89, tracer) ) # mod
      return tree
    elif rule == 78:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(59, tracer) ) # bitoreq
      return tree
    elif rule == 79:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(51, tracer) ) # dot
      return tree
    elif rule == 81:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(68, tracer) ) # bitand
      return tree
    elif rule == 82:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(34, tracer) ) # const
      return tree
    elif rule == 83:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(39, tracer) ) # decr
      return tree
    elif rule == 84:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(3, tracer) ) # modeq
      return tree
    elif rule == 85:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(40, tracer) ) # void
      return tree
    elif rule == 86:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(76, tracer) ) # number
      return tree
    elif rule == 87:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(82, tracer) ) # lparen
      return tree
    elif rule == 88:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(67, tracer) ) # sizeof
      return tree
    elif rule == 91:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(78, tracer) ) # identifier
      return tree
    elif rule == 93:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(87, tracer) ) # union
      return tree
    elif rule == 94:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(84, tracer) ) # integer_constant
      return tree
    elif rule == 95:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(54, tracer) ) # questionmark
      return tree
    elif rule == 96:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(19, tracer) ) # do
      return tree
    elif rule == 100:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(12, tracer) ) # add
      return tree
    elif rule == 101:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(53, tracer) ) # rsquare
      return tree
    elif rule == 104:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(35, tracer) ) # goto
      return tree
    elif rule == 106:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(77, tracer) ) # rshifteq
      return tree
    elif rule == 110:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(69, tracer) ) # lsquare
      return tree
    elif rule == 111:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(80, tracer) ) # switch
      return tree
    elif rule == 112:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(94, tracer) ) # subeq
      return tree
    elif rule == 114:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(64, tracer) ) # bitor
      return tree
    elif rule == 115:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(49, tracer) ) # for
      return tree
    elif rule == 116:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(57, tracer) ) # lbrace
      return tree
    elif rule == 117:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(15, tracer) ) # comma
      return tree
    elif rule == 118:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(62, tracer) ) # neq
      return tree
    elif rule == 122:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(26, tracer) ) # div
      return tree
    elif rule == 124:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(36, tracer) ) # restrict
      return tree
    elif rule == 125:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(71, tracer) ) # decimal_floating_constant
      return tree
    elif rule == 127:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(85, tracer) ) # colon
      return tree
    elif rule == 130:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(6, tracer) ) # sub
      return tree
    elif rule == 133:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(16, tracer) ) # while
      return tree
    elif rule == 137:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(27, tracer) ) # hexadecimal_floating_constant
      return tree
    elif rule == 140:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(29, tracer) ) # pound
      return tree
    elif rule == 142:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(70, tracer) ) # bitxor
      return tree
    elif rule == 144:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(22, tracer) ) # poundpound
      return tree
    elif rule == 146:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(30, tracer) ) # if
      return tree
    elif rule == 152:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(91, tracer) ) # lshifteq
      return tree
    elif rule == 153:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(69, tracer) ) # lsquare
      return tree
    elif rule == 156:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(99, tracer) ) # else
      return tree
    elif rule == 157:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(48, tracer) ) # default
      return tree
    elif rule == 158:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(31, tracer) ) # universal_character_name
      return tree
    elif rule == 159:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(53, tracer) ) # rsquare
      return tree
    elif rule == 161:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(20, tracer) ) # header_name
      return tree
    elif rule == 167:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(0, tracer) ) # tilde
      return tree
    elif rule == 169:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(52, tracer) ) # or
      return tree
    elif rule == 171:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(92, tracer) ) # string_literal
      return tree
    elif rule == 174:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(22, tracer) ) # poundpound
      return tree
    elif rule == 178:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(86, tracer) ) # enum
      return tree
    elif rule == 179:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(46, tracer) ) # incr
      return tree
    elif rule == 180:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(73, tracer) ) # unsigned
      return tree
    elif rule == 181:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(63, tracer) ) # rbrace
      return tree
    elif rule == 184:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(29, tracer) ) # pound
      return tree
    elif rule == 189:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(58, tracer) ) # and
      return tree
    elif rule == 192:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(28, tracer) ) # char
      return tree
    elif rule == 194:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(9, tracer) ) # auto
      return tree
    elif rule == 196:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(45, tracer) ) # inline
      return tree
    elif rule == 197:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(81, tracer) ) # register
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN4(self, depth = 0):
    rule = self.rule(116)
    if depth is not False:
      tracer = DebugTracer("__GEN4", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(116, self.getAtomString(116)), tracer )
    tree.list = 'nlist'
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 149:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._TYPE_QUALIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN4(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _INITILIZER_LIST_ITEM(self, depth = 0):
    rule = self.rule(117)
    if depth is not False:
      tracer = DebugTracer("_INITILIZER_LIST_ITEM", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(117, self.getAtomString(117)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN3(self, depth = 0):
    rule = self.rule(118)
    if depth is not False:
      tracer = DebugTracer("__GEN3", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(118, self.getAtomString(118)), tracer )
    tree.list = 'slist'
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 54:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(15, tracer) ) # comma
      subtree = self._INITILIZER_LIST_ITEM(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN3(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _PUNCTUATOR(self, depth = 0):
    rule = self.rule(119)
    if depth is not False:
      tracer = DebugTracer("_PUNCTUATOR", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(119, self.getAtomString(119)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 0:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(82, tracer) ) # lparen
      return tree
    elif rule == 1:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(46, tracer) ) # incr
      return tree
    elif rule == 3:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(59, tracer) ) # bitoreq
      return tree
    elif rule == 9:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(83, tracer) ) # eq
      return tree
    elif rule == 11:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(44, tracer) ) # arrow
      return tree
    elif rule == 13:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(52, tracer) ) # or
      return tree
    elif rule == 27:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(37, tracer) ) # lteq
      return tree
    elif rule == 28:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(58, tracer) ) # and
      return tree
    elif rule == 29:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(72, tracer) ) # bitandeq
      return tree
    elif rule == 43:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(98, tracer) ) # gteq
      return tree
    elif rule == 44:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(64, tracer) ) # bitor
      return tree
    elif rule == 46:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(97, tracer) ) # exclamation_point
      return tree
    elif rule == 55:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(75, tracer) ) # elipsis
      return tree
    elif rule == 61:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(62, tracer) ) # neq
      return tree
    elif rule == 62:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(63, tracer) ) # rbrace
      return tree
    elif rule == 97:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(10, tracer) ) # muleq
      return tree
    elif rule == 99:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(47, tracer) ) # semi
      return tree
    elif rule == 102:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(12, tracer) ) # add
      return tree
    elif rule == 107:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(54, tracer) ) # questionmark
      return tree
    elif rule == 109:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(102, tracer) ) # rshift
      return tree
    elif rule == 120:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(25, tracer) ) # lshift
      return tree
    elif rule == 121:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(89, tracer) ) # mod
      return tree
    elif rule == 126:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(77, tracer) ) # rshifteq
      return tree
    elif rule == 129:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(85, tracer) ) # colon
      return tree
    elif rule == 131:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(69, tracer) ) # lsquare
      return tree
    elif rule == 135:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(4, tracer) ) # assign
      return tree
    elif rule == 138:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(91, tracer) ) # lshifteq
      return tree
    elif rule == 139:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(53, tracer) ) # rsquare
      return tree
    elif rule == 143:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(15, tracer) ) # comma
      return tree
    elif rule == 145:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(26, tracer) ) # div
      return tree
    elif rule == 150:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(21, tracer) ) # gt
      return tree
    elif rule == 151:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(18, tracer) ) # lt
      return tree
    elif rule == 155:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(22, tracer) ) # poundpound
      return tree
    elif rule == 160:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(0, tracer) ) # tilde
      return tree
    elif rule == 163:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(70, tracer) ) # bitxor
      return tree
    elif rule == 165:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(32, tracer) ) # ampersand
      return tree
    elif rule == 166:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(57, tracer) ) # lbrace
      return tree
    elif rule == 172:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(65, tracer) ) # bitxoreq
      return tree
    elif rule == 173:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(51, tracer) ) # dot
      return tree
    elif rule == 175:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(90, tracer) ) # rparen
      return tree
    elif rule == 176:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(3, tracer) ) # modeq
      return tree
    elif rule == 177:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(29, tracer) ) # pound
      return tree
    elif rule == 182:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(39, tracer) ) # decr
      return tree
    elif rule == 183:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(101, tracer) ) # addeq
      return tree
    elif rule == 185:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(6, tracer) ) # sub
      return tree
    elif rule == 187:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(17, tracer) ) # mul
      return tree
    elif rule == 188:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(94, tracer) ) # subeq
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _CONSTANT(self, depth = 0):
    rule = self.rule(120)
    if depth is not False:
      tracer = DebugTracer("_CONSTANT", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(120, self.getAtomString(120)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  infixBp0 = {
    3: 2000,
    4: 2000,
    5: 2000,
    6: 12000,
    10: 2000,
    12: 12000,
    15: 1000,
    17: 13000,
    18: 10000,
    21: 10000,
    25: 11000,
    26: 13000,
    37: 10000,
    39: 16000,
    44: 16000,
    46: 16000,
    51: 16000,
    52: 4000,
    54: 3000,
    57: 15000,
    58: 5000,
    59: 2000,
    62: 9000,
    64: 8000,
    65: 2000,
    68: 6000,
    69: 16000,
    70: 7000,
    72: 2000,
    77: 2000,
    82: 16000,
    83: 9000,
    89: 13000,
    91: 2000,
    94: 2000,
    98: 10000,
    101: 2000,
    102: 11000,
  }
  prefixBp0 = {
    96: 14000,
    100: 14000,
    6: 14000,
    39: 14000,
    46: 14000,
    17: 14000,
    68: 14000,
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
      left.isExpr = True
      left.isNud = True
      tracer.add(left.tracer)
    while rbp < self.binding_power(self.sym, self.infixBp0):
      left = self.led0(left, depth)
      if isinstance(left, ParseTree):
        tracer.add(left.tracer)
    if left:
      left.isExpr = True
      left.tracer = tracer
    return left
  def nud0(self, tracer):
    tree = ParseTree( NonTerminal(113, '_expr') )
    if self.sym.getId() == 82: # 'lparen'
      tree.astTransform = AstTransformSubstitution(2)
      tree.add( self.expect(82, tracer) )
      tree.add( self.__EXPR() )
      tree.add( self.expect(90, tracer) )
    elif self.sym.getId() == 113: # _expr
      tree.astTransform = AstTransformNodeCreator('PostDecr', {'var': 0})
      return self.expect( 113, tracer )
    elif self.sym.getId() == 78: # 'identifier'
      tree.astTransform = AstTransformSubstitution(0)
      return self.expect( 78, tracer )
    elif self.sym.getId() == 92: # 'string_literal'
      tree.astTransform = AstTransformSubstitution(0)
      return self.expect( 92, tracer )
    elif self.sym.getId() == 68: # 'bitand'
      tree.astTransform = AstTransformNodeCreator('AddressOf', {'var': 1})
      tree.add( self.expect(68, tracer) )
      tree.add( self.__EXPR( self.prefixBp0[68] ) )
    elif self.sym.getId() == 39: # 'decr'
      tree.astTransform = AstTransformNodeCreator('PreDecr', {'var': 1})
      tree.add( self.expect(39, tracer) )
      tree.add( self.__EXPR( self.prefixBp0[39] ) )
    elif self.sym.getId() == 95: # 'lparen_cast'
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 0, 'initializer': 4})
      tree.add( self.expect(95, tracer) )
      tree.add( self._TYPE_NAME() )
      tree.add( self.expect(90, tracer) )
    elif self.sym.getId() == 17: # 'mul'
      tree.astTransform = AstTransformNodeCreator('Dereference', {'var': 1})
      tree.add( self.expect(17, tracer) )
      tree.add( self.__EXPR( self.prefixBp0[17] ) )
    elif self.sym.getId() == 67: # 'sizeof'
      tree.astTransform = AstTransformNodeCreator('SizeOfVar', {'var': 1})
      tree.add( self.expect(67, tracer) )
      tree.add( self.__EXPR() )
    elif self.sym.getId() == 46: # 'incr'
      tree.astTransform = AstTransformNodeCreator('PreIncr', {'var': 1})
      tree.add( self.expect(46, tracer) )
      tree.add( self.__EXPR( self.prefixBp0[46] ) )
    elif self.sym.getId() == 120: # constant
      tree.astTransform = AstTransformSubstitution(0)
      return self.expect( 120, tracer )
    return tree
  def led0(self, left, tracer):
    tree = ParseTree( NonTerminal(113, '_expr') )
    if  self.sym.getId() == 39: # 'decr'
      tree.astTransform = AstTransformNodeCreator('PostDecr', {'var': 0})
      if left:
        tree.add(left)
      return self.expect( 39, tracer )
    elif  self.sym.getId() == 25: # 'lshift'
      tree.astTransform = AstTransformNodeCreator('LeftShift', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(25, tracer) )
      tree.add( self.__EXPR( self.infixBp0[25] ) )
    elif  self.sym.getId() == 26: # 'div'
      tree.astTransform = AstTransformNodeCreator('Div', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(26, tracer) )
      tree.add( self.__EXPR( self.infixBp0[26] ) )
    elif  self.sym.getId() == 18: # 'lt'
      tree.astTransform = AstTransformNodeCreator('LessThan', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(18, tracer) )
      tree.add( self.__EXPR( self.infixBp0[18] ) )
    elif  self.sym.getId() == 10: # 'muleq'
      tree.astTransform = AstTransformNodeCreator('MultiplyAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(10, tracer) )
      tree.add( self.__EXPR( self.infixBp0[10] ) )
    elif  self.sym.getId() == 70: # 'bitxor'
      tree.astTransform = AstTransformNodeCreator('BitXOR', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(70, tracer) )
      tree.add( self.__EXPR( self.infixBp0[70] ) )
    elif  self.sym.getId() == 54: # 'questionmark'
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(54, tracer) )
      tree.add( self.__EXPR() )
      tree.add( self.expect(85, tracer) )
      tree.add( self.__EXPR() )
    elif  self.sym.getId() == 102: # 'rshift'
      tree.astTransform = AstTransformNodeCreator('RightShift', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(102, tracer) )
      tree.add( self.__EXPR( self.infixBp0[102] ) )
    elif  self.sym.getId() == 46: # 'incr'
      tree.astTransform = AstTransformNodeCreator('PostIncr', {'var': 0})
      if left:
        tree.add(left)
      return self.expect( 46, tracer )
    elif  self.sym.getId() == 5: # 'diveq'
      tree.astTransform = AstTransformNodeCreator('DivideAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(5, tracer) )
      tree.add( self.__EXPR( self.infixBp0[5] ) )
    elif  self.sym.getId() == 89: # 'mod'
      tree.astTransform = AstTransformNodeCreator('Mod', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(89, tracer) )
      tree.add( self.__EXPR( self.infixBp0[89] ) )
    elif  self.sym.getId() == 21: # 'gt'
      tree.astTransform = AstTransformNodeCreator('GreaterThan', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(21, tracer) )
      tree.add( self.__EXPR( self.infixBp0[21] ) )
    elif  self.sym.getId() == 3: # 'modeq'
      tree.astTransform = AstTransformNodeCreator('ModAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(3, tracer) )
      tree.add( self.__EXPR( self.infixBp0[3] ) )
    elif  self.sym.getId() == 68: # 'bitand'
      tree.astTransform = AstTransformNodeCreator('BitAND', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(68, tracer) )
      tree.add( self.__EXPR( self.infixBp0[68] ) )
    elif  self.sym.getId() == 64: # 'bitor'
      tree.astTransform = AstTransformNodeCreator('BitOR', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(64, tracer) )
      tree.add( self.__EXPR( self.infixBp0[64] ) )
    elif  self.sym.getId() == 57: # 'lbrace'
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 0, 'initializer': 4})
      if left:
        tree.add(left)
      tree.add( self.expect(57, tracer) )
      tree.add( self.__GEN2() )
      tree.add( self._COMMA_OPT() )
      tree.add( self.expect(63, tracer) )
    elif  self.sym.getId() == 77: # 'rshifteq'
      tree.astTransform = AstTransformNodeCreator('RightShiftAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(77, tracer) )
      tree.add( self.__EXPR( self.infixBp0[77] ) )
    elif  self.sym.getId() == 37: # 'lteq'
      tree.astTransform = AstTransformNodeCreator('LessThanEq', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(37, tracer) )
      tree.add( self.__EXPR( self.infixBp0[37] ) )
    elif  self.sym.getId() == 72: # 'bitandeq'
      tree.astTransform = AstTransformNodeCreator('ANDAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(72, tracer) )
      tree.add( self.__EXPR( self.infixBp0[72] ) )
    elif  self.sym.getId() == 82: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(82, tracer) )
      ls = AstList()
      if self.sym.getId() not in [53]:
        while 1:
          ls.append( self.__EXPR() )
          if self.sym.getId() != 15:
            break
          self.expect(15, tracer)
      tree.add( ls )
      tree.add( self.expect(90, tracer) )
    elif  self.sym.getId() == 59: # 'bitoreq'
      tree.astTransform = AstTransformNodeCreator('ORAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(59, tracer) )
      tree.add( self.__EXPR( self.infixBp0[59] ) )
    elif  self.sym.getId() == 51: # 'dot'
      tree.astTransform = AstTransformNodeCreator('MemberSelect', {'member': 2, 'object': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(51, tracer) )
      tree.add( self.__EXPR() )
    elif  self.sym.getId() == 98: # 'gteq'
      tree.astTransform = AstTransformNodeCreator('GreaterThanEq', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(98, tracer) )
      tree.add( self.__EXPR( self.infixBp0[98] ) )
    elif  self.sym.getId() == 83: # 'eq'
      tree.astTransform = AstTransformNodeCreator('Equals', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(83, tracer) )
      tree.add( self.__EXPR( self.infixBp0[83] ) )
    elif  self.sym.getId() == 12: # 'add'
      tree.astTransform = AstTransformNodeCreator('Add', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(12, tracer) )
      tree.add( self.__EXPR( self.infixBp0[12] ) )
    elif  self.sym.getId() == 65: # 'bitxoreq'
      tree.astTransform = AstTransformNodeCreator('XORAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(65, tracer) )
      tree.add( self.__EXPR( self.infixBp0[65] ) )
    elif  self.sym.getId() == 69: # 'lsquare'
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(69, tracer) )
      ls = AstList()
      if self.sym.getId() not in [53]:
        while 1:
          ls.append( self.__EXPR() )
          if self.sym.getId() != 15:
            break
          self.expect(15, tracer)
      tree.add( ls )
      tree.add( self.expect(53, tracer) )
    elif  self.sym.getId() == 101: # 'addeq'
      tree.astTransform = AstTransformNodeCreator('AddAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(101, tracer) )
      tree.add( self.__EXPR( self.infixBp0[101] ) )
    elif  self.sym.getId() == 4: # 'assign'
      tree.astTransform = AstTransformNodeCreator('Assign', {'var': 0, 'value': 2})
      if left:
        tree.add(left)
      tree.add( self.expect(4, tracer) )
      tree.add( self.__EXPR( self.infixBp0[4] ) )
    elif  self.sym.getId() == 44: # 'arrow'
      tree.astTransform = AstTransformNodeCreator('DerefMemberSelect', {'member': 2, 'object': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(44, tracer) )
      tree.add( self.__EXPR() )
    elif  self.sym.getId() == 17: # 'mul'
      tree.astTransform = AstTransformNodeCreator('Mul', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(17, tracer) )
      tree.add( self.__EXPR( self.infixBp0[17] ) )
    elif  self.sym.getId() == 91: # 'lshifteq'
      tree.astTransform = AstTransformNodeCreator('LeftShiftAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(91, tracer) )
      tree.add( self.__EXPR( self.infixBp0[91] ) )
    elif  self.sym.getId() == 6: # 'sub'
      tree.astTransform = AstTransformNodeCreator('Sub', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(6, tracer) )
      tree.add( self.__EXPR( self.infixBp0[6] ) )
    elif  self.sym.getId() == 15: # 'comma'
      tree.astTransform = AstTransformNodeCreator('Comma', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(15, tracer) )
      tree.add( self.__EXPR( self.infixBp0[15] ) )
    elif  self.sym.getId() == 94: # 'subeq'
      tree.astTransform = AstTransformNodeCreator('SubtractAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(94, tracer) )
      tree.add( self.__EXPR( self.infixBp0[94] ) )
    return tree
  infixBp1 = {
    69: 1000,
  }
  prefixBp1 = {
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
      left.isExpr = True
      left.isNud = True
      tracer.add(left.tracer)
    while rbp < self.binding_power(self.sym, self.infixBp1):
      left = self.led1(left, depth)
      if isinstance(left, ParseTree):
        tracer.add(left.tracer)
    if left:
      left.isExpr = True
      left.tracer = tracer
    return left
  def nud1(self, tracer):
    tree = ParseTree( NonTerminal(108, '_direct_declarator') )
    if self.sym.getId() == 108: # _direct_declarator
      tree.astTransform = AstTransformSubstitution(0)
      return self.expect( 108, tracer )
    elif self.sym.getId() == 78: # 'identifier'
      tree.astTransform = AstTransformSubstitution(0)
      return self.expect( 78, tracer )
    return tree
  def led1(self, left, tracer):
    tree = ParseTree( NonTerminal(108, '_direct_declarator') )
    if  self.sym.getId() == 69: # 'lsquare'
      tree.astTransform = AstTransformSubstitution(0)
      if left:
        tree.add(left)
      tree.add( self.expect(69, tracer) )
      tree.add( self.__GEN4() )
      tree.add( self.expect(53, tracer) )
    return tree
