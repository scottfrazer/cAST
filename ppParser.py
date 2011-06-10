import sys
def parse( iterator, entry ):
  p = Parser()
  return p.parse(iterator, entry)
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
  def __init__(self, nonterminal):
    self.children = []
    self.nonterminal = nonterminal
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
  def __init__(self, message):
    self.message = message
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
  TERMINAL_SEPARATOR = 0
  TERMINAL_OR = 1
  TERMINAL_LINE = 2
  TERMINAL_DIV = 3
  TERMINAL_SUBEQ = 4
  TERMINAL_UNDEF = 5
  TERMINAL_LPAREN = 6
  TERMINAL_ELIPSIS = 7
  TERMINAL_MODEQ = 8
  TERMINAL_ENDIF = 9
  TERMINAL_BITXOR = 10
  TERMINAL_CSOURCE = 11
  TERMINAL_ARROW = 12
  TERMINAL_CHARACTER_CONSTANT = 13
  TERMINAL_LTEQ = 14
  TERMINAL_POUND = 15
  TERMINAL_DOT = 16
  TERMINAL_RSHIFTEQ = 17
  TERMINAL_RSHIFT = 18
  TERMINAL_DEFINE = 19
  TERMINAL_POUNDPOUND = 20
  TERMINAL_SUB = 21
  TERMINAL_NOT = 22
  TERMINAL_AMPERSAND = 23
  TERMINAL_GTEQ = 24
  TERMINAL_IFDEF = 25
  TERMINAL_BITNOT = 26
  TERMINAL_LT = 27
  TERMINAL_MULEQ = 28
  TERMINAL_NEQ = 29
  TERMINAL_LPAREN_SPECIAL = 30
  TERMINAL_RSQUARE = 31
  TERMINAL_IF = 32
  TERMINAL_RBRACE = 33
  TERMINAL_LSHIFT = 34
  TERMINAL_ADD = 35
  TERMINAL_HEADER_LOCAL = 36
  TERMINAL_BITAND = 37
  TERMINAL_COMMA = 38
  TERMINAL_RPAREN = 39
  TERMINAL_AND = 40
  TERMINAL_EXCLAMATION_POINT = 41
  TERMINAL_IFNDEF = 42
  TERMINAL_BITANDEQ = 43
  TERMINAL_TILDE = 44
  TERMINAL_ADDEQ = 45
  TERMINAL_MOD = 46
  TERMINAL_ELIF = 47
  TERMINAL_SEMI = 48
  TERMINAL_ASSIGN = 49
  TERMINAL_IDENTIFIER = 50
  TERMINAL_ELSE = 51
  TERMINAL_INCLUDE = 52
  TERMINAL_MUL = 53
  TERMINAL_QUESTIONMARK = 54
  TERMINAL_GT = 55
  TERMINAL_BITOREQ = 56
  TERMINAL_PRAGMA = 57
  TERMINAL_EQ = 58
  TERMINAL_BITOR = 59
  TERMINAL_BITXOREQ = 60
  TERMINAL_LSQUARE = 61
  TERMINAL_ERROR = 62
  TERMINAL_HEADER_GLOBAL = 63
  TERMINAL_DECR = 64
  TERMINAL_COLON = 65
  TERMINAL_PP_NUMBER = 66
  TERMINAL_STRING_LITERAL = 67
  TERMINAL_LSHIFTEQ = 68
  TERMINAL_INCR = 69
  TERMINAL_LBRACE = 70
  terminal_str = {
    0: 'separator',
    1: 'or',
    2: 'line',
    3: 'div',
    4: 'subeq',
    5: 'undef',
    6: 'lparen',
    7: 'elipsis',
    8: 'modeq',
    9: 'endif',
    10: 'bitxor',
    11: 'csource',
    12: 'arrow',
    13: 'character_constant',
    14: 'lteq',
    15: 'pound',
    16: 'dot',
    17: 'rshifteq',
    18: 'rshift',
    19: 'define',
    20: 'poundpound',
    21: 'sub',
    22: 'not',
    23: 'ampersand',
    24: 'gteq',
    25: 'ifdef',
    26: 'bitnot',
    27: 'lt',
    28: 'muleq',
    29: 'neq',
    30: 'lparen_special',
    31: 'rsquare',
    32: 'if',
    33: 'rbrace',
    34: 'lshift',
    35: 'add',
    36: 'header_local',
    37: 'bitand',
    38: 'comma',
    39: 'rparen',
    40: 'and',
    41: 'exclamation_point',
    42: 'ifndef',
    43: 'bitandeq',
    44: 'tilde',
    45: 'addeq',
    46: 'mod',
    47: 'elif',
    48: 'semi',
    49: 'assign',
    50: 'identifier',
    51: 'else',
    52: 'include',
    53: 'mul',
    54: 'questionmark',
    55: 'gt',
    56: 'bitoreq',
    57: 'pragma',
    58: 'eq',
    59: 'bitor',
    60: 'bitxoreq',
    61: 'lsquare',
    62: 'error',
    63: 'header_global',
    64: 'decr',
    65: 'colon',
    66: 'pp_number',
    67: 'string_literal',
    68: 'lshifteq',
    69: 'incr',
    70: 'lbrace',
  }
  nonterminal_str = {
    71: '_expr',
    72: '_gen0',
    73: 'undef_line',
    74: '_gen5',
    75: 'pp_nodes',
    76: 'line_line',
    77: 'replacement_list',
    78: 'if_section',
    79: 'pp_directive',
    80: 'include_type',
    81: 'pragma_line',
    82: 'punctuator',
    83: '_gen6',
    84: '_gen4',
    85: 'control_line',
    86: 'pp_file',
    87: 'if_part',
    88: 'elseif_part',
    89: '_gen1',
    90: 'pp_nodes_list',
    91: 'include_line',
    92: 'pp_tokens',
    93: 'define_line',
    94: 'else_part',
    95: 'identifier',
    96: '_gen2',
    97: '_gen3',
    98: 'error_line',
    99: 'define_line_body',
  }
  str_terminal = {
    'separator': 0,
    'or': 1,
    'line': 2,
    'div': 3,
    'subeq': 4,
    'undef': 5,
    'lparen': 6,
    'elipsis': 7,
    'modeq': 8,
    'endif': 9,
    'bitxor': 10,
    'csource': 11,
    'arrow': 12,
    'character_constant': 13,
    'lteq': 14,
    'pound': 15,
    'dot': 16,
    'rshifteq': 17,
    'rshift': 18,
    'define': 19,
    'poundpound': 20,
    'sub': 21,
    'not': 22,
    'ampersand': 23,
    'gteq': 24,
    'ifdef': 25,
    'bitnot': 26,
    'lt': 27,
    'muleq': 28,
    'neq': 29,
    'lparen_special': 30,
    'rsquare': 31,
    'if': 32,
    'rbrace': 33,
    'lshift': 34,
    'add': 35,
    'header_local': 36,
    'bitand': 37,
    'comma': 38,
    'rparen': 39,
    'and': 40,
    'exclamation_point': 41,
    'ifndef': 42,
    'bitandeq': 43,
    'tilde': 44,
    'addeq': 45,
    'mod': 46,
    'elif': 47,
    'semi': 48,
    'assign': 49,
    'identifier': 50,
    'else': 51,
    'include': 52,
    'mul': 53,
    'questionmark': 54,
    'gt': 55,
    'bitoreq': 56,
    'pragma': 57,
    'eq': 58,
    'bitor': 59,
    'bitxoreq': 60,
    'lsquare': 61,
    'error': 62,
    'header_global': 63,
    'decr': 64,
    'colon': 65,
    'pp_number': 66,
    'string_literal': 67,
    'lshifteq': 68,
    'incr': 69,
    'lbrace': 70,
  }
  str_nonterminal = {
    '_expr': 71,
    '_gen0': 72,
    'undef_line': 73,
    '_gen5': 74,
    'pp_nodes': 75,
    'line_line': 76,
    'replacement_list': 77,
    'if_section': 78,
    'pp_directive': 79,
    'include_type': 80,
    'pragma_line': 81,
    'punctuator': 82,
    '_gen6': 83,
    '_gen4': 84,
    'control_line': 85,
    'pp_file': 86,
    'if_part': 87,
    'elseif_part': 88,
    '_gen1': 89,
    'pp_nodes_list': 90,
    'include_line': 91,
    'pp_tokens': 92,
    'define_line': 93,
    'else_part': 94,
    'identifier': 95,
    '_gen2': 96,
    '_gen3': 97,
    'error_line': 98,
    'define_line_body': 99,
  }
  terminal_count = 71
  nonterminal_count = 29
  parse_table = [
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, 2, -1, -1, 2, -1, -1, -1, -1, -1, 2, -1, -1, -1, -1, -1, -1, -1, 2, -1, -1, -1, -1, -1, 2, -1, -1, -1, -1, -1, -1, 2, -1, -1, -1, -1, -1, -1, -1, -1, -1, 2, -1, -1, -1, -1, -1, -1, -1, -1, -1, 2, -1, -1, -1, -1, 2, -1, -1, -1, -1, 2, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, 84, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, 79, -1, -1, 79, -1, -1, -1, -1, -1, 35, -1, -1, -1, -1, -1, -1, -1, 79, -1, -1, -1, -1, -1, 79, -1, -1, -1, -1, -1, -1, 79, -1, -1, -1, -1, -1, -1, -1, -1, -1, 79, -1, -1, -1, -1, -1, -1, -1, -1, -1, 79, -1, -1, -1, -1, 79, -1, -1, -1, -1, 79, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, 76, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, 29, -1, 29, 29, -1, 29, 29, 29, -1, 29, -1, 29, 29, 29, 29, 29, 29, 29, -1, 29, 29, -1, 29, 29, -1, -1, 29, 29, 29, -1, 29, -1, 29, 29, 29, 29, -1, 29, 29, 29, 29, -1, 29, 29, 29, 29, -1, 29, 29, 29, -1, -1, 29, 29, 29, 29, -1, 29, 29, 29, 29, -1, 29, 29, 29, 29, 29, 29, 29, 29],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 73, -1, -1, -1, -1, -1, -1, 73, -1, -1, -1, -1, -1, -1, -1, -1, -1, 73, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, 7, -1, -1, 7, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 7, -1, -1, -1, -1, -1, 92, -1, -1, -1, -1, -1, -1, 92, -1, -1, -1, -1, -1, -1, -1, -1, -1, 92, -1, -1, -1, -1, -1, -1, -1, -1, -1, 7, -1, -1, -1, -1, 7, -1, -1, -1, -1, 7, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 46, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 70, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 96, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 38, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, 39, -1, 41, 74, -1, 81, 17, 90, -1, 45, -1, 57, -1, 58, 78, 89, 66, 91, -1, 54, 15, -1, 94, 60, -1, -1, 88, 43, 49, -1, 11, -1, 95, 14, 27, -1, -1, 62, 44, 52, 1, -1, 42, 61, 82, 83, -1, 4, 50, -1, -1, -1, 24, 71, 97, 33, -1, 6, 3, 47, 48, -1, -1, 75, 19, -1, -1, 68, 22, 28],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, 23, -1, 23, 23, -1, 23, 23, 23, -1, 23, -1, 23, 23, 23, 23, 23, 23, 23, -1, 23, 23, -1, 23, 23, -1, -1, 23, 23, 23, -1, 23, -1, 23, 23, 23, 23, -1, 23, 23, 23, 23, -1, 23, 23, 23, 23, -1, 23, 23, 23, -1, -1, 23, 23, 23, 23, -1, 23, 23, 23, 23, -1, 23, 23, 23, 23, 23, 23, 23, 23],
  [-1, -1, 69, -1, -1, 63, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 55, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 32, -1, -1, -1, -1, 20, -1, -1, -1, -1, 37, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, 34, -1, -1, 34, -1, -1, -1, -1, -1, 34, -1, -1, -1, -1, -1, -1, -1, 34, -1, -1, -1, -1, -1, 34, -1, -1, -1, -1, -1, -1, 34, -1, -1, -1, -1, -1, -1, -1, -1, -1, 34, -1, -1, -1, -1, -1, -1, -1, -1, -1, 34, -1, -1, -1, -1, 34, -1, -1, -1, -1, 34, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 0, -1, -1, -1, -1, -1, -1, 87, -1, -1, -1, -1, -1, -1, -1, -1, -1, 10, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 18, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 16, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, 53, -1, -1, 53, -1, -1, -1, -1, -1, 53, -1, -1, -1, -1, -1, -1, -1, 53, -1, -1, -1, -1, -1, 53, -1, -1, -1, -1, -1, -1, 53, -1, -1, -1, -1, -1, -1, -1, -1, -1, 53, -1, -1, -1, -1, -1, -1, -1, -1, -1, 53, -1, -1, -1, -1, 53, -1, -1, -1, -1, 53, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 51, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, 93, -1, 93, 93, -1, 93, 93, 93, -1, 93, -1, 93, 72, 93, 93, 93, 93, 93, -1, 93, 93, -1, 93, 93, -1, -1, 93, 93, 93, -1, 93, -1, 93, 93, 93, 85, -1, 93, 93, 93, 93, -1, 93, 93, 93, 93, -1, 93, 93, 30, -1, -1, 93, 93, 93, 93, -1, 93, 93, 93, 93, -1, 77, 93, 93, 25, 59, 93, 93, 93],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 36, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 8, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 80, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 40, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 56, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 21, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, 9, -1, 9, 9, -1, 9, 9, 9, -1, 9, -1, 9, 9, 9, 9, 9, 9, 9, -1, 9, 9, -1, 9, 9, -1, -1, 9, 9, 9, 64, 9, -1, 9, 9, 9, 9, -1, 9, 9, 9, 9, -1, 9, 9, 9, 9, -1, 9, 9, 9, -1, -1, 9, 9, 9, 9, -1, 9, 9, 9, 9, -1, 9, 9, 9, 9, 9, 9, 9, 9]
  ]
  def terminal(self, str):
    return self.str_terminal[str]
  def terminalNames(self):
    return list(self.str_terminal.keys())
  def isTerminal(self, id):
    return 0 <= id <= 70
  def isNonTerminal(self, id):
    return 71 <= id <= 99
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
      raise SyntaxError('Syntax Error: Finished parsing without consuming all tokens.')
    self.iterator = None
    self.sym = None
    return tree
  def next(self):
    self.sym = self.getsym()
    if self.sym is not None and not self.isTerminal(self.sym.getId()):
      self.sym = None
      raise SyntaxError('Invalid symbol ID: %d (%s)'%(self.sym.getId(), self.sym))
    if self.recorder.awake and self.sym is not None:
      self.recorder.record(self.sym)
    return self.sym
  def expect(self, s):
    x = self.sym
    if self.sym and s == self.sym.getId():
      symbol = self.sym
      self.sym = self.next()
      print('expect %s, next %s' %(x, self.sym))
      return symbol
    else:
      raise SyntaxError('Unexpected symbol.  Expected %s, got %s.' %(self.terminal_str[s], self.sym if self.sym else 'None'))
  def rule(self, n):
    if self.sym == None: return -1
    return self.parse_table[n - 71][self.sym.getId()]
  def __GEN0(self):
    rule = self.rule(72)
    tree = ParseTree( NonTerminal(72, self.getAtomString(72)) )
    tree.list = 'tlist'
    if self.sym != None and (self.sym.getId() == 51 or self.sym.getId() == 47 or self.sym.getId() == 0 or self.sym.getId() == 9):
      return tree
    if self.sym != None and (self.sym.getId() == 51 or self.sym.getId() == 47 or self.sym.getId() == 0 or self.sym.getId() == 9):
      return tree
    if self.sym != None and (self.sym.getId() == 51 or self.sym.getId() == 47 or self.sym.getId() == 0 or self.sym.getId() == 9):
      return tree
    if self.sym != None and (self.sym.getId() == 51 or self.sym.getId() == 47 or self.sym.getId() == 0 or self.sym.getId() == 9):
      return tree
    if self.sym == None:
      return tree
    if rule == 2:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self._PP_NODES() )
      tree.add( self.expect(self.TERMINAL_SEPARATOR) )
      tree.add( self.__GEN0() )
      return tree
    return tree
  def _UNDEF_LINE(self):
    rule = self.rule(73)
    tree = ParseTree( NonTerminal(73, self.getAtomString(73)) )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 84:
      tree.astTransform = AstTransformNodeCreator('Undef', {'ident': 1})
      tree.add( self.expect(self.TERMINAL_UNDEF) )
      tree.add( self.expect(self.TERMINAL_IDENTIFIER) )
      return tree
    raise SyntaxError('Error: Unexpected symbol')
  def __GEN5(self):
    rule = self.rule(74)
    tree = ParseTree( NonTerminal(74, self.getAtomString(74)) )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    raise SyntaxError('Error: Unexpected symbol')
  def _PP_NODES(self):
    rule = self.rule(75)
    tree = ParseTree( NonTerminal(75, self.getAtomString(75)) )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 35:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_CSOURCE) )
      return tree
    elif rule == 79:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self._PP_DIRECTIVE() )
      return tree
    raise SyntaxError('Error: Unexpected symbol')
  def _LINE_LINE(self):
    rule = self.rule(76)
    tree = ParseTree( NonTerminal(76, self.getAtomString(76)) )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 76:
      tree.astTransform = AstTransformNodeCreator('Line', {'tokens': 1})
      tree.add( self.expect(self.TERMINAL_LINE) )
      tree.add( self.__GEN4() )
      return tree
    raise SyntaxError('Error: Unexpected symbol')
  def _REPLACEMENT_LIST(self):
    rule = self.rule(77)
    tree = ParseTree( NonTerminal(77, self.getAtomString(77)) )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 29:
      tree.astTransform = AstTransformNodeCreator('ReplacementList', {'tokens': 0})
      tree.add( self.__GEN4() )
      return tree
    raise SyntaxError('Error: Unexpected symbol')
  def _IF_SECTION(self):
    rule = self.rule(78)
    tree = ParseTree( NonTerminal(78, self.getAtomString(78)) )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 73:
      tree.astTransform = AstTransformNodeCreator('IfSection', {'elif': 1, 'else': 2, 'if': 0})
      tree.add( self._IF_PART() )
      tree.add( self.__GEN1() )
      tree.add( self._ELSE_PART() )
      tree.add( self.expect(self.TERMINAL_ENDIF) )
      return tree
    raise SyntaxError('Error: Unexpected symbol')
  def _PP_DIRECTIVE(self):
    rule = self.rule(79)
    tree = ParseTree( NonTerminal(79, self.getAtomString(79)) )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 7:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self._CONTROL_LINE() )
      return tree
    elif rule == 92:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self._IF_SECTION() )
      return tree
    raise SyntaxError('Error: Unexpected symbol')
  def _INCLUDE_TYPE(self):
    rule = self.rule(80)
    tree = ParseTree( NonTerminal(80, self.getAtomString(80)) )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 46:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_HEADER_LOCAL) )
      return tree
    elif rule == 70:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_IDENTIFIER) )
      return tree
    elif rule == 96:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_HEADER_GLOBAL) )
      return tree
    raise SyntaxError('Error: Unexpected symbol')
  def _PRAGMA_LINE(self):
    rule = self.rule(81)
    tree = ParseTree( NonTerminal(81, self.getAtomString(81)) )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 38:
      tree.astTransform = AstTransformNodeCreator('Pragma', {'tokens': 1})
      tree.add( self.expect(self.TERMINAL_PRAGMA) )
      tree.add( self.__GEN4() )
      return tree
    raise SyntaxError('Error: Unexpected symbol')
  def _PUNCTUATOR(self):
    rule = self.rule(82)
    tree = ParseTree( NonTerminal(82, self.getAtomString(82)) )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 1:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_EXCLAMATION_POINT) )
      return tree
    elif rule == 3:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITOR) )
      return tree
    elif rule == 4:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SEMI) )
      return tree
    elif rule == 6:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_EQ) )
      return tree
    elif rule == 11:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RSQUARE) )
      return tree
    elif rule == 14:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LSHIFT) )
      return tree
    elif rule == 15:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SUB) )
      return tree
    elif rule == 17:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ELIPSIS) )
      return tree
    elif rule == 19:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_COLON) )
      return tree
    elif rule == 22:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_INCR) )
      return tree
    elif rule == 24:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_MUL) )
      return tree
    elif rule == 27:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ADD) )
      return tree
    elif rule == 28:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LBRACE) )
      return tree
    elif rule == 33:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITOREQ) )
      return tree
    elif rule == 39:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_OR) )
      return tree
    elif rule == 41:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DIV) )
      return tree
    elif rule == 42:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITANDEQ) )
      return tree
    elif rule == 43:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_MULEQ) )
      return tree
    elif rule == 44:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RPAREN) )
      return tree
    elif rule == 45:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITXOR) )
      return tree
    elif rule == 47:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITXOREQ) )
      return tree
    elif rule == 48:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LSQUARE) )
      return tree
    elif rule == 49:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_NEQ) )
      return tree
    elif rule == 50:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ASSIGN) )
      return tree
    elif rule == 52:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_AND) )
      return tree
    elif rule == 54:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_POUNDPOUND) )
      return tree
    elif rule == 57:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ARROW) )
      return tree
    elif rule == 58:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LTEQ) )
      return tree
    elif rule == 60:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_GTEQ) )
      return tree
    elif rule == 61:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_TILDE) )
      return tree
    elif rule == 62:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_COMMA) )
      return tree
    elif rule == 66:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RSHIFTEQ) )
      return tree
    elif rule == 68:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LSHIFTEQ) )
      return tree
    elif rule == 71:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_QUESTIONMARK) )
      return tree
    elif rule == 74:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SUBEQ) )
      return tree
    elif rule == 75:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DECR) )
      return tree
    elif rule == 78:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_POUND) )
      return tree
    elif rule == 81:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LPAREN) )
      return tree
    elif rule == 82:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ADDEQ) )
      return tree
    elif rule == 83:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_MOD) )
      return tree
    elif rule == 88:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LT) )
      return tree
    elif rule == 89:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DOT) )
      return tree
    elif rule == 90:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_MODEQ) )
      return tree
    elif rule == 91:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RSHIFT) )
      return tree
    elif rule == 94:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_AMPERSAND) )
      return tree
    elif rule == 95:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RBRACE) )
      return tree
    elif rule == 97:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_GT) )
      return tree
    raise SyntaxError('Error: Unexpected symbol')
  def __GEN6(self):
    rule = self.rule(83)
    tree = ParseTree( NonTerminal(83, self.getAtomString(83)) )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    raise SyntaxError('Error: Unexpected symbol')
  def __GEN4(self):
    rule = self.rule(84)
    tree = ParseTree( NonTerminal(84, self.getAtomString(84)) )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() == 0):
      return tree
    if self.sym == None:
      return tree
    if rule == 23:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self._PP_TOKENS() )
      tree.add( self.__GEN4() )
      return tree
    return tree
  def _CONTROL_LINE(self):
    rule = self.rule(85)
    tree = ParseTree( NonTerminal(85, self.getAtomString(85)) )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 20:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self._PRAGMA_LINE() )
      return tree
    elif rule == 32:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self._INCLUDE_LINE() )
      return tree
    elif rule == 37:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self._ERROR_LINE() )
      return tree
    elif rule == 55:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self._DEFINE_LINE() )
      return tree
    elif rule == 63:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self._UNDEF_LINE() )
      return tree
    elif rule == 69:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self._LINE_LINE() )
      return tree
    raise SyntaxError('Error: Unexpected symbol')
  def _PP_FILE(self):
    rule = self.rule(86)
    tree = ParseTree( NonTerminal(86, self.getAtomString(86)) )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 34:
      tree.astTransform = AstTransformNodeCreator('PPFile', {'nodes': 0})
      tree.add( self._PP_NODES_LIST() )
      return tree
    raise SyntaxError('Error: Unexpected symbol')
  def _IF_PART(self):
    rule = self.rule(87)
    tree = ParseTree( NonTerminal(87, self.getAtomString(87)) )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 0:
      tree.astTransform = AstTransformNodeCreator('IfDef', {'nodes': 2, 'ident': 1})
      tree.add( self.expect(self.TERMINAL_IFDEF) )
      tree.add( self.expect(self.TERMINAL_IDENTIFIER) )
      tree.add( self._PP_NODES_LIST() )
      return tree
    elif rule == 10:
      tree.astTransform = AstTransformNodeCreator('IfNDef', {'nodes': 2, 'ident': 1})
      tree.add( self.expect(self.TERMINAL_IFNDEF) )
      tree.add( self.expect(self.TERMINAL_IDENTIFIER) )
      tree.add( self._PP_NODES_LIST() )
      return tree
    elif rule == 87:
      tree.astTransform = AstTransformNodeCreator('If', {'expr': 1, 'nodes': 1})
      tree.add( self.expect(self.TERMINAL_IF) )
      tree.add( self.__EXPR() )
      tree.add( self._PP_NODES_LIST() )
      return tree
    raise SyntaxError('Error: Unexpected symbol')
  def _ELSEIF_PART(self):
    rule = self.rule(88)
    tree = ParseTree( NonTerminal(88, self.getAtomString(88)) )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 18:
      tree.astTransform = AstTransformNodeCreator('ElseIf', {'expr': 1, 'nodes': 2})
      tree.add( self.expect(self.TERMINAL_ELIF) )
      tree.add( self.__EXPR() )
      tree.add( self._PP_NODES_LIST() )
      return tree
    raise SyntaxError('Error: Unexpected symbol')
  def __GEN1(self):
    rule = self.rule(89)
    tree = ParseTree( NonTerminal(89, self.getAtomString(89)) )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() == 51 or self.sym.getId() == 0):
      return tree
    if self.sym != None and (self.sym.getId() == 51 or self.sym.getId() == 0):
      return tree
    if self.sym == None:
      return tree
    elif rule == 16:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self._ELSEIF_PART() )
      tree.add( self.__GEN1() )
      return tree
    return tree
  def _PP_NODES_LIST(self):
    rule = self.rule(90)
    tree = ParseTree( NonTerminal(90, self.getAtomString(90)) )
    tree.list = False
    if self.sym != None and (self.sym.getId() == 47 or self.sym.getId() == 9 or self.sym.getId() == 0 or self.sym.getId() == 51):
      return tree
    if self.sym != None and (self.sym.getId() == 47 or self.sym.getId() == 9 or self.sym.getId() == 0 or self.sym.getId() == 51):
      return tree
    if self.sym != None and (self.sym.getId() == 47 or self.sym.getId() == 9 or self.sym.getId() == 0 or self.sym.getId() == 51):
      return tree
    if self.sym != None and (self.sym.getId() == 47 or self.sym.getId() == 9 or self.sym.getId() == 0 or self.sym.getId() == 51):
      return tree
    if self.sym == None:
      return tree
    if rule == 53:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.__GEN0() )
      return tree
    return tree
  def _INCLUDE_LINE(self):
    rule = self.rule(91)
    tree = ParseTree( NonTerminal(91, self.getAtomString(91)) )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 51:
      tree.astTransform = AstTransformNodeCreator('Include', {'file': 1})
      tree.add( self.expect(self.TERMINAL_INCLUDE) )
      tree.add( self._INCLUDE_TYPE() )
      return tree
    raise SyntaxError('Error: Unexpected symbol')
  def _PP_TOKENS(self):
    rule = self.rule(92)
    tree = ParseTree( NonTerminal(92, self.getAtomString(92)) )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 25:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_PP_NUMBER) )
      return tree
    elif rule == 30:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_IDENTIFIER) )
      return tree
    elif rule == 59:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_STRING_LITERAL) )
      return tree
    elif rule == 72:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_CHARACTER_CONSTANT) )
      return tree
    elif rule == 77:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_HEADER_GLOBAL) )
      return tree
    elif rule == 85:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_HEADER_LOCAL) )
      return tree
    elif rule == 93:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self._PUNCTUATOR() )
      return tree
    raise SyntaxError('Error: Unexpected symbol')
  def _DEFINE_LINE(self):
    rule = self.rule(93)
    tree = ParseTree( NonTerminal(93, self.getAtomString(93)) )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 36:
      tree.astTransform = AstTransformNodeCreator('Define', {'body': 2, 'ident': 1})
      tree.add( self.expect(self.TERMINAL_DEFINE) )
      tree.add( self.expect(self.TERMINAL_IDENTIFIER) )
      tree.add( self._DEFINE_LINE_BODY() )
      return tree
    raise SyntaxError('Error: Unexpected symbol')
  def _ELSE_PART(self):
    rule = self.rule(94)
    tree = ParseTree( NonTerminal(94, self.getAtomString(94)) )
    tree.list = False
    if self.sym != None and (self.sym.getId() == 9):
      return tree
    if self.sym == None:
      return tree
    if rule == 8:
      tree.astTransform = AstTransformNodeCreator('Else', {'nodes': 2})
      tree.add( self.expect(self.TERMINAL_ELSE) )
      tree.add( self._PP_NODES_LIST() )
      return tree
    return tree
  def _IDENTIFIER(self):
    rule = self.rule(95)
    tree = ParseTree( NonTerminal(95, self.getAtomString(95)) )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 80:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_IDENTIFIER) )
      return tree
    raise SyntaxError('Error: Unexpected symbol')
  def __GEN2(self):
    rule = self.rule(96)
    tree = ParseTree( NonTerminal(96, self.getAtomString(96)) )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() == 39):
      return tree
    if self.sym == None:
      return tree
    if rule == 40:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self._IDENTIFIER() )
      tree.add( self.__GEN3() )
      return tree
    return tree
  def __GEN3(self):
    rule = self.rule(97)
    tree = ParseTree( NonTerminal(97, self.getAtomString(97)) )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() == 39):
      return tree
    if self.sym == None:
      return tree
    if rule == 56:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_COMMA) )
      tree.add( self._IDENTIFIER() )
      tree.add( self.__GEN3() )
      return tree
    return tree
  def _ERROR_LINE(self):
    rule = self.rule(98)
    tree = ParseTree( NonTerminal(98, self.getAtomString(98)) )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 21:
      tree.astTransform = AstTransformNodeCreator('Error', {'tokens': 1})
      tree.add( self.expect(self.TERMINAL_ERROR) )
      tree.add( self.__GEN4() )
      return tree
    raise SyntaxError('Error: Unexpected symbol')
  def _DEFINE_LINE_BODY(self):
    rule = self.rule(99)
    tree = ParseTree( NonTerminal(99, self.getAtomString(99)) )
    tree.list = False
    if self.sym != None and (self.sym.getId() == 0):
      return tree
    if self.sym == None:
      return tree
    if rule == 9:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self._REPLACEMENT_LIST() )
      return tree
    elif rule == 64:
      tree.astTransform = AstTransformNodeCreator('Function', {'tokens': 3, 'params': 1})
      tree.add( self.expect(self.TERMINAL_LPAREN_SPECIAL) )
      tree.add( self.__GEN2() )
      tree.add( self.expect(self.TERMINAL_RPAREN) )
      tree.add( self._REPLACEMENT_LIST() )
      return tree
    return tree
  bp0 = {
    14: 9000,
    1: 3000,
    34: 10000,
    59: 7000,
    37: 5000,
    6: 14000,
    40: 4000,
    38: 1000,
    10: 6000,
    46: 12000,
    18: 10000,
    35: 11000,
    21: 11000,
    54: 2000,
    55: 9000,
    24: 9000,
    58: 8000,
    27: 9000,
    3: 12000,
    29: 8000,
    53: 12000,
  }
  def __EXPR( self, rbp = 0 ):
    t = self.sym
    left = self.nud0()
    while rbp < self.binding_power(self.sym, self.bp0):
      left = self.led0(left)
    left.isExpr = True
    return left
  def nud0(self):
    tree = ParseTree( NonTerminal(self.str_nonterminal['_expr'], '_expr') )
    if self.sym.getId() == 66:
      return self.expect(66)
      return tree
    if self.sym.getId() == 67:
      return self.expect(67)
      return tree
    if self.sym.getId() == 6:
      tree.add( self.expect(6) ) #here?
      tree.add(self.__EXPR())
      tree.add( self.expect(39) ) #here?
      return tree
    if self.sym.getId() == 71:
      return tree
    if self.sym.getId() == 13:
      return self.expect(13)
      return tree
    if self.sym.getId() == 50:
      return self.expect(50)
      return tree
  def led0(self, left):
    tree = ParseTree( NonTerminal(self.str_nonterminal['_expr'], '_expr') )
    if self.sym.getId() == 34:
      if left:
        tree.add( left )
      tree.add( self.expect(self.sym.getId()) )
      tree.add( self.__EXPR(10000) )
      tree.astTransform = AstTransformNodeCreator('LeftShift', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 35:
      if left:
        tree.add( left )
      tree.add( self.expect(self.sym.getId()) )
      tree.add( self.__EXPR(11000) )
      tree.astTransform = AstTransformNodeCreator('Add', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 37:
      if left:
        tree.add( left )
      tree.add( self.expect(self.sym.getId()) )
      tree.add( self.__EXPR(5000) )
      tree.astTransform = AstTransformNodeCreator('BitAND', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 38:
      if left:
        tree.add( left )
      tree.add( self.expect(self.sym.getId()) )
      tree.add( self.__EXPR(1000) )
      tree.astTransform = AstTransformNodeCreator('Comma', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 14:
      if left:
        tree.add( left )
      tree.add( self.expect(self.sym.getId()) )
      tree.add( self.__EXPR(9000) )
      tree.astTransform = AstTransformNodeCreator('LessThanEq', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 46:
      if left:
        tree.add( left )
      tree.add( self.expect(self.sym.getId()) )
      tree.add( self.__EXPR(12000) )
      tree.astTransform = AstTransformNodeCreator('Mod', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 29:
      if left:
        tree.add( left )
      tree.add( self.expect(self.sym.getId()) )
      tree.add( self.__EXPR(7999) )
      tree.astTransform = AstTransformNodeCreator('NotEquals', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 27:
      if left:
        tree.add( left )
      tree.add( self.expect(self.sym.getId()) )
      tree.add( self.__EXPR(9000) )
      tree.astTransform = AstTransformNodeCreator('LessThan', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 6:
      if left:
        tree.add( left )
      ls = []
      tree.add( self.expect(6) )
      if self.sym.getId() != 39:
        while 1:
          ls.append( self.__EXPR() )
          if self.sym.getId() != 38:
            break
          self.expect(38)
      tree.add( ls )
      tree.add( self.expect(39) )
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      return tree
    if self.sym.getId() == 18:
      if left:
        tree.add( left )
      tree.add( self.expect(self.sym.getId()) )
      tree.add( self.__EXPR(10000) )
      tree.astTransform = AstTransformNodeCreator('RightShift', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 3:
      if left:
        tree.add( left )
      tree.add( self.expect(self.sym.getId()) )
      tree.add( self.__EXPR(12000) )
      tree.astTransform = AstTransformNodeCreator('Div', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 53:
      if left:
        tree.add( left )
      tree.add( self.expect(self.sym.getId()) )
      tree.add( self.__EXPR(12000) )
      tree.astTransform = AstTransformNodeCreator('Mul', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 54:
      if left:
        tree.add( left )
      tree.add( self.expect(54) )
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      tree.add(self.__EXPR(0))
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      tree.add( self.expect(65) )
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      tree.add(self.__EXPR(0))
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      return tree
    if self.sym.getId() == 55:
      if left:
        tree.add( left )
      tree.add( self.expect(self.sym.getId()) )
      tree.add( self.__EXPR(9000) )
      tree.astTransform = AstTransformNodeCreator('GreaterThan', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 24:
      if left:
        tree.add( left )
      tree.add( self.expect(self.sym.getId()) )
      tree.add( self.__EXPR(9000) )
      tree.astTransform = AstTransformNodeCreator('GreaterThanEq', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 58:
      if left:
        tree.add( left )
      tree.add( self.expect(self.sym.getId()) )
      tree.add( self.__EXPR(7999) )
      tree.astTransform = AstTransformNodeCreator('Equals', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 59:
      if left:
        tree.add( left )
      tree.add( self.expect(self.sym.getId()) )
      tree.add( self.__EXPR(7000) )
      tree.astTransform = AstTransformNodeCreator('BitOR', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 10:
      if left:
        tree.add( left )
      tree.add( self.expect(self.sym.getId()) )
      tree.add( self.__EXPR(6000) )
      tree.astTransform = AstTransformNodeCreator('BitXOR', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 21:
      if left:
        tree.add( left )
      tree.add( self.expect(self.sym.getId()) )
      tree.add( self.__EXPR(11000) )
      tree.astTransform = AstTransformNodeCreator('Sub', {'right': 2, 'left': 0})
      return tree
