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
        return []
      offset = 1 if not isinstance(self.children[0], ParseTree) else 0
      r = [self.children[offset].toAst()]
      r.extend(self.children[offset+1].toAst())
      return r
    elif self.list == 'tlist':
      if len(self.children) == 0:
        return []
      r = [self.children[0].toAst()]
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
  TERMINAL_LINE = 0
  TERMINAL_RSHIFTEQ = 1
  TERMINAL_DIV = 2
  TERMINAL_SUBEQ = 3
  TERMINAL_BITAND = 4
  TERMINAL_ELIPSIS = 5
  TERMINAL_MODEQ = 6
  TERMINAL_BITXOR = 7
  TERMINAL_ARROW = 8
  TERMINAL_CHARACTER_CONSTANT = 9
  TERMINAL_LTEQ = 10
  TERMINAL_GTEQ = 11
  TERMINAL_ASSIGN = 12
  TERMINAL_RSHIFT = 13
  TERMINAL_DEFINE = 14
  TERMINAL_POUNDPOUND = 15
  TERMINAL_COMMA = 16
  TERMINAL_NOT = 17
  TERMINAL_CSOURCE = 18
  TERMINAL_BITNOT = 19
  TERMINAL_DEFINE_FUNCTION = 20
  TERMINAL_IFDEF = 21
  TERMINAL_SEMI = 22
  TERMINAL_LT = 23
  TERMINAL_MULEQ = 24
  TERMINAL_NEQ = 25
  TERMINAL_RSQUARE = 26
  TERMINAL_IF = 27
  TERMINAL_RBRACE = 28
  TERMINAL_LSHIFT = 29
  TERMINAL_ADD = 30
  TERMINAL_HEADER_LOCAL = 31
  TERMINAL_ENDIF = 32
  TERMINAL_RPAREN = 33
  TERMINAL_BITANDEQ = 34
  TERMINAL_AND = 35
  TERMINAL_EXCLAMATION_POINT = 36
  TERMINAL_IFNDEF = 37
  TERMINAL_LSHIFTEQ = 38
  TERMINAL_UNDEF = 39
  TERMINAL_TILDE = 40
  TERMINAL_ADDEQ = 41
  TERMINAL_DOT = 42
  TERMINAL_MOD = 43
  TERMINAL_ELIF = 44
  TERMINAL_SUB = 45
  TERMINAL_POUND = 46
  TERMINAL_LPAREN = 47
  TERMINAL_IDENTIFIER = 48
  TERMINAL_ELSE = 49
  TERMINAL_INCLUDE = 50
  TERMINAL_MUL = 51
  TERMINAL_QUESTIONMARK = 52
  TERMINAL_PRAGMA = 53
  TERMINAL_OR = 54
  TERMINAL_GT = 55
  TERMINAL_BITOREQ = 56
  TERMINAL_EQ = 57
  TERMINAL_BITOR = 58
  TERMINAL_ERROR = 59
  TERMINAL_BITXOREQ = 60
  TERMINAL_LSQUARE = 61
  TERMINAL_HEADER_GLOBAL = 62
  TERMINAL_DECR = 63
  TERMINAL_COLON = 64
  TERMINAL_PP_NUMBER = 65
  TERMINAL_STRING_LITERAL = 66
  TERMINAL_AMPERSAND = 67
  TERMINAL_SEPARATOR = 68
  TERMINAL_INCR = 69
  TERMINAL_LBRACE = 70
  terminal_str = {
    0: 'line',
    1: 'rshifteq',
    2: 'div',
    3: 'subeq',
    4: 'bitand',
    5: 'elipsis',
    6: 'modeq',
    7: 'bitxor',
    8: 'arrow',
    9: 'character_constant',
    10: 'lteq',
    11: 'gteq',
    12: 'assign',
    13: 'rshift',
    14: 'define',
    15: 'poundpound',
    16: 'comma',
    17: 'not',
    18: 'csource',
    19: 'bitnot',
    20: 'define_function',
    21: 'ifdef',
    22: 'semi',
    23: 'lt',
    24: 'muleq',
    25: 'neq',
    26: 'rsquare',
    27: 'if',
    28: 'rbrace',
    29: 'lshift',
    30: 'add',
    31: 'header_local',
    32: 'endif',
    33: 'rparen',
    34: 'bitandeq',
    35: 'and',
    36: 'exclamation_point',
    37: 'ifndef',
    38: 'lshifteq',
    39: 'undef',
    40: 'tilde',
    41: 'addeq',
    42: 'dot',
    43: 'mod',
    44: 'elif',
    45: 'sub',
    46: 'pound',
    47: 'lparen',
    48: 'identifier',
    49: 'else',
    50: 'include',
    51: 'mul',
    52: 'questionmark',
    53: 'pragma',
    54: 'or',
    55: 'gt',
    56: 'bitoreq',
    57: 'eq',
    58: 'bitor',
    59: 'error',
    60: 'bitxoreq',
    61: 'lsquare',
    62: 'header_global',
    63: 'decr',
    64: 'colon',
    65: 'pp_number',
    66: 'string_literal',
    67: 'ampersand',
    68: 'separator',
    69: 'incr',
    70: 'lbrace',
  }
  nonterminal_str = {
    71: '_expr',
    72: '_gen0',
    73: 'undef_line',
    74: 'pp_nodes',
    75: 'line_line',
    76: '_gen5',
    77: '_gen4',
    78: '_gen3',
    79: 'include_type',
    80: 'pragma_line',
    81: 'punctuator',
    82: 'pp_tokens',
    83: 'control_line',
    84: 'pp_file',
    85: 'if_part',
    86: 'elseif_part',
    87: '_gen1',
    88: 'pp_nodes_list',
    89: 'include_line',
    90: '_gen6',
    91: 'define_line',
    92: 'else_part',
    93: '_gen2',
    94: 'pp_directive',
    95: 'if_section',
    96: 'identifier',
    97: 'error_line',
    98: 'replacement_list',
  }
  str_terminal = {
    'line': 0,
    'rshifteq': 1,
    'div': 2,
    'subeq': 3,
    'bitand': 4,
    'elipsis': 5,
    'modeq': 6,
    'bitxor': 7,
    'arrow': 8,
    'character_constant': 9,
    'lteq': 10,
    'gteq': 11,
    'assign': 12,
    'rshift': 13,
    'define': 14,
    'poundpound': 15,
    'comma': 16,
    'not': 17,
    'csource': 18,
    'bitnot': 19,
    'define_function': 20,
    'ifdef': 21,
    'semi': 22,
    'lt': 23,
    'muleq': 24,
    'neq': 25,
    'rsquare': 26,
    'if': 27,
    'rbrace': 28,
    'lshift': 29,
    'add': 30,
    'header_local': 31,
    'endif': 32,
    'rparen': 33,
    'bitandeq': 34,
    'and': 35,
    'exclamation_point': 36,
    'ifndef': 37,
    'lshifteq': 38,
    'undef': 39,
    'tilde': 40,
    'addeq': 41,
    'dot': 42,
    'mod': 43,
    'elif': 44,
    'sub': 45,
    'pound': 46,
    'lparen': 47,
    'identifier': 48,
    'else': 49,
    'include': 50,
    'mul': 51,
    'questionmark': 52,
    'pragma': 53,
    'or': 54,
    'gt': 55,
    'bitoreq': 56,
    'eq': 57,
    'bitor': 58,
    'error': 59,
    'bitxoreq': 60,
    'lsquare': 61,
    'header_global': 62,
    'decr': 63,
    'colon': 64,
    'pp_number': 65,
    'string_literal': 66,
    'ampersand': 67,
    'separator': 68,
    'incr': 69,
    'lbrace': 70,
  }
  str_nonterminal = {
    '_expr': 71,
    '_gen0': 72,
    'undef_line': 73,
    'pp_nodes': 74,
    'line_line': 75,
    '_gen5': 76,
    '_gen4': 77,
    '_gen3': 78,
    'include_type': 79,
    'pragma_line': 80,
    'punctuator': 81,
    'pp_tokens': 82,
    'control_line': 83,
    'pp_file': 84,
    'if_part': 85,
    'elseif_part': 86,
    '_gen1': 87,
    'pp_nodes_list': 88,
    'include_line': 89,
    '_gen6': 90,
    'define_line': 91,
    'else_part': 92,
    '_gen2': 93,
    'pp_directive': 94,
    'if_section': 95,
    'identifier': 96,
    'error_line': 97,
    'replacement_list': 98,
  }
  terminal_count = 71
  nonterminal_count = 28
  parse_table = [
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [3, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 3, -1, -1, -1, 3, -1, 3, 3, -1, -1, -1, -1, -1, 3, -1, -1, -1, -1, -1, -1, -1, -1, -1, 3, -1, 3, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 3, -1, -1, 3, -1, -1, -1, -1, -1, 3, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 22, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [72, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 72, -1, -1, -1, 37, -1, 72, 72, -1, -1, -1, -1, -1, 72, -1, -1, -1, -1, -1, -1, -1, -1, -1, 72, -1, 72, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 72, -1, -1, 72, -1, -1, -1, -1, -1, 72, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [36, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, 1, 1, 1, -1, 1, 1, 1, 1, 1, 1, 1, 1, 1, -1, 1, 1, -1, -1, -1, -1, -1, 1, 1, 1, 1, 1, -1, 1, 1, 1, 1, -1, 1, 1, 1, 1, -1, 1, -1, 1, 1, 1, 1, -1, 1, 1, 1, 1, -1, -1, 1, 1, -1, 1, 1, 1, 1, 1, -1, 1, 1, 1, 1, 1, 1, 1, 1, -1, 1, 1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 51, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 43, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 69, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 91, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 33, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, 61, 8, 73, -1, 15, 85, 30, 53, -1, 54, 56, 47, 84, -1, 50, 57, -1, -1, -1, -1, -1, 4, 83, 93, 46, 10, -1, 88, 16, 28, -1, -1, 95, 42, 49, 94, -1, 65, -1, 26, 77, 82, 76, -1, 11, 75, 74, -1, -1, -1, 25, 64, -1, 79, 90, 41, 7, 13, -1, 45, 60, -1, 68, 19, -1, -1, 89, -1, 35, 29],
  [-1, 86, 86, 86, -1, 86, 86, 86, 86, 71, 86, 86, 86, 86, -1, 86, 86, -1, -1, -1, -1, -1, 86, 86, 86, 86, 86, -1, 86, 86, 86, 12, -1, 86, 86, 86, 86, -1, 86, -1, 86, 86, 86, 86, -1, 86, 86, 86, 31, -1, -1, 86, 86, -1, 86, 86, 86, 86, 86, -1, 86, 86, 70, 86, 86, 5, 55, 86, -1, 86, 86],
  [62, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 52, -1, -1, -1, -1, -1, 52, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 59, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 32, -1, -1, 20, -1, -1, -1, -1, -1, 23, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [34, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 34, -1, -1, -1, 34, -1, 34, 34, -1, -1, -1, -1, -1, 34, -1, -1, -1, -1, -1, -1, -1, -1, -1, 34, -1, 34, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 34, -1, -1, 34, -1, -1, -1, -1, -1, 34, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 92, -1, -1, -1, -1, -1, 80, -1, -1, -1, -1, -1, -1, -1, -1, -1, 9, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 17, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 18, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [38, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 38, -1, -1, -1, 38, -1, 38, 38, -1, -1, -1, -1, -1, 38, -1, -1, -1, -1, -1, -1, -1, -1, -1, 38, -1, 38, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 38, -1, -1, 38, -1, -1, -1, -1, -1, 38, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 48, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 39, -1, -1, -1, -1, -1, 96, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 2, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 63, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [0, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 0, -1, -1, -1, -1, -1, 0, 87, -1, -1, -1, -1, -1, 87, -1, -1, -1, -1, -1, -1, -1, -1, -1, 87, -1, 0, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 0, -1, -1, 0, -1, -1, -1, -1, -1, 0, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 66, -1, -1, -1, -1, -1, 66, -1, -1, -1, -1, -1, -1, -1, -1, -1, 66, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 67, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 40, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, 21, 21, 21, -1, 21, 21, 21, 21, 21, 21, 21, 21, 21, -1, 21, 21, -1, -1, -1, -1, -1, 21, 21, 21, 21, 21, -1, 21, 21, 21, 21, -1, 21, 21, 21, 21, -1, 21, -1, 21, 21, 21, 21, -1, 21, 21, 21, 21, -1, -1, 21, 21, -1, 21, 21, 21, 21, 21, -1, 21, 21, 21, 21, 21, 21, 21, 21, -1, 21, 21]
  ]
  def terminal(self, str):
    return self.str_terminal[str]
  def terminalNames(self):
    return list(self.str_terminal.keys())
  def isTerminal(self, id):
    return 0 <= id <= 70
  def isNonTerminal(self, id):
    return 71 <= id <= 98
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
    return self.parse_table[n - 71][self.sym.getId()]
  def __GEN0(self, depth = 0):
    rule = self.rule(72)
    if depth is not False:
      tracer = DebugTracer("__GEN0", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(72, self.getAtomString(72)), tracer )
    tree.list = 'tlist'
    if self.sym != None and (self.sym.getId() == 49 or self.sym.getId() == 44 or self.sym.getId() == 68 or self.sym.getId() == 32):
      return tree
    if self.sym != None and (self.sym.getId() == 49 or self.sym.getId() == 44 or self.sym.getId() == 68 or self.sym.getId() == 32):
      return tree
    if self.sym != None and (self.sym.getId() == 49 or self.sym.getId() == 44 or self.sym.getId() == 68 or self.sym.getId() == 32):
      return tree
    if self.sym != None and (self.sym.getId() == 49 or self.sym.getId() == 44 or self.sym.getId() == 68 or self.sym.getId() == 32):
      return tree
    if self.sym == None:
      return tree
    if rule == 3:
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
  def _UNDEF_LINE(self, depth = 0):
    rule = self.rule(73)
    if depth is not False:
      tracer = DebugTracer("_UNDEF_LINE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(73, self.getAtomString(73)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 22:
      tree.astTransform = AstTransformNodeCreator('Undef', {'ident': 1})
      tree.add( self.expect(self.TERMINAL_UNDEF, tracer) )
      tree.add( self.expect(self.TERMINAL_IDENTIFIER, tracer) )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PP_NODES(self, depth = 0):
    rule = self.rule(74)
    if depth is not False:
      tracer = DebugTracer("_PP_NODES", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(74, self.getAtomString(74)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 37:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_CSOURCE, tracer) )
      return tree
    elif rule == 72:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PP_DIRECTIVE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _LINE_LINE(self, depth = 0):
    rule = self.rule(75)
    if depth is not False:
      tracer = DebugTracer("_LINE_LINE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(75, self.getAtomString(75)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 36:
      tree.astTransform = AstTransformNodeCreator('Line', {'tokens': 1})
      tree.add( self.expect(self.TERMINAL_LINE, tracer) )
      subtree = self.__GEN4(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN5(self, depth = 0):
    rule = self.rule(76)
    if depth is not False:
      tracer = DebugTracer("__GEN5", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(76, self.getAtomString(76)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN4(self, depth = 0):
    rule = self.rule(77)
    if depth is not False:
      tracer = DebugTracer("__GEN4", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(77, self.getAtomString(77)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() == 68):
      return tree
    if self.sym == None:
      return tree
    if rule == 1:
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
  def __GEN3(self, depth = 0):
    rule = self.rule(78)
    if depth is not False:
      tracer = DebugTracer("__GEN3", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(78, self.getAtomString(78)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() == 33):
      return tree
    if self.sym == None:
      return tree
    if rule == 51:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_COMMA, tracer) )
      subtree = self._IDENTIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN3(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _INCLUDE_TYPE(self, depth = 0):
    rule = self.rule(79)
    if depth is not False:
      tracer = DebugTracer("_INCLUDE_TYPE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(79, self.getAtomString(79)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 43:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_HEADER_LOCAL, tracer) )
      return tree
    elif rule == 69:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_IDENTIFIER, tracer) )
      return tree
    elif rule == 91:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_HEADER_GLOBAL, tracer) )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PRAGMA_LINE(self, depth = 0):
    rule = self.rule(80)
    if depth is not False:
      tracer = DebugTracer("_PRAGMA_LINE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(80, self.getAtomString(80)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 33:
      tree.astTransform = AstTransformNodeCreator('Pragma', {'tokens': 1})
      tree.add( self.expect(self.TERMINAL_PRAGMA, tracer) )
      subtree = self.__GEN4(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PUNCTUATOR(self, depth = 0):
    rule = self.rule(81)
    if depth is not False:
      tracer = DebugTracer("_PUNCTUATOR", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(81, self.getAtomString(81)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 4:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SEMI, tracer) )
      return tree
    elif rule == 7:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_EQ, tracer) )
      return tree
    elif rule == 8:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DIV, tracer) )
      return tree
    elif rule == 10:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RSQUARE, tracer) )
      return tree
    elif rule == 11:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SUB, tracer) )
      return tree
    elif rule == 13:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITOR, tracer) )
      return tree
    elif rule == 15:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ELIPSIS, tracer) )
      return tree
    elif rule == 16:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LSHIFT, tracer) )
      return tree
    elif rule == 19:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_COLON, tracer) )
      return tree
    elif rule == 25:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_MUL, tracer) )
      return tree
    elif rule == 26:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_TILDE, tracer) )
      return tree
    elif rule == 28:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ADD, tracer) )
      return tree
    elif rule == 29:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LBRACE, tracer) )
      return tree
    elif rule == 30:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITXOR, tracer) )
      return tree
    elif rule == 35:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_INCR, tracer) )
      return tree
    elif rule == 41:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITOREQ, tracer) )
      return tree
    elif rule == 42:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITANDEQ, tracer) )
      return tree
    elif rule == 45:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITXOREQ, tracer) )
      return tree
    elif rule == 46:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_NEQ, tracer) )
      return tree
    elif rule == 47:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ASSIGN, tracer) )
      return tree
    elif rule == 49:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_AND, tracer) )
      return tree
    elif rule == 50:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_POUNDPOUND, tracer) )
      return tree
    elif rule == 53:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ARROW, tracer) )
      return tree
    elif rule == 54:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LTEQ, tracer) )
      return tree
    elif rule == 56:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_GTEQ, tracer) )
      return tree
    elif rule == 57:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_COMMA, tracer) )
      return tree
    elif rule == 60:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LSQUARE, tracer) )
      return tree
    elif rule == 61:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RSHIFTEQ, tracer) )
      return tree
    elif rule == 64:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_QUESTIONMARK, tracer) )
      return tree
    elif rule == 65:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LSHIFTEQ, tracer) )
      return tree
    elif rule == 68:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DECR, tracer) )
      return tree
    elif rule == 73:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SUBEQ, tracer) )
      return tree
    elif rule == 74:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LPAREN, tracer) )
      return tree
    elif rule == 75:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_POUND, tracer) )
      return tree
    elif rule == 76:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_MOD, tracer) )
      return tree
    elif rule == 77:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ADDEQ, tracer) )
      return tree
    elif rule == 79:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_OR, tracer) )
      return tree
    elif rule == 82:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DOT, tracer) )
      return tree
    elif rule == 83:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LT, tracer) )
      return tree
    elif rule == 84:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RSHIFT, tracer) )
      return tree
    elif rule == 85:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_MODEQ, tracer) )
      return tree
    elif rule == 88:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RBRACE, tracer) )
      return tree
    elif rule == 89:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_AMPERSAND, tracer) )
      return tree
    elif rule == 90:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_GT, tracer) )
      return tree
    elif rule == 93:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_MULEQ, tracer) )
      return tree
    elif rule == 94:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_EXCLAMATION_POINT, tracer) )
      return tree
    elif rule == 95:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RPAREN, tracer) )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PP_TOKENS(self, depth = 0):
    rule = self.rule(82)
    if depth is not False:
      tracer = DebugTracer("_PP_TOKENS", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(82, self.getAtomString(82)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 5:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_PP_NUMBER, tracer) )
      return tree
    elif rule == 12:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_HEADER_LOCAL, tracer) )
      return tree
    elif rule == 31:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_IDENTIFIER, tracer) )
      return tree
    elif rule == 55:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_STRING_LITERAL, tracer) )
      return tree
    elif rule == 70:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_HEADER_GLOBAL, tracer) )
      return tree
    elif rule == 71:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_CHARACTER_CONSTANT, tracer) )
      return tree
    elif rule == 86:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PUNCTUATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _CONTROL_LINE(self, depth = 0):
    rule = self.rule(83)
    if depth is not False:
      tracer = DebugTracer("_CONTROL_LINE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(83, self.getAtomString(83)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 20:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PRAGMA_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 23:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ERROR_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 32:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._INCLUDE_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 52:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DEFINE_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 59:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._UNDEF_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 62:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._LINE_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PP_FILE(self, depth = 0):
    rule = self.rule(84)
    if depth is not False:
      tracer = DebugTracer("_PP_FILE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(84, self.getAtomString(84)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 34:
      tree.astTransform = AstTransformNodeCreator('PPFile', {'nodes': 0})
      subtree = self._PP_NODES_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _IF_PART(self, depth = 0):
    rule = self.rule(85)
    if depth is not False:
      tracer = DebugTracer("_IF_PART", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(85, self.getAtomString(85)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 9:
      tree.astTransform = AstTransformNodeCreator('IfNDef', {'nodes': 2, 'ident': 1})
      tree.add( self.expect(self.TERMINAL_IFNDEF, tracer) )
      tree.add( self.expect(self.TERMINAL_IDENTIFIER, tracer) )
      subtree = self._PP_NODES_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 80:
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
    elif rule == 92:
      tree.astTransform = AstTransformNodeCreator('IfDef', {'nodes': 2, 'ident': 1})
      tree.add( self.expect(self.TERMINAL_IFDEF, tracer) )
      tree.add( self.expect(self.TERMINAL_IDENTIFIER, tracer) )
      subtree = self._PP_NODES_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _ELSEIF_PART(self, depth = 0):
    rule = self.rule(86)
    if depth is not False:
      tracer = DebugTracer("_ELSEIF_PART", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(86, self.getAtomString(86)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 17:
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
    rule = self.rule(87)
    if depth is not False:
      tracer = DebugTracer("__GEN1", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(87, self.getAtomString(87)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() == 49 or self.sym.getId() == 68):
      return tree
    if self.sym != None and (self.sym.getId() == 49 or self.sym.getId() == 68):
      return tree
    if self.sym == None:
      return tree
    elif rule == 18:
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
    rule = self.rule(88)
    if depth is not False:
      tracer = DebugTracer("_PP_NODES_LIST", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(88, self.getAtomString(88)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() == 44 or self.sym.getId() == 68 or self.sym.getId() == 32 or self.sym.getId() == 49):
      return tree
    if self.sym != None and (self.sym.getId() == 44 or self.sym.getId() == 68 or self.sym.getId() == 32 or self.sym.getId() == 49):
      return tree
    if self.sym != None and (self.sym.getId() == 44 or self.sym.getId() == 68 or self.sym.getId() == 32 or self.sym.getId() == 49):
      return tree
    if self.sym != None and (self.sym.getId() == 44 or self.sym.getId() == 68 or self.sym.getId() == 32 or self.sym.getId() == 49):
      return tree
    if self.sym == None:
      return tree
    if rule == 38:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN0(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _INCLUDE_LINE(self, depth = 0):
    rule = self.rule(89)
    if depth is not False:
      tracer = DebugTracer("_INCLUDE_LINE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(89, self.getAtomString(89)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 48:
      tree.astTransform = AstTransformNodeCreator('Include', {'file': 1})
      tree.add( self.expect(self.TERMINAL_INCLUDE, tracer) )
      subtree = self._INCLUDE_TYPE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN6(self, depth = 0):
    rule = self.rule(90)
    if depth is not False:
      tracer = DebugTracer("__GEN6", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(90, self.getAtomString(90)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _DEFINE_LINE(self, depth = 0):
    rule = self.rule(91)
    if depth is not False:
      tracer = DebugTracer("_DEFINE_LINE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(91, self.getAtomString(91)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 39:
      tree.astTransform = AstTransformNodeCreator('Define', {'body': 2, 'ident': 1})
      tree.add( self.expect(self.TERMINAL_DEFINE, tracer) )
      tree.add( self.expect(self.TERMINAL_IDENTIFIER, tracer) )
      subtree = self._REPLACEMENT_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 96:
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
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _ELSE_PART(self, depth = 0):
    rule = self.rule(92)
    if depth is not False:
      tracer = DebugTracer("_ELSE_PART", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(92, self.getAtomString(92)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() == 32):
      return tree
    if self.sym == None:
      return tree
    if rule == 2:
      tree.astTransform = AstTransformNodeCreator('Else', {'nodes': 2})
      tree.add( self.expect(self.TERMINAL_ELSE, tracer) )
      subtree = self._PP_NODES_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN2(self, depth = 0):
    rule = self.rule(93)
    if depth is not False:
      tracer = DebugTracer("__GEN2", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(93, self.getAtomString(93)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() == 33):
      return tree
    if self.sym == None:
      return tree
    elif rule == 63:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._IDENTIFIER(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN3(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _PP_DIRECTIVE(self, depth = 0):
    rule = self.rule(94)
    if depth is not False:
      tracer = DebugTracer("_PP_DIRECTIVE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(94, self.getAtomString(94)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 0:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._CONTROL_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 87:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._IF_SECTION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _IF_SECTION(self, depth = 0):
    rule = self.rule(95)
    if depth is not False:
      tracer = DebugTracer("_IF_SECTION", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(95, self.getAtomString(95)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 66:
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
  def _IDENTIFIER(self, depth = 0):
    rule = self.rule(96)
    if depth is not False:
      tracer = DebugTracer("_IDENTIFIER", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(96, self.getAtomString(96)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 67:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_IDENTIFIER, tracer) )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _ERROR_LINE(self, depth = 0):
    rule = self.rule(97)
    if depth is not False:
      tracer = DebugTracer("_ERROR_LINE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(97, self.getAtomString(97)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 40:
      tree.astTransform = AstTransformNodeCreator('Error', {'tokens': 1})
      tree.add( self.expect(self.TERMINAL_ERROR, tracer) )
      subtree = self.__GEN4(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _REPLACEMENT_LIST(self, depth = 0):
    rule = self.rule(98)
    if depth is not False:
      tracer = DebugTracer("_REPLACEMENT_LIST", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(98, self.getAtomString(98)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() == 68):
      return tree
    if self.sym == None:
      return tree
    if rule == 21:
      tree.astTransform = AstTransformNodeCreator('ReplacementList', {'tokens': 0})
      subtree = self.__GEN4(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  bp0 = {
    16: 1000,
    2: 12000,
    35: 4000,
    4: 5000,
    55: 9000,
    7: 6000,
    10: 9000,
    43: 12000,
    13: 10000,
    45: 11000,
    11: 9000,
    51: 12000,
    52: 2000,
    57: 8000,
    54: 3000,
    23: 9000,
    25: 8000,
    58: 7000,
    47: 14000,
    29: 10000,
    30: 11000,
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
    left.isExpr = True
    left.tracer = tracer
    return left
  def nud0(self, tracer):
    tree = ParseTree( NonTerminal(self.str_nonterminal['_expr'], '_expr') )
    if self.sym.getId() == 65:
      return self.expect( 65, tracer )
      return tree
    if self.sym.getId() == 66:
      return self.expect( 66, tracer )
      return tree
    if self.sym.getId() == 71:
      return tree
    if self.sym.getId() == 9:
      return self.expect( 9, tracer )
      return tree
    if self.sym.getId() == 47:
      tree.add( self.expect( 47, tracer ) ) #here?
      tree.astTransform = AstTransformSubstitution(1)
      tree.add(self.__EXPR())
      tree.astTransform = AstTransformSubstitution(1)
      tree.add( self.expect( 33, tracer ) ) #here?
      tree.astTransform = AstTransformSubstitution(1)
      return tree
    if self.sym.getId() == 48:
      return self.expect( 48, tracer )
      return tree
  def led0(self, left, tracer):
    tree = ParseTree( NonTerminal(self.str_nonterminal['_expr'], '_expr') )
    if self.sym.getId() == 2:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(12000) )
      tree.astTransform = AstTransformNodeCreator('Div', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 43:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(12000) )
      tree.astTransform = AstTransformNodeCreator('Mod', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 4:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(5000) )
      tree.astTransform = AstTransformNodeCreator('BitAND', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 25:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(7999) )
      tree.astTransform = AstTransformNodeCreator('NotEquals', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 7:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(6000) )
      tree.astTransform = AstTransformNodeCreator('BitXOR', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 10:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(9000) )
      tree.astTransform = AstTransformNodeCreator('LessThanEq', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 11:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(9000) )
      tree.astTransform = AstTransformNodeCreator('GreaterThanEq', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 13:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(10000) )
      tree.astTransform = AstTransformNodeCreator('RightShift', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 45:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(11000) )
      tree.astTransform = AstTransformNodeCreator('Sub', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 16:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(1000) )
      tree.astTransform = AstTransformNodeCreator('Comma', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 51:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(12000) )
      tree.astTransform = AstTransformNodeCreator('Mul', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 52:
      if left:
        tree.add( left )
      tree.add( self.expect( 52, tracer ) )
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      tree.add(self.__EXPR())
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      tree.add( self.expect( 64, tracer ) )
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      tree.add(self.__EXPR())
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      return tree
    if self.sym.getId() == 55:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(9000) )
      tree.astTransform = AstTransformNodeCreator('GreaterThan', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 23:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(9000) )
      tree.astTransform = AstTransformNodeCreator('LessThan', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 57:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(7999) )
      tree.astTransform = AstTransformNodeCreator('Equals', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 58:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(7000) )
      tree.astTransform = AstTransformNodeCreator('BitOR', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 47:
      if left:
        tree.add( left )
      ls = []
      tree.add( self.expect( 47, tracer ) )
      if self.sym.getId() != 33:
        while 1:
          ls.append( self.__EXPR() )
          if self.sym.getId() != 16:
            break
          self.expect( 16, tracer )
      tree.add( ls )
      tree.add( self.expect(33, tracer ) )
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      return tree
    if self.sym.getId() == 29:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(10000) )
      tree.astTransform = AstTransformNodeCreator('LeftShift', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 30:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(11000) )
      tree.astTransform = AstTransformNodeCreator('Add', {'right': 2, 'left': 0})
      return tree
