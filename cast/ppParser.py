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
      'pp_file': self._PP_FILE,
    }
  TERMINAL_BITOREQ = 0
  TERMINAL_OR = 1
  TERMINAL_BITXOREQ = 2
  TERMINAL_DIV = 3
  TERMINAL_AND = 4
  TERMINAL_CSOURCE = 5
  TERMINAL_ELIPSIS = 6
  TERMINAL_BITOR = 7
  TERMINAL_IF = 8
  TERMINAL_LSHIFTEQ = 9
  TERMINAL_BITNOT = 10
  TERMINAL_BITXOR = 11
  TERMINAL_RSHIFTEQ = 12
  TERMINAL_SEPARATOR = 13
  TERMINAL_ARROW = 14
  TERMINAL_SUB = 15
  TERMINAL_RBRACE = 16
  TERMINAL_DOT = 17
  TERMINAL_ERROR = 18
  TERMINAL_UNDEF = 19
  TERMINAL_LTEQ = 20
  TERMINAL_MODEQ = 21
  TERMINAL_WARNING = 22
  TERMINAL_ADDEQ = 23
  TERMINAL_MULEQ = 24
  TERMINAL_GTEQ = 25
  TERMINAL_INCLUDE = 26
  TERMINAL_RPAREN = 27
  TERMINAL_LT = 28
  TERMINAL_PRAGMA = 29
  TERMINAL_DEFINE = 30
  TERMINAL_ASSIGN = 31
  TERMINAL_NEQ = 32
  TERMINAL_RSQUARE = 33
  TERMINAL_LINE = 34
  TERMINAL_LPAREN = 35
  TERMINAL_ADD = 36
  TERMINAL_POUND = 37
  TERMINAL_LSQUARE = 38
  TERMINAL_RSHIFT = 39
  TERMINAL_COMMA = 40
  TERMINAL_EXCLAMATION_POINT = 41
  TERMINAL_DEFINED = 42
  TERMINAL_DEFINE_FUNCTION = 43
  TERMINAL_BITANDEQ = 44
  TERMINAL_HEADER_GLOBAL = 45
  TERMINAL_SEMI = 46
  TERMINAL_EQ = 47
  TERMINAL_MOD = 48
  TERMINAL_HEADER_LOCAL = 49
  TERMINAL_ELSE = 50
  TERMINAL_COLON = 51
  TERMINAL_IFDEF = 52
  TERMINAL_ENDIF = 53
  TERMINAL_QUESTIONMARK = 54
  TERMINAL_MUL = 55
  TERMINAL_IDENTIFIER = 56
  TERMINAL_IFNDEF = 57
  TERMINAL_GT = 58
  TERMINAL_BITAND = 59
  TERMINAL_PP_NUMBER = 60
  TERMINAL_ELIF = 61
  TERMINAL_LSHIFT = 62
  TERMINAL_CHARACTER_CONSTANT = 63
  TERMINAL_POUNDPOUND = 64
  TERMINAL_DECR = 65
  TERMINAL_STRING_LITERAL = 66
  TERMINAL_SUBEQ = 67
  TERMINAL_TILDE = 68
  TERMINAL_AMPERSAND = 69
  TERMINAL_INCR = 70
  TERMINAL_LBRACE = 71
  terminal_str = {
    0: 'bitoreq',
    1: 'or',
    2: 'bitxoreq',
    3: 'div',
    4: 'and',
    5: 'csource',
    6: 'elipsis',
    7: 'bitor',
    8: 'if',
    9: 'lshifteq',
    10: 'bitnot',
    11: 'bitxor',
    12: 'rshifteq',
    13: 'separator',
    14: 'arrow',
    15: 'sub',
    16: 'rbrace',
    17: 'dot',
    18: 'error',
    19: 'undef',
    20: 'lteq',
    21: 'modeq',
    22: 'warning',
    23: 'addeq',
    24: 'muleq',
    25: 'gteq',
    26: 'include',
    27: 'rparen',
    28: 'lt',
    29: 'pragma',
    30: 'define',
    31: 'assign',
    32: 'neq',
    33: 'rsquare',
    34: 'line',
    35: 'lparen',
    36: 'add',
    37: 'pound',
    38: 'lsquare',
    39: 'rshift',
    40: 'comma',
    41: 'exclamation_point',
    42: 'defined',
    43: 'define_function',
    44: 'bitandeq',
    45: 'header_global',
    46: 'semi',
    47: 'eq',
    48: 'mod',
    49: 'header_local',
    50: 'else',
    51: 'colon',
    52: 'ifdef',
    53: 'endif',
    54: 'questionmark',
    55: 'mul',
    56: 'identifier',
    57: 'ifndef',
    58: 'gt',
    59: 'bitand',
    60: 'pp_number',
    61: 'elif',
    62: 'lshift',
    63: 'character_constant',
    64: 'poundpound',
    65: 'decr',
    66: 'string_literal',
    67: 'subeq',
    68: 'tilde',
    69: 'ampersand',
    70: 'incr',
    71: 'lbrace',
  }
  nonterminal_str = {
    72: 'elseif_part',
    73: '_gen1',
    74: 'pp_nodes_list',
    75: 'punctuator',
    76: '_gen4',
    77: 'replacement_list',
    78: 'define_line',
    79: '_gen6',
    80: 'pp_nodes',
    81: 'pp_tokens',
    82: 'pp_directive',
    83: 'define_func_param',
    84: 'else_part',
    85: '_gen2',
    86: 'identifier',
    87: '_gen3',
    88: '_gen0',
    89: 'error_line',
    90: 'warning_line',
    91: 'undef_line',
    92: 'line_line',
    93: '_expr',
    94: 'if_section',
    95: 'include_line',
    96: 'include_type',
    97: 'if_part',
    98: '_gen5',
    99: 'control_line',
    100: 'pragma_line',
    101: 'pp_file',
    102: 'elipsis_opt',
  }
  str_terminal = {
    'bitoreq': 0,
    'or': 1,
    'bitxoreq': 2,
    'div': 3,
    'and': 4,
    'csource': 5,
    'elipsis': 6,
    'bitor': 7,
    'if': 8,
    'lshifteq': 9,
    'bitnot': 10,
    'bitxor': 11,
    'rshifteq': 12,
    'separator': 13,
    'arrow': 14,
    'sub': 15,
    'rbrace': 16,
    'dot': 17,
    'error': 18,
    'undef': 19,
    'lteq': 20,
    'modeq': 21,
    'warning': 22,
    'addeq': 23,
    'muleq': 24,
    'gteq': 25,
    'include': 26,
    'rparen': 27,
    'lt': 28,
    'pragma': 29,
    'define': 30,
    'assign': 31,
    'neq': 32,
    'rsquare': 33,
    'line': 34,
    'lparen': 35,
    'add': 36,
    'pound': 37,
    'lsquare': 38,
    'rshift': 39,
    'comma': 40,
    'exclamation_point': 41,
    'defined': 42,
    'define_function': 43,
    'bitandeq': 44,
    'header_global': 45,
    'semi': 46,
    'eq': 47,
    'mod': 48,
    'header_local': 49,
    'else': 50,
    'colon': 51,
    'ifdef': 52,
    'endif': 53,
    'questionmark': 54,
    'mul': 55,
    'identifier': 56,
    'ifndef': 57,
    'gt': 58,
    'bitand': 59,
    'pp_number': 60,
    'elif': 61,
    'lshift': 62,
    'character_constant': 63,
    'poundpound': 64,
    'decr': 65,
    'string_literal': 66,
    'subeq': 67,
    'tilde': 68,
    'ampersand': 69,
    'incr': 70,
    'lbrace': 71,
  }
  str_nonterminal = {
    'elseif_part': 72,
    '_gen1': 73,
    'pp_nodes_list': 74,
    'punctuator': 75,
    '_gen4': 76,
    'replacement_list': 77,
    'define_line': 78,
    '_gen6': 79,
    'pp_nodes': 80,
    'pp_tokens': 81,
    'pp_directive': 82,
    'define_func_param': 83,
    'else_part': 84,
    '_gen2': 85,
    'identifier': 86,
    '_gen3': 87,
    '_gen0': 88,
    'error_line': 89,
    'warning_line': 90,
    'undef_line': 91,
    'line_line': 92,
    '_expr': 93,
    'if_section': 94,
    'include_line': 95,
    'include_type': 96,
    'if_part': 97,
    '_gen5': 98,
    'control_line': 99,
    'pragma_line': 100,
    'pp_file': 101,
    'elipsis_opt': 102,
  }
  terminal_count = 72
  nonterminal_count = 31
  parse_table = [
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 20, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 24, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, 80, -1, -1, 80, -1, -1, -1, -1, -1, -1, -1, -1, -1, 80, 80, -1, -1, 80, -1, -1, -1, 80, -1, -1, 80, 80, -1, -1, -1, 80, -1, -1, -1, -1, -1, -1, -1, -1, 80, -1, -1, -1, -1, -1, -1, -1, -1, 80, -1, -1, -1, -1, 80, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [36, 68, 56, 1, 57, -1, 13, 3, -1, 28, 76, 4, 74, -1, 89, 11, 106, 65, -1, -1, 102, 99, -1, 93, 46, 21, -1, 78, 47, -1, -1, 73, 82, 35, -1, 79, 31, 83, 55, 49, 19, 100, 103, -1, 62, -1, 17, 85, 96, -1, -1, 18, -1, -1, 61, 25, -1, -1, 29, 33, -1, -1, 2, -1, 71, 69, -1, 86, 107, 39, 22, 32],
  [27, 27, 27, 27, 27, -1, 27, 27, -1, 27, 27, 27, 27, -1, 27, 27, 27, 27, -1, -1, 27, 27, -1, 27, 27, 27, -1, 27, 27, -1, -1, 27, 27, 27, -1, 27, 27, 27, 27, 27, 27, 27, 27, -1, 27, 27, 27, 27, 27, 27, -1, 27, -1, -1, 27, 27, 27, -1, 27, 27, 27, -1, 27, 27, 27, 27, 27, 27, 27, 27, 27, 27],
  [72, 72, 72, 72, 72, -1, 72, 72, -1, 72, 72, 72, 72, -1, 72, 72, 72, 72, -1, -1, 72, 72, -1, 72, 72, 72, -1, 72, 72, -1, -1, 72, 72, 72, -1, 72, 72, 72, 72, 72, 72, 72, 72, -1, 72, 72, 72, 72, 72, 72, -1, 72, -1, -1, 72, 72, 72, -1, 72, 72, 72, -1, 72, 72, 72, 72, 72, 72, 72, 72, 72, 72],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 98, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 45, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, 81, -1, -1, 70, -1, -1, -1, -1, -1, -1, -1, -1, -1, 70, 70, -1, -1, 70, -1, -1, -1, 70, -1, -1, 70, 70, -1, -1, -1, 70, -1, -1, -1, -1, -1, -1, -1, -1, 70, -1, -1, -1, -1, -1, -1, -1, -1, 70, -1, -1, -1, -1, 70, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [23, 23, 23, 23, 23, -1, 23, 23, -1, 23, 23, 23, 23, -1, 23, 23, 23, 23, -1, -1, 23, 23, -1, 23, 23, 23, -1, 23, 23, -1, -1, 23, 23, 23, -1, 23, 23, 23, 23, 23, 23, 23, 23, -1, 23, 9, 23, 23, 23, 15, -1, 23, -1, -1, 23, 23, 30, -1, 23, 23, 34, -1, 23, 40, 23, 23, 0, 23, 23, 23, 23, 23],
  [-1, -1, -1, -1, -1, -1, -1, -1, 66, -1, -1, -1, -1, -1, -1, -1, -1, -1, 59, 59, -1, -1, 59, -1, -1, -1, 59, -1, -1, 59, 59, -1, -1, -1, 59, -1, -1, -1, -1, -1, -1, -1, -1, 59, -1, -1, -1, -1, -1, -1, -1, -1, 66, -1, -1, -1, -1, 66, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, 43, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 95, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 10, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, 90, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 90, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 87, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 37, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, 88, -1, -1, 88, -1, -1, -1, -1, -1, -1, -1, -1, -1, 88, 88, -1, -1, 88, -1, -1, -1, 88, -1, -1, 88, 88, -1, -1, -1, 88, -1, -1, -1, -1, -1, -1, -1, -1, 88, -1, -1, -1, -1, -1, -1, -1, -1, 88, -1, -1, -1, -1, 88, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 52, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 51, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 67, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 54, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, 5, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 5, -1, -1, -1, -1, 5, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 63, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 12, -1, -1, -1, 75, -1, -1, -1, -1, -1, -1, 94, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, 104, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 16, -1, -1, -1, -1, 38, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 77, 105, -1, -1, 53, -1, -1, -1, 84, -1, -1, 97, 41, -1, -1, -1, 42, -1, -1, -1, -1, -1, -1, -1, -1, 41, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 91, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, 60, -1, -1, 60, -1, -1, -1, -1, -1, -1, -1, -1, -1, 60, 60, -1, -1, 60, -1, -1, -1, 60, -1, -1, 60, 60, -1, -1, -1, 60, -1, -1, -1, -1, -1, -1, -1, -1, 60, -1, -1, -1, -1, -1, -1, -1, -1, 60, -1, -1, -1, -1, 60, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 6, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1]
  ]
  def terminal(self, str):
    return self.str_terminal[str]
  def terminalNames(self):
    return list(self.str_terminal.keys())
  def isTerminal(self, id):
    return 0 <= id <= 71
  def isNonTerminal(self, id):
    return 72 <= id <= 102
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
    return self.parse_table[n - 72][self.sym.getId()]
  def call(self, nt_str):
    return getattr(self, nt_str)()
  def _ELSEIF_PART(self, depth = 0):
    rule = self.rule(72)
    if depth is not False:
      tracer = DebugTracer("_ELSEIF_PART", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(72, self.getAtomString(72)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 20:
      tree.astTransform = AstTransformNodeCreator('ElseIf', {'expr': 1, 'nodes': 2})
      tree.add( self.expect(self.TERMINAL_ELIF, tracer) )
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._PP_NODES_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN1(self, depth = 0):
    rule = self.rule(73)
    if depth is not False:
      tracer = DebugTracer("__GEN1", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(73, self.getAtomString(73)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() == 13 or self.sym.getId() == 50):
      return tree
    if self.sym != None and (self.sym.getId() == 13 or self.sym.getId() == 50):
      return tree
    if self.sym == None:
      return tree
    if rule == 24:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ELSEIF_PART(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN1(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _PP_NODES_LIST(self, depth = 0):
    rule = self.rule(74)
    if depth is not False:
      tracer = DebugTracer("_PP_NODES_LIST", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(74, self.getAtomString(74)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() == 53 or self.sym.getId() == 50 or self.sym.getId() == 61 or self.sym.getId() == 13):
      return tree
    if self.sym != None and (self.sym.getId() == 53 or self.sym.getId() == 50 or self.sym.getId() == 61 or self.sym.getId() == 13):
      return tree
    if self.sym != None and (self.sym.getId() == 53 or self.sym.getId() == 50 or self.sym.getId() == 61 or self.sym.getId() == 13):
      return tree
    if self.sym != None and (self.sym.getId() == 53 or self.sym.getId() == 50 or self.sym.getId() == 61 or self.sym.getId() == 13):
      return tree
    if self.sym == None:
      return tree
    elif rule == 80:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN0(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _PUNCTUATOR(self, depth = 0):
    rule = self.rule(75)
    if depth is not False:
      tracer = DebugTracer("_PUNCTUATOR", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(75, self.getAtomString(75)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 1:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DIV, tracer) )
      return tree
    elif rule == 2:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LSHIFT, tracer) )
      return tree
    elif rule == 3:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITOR, tracer) )
      return tree
    elif rule == 4:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITXOR, tracer) )
      return tree
    elif rule == 8:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITXOR, tracer) )
      return tree
    elif rule == 11:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SUB, tracer) )
      return tree
    elif rule == 13:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ELIPSIS, tracer) )
      return tree
    elif rule == 14:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITOR, tracer) )
      return tree
    elif rule == 17:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SEMI, tracer) )
      return tree
    elif rule == 18:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_COLON, tracer) )
      return tree
    elif rule == 19:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_COMMA, tracer) )
      return tree
    elif rule == 21:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_GTEQ, tracer) )
      return tree
    elif rule == 22:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_INCR, tracer) )
      return tree
    elif rule == 25:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_MUL, tracer) )
      return tree
    elif rule == 28:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LSHIFTEQ, tracer) )
      return tree
    elif rule == 29:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_GT, tracer) )
      return tree
    elif rule == 31:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ADD, tracer) )
      return tree
    elif rule == 32:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LBRACE, tracer) )
      return tree
    elif rule == 33:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITAND, tracer) )
      return tree
    elif rule == 35:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RSQUARE, tracer) )
      return tree
    elif rule == 36:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITOREQ, tracer) )
      return tree
    elif rule == 39:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_AMPERSAND, tracer) )
      return tree
    elif rule == 46:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_MULEQ, tracer) )
      return tree
    elif rule == 47:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LT, tracer) )
      return tree
    elif rule == 49:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RSHIFT, tracer) )
      return tree
    elif rule == 55:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LSQUARE, tracer) )
      return tree
    elif rule == 56:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITXOREQ, tracer) )
      return tree
    elif rule == 57:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_AND, tracer) )
      return tree
    elif rule == 61:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_QUESTIONMARK, tracer) )
      return tree
    elif rule == 62:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITANDEQ, tracer) )
      return tree
    elif rule == 65:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DOT, tracer) )
      return tree
    elif rule == 68:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_OR, tracer) )
      return tree
    elif rule == 69:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DECR, tracer) )
      return tree
    elif rule == 71:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_POUNDPOUND, tracer) )
      return tree
    elif rule == 73:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ASSIGN, tracer) )
      return tree
    elif rule == 74:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RSHIFTEQ, tracer) )
      return tree
    elif rule == 76:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITNOT, tracer) )
      return tree
    elif rule == 78:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RPAREN, tracer) )
      return tree
    elif rule == 79:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LPAREN, tracer) )
      return tree
    elif rule == 82:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_NEQ, tracer) )
      return tree
    elif rule == 83:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_POUND, tracer) )
      return tree
    elif rule == 85:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_EQ, tracer) )
      return tree
    elif rule == 86:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SUBEQ, tracer) )
      return tree
    elif rule == 89:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ARROW, tracer) )
      return tree
    elif rule == 93:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ADDEQ, tracer) )
      return tree
    elif rule == 96:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_MOD, tracer) )
      return tree
    elif rule == 99:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_MODEQ, tracer) )
      return tree
    elif rule == 100:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_EXCLAMATION_POINT, tracer) )
      return tree
    elif rule == 102:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LTEQ, tracer) )
      return tree
    elif rule == 103:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DEFINED, tracer) )
      return tree
    elif rule == 106:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RBRACE, tracer) )
      return tree
    elif rule == 107:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_TILDE, tracer) )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN4(self, depth = 0):
    rule = self.rule(76)
    if depth is not False:
      tracer = DebugTracer("__GEN4", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(76, self.getAtomString(76)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() == 13):
      return tree
    if self.sym == None:
      return tree
    elif rule == 27:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PP_TOKENS(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN4(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _REPLACEMENT_LIST(self, depth = 0):
    rule = self.rule(77)
    if depth is not False:
      tracer = DebugTracer("_REPLACEMENT_LIST", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(77, self.getAtomString(77)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() == 13):
      return tree
    if self.sym == None:
      return tree
    elif rule == 72:
      tree.astTransform = AstTransformNodeCreator('ReplacementList', {'tokens': 0})
      subtree = self.__GEN4(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _DEFINE_LINE(self, depth = 0):
    rule = self.rule(78)
    if depth is not False:
      tracer = DebugTracer("_DEFINE_LINE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(78, self.getAtomString(78)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 45:
      tree.astTransform = AstTransformNodeCreator('DefineFunction', {'body': 5, 'ident': 1, 'params': 3})
      tree.add( self.expect(self.TERMINAL_DEFINE_FUNCTION, tracer) )
      tree.add( self.expect(self.TERMINAL_IDENTIFIER, tracer) )
      tree.add( self.expect(self.TERMINAL_LPAREN, tracer) )
      subtree = self.__GEN2(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(self.TERMINAL_RPAREN, tracer) )
      subtree = self._REPLACEMENT_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 98:
      tree.astTransform = AstTransformNodeCreator('Define', {'body': 2, 'ident': 1})
      tree.add( self.expect(self.TERMINAL_DEFINE, tracer) )
      tree.add( self.expect(self.TERMINAL_IDENTIFIER, tracer) )
      subtree = self._REPLACEMENT_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN6(self, depth = 0):
    rule = self.rule(79)
    if depth is not False:
      tracer = DebugTracer("__GEN6", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(79, self.getAtomString(79)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PP_NODES(self, depth = 0):
    rule = self.rule(80)
    if depth is not False:
      tracer = DebugTracer("_PP_NODES", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(80, self.getAtomString(80)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 70:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PP_DIRECTIVE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 81:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_CSOURCE, tracer) )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PP_TOKENS(self, depth = 0):
    rule = self.rule(81)
    if depth is not False:
      tracer = DebugTracer("_PP_TOKENS", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(81, self.getAtomString(81)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 0:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_STRING_LITERAL, tracer) )
      return tree
    elif rule == 9:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_HEADER_GLOBAL, tracer) )
      return tree
    elif rule == 15:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_HEADER_LOCAL, tracer) )
      return tree
    elif rule == 23:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PUNCTUATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 30:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_IDENTIFIER, tracer) )
      return tree
    elif rule == 34:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_PP_NUMBER, tracer) )
      return tree
    elif rule == 40:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_CHARACTER_CONSTANT, tracer) )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PP_DIRECTIVE(self, depth = 0):
    rule = self.rule(82)
    if depth is not False:
      tracer = DebugTracer("_PP_DIRECTIVE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(82, self.getAtomString(82)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 59:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._CONTROL_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 66:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._IF_SECTION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _DEFINE_FUNC_PARAM(self, depth = 0):
    rule = self.rule(83)
    if depth is not False:
      tracer = DebugTracer("_DEFINE_FUNC_PARAM", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(83, self.getAtomString(83)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 43:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ELIPSIS, tracer) )
      return tree
    elif rule == 95:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_IDENTIFIER, tracer) )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _ELSE_PART(self, depth = 0):
    rule = self.rule(84)
    if depth is not False:
      tracer = DebugTracer("_ELSE_PART", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(84, self.getAtomString(84)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() == 53):
      return tree
    if self.sym == None:
      return tree
    if rule == 10:
      tree.astTransform = AstTransformNodeCreator('Else', {'nodes': 1})
      tree.add( self.expect(self.TERMINAL_ELSE, tracer) )
      subtree = self._PP_NODES_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN2(self, depth = 0):
    rule = self.rule(85)
    if depth is not False:
      tracer = DebugTracer("__GEN2", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(85, self.getAtomString(85)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() == 27):
      return tree
    if self.sym == None:
      return tree
    if rule == 90:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DEFINE_FUNC_PARAM(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN3(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _IDENTIFIER(self, depth = 0):
    rule = self.rule(86)
    if depth is not False:
      tracer = DebugTracer("_IDENTIFIER", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(86, self.getAtomString(86)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 87:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_IDENTIFIER, tracer) )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN3(self, depth = 0):
    rule = self.rule(87)
    if depth is not False:
      tracer = DebugTracer("__GEN3", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(87, self.getAtomString(87)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() == 27):
      return tree
    if self.sym == None:
      return tree
    if rule == 37:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_COMMA, tracer) )
      subtree = self._DEFINE_FUNC_PARAM(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN3(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN0(self, depth = 0):
    rule = self.rule(88)
    if depth is not False:
      tracer = DebugTracer("__GEN0", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(88, self.getAtomString(88)), tracer )
    tree.list = 'tlist'
    if self.sym != None and (self.sym.getId() == 53 or self.sym.getId() == 13 or self.sym.getId() == 61 or self.sym.getId() == 50):
      return tree
    if self.sym != None and (self.sym.getId() == 53 or self.sym.getId() == 13 or self.sym.getId() == 61 or self.sym.getId() == 50):
      return tree
    if self.sym != None and (self.sym.getId() == 53 or self.sym.getId() == 13 or self.sym.getId() == 61 or self.sym.getId() == 50):
      return tree
    if self.sym != None and (self.sym.getId() == 53 or self.sym.getId() == 13 or self.sym.getId() == 61 or self.sym.getId() == 50):
      return tree
    if self.sym == None:
      return tree
    if rule == 88:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PP_NODES(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(self.TERMINAL_SEPARATOR, tracer) )
      subtree = self.__GEN0(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _ERROR_LINE(self, depth = 0):
    rule = self.rule(89)
    if depth is not False:
      tracer = DebugTracer("_ERROR_LINE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(89, self.getAtomString(89)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 52:
      tree.astTransform = AstTransformNodeCreator('Error', {'tokens': 1})
      tree.add( self.expect(self.TERMINAL_ERROR, tracer) )
      subtree = self.__GEN4(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _WARNING_LINE(self, depth = 0):
    rule = self.rule(90)
    if depth is not False:
      tracer = DebugTracer("_WARNING_LINE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(90, self.getAtomString(90)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 51:
      tree.astTransform = AstTransformNodeCreator('Warning', {'tokens': 1})
      tree.add( self.expect(self.TERMINAL_WARNING, tracer) )
      subtree = self.__GEN4(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _UNDEF_LINE(self, depth = 0):
    rule = self.rule(91)
    if depth is not False:
      tracer = DebugTracer("_UNDEF_LINE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(91, self.getAtomString(91)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 67:
      tree.astTransform = AstTransformNodeCreator('Undef', {'ident': 1})
      tree.add( self.expect(self.TERMINAL_UNDEF, tracer) )
      tree.add( self.expect(self.TERMINAL_IDENTIFIER, tracer) )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _LINE_LINE(self, depth = 0):
    rule = self.rule(92)
    if depth is not False:
      tracer = DebugTracer("_LINE_LINE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(92, self.getAtomString(92)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 54:
      tree.astTransform = AstTransformNodeCreator('Line', {'tokens': 1})
      tree.add( self.expect(self.TERMINAL_LINE, tracer) )
      subtree = self.__GEN4(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _IF_SECTION(self, depth = 0):
    rule = self.rule(94)
    if depth is not False:
      tracer = DebugTracer("_IF_SECTION", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(94, self.getAtomString(94)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 5:
      tree.astTransform = AstTransformNodeCreator('IfSection', {'elif': 1, 'else': 2, 'if': 0})
      subtree = self._IF_PART(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN1(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._ELSE_PART(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(self.TERMINAL_ENDIF, tracer) )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _INCLUDE_LINE(self, depth = 0):
    rule = self.rule(95)
    if depth is not False:
      tracer = DebugTracer("_INCLUDE_LINE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(95, self.getAtomString(95)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 63:
      tree.astTransform = AstTransformNodeCreator('Include', {'file': 1})
      tree.add( self.expect(self.TERMINAL_INCLUDE, tracer) )
      subtree = self._INCLUDE_TYPE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _INCLUDE_TYPE(self, depth = 0):
    rule = self.rule(96)
    if depth is not False:
      tracer = DebugTracer("_INCLUDE_TYPE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(96, self.getAtomString(96)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 12:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_HEADER_GLOBAL, tracer) )
      return tree
    elif rule == 75:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_HEADER_LOCAL, tracer) )
      return tree
    elif rule == 94:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_IDENTIFIER, tracer) )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _IF_PART(self, depth = 0):
    rule = self.rule(97)
    if depth is not False:
      tracer = DebugTracer("_IF_PART", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(97, self.getAtomString(97)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 16:
      tree.astTransform = AstTransformNodeCreator('IfDef', {'nodes': 2, 'ident': 1})
      tree.add( self.expect(self.TERMINAL_IFDEF, tracer) )
      tree.add( self.expect(self.TERMINAL_IDENTIFIER, tracer) )
      subtree = self._PP_NODES_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 38:
      tree.astTransform = AstTransformNodeCreator('IfNDef', {'nodes': 2, 'ident': 1})
      tree.add( self.expect(self.TERMINAL_IFNDEF, tracer) )
      tree.add( self.expect(self.TERMINAL_IDENTIFIER, tracer) )
      subtree = self._PP_NODES_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 104:
      tree.astTransform = AstTransformNodeCreator('If', {'expr': 1, 'nodes': 2})
      tree.add( self.expect(self.TERMINAL_IF, tracer) )
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._PP_NODES_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN5(self, depth = 0):
    rule = self.rule(98)
    if depth is not False:
      tracer = DebugTracer("__GEN5", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(98, self.getAtomString(98)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _CONTROL_LINE(self, depth = 0):
    rule = self.rule(99)
    if depth is not False:
      tracer = DebugTracer("_CONTROL_LINE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(99, self.getAtomString(99)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 41:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DEFINE_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 42:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._LINE_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 53:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._WARNING_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 77:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ERROR_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 84:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._INCLUDE_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 97:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PRAGMA_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 105:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._UNDEF_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PRAGMA_LINE(self, depth = 0):
    rule = self.rule(100)
    if depth is not False:
      tracer = DebugTracer("_PRAGMA_LINE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(100, self.getAtomString(100)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 91:
      tree.astTransform = AstTransformNodeCreator('Pragma', {'tokens': 1})
      tree.add( self.expect(self.TERMINAL_PRAGMA, tracer) )
      subtree = self.__GEN4(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PP_FILE(self, depth = 0):
    rule = self.rule(101)
    if depth is not False:
      tracer = DebugTracer("_PP_FILE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(101, self.getAtomString(101)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 60:
      tree.astTransform = AstTransformNodeCreator('PPFile', {'nodes': 0})
      subtree = self._PP_NODES_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _ELIPSIS_OPT(self, depth = 0):
    rule = self.rule(102)
    if depth is not False:
      tracer = DebugTracer("_ELIPSIS_OPT", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(102, self.getAtomString(102)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 6:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_COMMA, tracer) )
      tree.add( self.expect(self.TERMINAL_ELIPSIS, tracer) )
      return tree
    return tree
  bp0 = {
    32: 8000,
    1: 3000,
    35: 14000,
    4: 4000,
    25: 9000,
    39: 10000,
    40: 1000,
    47: 8000,
    7: 7000,
    15: 11000,
    48: 12000,
    11: 6000,
    3: 12000,
    20: 9000,
    54: 2000,
    55: 12000,
    36: 11000,
    58: 9000,
    59: 5000,
    28: 9000,
    62: 10000,
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
    if self.sym.getId() == 66:
      return self.expect( 66, tracer )
      return tree
    if self.sym.getId() == 35:
      tree.add( self.expect( 35, tracer ) ) #here?
      tree.astTransform = AstTransformSubstitution(1)
      tree.add(self.__EXPR())
      tree.astTransform = AstTransformSubstitution(1)
      tree.add( self.expect( 27, tracer ) ) #here?
      tree.astTransform = AstTransformSubstitution(1)
      return tree
    if self.sym.getId() == 41:
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(13000) )
      tree.astTransform = AstTransformNodeCreator('Not', {'expr': 1})
      return tree
    if self.sym.getId() == 42:
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(13000) )
      tree.astTransform = AstTransformNodeCreator('IsDefined', {'expr': 1})
      return tree
    if self.sym.getId() == 93:
      return tree
    if self.sym.getId() == 56:
      return self.expect( 56, tracer )
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      return tree
    if self.sym.getId() == 60:
      return self.expect( 60, tracer )
      return tree
    if self.sym.getId() == 10:
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(13000) )
      tree.astTransform = AstTransformNodeCreator('BitNOT', {'expr': 1})
      return tree
    if self.sym.getId() == 63:
      return self.expect( 63, tracer )
      return tree
  def led0(self, left, tracer):
    tree = ParseTree( NonTerminal(self.str_nonterminal['_expr'], '_expr') )
    if self.sym.getId() == 32:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(7999) )
      tree.astTransform = AstTransformNodeCreator('NotEquals', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 1:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(3000) )
      tree.astTransform = AstTransformNodeCreator('Or', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 35:
      if left:
        tree.add( left )
      ls = AstList()
      tree.add( self.expect( 35, tracer ) )
      if self.sym.getId() != 27:
        while 1:
          ls.append( self.__EXPR() )
          if self.sym.getId() != 40:
            break
          self.expect( 40, tracer )
      tree.add( ls )
      tree.add( self.expect(27, tracer ) )
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      return tree
    if self.sym.getId() == 36:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(11000) )
      tree.astTransform = AstTransformNodeCreator('Add', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 4:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(4000) )
      tree.astTransform = AstTransformNodeCreator('And', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 39:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(10000) )
      tree.astTransform = AstTransformNodeCreator('RightShift', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 40:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(1000) )
      tree.astTransform = AstTransformNodeCreator('Comma', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 11:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(6000) )
      tree.astTransform = AstTransformNodeCreator('BitXOR', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 47:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(7999) )
      tree.astTransform = AstTransformNodeCreator('Equals', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 48:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(12000) )
      tree.astTransform = AstTransformNodeCreator('Mod', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 59:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(5000) )
      tree.astTransform = AstTransformNodeCreator('BitAND', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 3:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(12000) )
      tree.astTransform = AstTransformNodeCreator('Div', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 20:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(9000) )
      tree.astTransform = AstTransformNodeCreator('LessThanEq', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 54:
      if left:
        tree.add( left )
      tree.add( self.expect( 54, tracer ) )
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      tree.add(self.__EXPR())
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      tree.add( self.expect( 51, tracer ) )
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      tree.add(self.__EXPR())
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      return tree
    if self.sym.getId() == 55:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(12000) )
      tree.astTransform = AstTransformNodeCreator('Mul', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 7:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(7000) )
      tree.astTransform = AstTransformNodeCreator('BitOR', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 25:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(9000) )
      tree.astTransform = AstTransformNodeCreator('GreaterThanEq', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 58:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(9000) )
      tree.astTransform = AstTransformNodeCreator('GreaterThan', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 15:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(11000) )
      tree.astTransform = AstTransformNodeCreator('Sub', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 28:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(9000) )
      tree.astTransform = AstTransformNodeCreator('LessThan', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 62:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(10000) )
      tree.astTransform = AstTransformNodeCreator('LeftShift', {'right': 2, 'left': 0})
      return tree
