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
      'pp_file': self._PP_FILE,
    }
  TERMINAL_DECR = 0
  TERMINAL_BITOREQ = 1
  TERMINAL_EQ = 2
  TERMINAL_WARNING = 3
  TERMINAL_BITXOREQ = 4
  TERMINAL_ELIF = 5
  TERMINAL_ASSIGN = 6
  TERMINAL_LTEQ = 7
  TERMINAL_LPAREN = 8
  TERMINAL_AMPERSAND = 9
  TERMINAL_UNDEF = 10
  TERMINAL_IF = 11
  TERMINAL_DEFINE = 12
  TERMINAL_PP_NUMBER = 13
  TERMINAL_LINE = 14
  TERMINAL_TILDE = 15
  TERMINAL_LT = 16
  TERMINAL_OR = 17
  TERMINAL_NEQ = 18
  TERMINAL_SUB = 19
  TERMINAL_GT = 20
  TERMINAL_IFNDEF = 21
  TERMINAL_SUBEQ = 22
  TERMINAL_DEFINE_FUNCTION = 23
  TERMINAL_IFDEF = 24
  TERMINAL_LSHIFT = 25
  TERMINAL_MUL = 26
  TERMINAL_ADDEQ = 27
  TERMINAL_ELSE = 28
  TERMINAL_CSOURCE = 29
  TERMINAL_MODEQ = 30
  TERMINAL_CHARACTER_CONSTANT = 31
  TERMINAL_MOD = 32
  TERMINAL_ENDIF = 33
  TERMINAL_BITOR = 34
  TERMINAL_MULEQ = 35
  TERMINAL_ELIPSIS = 36
  TERMINAL_SEPARATOR = 37
  TERMINAL_IDENTIFIER = 38
  TERMINAL_SEMI = 39
  TERMINAL_RSHIFTEQ = 40
  TERMINAL_INCR = 41
  TERMINAL_COLON = 42
  TERMINAL_POUNDPOUND = 43
  TERMINAL_ARROW = 44
  TERMINAL_DOT = 45
  TERMINAL_POUND = 46
  TERMINAL_STRING_LITERAL = 47
  TERMINAL_QUESTIONMARK = 48
  TERMINAL_COMMA = 49
  TERMINAL_DIV = 50
  TERMINAL_LBRACE = 51
  TERMINAL_AND = 52
  TERMINAL_BITAND = 53
  TERMINAL_RBRACE = 54
  TERMINAL_DEFINED = 55
  TERMINAL_BITNOT = 56
  TERMINAL_EXCLAMATION_POINT = 57
  TERMINAL_BITANDEQ = 58
  TERMINAL_LSQUARE = 59
  TERMINAL_BITXOR = 60
  TERMINAL_RSHIFT = 61
  TERMINAL_HEADER_GLOBAL = 62
  TERMINAL_PRAGMA = 63
  TERMINAL_RSQUARE = 64
  TERMINAL_INCLUDE = 65
  TERMINAL_LSHIFTEQ = 66
  TERMINAL_GTEQ = 67
  TERMINAL_HEADER_LOCAL = 68
  TERMINAL_RPAREN = 69
  TERMINAL_ERROR = 70
  TERMINAL_ADD = 71
  terminal_str = {
    0: 'decr',
    1: 'bitoreq',
    2: 'eq',
    3: 'warning',
    4: 'bitxoreq',
    5: 'elif',
    6: 'assign',
    7: 'lteq',
    8: 'lparen',
    9: 'ampersand',
    10: 'undef',
    11: 'if',
    12: 'define',
    13: 'pp_number',
    14: 'line',
    15: 'tilde',
    16: 'lt',
    17: 'or',
    18: 'neq',
    19: 'sub',
    20: 'gt',
    21: 'ifndef',
    22: 'subeq',
    23: 'define_function',
    24: 'ifdef',
    25: 'lshift',
    26: 'mul',
    27: 'addeq',
    28: 'else',
    29: 'csource',
    30: 'modeq',
    31: 'character_constant',
    32: 'mod',
    33: 'endif',
    34: 'bitor',
    35: 'muleq',
    36: 'elipsis',
    37: 'separator',
    38: 'identifier',
    39: 'semi',
    40: 'rshifteq',
    41: 'incr',
    42: 'colon',
    43: 'poundpound',
    44: 'arrow',
    45: 'dot',
    46: 'pound',
    47: 'string_literal',
    48: 'questionmark',
    49: 'comma',
    50: 'div',
    51: 'lbrace',
    52: 'and',
    53: 'bitand',
    54: 'rbrace',
    55: 'defined',
    56: 'bitnot',
    57: 'exclamation_point',
    58: 'bitandeq',
    59: 'lsquare',
    60: 'bitxor',
    61: 'rshift',
    62: 'header_global',
    63: 'pragma',
    64: 'rsquare',
    65: 'include',
    66: 'lshifteq',
    67: 'gteq',
    68: 'header_local',
    69: 'rparen',
    70: 'error',
    71: 'add',
  }
  nonterminal_str = {
    72: 'pp_directive',
    73: 'include_line',
    74: 'punctuator',
    75: 'else_part',
    76: 'define_line',
    77: 'identifier',
    78: '_gen0',
    79: 'pragma_line',
    80: '_expr',
    81: 'pp_nodes',
    82: 'replacement_list',
    83: '_gen4',
    84: '_gen3',
    85: 'error_line',
    86: 'warning_line',
    87: 'pp_nodes_list',
    88: 'define_func_param',
    89: '_gen5',
    90: 'if_section',
    91: 'pp_tokens',
    92: '_gen2',
    93: 'elipsis_opt',
    94: 'control_line',
    95: '_gen6',
    96: 'line_line',
    97: 'pp_file',
    98: 'if_part',
    99: 'elseif_part',
    100: '_gen1',
    101: 'include_type',
    102: 'undef_line',
  }
  str_terminal = {
    'decr': 0,
    'bitoreq': 1,
    'eq': 2,
    'warning': 3,
    'bitxoreq': 4,
    'elif': 5,
    'assign': 6,
    'lteq': 7,
    'lparen': 8,
    'ampersand': 9,
    'undef': 10,
    'if': 11,
    'define': 12,
    'pp_number': 13,
    'line': 14,
    'tilde': 15,
    'lt': 16,
    'or': 17,
    'neq': 18,
    'sub': 19,
    'gt': 20,
    'ifndef': 21,
    'subeq': 22,
    'define_function': 23,
    'ifdef': 24,
    'lshift': 25,
    'mul': 26,
    'addeq': 27,
    'else': 28,
    'csource': 29,
    'modeq': 30,
    'character_constant': 31,
    'mod': 32,
    'endif': 33,
    'bitor': 34,
    'muleq': 35,
    'elipsis': 36,
    'separator': 37,
    'identifier': 38,
    'semi': 39,
    'rshifteq': 40,
    'incr': 41,
    'colon': 42,
    'poundpound': 43,
    'arrow': 44,
    'dot': 45,
    'pound': 46,
    'string_literal': 47,
    'questionmark': 48,
    'comma': 49,
    'div': 50,
    'lbrace': 51,
    'and': 52,
    'bitand': 53,
    'rbrace': 54,
    'defined': 55,
    'bitnot': 56,
    'exclamation_point': 57,
    'bitandeq': 58,
    'lsquare': 59,
    'bitxor': 60,
    'rshift': 61,
    'header_global': 62,
    'pragma': 63,
    'rsquare': 64,
    'include': 65,
    'lshifteq': 66,
    'gteq': 67,
    'header_local': 68,
    'rparen': 69,
    'error': 70,
    'add': 71,
  }
  str_nonterminal = {
    'pp_directive': 72,
    'include_line': 73,
    'punctuator': 74,
    'else_part': 75,
    'define_line': 76,
    'identifier': 77,
    '_gen0': 78,
    'pragma_line': 79,
    '_expr': 80,
    'pp_nodes': 81,
    'replacement_list': 82,
    '_gen4': 83,
    '_gen3': 84,
    'error_line': 85,
    'warning_line': 86,
    'pp_nodes_list': 87,
    'define_func_param': 88,
    '_gen5': 89,
    'if_section': 90,
    'pp_tokens': 91,
    '_gen2': 92,
    'elipsis_opt': 93,
    'control_line': 94,
    '_gen6': 95,
    'line_line': 96,
    'pp_file': 97,
    'if_part': 98,
    'elseif_part': 99,
    '_gen1': 100,
    'include_type': 101,
    'undef_line': 102,
  }
  terminal_count = 72
  nonterminal_count = 31
  parse_table = [
    [-1, -1, -1, 0, -1, -1, -1, -1, -1, -1, 0, 22, 0, -1, 0, -1, -1, -1, -1, -1, -1, 22, -1, 0, 22, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 0, -1, 0, -1, -1, -1, -1, 0, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 59, -1, -1, -1, -1, -1, -1],
  [105, 28, 42, -1, 80, -1, 92, 27, 26, 77, -1, -1, -1, -1, -1, 81, 14, 11, 32, 87, 4, -1, 46, -1, -1, 107, 40, 98, -1, -1, 97, -1, 17, -1, 8, 58, 84, -1, -1, 18, 56, 86, 54, 30, 10, 38, 68, -1, 89, 60, 71, 7, 48, 64, 101, 52, 102, 74, 29, 2, 24, 78, -1, -1, 50, -1, 12, 63, -1, 73, -1, 75],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 88, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 20, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 76, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 3, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, 93, -1, -1, -1, -1, -1, -1, 93, 93, 93, -1, 93, -1, -1, -1, -1, -1, -1, 93, -1, 93, 93, -1, -1, -1, -1, 93, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 93, -1, 93, -1, -1, -1, -1, 93, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 21, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, 23, -1, -1, -1, -1, -1, -1, 23, 23, 23, -1, 23, -1, -1, -1, -1, -1, -1, 23, -1, 23, 23, -1, -1, -1, -1, 57, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 23, -1, 23, -1, -1, -1, -1, 23, -1],
  [79, 79, 79, -1, 79, -1, 79, 79, 79, 79, -1, -1, -1, 79, -1, 79, 79, 79, 79, 79, 79, -1, 79, -1, -1, 79, 79, 79, -1, -1, 79, 79, 79, -1, 79, 79, 79, -1, 79, 79, 79, 79, 79, 79, 79, 79, 79, 79, 79, 79, 79, 79, 79, 79, 79, 79, 79, 79, 79, 79, 79, 79, 79, -1, 79, -1, 79, 79, 79, 79, -1, 79],
  [65, 65, 65, -1, 65, -1, 65, 65, 65, 65, -1, -1, -1, 65, -1, 65, 65, 65, 65, 65, 65, -1, 65, -1, -1, 65, 65, 65, -1, -1, 65, 65, 65, -1, 65, 65, 65, -1, 65, 65, 65, 65, 65, 65, 65, 65, 65, 65, 65, 65, 65, 65, 65, 65, 65, 65, 65, 65, 65, 65, 65, 65, 65, -1, 65, -1, 65, 65, 65, 65, -1, 65],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 44, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 6, -1],
  [-1, -1, -1, 41, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, 25, -1, -1, -1, -1, -1, -1, 25, 25, 25, -1, 25, -1, -1, -1, -1, -1, -1, 25, -1, 25, 25, -1, -1, -1, -1, 25, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 25, -1, 25, -1, -1, -1, -1, 25, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 100, -1, 90, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 19, -1, -1, -1, -1, -1, -1, -1, -1, -1, 19, -1, -1, 19, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [45, 45, 45, -1, 45, -1, 45, 45, 45, 45, -1, -1, -1, 49, -1, 45, 45, 45, 45, 45, 45, -1, 45, -1, -1, 45, 45, 45, -1, -1, 45, 43, 45, -1, 45, 45, 45, -1, 67, 45, 45, 45, 45, 45, 45, 45, 45, 13, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 15, -1, 45, -1, 45, 45, 106, 45, -1, 45],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 35, -1, 35, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 103, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, 62, -1, -1, -1, -1, -1, -1, 61, -1, 9, -1, 1, -1, -1, -1, -1, -1, -1, -1, -1, 9, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 95, -1, 96, -1, -1, -1, -1, 53, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 34, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, 16, -1, -1, -1, -1, -1, -1, 16, 16, 16, -1, 16, -1, -1, -1, -1, -1, -1, 16, -1, 16, 16, -1, -1, -1, -1, 16, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 16, -1, 16, -1, -1, -1, -1, 16, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 5, -1, -1, -1, -1, -1, -1, -1, -1, -1, 69, -1, -1, 39, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, 85, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, 31, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 72, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 37, -1, -1, -1, -1, -1, 66, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 104, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1]
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
  def _PP_DIRECTIVE(self, depth = 0):
    rule = self.rule(72)
    if depth is not False:
      tracer = DebugTracer("_PP_DIRECTIVE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(72, self.getAtomString(72)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 0:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._CONTROL_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 22:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._IF_SECTION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _INCLUDE_LINE(self, depth = 0):
    rule = self.rule(73)
    if depth is not False:
      tracer = DebugTracer("_INCLUDE_LINE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(73, self.getAtomString(73)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 59:
      tree.astTransform = AstTransformNodeCreator('Include', {'file': 1})
      tree.add( self.expect(65, tracer) ) # include
      subtree = self._INCLUDE_TYPE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PUNCTUATOR(self, depth = 0):
    rule = self.rule(74)
    if depth is not False:
      tracer = DebugTracer("_PUNCTUATOR", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(74, self.getAtomString(74)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 2:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(59, tracer) ) # lsquare
      return tree
    elif rule == 4:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(20, tracer) ) # gt
      return tree
    elif rule == 7:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(51, tracer) ) # lbrace
      return tree
    elif rule == 8:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(34, tracer) ) # bitor
      return tree
    elif rule == 10:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(44, tracer) ) # arrow
      return tree
    elif rule == 11:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(17, tracer) ) # or
      return tree
    elif rule == 12:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(66, tracer) ) # lshifteq
      return tree
    elif rule == 14:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(16, tracer) ) # lt
      return tree
    elif rule == 17:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(32, tracer) ) # mod
      return tree
    elif rule == 18:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(39, tracer) ) # semi
      return tree
    elif rule == 24:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(60, tracer) ) # bitxor
      return tree
    elif rule == 26:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(8, tracer) ) # lparen
      return tree
    elif rule == 27:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(7, tracer) ) # lteq
      return tree
    elif rule == 28:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(1, tracer) ) # bitoreq
      return tree
    elif rule == 29:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(58, tracer) ) # bitandeq
      return tree
    elif rule == 30:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(43, tracer) ) # poundpound
      return tree
    elif rule == 32:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(18, tracer) ) # neq
      return tree
    elif rule == 38:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(45, tracer) ) # dot
      return tree
    elif rule == 40:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(26, tracer) ) # mul
      return tree
    elif rule == 42:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(2, tracer) ) # eq
      return tree
    elif rule == 46:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(22, tracer) ) # subeq
      return tree
    elif rule == 48:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(52, tracer) ) # and
      return tree
    elif rule == 50:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(64, tracer) ) # rsquare
      return tree
    elif rule == 52:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(55, tracer) ) # defined
      return tree
    elif rule == 54:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(42, tracer) ) # colon
      return tree
    elif rule == 56:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(40, tracer) ) # rshifteq
      return tree
    elif rule == 58:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(35, tracer) ) # muleq
      return tree
    elif rule == 60:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(49, tracer) ) # comma
      return tree
    elif rule == 63:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(67, tracer) ) # gteq
      return tree
    elif rule == 64:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(53, tracer) ) # bitand
      return tree
    elif rule == 68:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(46, tracer) ) # pound
      return tree
    elif rule == 71:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(50, tracer) ) # div
      return tree
    elif rule == 73:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(69, tracer) ) # rparen
      return tree
    elif rule == 74:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(57, tracer) ) # exclamation_point
      return tree
    elif rule == 75:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(71, tracer) ) # add
      return tree
    elif rule == 77:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(9, tracer) ) # ampersand
      return tree
    elif rule == 78:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(61, tracer) ) # rshift
      return tree
    elif rule == 80:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(4, tracer) ) # bitxoreq
      return tree
    elif rule == 81:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(15, tracer) ) # tilde
      return tree
    elif rule == 84:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(36, tracer) ) # elipsis
      return tree
    elif rule == 86:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(41, tracer) ) # incr
      return tree
    elif rule == 87:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(19, tracer) ) # sub
      return tree
    elif rule == 89:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(48, tracer) ) # questionmark
      return tree
    elif rule == 92:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(6, tracer) ) # assign
      return tree
    elif rule == 94:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(34, tracer) ) # bitor
      return tree
    elif rule == 97:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(30, tracer) ) # modeq
      return tree
    elif rule == 98:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(27, tracer) ) # addeq
      return tree
    elif rule == 99:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(60, tracer) ) # bitxor
      return tree
    elif rule == 101:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(54, tracer) ) # rbrace
      return tree
    elif rule == 102:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(56, tracer) ) # bitnot
      return tree
    elif rule == 105:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(0, tracer) ) # decr
      return tree
    elif rule == 107:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(25, tracer) ) # lshift
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _ELSE_PART(self, depth = 0):
    rule = self.rule(75)
    if depth is not False:
      tracer = DebugTracer("_ELSE_PART", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(75, self.getAtomString(75)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() == 33):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 88:
      tree.astTransform = AstTransformNodeCreator('Else', {'nodes': 1})
      tree.add( self.expect(28, tracer) ) # else
      subtree = self._PP_NODES_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _DEFINE_LINE(self, depth = 0):
    rule = self.rule(76)
    if depth is not False:
      tracer = DebugTracer("_DEFINE_LINE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(76, self.getAtomString(76)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 20:
      tree.astTransform = AstTransformNodeCreator('Define', {'body': 2, 'ident': 1})
      tree.add( self.expect(12, tracer) ) # define
      tree.add( self.expect(38, tracer) ) # identifier
      subtree = self._REPLACEMENT_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 76:
      tree.astTransform = AstTransformNodeCreator('DefineFunction', {'body': 5, 'ident': 1, 'params': 3})
      tree.add( self.expect(23, tracer) ) # define_function
      tree.add( self.expect(38, tracer) ) # identifier
      tree.add( self.expect(8, tracer) ) # lparen
      subtree = self.__GEN2(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(69, tracer) ) # rparen
      subtree = self._REPLACEMENT_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _IDENTIFIER(self, depth = 0):
    rule = self.rule(77)
    if depth is not False:
      tracer = DebugTracer("_IDENTIFIER", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(77, self.getAtomString(77)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 3:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(38, tracer) ) # identifier
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN0(self, depth = 0):
    rule = self.rule(78)
    if depth is not False:
      tracer = DebugTracer("__GEN0", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(78, self.getAtomString(78)), tracer )
    tree.list = 'tlist'
    if self.sym != None and (self.sym.getId() == 28 or self.sym.getId() == 33 or self.sym.getId() == 37 or self.sym.getId() == 5):
      return tree
    if self.sym != None and (self.sym.getId() == 28 or self.sym.getId() == 33 or self.sym.getId() == 37 or self.sym.getId() == 5):
      return tree
    if self.sym != None and (self.sym.getId() == 28 or self.sym.getId() == 33 or self.sym.getId() == 37 or self.sym.getId() == 5):
      return tree
    if self.sym != None and (self.sym.getId() == 28 or self.sym.getId() == 33 or self.sym.getId() == 37 or self.sym.getId() == 5):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 93:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PP_NODES(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(37, tracer) ) # separator
      subtree = self.__GEN0(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _PRAGMA_LINE(self, depth = 0):
    rule = self.rule(79)
    if depth is not False:
      tracer = DebugTracer("_PRAGMA_LINE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(79, self.getAtomString(79)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 21:
      tree.astTransform = AstTransformNodeCreator('Pragma', {'tokens': 1})
      tree.add( self.expect(63, tracer) ) # pragma
      subtree = self.__GEN4(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PP_NODES(self, depth = 0):
    rule = self.rule(81)
    if depth is not False:
      tracer = DebugTracer("_PP_NODES", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(81, self.getAtomString(81)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 23:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PP_DIRECTIVE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 57:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(29, tracer) ) # csource
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _REPLACEMENT_LIST(self, depth = 0):
    rule = self.rule(82)
    if depth is not False:
      tracer = DebugTracer("_REPLACEMENT_LIST", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(82, self.getAtomString(82)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() == 37):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 79:
      tree.astTransform = AstTransformNodeCreator('ReplacementList', {'tokens': 0})
      subtree = self.__GEN4(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN4(self, depth = 0):
    rule = self.rule(83)
    if depth is not False:
      tracer = DebugTracer("__GEN4", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(83, self.getAtomString(83)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() == 37):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 65:
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
    rule = self.rule(84)
    if depth is not False:
      tracer = DebugTracer("__GEN3", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(84, self.getAtomString(84)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() == 69):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 44:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(49, tracer) ) # comma
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
  def _ERROR_LINE(self, depth = 0):
    rule = self.rule(85)
    if depth is not False:
      tracer = DebugTracer("_ERROR_LINE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(85, self.getAtomString(85)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 6:
      tree.astTransform = AstTransformNodeCreator('Error', {'tokens': 1})
      tree.add( self.expect(70, tracer) ) # error
      subtree = self.__GEN4(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _WARNING_LINE(self, depth = 0):
    rule = self.rule(86)
    if depth is not False:
      tracer = DebugTracer("_WARNING_LINE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(86, self.getAtomString(86)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 41:
      tree.astTransform = AstTransformNodeCreator('Warning', {'tokens': 1})
      tree.add( self.expect(3, tracer) ) # warning
      subtree = self.__GEN4(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PP_NODES_LIST(self, depth = 0):
    rule = self.rule(87)
    if depth is not False:
      tracer = DebugTracer("_PP_NODES_LIST", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(87, self.getAtomString(87)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() == 37 or self.sym.getId() == 28 or self.sym.getId() == 33 or self.sym.getId() == 5):
      return tree
    if self.sym != None and (self.sym.getId() == 37 or self.sym.getId() == 28 or self.sym.getId() == 33 or self.sym.getId() == 5):
      return tree
    if self.sym != None and (self.sym.getId() == 37 or self.sym.getId() == 28 or self.sym.getId() == 33 or self.sym.getId() == 5):
      return tree
    if self.sym != None and (self.sym.getId() == 37 or self.sym.getId() == 28 or self.sym.getId() == 33 or self.sym.getId() == 5):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 25:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN0(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _DEFINE_FUNC_PARAM(self, depth = 0):
    rule = self.rule(88)
    if depth is not False:
      tracer = DebugTracer("_DEFINE_FUNC_PARAM", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(88, self.getAtomString(88)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 90:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(38, tracer) ) # identifier
      return tree
    elif rule == 100:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(36, tracer) ) # elipsis
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
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _IF_SECTION(self, depth = 0):
    rule = self.rule(90)
    if depth is not False:
      tracer = DebugTracer("_IF_SECTION", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(90, self.getAtomString(90)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 19:
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
      tree.add( self.expect(33, tracer) ) # endif
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PP_TOKENS(self, depth = 0):
    rule = self.rule(91)
    if depth is not False:
      tracer = DebugTracer("_PP_TOKENS", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(91, self.getAtomString(91)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 13:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(47, tracer) ) # string_literal
      return tree
    elif rule == 15:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(62, tracer) ) # header_global
      return tree
    elif rule == 43:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(31, tracer) ) # character_constant
      return tree
    elif rule == 45:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PUNCTUATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 49:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(13, tracer) ) # pp_number
      return tree
    elif rule == 67:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(38, tracer) ) # identifier
      return tree
    elif rule == 106:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(68, tracer) ) # header_local
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN2(self, depth = 0):
    rule = self.rule(92)
    if depth is not False:
      tracer = DebugTracer("__GEN2", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(92, self.getAtomString(92)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() == 69):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 35:
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
  def _ELIPSIS_OPT(self, depth = 0):
    rule = self.rule(93)
    if depth is not False:
      tracer = DebugTracer("_ELIPSIS_OPT", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(93, self.getAtomString(93)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 103:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(49, tracer) ) # comma
      tree.add( self.expect(36, tracer) ) # elipsis
      return tree
    return tree
  def _CONTROL_LINE(self, depth = 0):
    rule = self.rule(94)
    if depth is not False:
      tracer = DebugTracer("_CONTROL_LINE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(94, self.getAtomString(94)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 1:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._LINE_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 9:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DEFINE_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 53:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ERROR_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 61:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._UNDEF_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 62:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._WARNING_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 95:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PRAGMA_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 96:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._INCLUDE_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN6(self, depth = 0):
    rule = self.rule(95)
    if depth is not False:
      tracer = DebugTracer("__GEN6", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(95, self.getAtomString(95)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _LINE_LINE(self, depth = 0):
    rule = self.rule(96)
    if depth is not False:
      tracer = DebugTracer("_LINE_LINE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(96, self.getAtomString(96)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 34:
      tree.astTransform = AstTransformNodeCreator('Line', {'tokens': 1})
      tree.add( self.expect(14, tracer) ) # line
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
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 16:
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
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 5:
      tree.astTransform = AstTransformNodeCreator('If', {'expr': 1, 'nodes': 2})
      tree.add( self.expect(11, tracer) ) # if
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._PP_NODES_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 39:
      tree.astTransform = AstTransformNodeCreator('IfDef', {'nodes': 2, 'ident': 1})
      tree.add( self.expect(24, tracer) ) # ifdef
      tree.add( self.expect(38, tracer) ) # identifier
      subtree = self._PP_NODES_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 69:
      tree.astTransform = AstTransformNodeCreator('IfNDef', {'nodes': 2, 'ident': 1})
      tree.add( self.expect(21, tracer) ) # ifndef
      tree.add( self.expect(38, tracer) ) # identifier
      subtree = self._PP_NODES_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _ELSEIF_PART(self, depth = 0):
    rule = self.rule(99)
    if depth is not False:
      tracer = DebugTracer("_ELSEIF_PART", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(99, self.getAtomString(99)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 85:
      tree.astTransform = AstTransformNodeCreator('ElseIf', {'expr': 1, 'nodes': 2})
      tree.add( self.expect(5, tracer) ) # elif
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
    rule = self.rule(100)
    if depth is not False:
      tracer = DebugTracer("__GEN1", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(100, self.getAtomString(100)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() == 28 or self.sym.getId() == 37):
      return tree
    if self.sym != None and (self.sym.getId() == 28 or self.sym.getId() == 37):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 31:
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
  def _INCLUDE_TYPE(self, depth = 0):
    rule = self.rule(101)
    if depth is not False:
      tracer = DebugTracer("_INCLUDE_TYPE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(101, self.getAtomString(101)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 37:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(62, tracer) ) # header_global
      return tree
    elif rule == 66:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(68, tracer) ) # header_local
      return tree
    elif rule == 72:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(38, tracer) ) # identifier
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _UNDEF_LINE(self, depth = 0):
    rule = self.rule(102)
    if depth is not False:
      tracer = DebugTracer("_UNDEF_LINE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(102, self.getAtomString(102)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 104:
      tree.astTransform = AstTransformNodeCreator('Undef', {'ident': 1})
      tree.add( self.expect(10, tracer) ) # undef
      tree.add( self.expect(38, tracer) ) # identifier
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  infixBp0 = {
    32: 12000,
    16: 9000,
    34: 7000,
    67: 9000,
    49: 1000,
    7: 9000,
    8: 14000,
    18: 8000,
    2: 8000,
    48: 2000,
    17: 3000,
    50: 12000,
    19: 11000,
    52: 4000,
    53: 5000,
    71: 11000,
    25: 10000,
    26: 12000,
    60: 6000,
    61: 10000,
    20: 9000,
  }
  prefixBp0 = {
    19: 13000,
    53: 13000,
    55: 13000,
    56: 13000,
    57: 13000,
    26: 13000,
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
    tree = ParseTree( NonTerminal(80, '_expr') )
    if self.sym.getId() == 31: # 'character_constant'
      tree.astTransform = AstTransformSubstitution(0)
      return self.expect( 31, tracer )
    elif self.sym.getId() == 13: # 'pp_number'
      tree.astTransform = AstTransformSubstitution(0)
      return self.expect( 13, tracer )
    elif self.sym.getId() == 8: # 'lparen'
      tree.astTransform = AstTransformSubstitution(1)
      tree.add( self.expect(8, tracer) )
      tree.add( self.__EXPR() )
      tree.add( self.expect(69, tracer) )
    elif self.sym.getId() == 55: # 'defined'
      tree.astTransform = AstTransformNodeCreator('IsDefined', {'expr': 1})
      tree.add( self.expect(55, tracer) )
      tree.add( self.__EXPR() )
    elif self.sym.getId() == 47: # 'string_literal'
      tree.astTransform = AstTransformSubstitution(0)
      return self.expect( 47, tracer )
    elif self.sym.getId() == 56: # 'bitnot'
      tree.astTransform = AstTransformNodeCreator('BitNOT', {'expr': 1})
      tree.add( self.expect(56, tracer) )
      tree.add( self.__EXPR( self.prefixBp0[56] ) )
    elif self.sym.getId() == 38: # 'identifier'
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      return self.expect( 38, tracer )
    elif self.sym.getId() == 57: # 'exclamation_point'
      tree.astTransform = AstTransformNodeCreator('Not', {'expr': 1})
      tree.add( self.expect(57, tracer) )
      tree.add( self.__EXPR( self.prefixBp0[57] ) )
    elif self.sym.getId() == 80: # _expr
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      return self.expect( 80, tracer )
    return tree
  def led0(self, left, tracer):
    tree = ParseTree( NonTerminal(80, '_expr') )
    if  self.sym.getId() == 32: # 'mod'
      tree.astTransform = AstTransformNodeCreator('Mod', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(32, tracer) )
      tree.add( self.__EXPR( self.infixBp0[32] ) )
    elif  self.sym.getId() == 20: # 'gt'
      tree.astTransform = AstTransformNodeCreator('GreaterThan', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(20, tracer) )
      tree.add( self.__EXPR( self.infixBp0[20] ) )
    elif  self.sym.getId() == 17: # 'or'
      tree.astTransform = AstTransformNodeCreator('Or', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(17, tracer) )
      tree.add( self.__EXPR( self.infixBp0[17] ) )
    elif  self.sym.getId() == 53: # 'bitand'
      tree.astTransform = AstTransformNodeCreator('BitAND', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(53, tracer) )
      tree.add( self.__EXPR( self.infixBp0[53] ) )
    elif  self.sym.getId() == 2: # 'eq'
      tree.astTransform = AstTransformNodeCreator('Equals', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(2, tracer) )
      tree.add( self.__EXPR( self.infixBp0[2] ) )
    elif  self.sym.getId() == 7: # 'lteq'
      tree.astTransform = AstTransformNodeCreator('LessThanEq', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(7, tracer) )
      tree.add( self.__EXPR( self.infixBp0[7] ) )
    elif  self.sym.getId() == 34: # 'bitor'
      tree.astTransform = AstTransformNodeCreator('BitOR', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(34, tracer) )
      tree.add( self.__EXPR( self.infixBp0[34] ) )
    elif  self.sym.getId() == 18: # 'neq'
      tree.astTransform = AstTransformNodeCreator('NotEquals', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(18, tracer) )
      tree.add( self.__EXPR( self.infixBp0[18] ) )
    elif  self.sym.getId() == 67: # 'gteq'
      tree.astTransform = AstTransformNodeCreator('GreaterThanEq', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(67, tracer) )
      tree.add( self.__EXPR( self.infixBp0[67] ) )
    elif  self.sym.getId() == 71: # 'add'
      tree.astTransform = AstTransformNodeCreator('Add', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(71, tracer) )
      tree.add( self.__EXPR( self.infixBp0[71] ) )
    elif  self.sym.getId() == 60: # 'bitxor'
      tree.astTransform = AstTransformNodeCreator('BitXOR', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(60, tracer) )
      tree.add( self.__EXPR( self.infixBp0[60] ) )
    elif  self.sym.getId() == 49: # 'comma'
      tree.astTransform = AstTransformNodeCreator('Comma', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(49, tracer) )
      tree.add( self.__EXPR( self.infixBp0[49] ) )
    elif  self.sym.getId() == 8: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(8, tracer) )
      ls = AstList()
      if self.sym.getId() not in [69]:
        while 1:
          ls.append( self.__EXPR() )
          if self.sym.getId() != 49:
            break
          self.expect(49, tracer)
      tree.add( ls )
      tree.add( self.expect(69, tracer) )
    elif  self.sym.getId() == 26: # 'mul'
      tree.astTransform = AstTransformNodeCreator('Mul', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(26, tracer) )
      tree.add( self.__EXPR( self.infixBp0[26] ) )
    elif  self.sym.getId() == 19: # 'sub'
      tree.astTransform = AstTransformNodeCreator('Sub', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(19, tracer) )
      tree.add( self.__EXPR( self.infixBp0[19] ) )
    elif  self.sym.getId() == 25: # 'lshift'
      tree.astTransform = AstTransformNodeCreator('LeftShift', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(25, tracer) )
      tree.add( self.__EXPR( self.infixBp0[25] ) )
    elif  self.sym.getId() == 50: # 'div'
      tree.astTransform = AstTransformNodeCreator('Div', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(50, tracer) )
      tree.add( self.__EXPR( self.infixBp0[50] ) )
    elif  self.sym.getId() == 16: # 'lt'
      tree.astTransform = AstTransformNodeCreator('LessThan', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(16, tracer) )
      tree.add( self.__EXPR( self.infixBp0[16] ) )
    elif  self.sym.getId() == 48: # 'questionmark'
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(48, tracer) )
      tree.add( self.__EXPR() )
      tree.add( self.expect(42, tracer) )
      tree.add( self.__EXPR() )
    elif  self.sym.getId() == 52: # 'and'
      tree.astTransform = AstTransformNodeCreator('And', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(52, tracer) )
      tree.add( self.__EXPR( self.infixBp0[52] ) )
    elif  self.sym.getId() == 61: # 'rshift'
      tree.astTransform = AstTransformNodeCreator('RightShift', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(61, tracer) )
      tree.add( self.__EXPR( self.infixBp0[61] ) )
    return tree
