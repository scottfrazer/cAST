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
  TERMINAL_PRAGMA = 1
  TERMINAL_OR = 2
  TERMINAL_BITXOREQ = 3
  TERMINAL_DIV = 4
  TERMINAL_AND = 5
  TERMINAL_CSOURCE = 6
  TERMINAL_DEFINE = 7
  TERMINAL_ELIPSIS = 8
  TERMINAL_BITOR = 9
  TERMINAL_IF = 10
  TERMINAL_UNDEF = 11
  TERMINAL_BITNOT = 12
  TERMINAL_BITXOR = 13
  TERMINAL_RSHIFTEQ = 14
  TERMINAL_SEPARATOR = 15
  TERMINAL_ARROW = 16
  TERMINAL_SEMI = 17
  TERMINAL_RBRACE = 18
  TERMINAL_EQ = 19
  TERMINAL_ADDEQ = 20
  TERMINAL_LTEQ = 21
  TERMINAL_LINE = 22
  TERMINAL_MODEQ = 23
  TERMINAL_AMPERSAND = 24
  TERMINAL_GTEQ = 25
  TERMINAL_MULEQ = 26
  TERMINAL_RPAREN = 27
  TERMINAL_LSQUARE = 28
  TERMINAL_NEQ = 29
  TERMINAL_ASSIGN = 30
  TERMINAL_RSQUARE = 31
  TERMINAL_POUNDPOUND = 32
  TERMINAL_LPAREN = 33
  TERMINAL_ADD = 34
  TERMINAL_POUND = 35
  TERMINAL_LT = 36
  TERMINAL_RSHIFT = 37
  TERMINAL_COMMA = 38
  TERMINAL_ERROR = 39
  TERMINAL_DEFINE_FUNCTION = 40
  TERMINAL_EXCLAMATION_POINT = 41
  TERMINAL_DEFINED = 42
  TERMINAL_TILDE = 43
  TERMINAL_BITANDEQ = 44
  TERMINAL_HEADER_GLOBAL = 45
  TERMINAL_SUB = 46
  TERMINAL_DOT = 47
  TERMINAL_MOD = 48
  TERMINAL_HEADER_LOCAL = 49
  TERMINAL_ELSE = 50
  TERMINAL_COLON = 51
  TERMINAL_IFDEF = 52
  TERMINAL_ENDIF = 53
  TERMINAL_MUL = 54
  TERMINAL_QUESTIONMARK = 55
  TERMINAL_IDENTIFIER = 56
  TERMINAL_IFNDEF = 57
  TERMINAL_GT = 58
  TERMINAL_BITAND = 59
  TERMINAL_PP_NUMBER = 60
  TERMINAL_INCLUDE = 61
  TERMINAL_ELIF = 62
  TERMINAL_LSHIFT = 63
  TERMINAL_CHARACTER_CONSTANT = 64
  TERMINAL_DECR = 65
  TERMINAL_STRING_LITERAL = 66
  TERMINAL_SUBEQ = 67
  TERMINAL_LSHIFTEQ = 68
  TERMINAL_INCR = 69
  TERMINAL_LBRACE = 70
  terminal_str = {
    0: 'bitoreq',
    1: 'pragma',
    2: 'or',
    3: 'bitxoreq',
    4: 'div',
    5: 'and',
    6: 'csource',
    7: 'define',
    8: 'elipsis',
    9: 'bitor',
    10: 'if',
    11: 'undef',
    12: 'bitnot',
    13: 'bitxor',
    14: 'rshifteq',
    15: 'separator',
    16: 'arrow',
    17: 'semi',
    18: 'rbrace',
    19: 'eq',
    20: 'addeq',
    21: 'lteq',
    22: 'line',
    23: 'modeq',
    24: 'ampersand',
    25: 'gteq',
    26: 'muleq',
    27: 'rparen',
    28: 'lsquare',
    29: 'neq',
    30: 'assign',
    31: 'rsquare',
    32: 'poundpound',
    33: 'lparen',
    34: 'add',
    35: 'pound',
    36: 'lt',
    37: 'rshift',
    38: 'comma',
    39: 'error',
    40: 'define_function',
    41: 'exclamation_point',
    42: 'defined',
    43: 'tilde',
    44: 'bitandeq',
    45: 'header_global',
    46: 'sub',
    47: 'dot',
    48: 'mod',
    49: 'header_local',
    50: 'else',
    51: 'colon',
    52: 'ifdef',
    53: 'endif',
    54: 'mul',
    55: 'questionmark',
    56: 'identifier',
    57: 'ifndef',
    58: 'gt',
    59: 'bitand',
    60: 'pp_number',
    61: 'include',
    62: 'elif',
    63: 'lshift',
    64: 'character_constant',
    65: 'decr',
    66: 'string_literal',
    67: 'subeq',
    68: 'lshifteq',
    69: 'incr',
    70: 'lbrace',
  }
  nonterminal_str = {
    71: 'elseif_part',
    72: '_gen1',
    73: 'replacement_list',
    74: 'pp_nodes_list',
    75: 'include_line',
    76: '_gen4',
    77: 'define_line',
    78: '_gen2',
    79: '_gen3',
    80: 'pp_directive',
    81: 'punctuator',
    82: 'else_part',
    83: 'pp_tokens',
    84: 'error_line',
    85: '_gen0',
    86: '_expr',
    87: 'undef_line',
    88: 'line_line',
    89: '_gen5',
    90: 'identifier',
    91: '_gen6',
    92: 'include_type',
    93: 'pp_nodes',
    94: 'if_section',
    95: 'control_line',
    96: 'pragma_line',
    97: 'pp_file',
    98: 'if_part',
  }
  str_terminal = {
    'bitoreq': 0,
    'pragma': 1,
    'or': 2,
    'bitxoreq': 3,
    'div': 4,
    'and': 5,
    'csource': 6,
    'define': 7,
    'elipsis': 8,
    'bitor': 9,
    'if': 10,
    'undef': 11,
    'bitnot': 12,
    'bitxor': 13,
    'rshifteq': 14,
    'separator': 15,
    'arrow': 16,
    'semi': 17,
    'rbrace': 18,
    'eq': 19,
    'addeq': 20,
    'lteq': 21,
    'line': 22,
    'modeq': 23,
    'ampersand': 24,
    'gteq': 25,
    'muleq': 26,
    'rparen': 27,
    'lsquare': 28,
    'neq': 29,
    'assign': 30,
    'rsquare': 31,
    'poundpound': 32,
    'lparen': 33,
    'add': 34,
    'pound': 35,
    'lt': 36,
    'rshift': 37,
    'comma': 38,
    'error': 39,
    'define_function': 40,
    'exclamation_point': 41,
    'defined': 42,
    'tilde': 43,
    'bitandeq': 44,
    'header_global': 45,
    'sub': 46,
    'dot': 47,
    'mod': 48,
    'header_local': 49,
    'else': 50,
    'colon': 51,
    'ifdef': 52,
    'endif': 53,
    'mul': 54,
    'questionmark': 55,
    'identifier': 56,
    'ifndef': 57,
    'gt': 58,
    'bitand': 59,
    'pp_number': 60,
    'include': 61,
    'elif': 62,
    'lshift': 63,
    'character_constant': 64,
    'decr': 65,
    'string_literal': 66,
    'subeq': 67,
    'lshifteq': 68,
    'incr': 69,
    'lbrace': 70,
  }
  str_nonterminal = {
    'elseif_part': 71,
    '_gen1': 72,
    'replacement_list': 73,
    'pp_nodes_list': 74,
    'include_line': 75,
    '_gen4': 76,
    'define_line': 77,
    '_gen2': 78,
    '_gen3': 79,
    'pp_directive': 80,
    'punctuator': 81,
    'else_part': 82,
    'pp_tokens': 83,
    'error_line': 84,
    '_gen0': 85,
    '_expr': 86,
    'undef_line': 87,
    'line_line': 88,
    '_gen5': 89,
    'identifier': 90,
    '_gen6': 91,
    'include_type': 92,
    'pp_nodes': 93,
    'if_section': 94,
    'control_line': 95,
    'pragma_line': 96,
    'pp_file': 97,
    'if_part': 98,
  }
  terminal_count = 71
  nonterminal_count = 28
  parse_table = [
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 62, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 27, -1, -1, -1, -1, -1, -1, -1, -1],
  [89, -1, 89, 89, 89, 89, -1, -1, 89, 89, -1, -1, 89, 89, 89, -1, 89, 89, 89, 89, 89, 89, -1, 89, 89, 89, 89, 89, 89, 89, 89, 89, 89, 89, 89, 89, 89, 89, 89, -1, -1, 89, 89, 89, 89, 89, 89, 89, 89, 89, -1, 89, -1, -1, 89, 89, 89, -1, 89, 89, 89, -1, -1, 89, 89, 89, 89, 89, 89, 89, 89],
  [-1, 85, -1, -1, -1, -1, 85, 85, -1, -1, 85, 85, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 85, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 85, 85, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 85, -1, -1, -1, -1, 85, -1, -1, -1, 85, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 40, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [93, -1, 93, 93, 93, 93, -1, -1, 93, 93, -1, -1, 93, 93, 93, -1, 93, 93, 93, 93, 93, 93, -1, 93, 93, 93, 93, 93, 93, 93, 93, 93, 93, 93, 93, 93, 93, 93, 93, -1, -1, 93, 93, 93, 93, 93, 93, 93, 93, 93, -1, 93, -1, -1, 93, 93, 93, -1, 93, 93, 93, -1, -1, 93, 93, 93, 93, 93, 93, 93, 93],
  [-1, -1, -1, -1, -1, -1, -1, 28, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 7, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 83, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 86, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, 45, -1, -1, -1, -1, -1, 45, -1, -1, 72, 45, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 45, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 45, 45, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 72, -1, -1, -1, -1, 72, -1, -1, -1, 45, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [57, -1, 41, 50, 52, 44, -1, -1, 88, 21, -1, -1, 11, 48, 8, -1, 22, 92, 36, 64, 25, 33, -1, 31, 23, 97, 37, 13, 42, 16, 55, 51, 54, 59, 58, 63, 5, 65, 66, -1, -1, 73, 74, 77, 87, -1, 84, 49, 4, -1, -1, 94, -1, -1, 10, 46, -1, -1, 68, 76, -1, -1, -1, 80, -1, 53, -1, 18, 19, 14, 67],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 6, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [101, -1, 101, 101, 101, 101, -1, -1, 101, 101, -1, -1, 101, 101, 101, -1, 101, 101, 101, 101, 101, 101, -1, 101, 101, 101, 101, 101, 101, 101, 101, 101, 101, 101, 101, 101, 101, 101, 101, -1, -1, 101, 101, 101, 101, 1, 101, 101, 101, 90, -1, 101, -1, -1, 101, 101, 39, -1, 101, 101, 9, -1, -1, 101, 34, 101, 71, 101, 101, 101, 101],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 0, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, 15, -1, -1, -1, -1, 15, 15, -1, -1, 15, 15, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 15, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 15, 15, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 15, -1, -1, -1, -1, 15, -1, -1, -1, 15, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 69, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 20, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 24, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 38, -1, -1, -1, 47, -1, -1, -1, -1, -1, -1, 99, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, 30, -1, -1, -1, -1, 61, 30, -1, -1, 30, 30, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 30, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 30, 30, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 30, -1, -1, -1, -1, 30, -1, -1, -1, 30, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 81, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 81, -1, -1, -1, -1, 81, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, 26, -1, -1, -1, -1, -1, 43, -1, -1, -1, 82, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 75, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 56, 43, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 17, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, 60, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, 78, -1, -1, -1, -1, 78, 78, -1, -1, 78, 78, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 78, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 78, 78, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 78, -1, -1, -1, -1, 78, -1, -1, -1, 78, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 35, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 91, -1, -1, -1, -1, 3, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1]
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
  def call(self, nt_str):
    return getattr(self, nt_str)()
  def _ELSEIF_PART(self, depth = 0):
    rule = self.rule(71)
    if depth is not False:
      tracer = DebugTracer("_ELSEIF_PART", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(71, self.getAtomString(71)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 62:
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
    rule = self.rule(72)
    if depth is not False:
      tracer = DebugTracer("__GEN1", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(72, self.getAtomString(72)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() == 15 or self.sym.getId() == 50):
      return tree
    if self.sym != None and (self.sym.getId() == 15 or self.sym.getId() == 50):
      return tree
    if self.sym == None:
      return tree
    if rule == 27:
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
  def _REPLACEMENT_LIST(self, depth = 0):
    rule = self.rule(73)
    if depth is not False:
      tracer = DebugTracer("_REPLACEMENT_LIST", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(73, self.getAtomString(73)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() == 15):
      return tree
    if self.sym == None:
      return tree
    if rule == 89:
      tree.astTransform = AstTransformNodeCreator('ReplacementList', {'tokens': 0})
      subtree = self.__GEN4(depth)
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
    if self.sym != None and (self.sym.getId() == 53 or self.sym.getId() == 62 or self.sym.getId() == 50 or self.sym.getId() == 15):
      return tree
    if self.sym != None and (self.sym.getId() == 53 or self.sym.getId() == 62 or self.sym.getId() == 50 or self.sym.getId() == 15):
      return tree
    if self.sym != None and (self.sym.getId() == 53 or self.sym.getId() == 62 or self.sym.getId() == 50 or self.sym.getId() == 15):
      return tree
    if self.sym != None and (self.sym.getId() == 53 or self.sym.getId() == 62 or self.sym.getId() == 50 or self.sym.getId() == 15):
      return tree
    if self.sym == None:
      return tree
    if rule == 85:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN0(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _INCLUDE_LINE(self, depth = 0):
    rule = self.rule(75)
    if depth is not False:
      tracer = DebugTracer("_INCLUDE_LINE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(75, self.getAtomString(75)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 40:
      tree.astTransform = AstTransformNodeCreator('Include', {'file': 1})
      tree.add( self.expect(self.TERMINAL_INCLUDE, tracer) )
      subtree = self._INCLUDE_TYPE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
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
    if self.sym != None and (self.sym.getId() == 15):
      return tree
    if self.sym == None:
      return tree
    if rule == 93:
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
  def _DEFINE_LINE(self, depth = 0):
    rule = self.rule(77)
    if depth is not False:
      tracer = DebugTracer("_DEFINE_LINE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(77, self.getAtomString(77)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 7:
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
    elif rule == 28:
      tree.astTransform = AstTransformNodeCreator('Define', {'body': 2, 'ident': 1})
      tree.add( self.expect(self.TERMINAL_DEFINE, tracer) )
      tree.add( self.expect(self.TERMINAL_IDENTIFIER, tracer) )
      subtree = self._REPLACEMENT_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN2(self, depth = 0):
    rule = self.rule(78)
    if depth is not False:
      tracer = DebugTracer("__GEN2", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(78, self.getAtomString(78)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() == 27):
      return tree
    if self.sym == None:
      return tree
    elif rule == 83:
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
  def __GEN3(self, depth = 0):
    rule = self.rule(79)
    if depth is not False:
      tracer = DebugTracer("__GEN3", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(79, self.getAtomString(79)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() == 27):
      return tree
    if self.sym == None:
      return tree
    elif rule == 86:
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
  def _PP_DIRECTIVE(self, depth = 0):
    rule = self.rule(80)
    if depth is not False:
      tracer = DebugTracer("_PP_DIRECTIVE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(80, self.getAtomString(80)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 45:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._CONTROL_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 72:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._IF_SECTION(depth)
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
      tree.add( self.expect(self.TERMINAL_MOD, tracer) )
      return tree
    elif rule == 5:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LT, tracer) )
      return tree
    elif rule == 8:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RSHIFTEQ, tracer) )
      return tree
    elif rule == 10:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_MUL, tracer) )
      return tree
    elif rule == 11:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITNOT, tracer) )
      return tree
    elif rule == 13:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RPAREN, tracer) )
      return tree
    elif rule == 14:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_INCR, tracer) )
      return tree
    elif rule == 16:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_NEQ, tracer) )
      return tree
    elif rule == 18:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SUBEQ, tracer) )
      return tree
    elif rule == 19:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LSHIFTEQ, tracer) )
      return tree
    elif rule == 21:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITOR, tracer) )
      return tree
    elif rule == 22:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ARROW, tracer) )
      return tree
    elif rule == 23:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_AMPERSAND, tracer) )
      return tree
    elif rule == 25:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ADDEQ, tracer) )
      return tree
    elif rule == 31:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_MODEQ, tracer) )
      return tree
    elif rule == 33:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LTEQ, tracer) )
      return tree
    elif rule == 36:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RBRACE, tracer) )
      return tree
    elif rule == 37:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_MULEQ, tracer) )
      return tree
    elif rule == 41:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_OR, tracer) )
      return tree
    elif rule == 42:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LSQUARE, tracer) )
      return tree
    elif rule == 44:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_AND, tracer) )
      return tree
    elif rule == 46:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_QUESTIONMARK, tracer) )
      return tree
    elif rule == 48:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITXOR, tracer) )
      return tree
    elif rule == 49:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DOT, tracer) )
      return tree
    elif rule == 50:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITXOREQ, tracer) )
      return tree
    elif rule == 51:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RSQUARE, tracer) )
      return tree
    elif rule == 52:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DIV, tracer) )
      return tree
    elif rule == 53:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DECR, tracer) )
      return tree
    elif rule == 54:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_POUNDPOUND, tracer) )
      return tree
    elif rule == 55:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ASSIGN, tracer) )
      return tree
    elif rule == 57:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITOREQ, tracer) )
      return tree
    elif rule == 58:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ADD, tracer) )
      return tree
    elif rule == 59:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LPAREN, tracer) )
      return tree
    elif rule == 63:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_POUND, tracer) )
      return tree
    elif rule == 64:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_EQ, tracer) )
      return tree
    elif rule == 65:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_RSHIFT, tracer) )
      return tree
    elif rule == 66:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_COMMA, tracer) )
      return tree
    elif rule == 67:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LBRACE, tracer) )
      return tree
    elif rule == 68:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_GT, tracer) )
      return tree
    elif rule == 70:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITXOR, tracer) )
      return tree
    elif rule == 73:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_EXCLAMATION_POINT, tracer) )
      return tree
    elif rule == 74:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_DEFINED, tracer) )
      return tree
    elif rule == 76:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITAND, tracer) )
      return tree
    elif rule == 77:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_TILDE, tracer) )
      return tree
    elif rule == 79:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITOR, tracer) )
      return tree
    elif rule == 80:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_LSHIFT, tracer) )
      return tree
    elif rule == 84:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SUB, tracer) )
      return tree
    elif rule == 87:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_BITANDEQ, tracer) )
      return tree
    elif rule == 88:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_ELIPSIS, tracer) )
      return tree
    elif rule == 92:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_SEMI, tracer) )
      return tree
    elif rule == 94:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_COLON, tracer) )
      return tree
    elif rule == 97:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_GTEQ, tracer) )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _ELSE_PART(self, depth = 0):
    rule = self.rule(82)
    if depth is not False:
      tracer = DebugTracer("_ELSE_PART", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(82, self.getAtomString(82)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() == 53):
      return tree
    if self.sym == None:
      return tree
    elif rule == 6:
      tree.astTransform = AstTransformNodeCreator('Else', {'nodes': 1})
      tree.add( self.expect(self.TERMINAL_ELSE, tracer) )
      subtree = self._PP_NODES_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _PP_TOKENS(self, depth = 0):
    rule = self.rule(83)
    if depth is not False:
      tracer = DebugTracer("_PP_TOKENS", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(83, self.getAtomString(83)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 1:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_HEADER_GLOBAL, tracer) )
      return tree
    elif rule == 9:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_PP_NUMBER, tracer) )
      return tree
    elif rule == 34:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_CHARACTER_CONSTANT, tracer) )
      return tree
    elif rule == 39:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_IDENTIFIER, tracer) )
      return tree
    elif rule == 71:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_STRING_LITERAL, tracer) )
      return tree
    elif rule == 90:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_HEADER_LOCAL, tracer) )
      return tree
    elif rule == 101:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PUNCTUATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _ERROR_LINE(self, depth = 0):
    rule = self.rule(84)
    if depth is not False:
      tracer = DebugTracer("_ERROR_LINE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(84, self.getAtomString(84)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 0:
      tree.astTransform = AstTransformNodeCreator('Error', {'tokens': 1})
      tree.add( self.expect(self.TERMINAL_ERROR, tracer) )
      subtree = self.__GEN4(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN0(self, depth = 0):
    rule = self.rule(85)
    if depth is not False:
      tracer = DebugTracer("__GEN0", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(85, self.getAtomString(85)), tracer )
    tree.list = 'tlist'
    if self.sym != None and (self.sym.getId() == 53 or self.sym.getId() == 15 or self.sym.getId() == 62 or self.sym.getId() == 50):
      return tree
    if self.sym != None and (self.sym.getId() == 53 or self.sym.getId() == 15 or self.sym.getId() == 62 or self.sym.getId() == 50):
      return tree
    if self.sym != None and (self.sym.getId() == 53 or self.sym.getId() == 15 or self.sym.getId() == 62 or self.sym.getId() == 50):
      return tree
    if self.sym != None and (self.sym.getId() == 53 or self.sym.getId() == 15 or self.sym.getId() == 62 or self.sym.getId() == 50):
      return tree
    if self.sym == None:
      return tree
    if rule == 15:
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
    rule = self.rule(87)
    if depth is not False:
      tracer = DebugTracer("_UNDEF_LINE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(87, self.getAtomString(87)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 69:
      tree.astTransform = AstTransformNodeCreator('Undef', {'ident': 1})
      tree.add( self.expect(self.TERMINAL_UNDEF, tracer) )
      tree.add( self.expect(self.TERMINAL_IDENTIFIER, tracer) )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _LINE_LINE(self, depth = 0):
    rule = self.rule(88)
    if depth is not False:
      tracer = DebugTracer("_LINE_LINE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(88, self.getAtomString(88)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 20:
      tree.astTransform = AstTransformNodeCreator('Line', {'tokens': 1})
      tree.add( self.expect(self.TERMINAL_LINE, tracer) )
      subtree = self.__GEN4(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN5(self, depth = 0):
    rule = self.rule(89)
    if depth is not False:
      tracer = DebugTracer("__GEN5", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(89, self.getAtomString(89)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _IDENTIFIER(self, depth = 0):
    rule = self.rule(90)
    if depth is not False:
      tracer = DebugTracer("_IDENTIFIER", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(90, self.getAtomString(90)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 24:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_IDENTIFIER, tracer) )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN6(self, depth = 0):
    rule = self.rule(91)
    if depth is not False:
      tracer = DebugTracer("__GEN6", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(91, self.getAtomString(91)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _INCLUDE_TYPE(self, depth = 0):
    rule = self.rule(92)
    if depth is not False:
      tracer = DebugTracer("_INCLUDE_TYPE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(92, self.getAtomString(92)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 38:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_HEADER_GLOBAL, tracer) )
      return tree
    elif rule == 47:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_HEADER_LOCAL, tracer) )
      return tree
    elif rule == 99:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_IDENTIFIER, tracer) )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PP_NODES(self, depth = 0):
    rule = self.rule(93)
    if depth is not False:
      tracer = DebugTracer("_PP_NODES", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(93, self.getAtomString(93)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 30:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PP_DIRECTIVE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 61:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(self.TERMINAL_CSOURCE, tracer) )
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
    if rule == 81:
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
  def _CONTROL_LINE(self, depth = 0):
    rule = self.rule(95)
    if depth is not False:
      tracer = DebugTracer("_CONTROL_LINE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(95, self.getAtomString(95)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 17:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._INCLUDE_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 26:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PRAGMA_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 43:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DEFINE_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 56:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ERROR_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 75:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._LINE_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 82:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._UNDEF_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PRAGMA_LINE(self, depth = 0):
    rule = self.rule(96)
    if depth is not False:
      tracer = DebugTracer("_PRAGMA_LINE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(96, self.getAtomString(96)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 60:
      tree.astTransform = AstTransformNodeCreator('Pragma', {'tokens': 1})
      tree.add( self.expect(self.TERMINAL_PRAGMA, tracer) )
      subtree = self.__GEN4(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PP_FILE(self, depth = 0):
    rule = self.rule(97)
    if depth is not False:
      tracer = DebugTracer("_PP_FILE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(97, self.getAtomString(97)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 78:
      tree.astTransform = AstTransformNodeCreator('PPFile', {'nodes': 0})
      subtree = self._PP_NODES_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _IF_PART(self, depth = 0):
    rule = self.rule(98)
    if depth is not False:
      tracer = DebugTracer("_IF_PART", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(98, self.getAtomString(98)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 3:
      tree.astTransform = AstTransformNodeCreator('IfNDef', {'nodes': 2, 'ident': 1})
      tree.add( self.expect(self.TERMINAL_IFNDEF, tracer) )
      tree.add( self.expect(self.TERMINAL_IDENTIFIER, tracer) )
      subtree = self._PP_NODES_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 35:
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
    elif rule == 91:
      tree.astTransform = AstTransformNodeCreator('IfDef', {'nodes': 2, 'ident': 1})
      tree.add( self.expect(self.TERMINAL_IFDEF, tracer) )
      tree.add( self.expect(self.TERMINAL_IDENTIFIER, tracer) )
      subtree = self._PP_NODES_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  bp0 = {
    33: 14000,
    2: 3000,
    34: 11000,
    4: 12000,
    5: 4000,
    38: 1000,
    63: 10000,
    55: 2000,
    13: 6000,
    46: 11000,
    48: 12000,
    19: 8000,
    21: 9000,
    54: 12000,
    9: 7000,
    25: 9000,
    58: 9000,
    59: 5000,
    36: 9000,
    29: 8000,
    37: 10000,
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
      return tree
    if self.sym.getId() == 33:
      tree.add( self.expect( 33, tracer ) ) #here?
      tree.astTransform = AstTransformSubstitution(1)
      tree.add(self.__EXPR())
      tree.astTransform = AstTransformSubstitution(1)
      tree.add( self.expect( 27, tracer ) ) #here?
      tree.astTransform = AstTransformSubstitution(1)
      return tree
    if self.sym.getId() == 66:
      return self.expect( 66, tracer )
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
    if self.sym.getId() == 12:
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(13000) )
      tree.astTransform = AstTransformNodeCreator('BitNOT', {'expr': 1})
      return tree
    if self.sym.getId() == 86:
      return tree
    if self.sym.getId() == 56:
      return self.expect( 56, tracer )
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      return tree
    if self.sym.getId() == 60:
      return self.expect( 60, tracer )
      return tree
  def led0(self, left, tracer):
    tree = ParseTree( NonTerminal(self.str_nonterminal['_expr'], '_expr') )
    if self.sym.getId() == 33:
      if left:
        tree.add( left )
      ls = AstList()
      tree.add( self.expect( 33, tracer ) )
      if self.sym.getId() != 27:
        while 1:
          ls.append( self.__EXPR() )
          if self.sym.getId() != 38:
            break
          self.expect( 38, tracer )
      tree.add( ls )
      tree.add( self.expect(27, tracer ) )
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      return tree
    if self.sym.getId() == 34:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(11000) )
      tree.astTransform = AstTransformNodeCreator('Add', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 36:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(9000) )
      tree.astTransform = AstTransformNodeCreator('LessThan', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 37:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(10000) )
      tree.astTransform = AstTransformNodeCreator('RightShift', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 38:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(1000) )
      tree.astTransform = AstTransformNodeCreator('Comma', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 9:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(7000) )
      tree.astTransform = AstTransformNodeCreator('BitOR', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 2:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(3000) )
      tree.astTransform = AstTransformNodeCreator('Or', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 46:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(11000) )
      tree.astTransform = AstTransformNodeCreator('Sub', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 13:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(6000) )
      tree.astTransform = AstTransformNodeCreator('BitXOR', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 48:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(12000) )
      tree.astTransform = AstTransformNodeCreator('Mod', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 19:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(7999) )
      tree.astTransform = AstTransformNodeCreator('Equals', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 21:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(9000) )
      tree.astTransform = AstTransformNodeCreator('LessThanEq', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 54:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(12000) )
      tree.astTransform = AstTransformNodeCreator('Mul', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 55:
      if left:
        tree.add( left )
      tree.add( self.expect( 55, tracer ) )
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      tree.add(self.__EXPR())
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      tree.add( self.expect( 51, tracer ) )
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      tree.add(self.__EXPR())
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
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
    if self.sym.getId() == 59:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(5000) )
      tree.astTransform = AstTransformNodeCreator('BitAND', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 5:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(4000) )
      tree.astTransform = AstTransformNodeCreator('And', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 29:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(7999) )
      tree.astTransform = AstTransformNodeCreator('NotEquals', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 4:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(12000) )
      tree.astTransform = AstTransformNodeCreator('Div', {'right': 2, 'left': 0})
      return tree
    if self.sym.getId() == 63:
      if left:
        tree.add( left )
      tree.add( self.expect( self.sym.getId(), tracer ) )
      tree.add( self.__EXPR(10000) )
      tree.astTransform = AstTransformNodeCreator('LeftShift', {'right': 2, 'left': 0})
      return tree
