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
    self.isPrefix = False
    self.isInfix = False
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
        return AstList()
      r = AstList([self.children[0].toAst()])
      r.extend(self.children[2].toAst())
      return r
    elif self.list == 'mlist':
      r = AstList()
      if len(self.children) == 0:
        return r
      lastElement = len(self.children) - 1
      for i in range(lastElement):
        r.append(self.children[i].toAst())
      r.extend(self.children[lastElement].toAst())
      return r
    elif self.isExpr:
      if isinstance(self.astTransform, AstTransformSubstitution):
        return self.children[self.astTransform.idx].toAst()
      elif isinstance(self.astTransform, AstTransformNodeCreator):
        parameters = {}
        for name, idx in self.astTransform.parameters.items():
          if idx == '$':
            child = self.children[0]
          elif isinstance(self.children[0], ParseTree) and \
               self.children[0].isNud and \
               not self.children[0].isPrefix and \
               not self.isInfix and \
               not self.children[0].isInfix: # implies .isExpr
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
class Parser:
  def __init__(self):
    self.iterator = None
    self.sym = None
  TERMINAL_UNDEF = 0
  TERMINAL_RSHIFTEQ = 1
  TERMINAL_STRING_LITERAL = 2
  TERMINAL_DEFINE_FUNCTION = 3
  TERMINAL_LSHIFT = 4
  TERMINAL_INCLUDE = 5
  TERMINAL_SUBEQ = 6
  TERMINAL_DEFINED = 7
  TERMINAL_ARROW = 8
  TERMINAL_RSHIFT = 9
  TERMINAL_SEMI = 10
  TERMINAL_ADDEQ = 11
  TERMINAL_SUB = 12
  TERMINAL_MOD = 13
  TERMINAL_IF = 14
  TERMINAL_MODEQ = 15
  TERMINAL_ELIF = 16
  TERMINAL_DEFINE = 17
  TERMINAL_ELIPSIS = 18
  TERMINAL_MULEQ = 19
  TERMINAL_MUL = 20
  TERMINAL_EXCLAMATION_POINT = 21
  TERMINAL_DIVEQ = 22
  TERMINAL_DIV = 23
  TERMINAL_COLON = 24
  TERMINAL_ASSIGN = 25
  TERMINAL_AMPERSAND = 26
  TERMINAL_ADD = 27
  TERMINAL_QUESTIONMARK = 28
  TERMINAL_LPAREN = 29
  TERMINAL_SEPARATOR = 30
  TERMINAL_DECR = 31
  TERMINAL_LINE = 32
  TERMINAL_GT = 33
  TERMINAL_POUND = 34
  TERMINAL_INCR = 35
  TERMINAL_IFNDEF = 36
  TERMINAL_BITNOT = 37
  TERMINAL_DOT = 38
  TERMINAL_COMMA = 39
  TERMINAL_OR = 40
  TERMINAL_TILDE = 41
  TERMINAL_BITOR = 42
  TERMINAL_LBRACE = 43
  TERMINAL_HEADER_GLOBAL = 44
  TERMINAL_IFDEF = 45
  TERMINAL_BITXOR = 46
  TERMINAL_RBRACE = 47
  TERMINAL_NEQ = 48
  TERMINAL_AND = 49
  TERMINAL_BITOREQ = 50
  TERMINAL__EXPR = 51
  TERMINAL_BITAND = 52
  TERMINAL_LSQUARE = 53
  TERMINAL_EQ = 54
  TERMINAL_ELSE = 55
  TERMINAL_PRAGMA = 56
  TERMINAL_BITXOREQ = 57
  TERMINAL_CHARACTER_CONSTANT = 58
  TERMINAL_IDENTIFIER = 59
  TERMINAL_LTEQ = 60
  TERMINAL_HEADER_LOCAL = 61
  TERMINAL_ERROR = 62
  TERMINAL_RSQUARE = 63
  TERMINAL_BITANDEQ = 64
  TERMINAL_PP_NUMBER = 65
  TERMINAL_LSHIFTEQ = 66
  TERMINAL_GTEQ = 67
  TERMINAL_LT = 68
  TERMINAL_WARNING = 69
  TERMINAL_ENDIF = 70
  TERMINAL_RPAREN = 71
  TERMINAL_POUNDPOUND = 72
  TERMINAL_DEFINED_SEPARATOR = 73
  TERMINAL_CSOURCE = 74
  terminal_str = {
    0: 'undef',
    1: 'rshifteq',
    2: 'string_literal',
    3: 'define_function',
    4: 'lshift',
    5: 'include',
    6: 'subeq',
    7: 'defined',
    8: 'arrow',
    9: 'rshift',
    10: 'semi',
    11: 'addeq',
    12: 'sub',
    13: 'mod',
    14: 'if',
    15: 'modeq',
    16: 'elif',
    17: 'define',
    18: 'elipsis',
    19: 'muleq',
    20: 'mul',
    21: 'exclamation_point',
    22: 'diveq',
    23: 'div',
    24: 'colon',
    25: 'assign',
    26: 'ampersand',
    27: 'add',
    28: 'questionmark',
    29: 'lparen',
    30: 'separator',
    31: 'decr',
    32: 'line',
    33: 'gt',
    34: 'pound',
    35: 'incr',
    36: 'ifndef',
    37: 'bitnot',
    38: 'dot',
    39: 'comma',
    40: 'or',
    41: 'tilde',
    42: 'bitor',
    43: 'lbrace',
    44: 'header_global',
    45: 'ifdef',
    46: 'bitxor',
    47: 'rbrace',
    48: 'neq',
    49: 'and',
    50: 'bitoreq',
    51: '_expr',
    52: 'bitand',
    53: 'lsquare',
    54: 'eq',
    55: 'else',
    56: 'pragma',
    57: 'bitxoreq',
    58: 'character_constant',
    59: 'identifier',
    60: 'lteq',
    61: 'header_local',
    62: 'error',
    63: 'rsquare',
    64: 'bitandeq',
    65: 'pp_number',
    66: 'lshifteq',
    67: 'gteq',
    68: 'lt',
    69: 'warning',
    70: 'endif',
    71: 'rparen',
    72: 'poundpound',
    73: 'defined_separator',
    74: 'csource',
  }
  nonterminal_str = {
    75: 'control_line',
    76: '_gen5',
    77: 'pp_nodes',
    78: 'pragma_line',
    79: 'defined_identifier',
    80: '_expr',
    81: 'pp_directive',
    82: '_gen6',
    83: 'include_line',
    84: 'elseif_part',
    85: 'error_line',
    86: 'replacement_list',
    87: 'include_type',
    88: 'pp_nodes_list',
    89: '_gen4',
    90: 'elipsis_opt',
    91: 'define_func_param',
    92: 'warning_line',
    93: '_gen1',
    94: 'undef_line',
    95: '_gen0',
    96: 'if_section',
    97: 'punctuator',
    98: 'define_line',
    99: '_gen2',
    100: 'line_line',
    101: 'pp_tokens',
    102: 'if_part',
    103: 'else_part',
    104: '_gen3',
    105: 'pp_file',
  }
  str_terminal = {
    'undef': 0,
    'rshifteq': 1,
    'string_literal': 2,
    'define_function': 3,
    'lshift': 4,
    'include': 5,
    'subeq': 6,
    'defined': 7,
    'arrow': 8,
    'rshift': 9,
    'semi': 10,
    'addeq': 11,
    'sub': 12,
    'mod': 13,
    'if': 14,
    'modeq': 15,
    'elif': 16,
    'define': 17,
    'elipsis': 18,
    'muleq': 19,
    'mul': 20,
    'exclamation_point': 21,
    'diveq': 22,
    'div': 23,
    'colon': 24,
    'assign': 25,
    'ampersand': 26,
    'add': 27,
    'questionmark': 28,
    'lparen': 29,
    'separator': 30,
    'decr': 31,
    'line': 32,
    'gt': 33,
    'pound': 34,
    'incr': 35,
    'ifndef': 36,
    'bitnot': 37,
    'dot': 38,
    'comma': 39,
    'or': 40,
    'tilde': 41,
    'bitor': 42,
    'lbrace': 43,
    'header_global': 44,
    'ifdef': 45,
    'bitxor': 46,
    'rbrace': 47,
    'neq': 48,
    'and': 49,
    'bitoreq': 50,
    '_expr': 51,
    'bitand': 52,
    'lsquare': 53,
    'eq': 54,
    'else': 55,
    'pragma': 56,
    'bitxoreq': 57,
    'character_constant': 58,
    'identifier': 59,
    'lteq': 60,
    'header_local': 61,
    'error': 62,
    'rsquare': 63,
    'bitandeq': 64,
    'pp_number': 65,
    'lshifteq': 66,
    'gteq': 67,
    'lt': 68,
    'warning': 69,
    'endif': 70,
    'rparen': 71,
    'poundpound': 72,
    'defined_separator': 73,
    'csource': 74,
  }
  str_nonterminal = {
    'control_line': 75,
    '_gen5': 76,
    'pp_nodes': 77,
    'pragma_line': 78,
    'defined_identifier': 79,
    '_expr': 80,
    'pp_directive': 81,
    '_gen6': 82,
    'include_line': 83,
    'elseif_part': 84,
    'error_line': 85,
    'replacement_list': 86,
    'include_type': 87,
    'pp_nodes_list': 88,
    '_gen4': 89,
    'elipsis_opt': 90,
    'define_func_param': 91,
    'warning_line': 92,
    '_gen1': 93,
    'undef_line': 94,
    '_gen0': 95,
    'if_section': 96,
    'punctuator': 97,
    'define_line': 98,
    '_gen2': 99,
    'line_line': 100,
    'pp_tokens': 101,
    'if_part': 102,
    'else_part': 103,
    '_gen3': 104,
    'pp_file': 105,
  }
  terminal_count = 75
  nonterminal_count = 31
  parse_table = [
    [45, -1, -1, 133, -1, 15, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 133, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 93, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 14, -1, -1, -1, -1, -1, 27, -1, -1, -1, -1, -1, -1, 33, -1, -1, -1, -1, -1],
    [-1, -1, 4, -1, -1, -1, -1, 4, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 4, -1, -1, -1, -1, -1, -1, -1, 4, -1, -1, -1, -1, -1, -1, -1, 4, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 4, -1, -1, -1, -1, -1, -1, 4, 4, -1, -1, -1, -1, -1, 4, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [74, -1, -1, 74, -1, 74, -1, -1, -1, -1, -1, -1, -1, -1, 74, -1, -1, 74, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 74, -1, -1, -1, 74, -1, -1, -1, -1, -1, -1, -1, -1, 74, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 74, -1, -1, -1, -1, -1, 74, -1, -1, -1, -1, -1, -1, 74, -1, -1, -1, -1, 124],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 64, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 105, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 89, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [12, -1, -1, 12, -1, 12, -1, -1, -1, -1, -1, -1, -1, -1, 31, -1, -1, 12, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 12, -1, -1, -1, 31, -1, -1, -1, -1, -1, -1, -1, -1, 31, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 12, -1, -1, -1, -1, -1, 12, -1, -1, -1, -1, -1, -1, 12, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 26, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, 73, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 66, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 41, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, 2, 2, -1, 2, -1, 2, 2, 2, 2, 2, 2, 2, 2, -1, 2, -1, -1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, -1, 2, 2, 2, -1, 2, 2, 2, 2, 2, 2, 2, 2, -1, 2, 2, 2, 2, 2, -1, 2, 2, 2, -1, -1, 2, 2, 2, 2, 2, -1, 2, 2, 2, 2, 2, 2, -1, -1, 2, 2, 2, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 88, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 75, -1, 65, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [11, -1, -1, 11, -1, 11, -1, -1, -1, -1, -1, -1, -1, -1, 11, -1, 11, 11, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 11, -1, -1, -1, 11, -1, -1, -1, -1, -1, -1, -1, -1, 11, -1, -1, -1, -1, -1, -1, -1, -1, -1, 11, 11, -1, -1, -1, -1, -1, 11, -1, -1, -1, -1, -1, -1, 11, 11, -1, -1, -1, 11],
    [-1, 121, 121, -1, 121, -1, 121, 121, 121, 121, 121, 121, 121, 121, -1, 121, -1, -1, 121, 121, 121, 121, 121, 121, 121, 121, 121, 121, 121, 121, 123, 121, -1, 121, 121, 121, -1, 121, 121, 121, 121, 121, 121, 121, 121, -1, 121, 121, 121, 121, 121, -1, 121, 121, 121, -1, -1, 121, 121, 121, 121, 121, -1, 121, 121, 121, 121, 121, 121, -1, -1, 121, 121, 121, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 51, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 7, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 136, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 97, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 60, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 63, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [128, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [38, -1, -1, 38, -1, 38, -1, -1, -1, -1, -1, -1, -1, -1, 38, -1, 40, 38, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 38, -1, -1, -1, 38, -1, -1, -1, -1, -1, -1, -1, -1, 38, -1, -1, -1, -1, -1, -1, -1, -1, -1, 40, 38, -1, -1, -1, -1, -1, 38, -1, -1, -1, -1, -1, -1, 38, 40, -1, -1, -1, 38],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 70, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 70, -1, -1, -1, -1, -1, -1, -1, -1, 70, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, 76, -1, -1, 82, -1, 34, -1, 107, 68, 129, 98, 92, 111, -1, 114, -1, -1, 120, 139, 78, 80, 131, 112, 23, 6, 137, 117, 110, 108, -1, 8, -1, 118, 9, 19, -1, 25, 42, 39, 55, 37, 35, 77, -1, -1, 43, 134, 50, 103, 57, -1, 79, 83, 53, -1, -1, 67, -1, -1, 119, -1, -1, 127, 140, -1, 99, 90, 28, -1, -1, 101, 1, -1, -1],
    [-1, -1, -1, 32, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 85, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 113, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 113, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 87, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 54, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, 58, 71, -1, 58, -1, 58, 84, 58, 58, 58, 58, 58, 58, -1, 58, -1, -1, 58, 58, 58, 58, 58, 58, 58, 58, 58, 58, 58, 58, -1, 58, -1, 58, 58, 58, -1, 58, 58, 58, 58, 58, 58, 58, 86, -1, 58, 58, 58, 58, 58, -1, 58, 58, 58, -1, -1, 58, 96, 13, 58, 3, -1, 58, 58, 17, 58, 58, 58, -1, -1, 58, 58, 100, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 132, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 104, -1, -1, -1, -1, -1, -1, -1, -1, 116, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 126, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 21, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 125, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 94, -1, -1, -1],
    [115, -1, -1, 115, -1, 115, -1, -1, -1, -1, -1, -1, -1, -1, 115, -1, -1, 115, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 115, -1, -1, -1, 115, -1, -1, -1, -1, -1, -1, -1, -1, 115, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 115, -1, -1, -1, -1, -1, 115, -1, -1, -1, -1, -1, -1, 115, -1, -1, -1, -1, 115],
  ]
  def terminal(self, str):
    return self.str_terminal[str]
  def terminalNames(self):
    return list(self.str_terminal.keys())
  def isTerminal(self, id):
    return 0 <= id <= 74
  def isNonTerminal(self, id):
    return 75 <= id <= 105
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
  def parse(self, iterator):
    self.iterator = iter(iterator)
    self.sym = self.getsym()
    self.start = 'PP_FILE'
    tree = self._PP_FILE()
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
    return self.parse_table[n - 75][self.sym.getId()]
  def call(self, nt_str):
    return getattr(self, nt_str)()
  def _CONTROL_LINE(self, depth=0, tracer=None):
    rule = self.rule(75)
    tree = ParseTree( NonTerminal(75, self.getAtomString(75)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 14:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PRAGMA_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 15:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._INCLUDE_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 27:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ERROR_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 33:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._WARNING_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 45:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._UNDEF_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 93:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._LINE_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 133:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DEFINE_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN5(self, depth=0, tracer=None):
    rule = self.rule(76)
    tree = ParseTree( NonTerminal(76, self.getAtomString(76)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 4:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN6(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _PP_NODES(self, depth=0, tracer=None):
    rule = self.rule(77)
    tree = ParseTree( NonTerminal(77, self.getAtomString(77)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 74:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PP_DIRECTIVE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 124:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(74, tracer) ) # csource
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PRAGMA_LINE(self, depth=0, tracer=None):
    rule = self.rule(78)
    tree = ParseTree( NonTerminal(78, self.getAtomString(78)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 64:
      tree.astTransform = AstTransformNodeCreator('Pragma', {'tokens': 1})
      tree.add( self.expect(56, tracer) ) # pragma
      subtree = self.__GEN4(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _DEFINED_IDENTIFIER(self, depth=0, tracer=None):
    rule = self.rule(79)
    tree = ParseTree( NonTerminal(79, self.getAtomString(79)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 89:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(59, tracer) ) # identifier
      return tree
    elif rule == 105:
      tree.astTransform = AstTransformSubstitution(1)
      tree.add( self.expect(29, tracer) ) # lparen
      tree.add( self.expect(59, tracer) ) # identifier
      tree.add( self.expect(71, tracer) ) # rparen
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PP_DIRECTIVE(self, depth=0, tracer=None):
    rule = self.rule(81)
    tree = ParseTree( NonTerminal(81, self.getAtomString(81)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 12:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._CONTROL_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 31:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._IF_SECTION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN6(self, depth=0, tracer=None):
    rule = self.rule(82)
    tree = ParseTree( NonTerminal(82, self.getAtomString(82)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 26:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(39, tracer) ) # comma
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.__GEN6(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _INCLUDE_LINE(self, depth=0, tracer=None):
    rule = self.rule(83)
    tree = ParseTree( NonTerminal(83, self.getAtomString(83)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 73:
      tree.astTransform = AstTransformNodeCreator('Include', {'file': 1})
      tree.add( self.expect(5, tracer) ) # include
      subtree = self._INCLUDE_TYPE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _ELSEIF_PART(self, depth=0, tracer=None):
    rule = self.rule(84)
    tree = ParseTree( NonTerminal(84, self.getAtomString(84)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 66:
      tree.astTransform = AstTransformNodeCreator('ElseIf', {'expr': 1, 'nodes': 2})
      tree.add( self.expect(16, tracer) ) # elif
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
  def _ERROR_LINE(self, depth=0, tracer=None):
    rule = self.rule(85)
    tree = ParseTree( NonTerminal(85, self.getAtomString(85)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 41:
      tree.astTransform = AstTransformNodeCreator('Error', {'tokens': 1})
      tree.add( self.expect(62, tracer) ) # error
      subtree = self.__GEN4(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _REPLACEMENT_LIST(self, depth=0, tracer=None):
    rule = self.rule(86)
    tree = ParseTree( NonTerminal(86, self.getAtomString(86)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [30]):
      return tree
    if self.sym == None:
      return tree
    if rule == 2:
      tree.astTransform = AstTransformNodeCreator('ReplacementList', {'tokens': 0})
      subtree = self.__GEN4(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _INCLUDE_TYPE(self, depth=0, tracer=None):
    rule = self.rule(87)
    tree = ParseTree( NonTerminal(87, self.getAtomString(87)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 65:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(61, tracer) ) # header_local
      return tree
    elif rule == 75:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(59, tracer) ) # identifier
      return tree
    elif rule == 88:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(44, tracer) ) # header_global
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PP_NODES_LIST(self, depth=0, tracer=None):
    rule = self.rule(88)
    tree = ParseTree( NonTerminal(88, self.getAtomString(88)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [16, 70, 55, -1]):
      return tree
    if self.sym == None:
      return tree
    if rule == 11:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN0(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN4(self, depth=0, tracer=None):
    rule = self.rule(89)
    tree = ParseTree( NonTerminal(89, self.getAtomString(89)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [30]):
      return tree
    if self.sym == None:
      return tree
    if rule == 121:
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
  def _ELIPSIS_OPT(self, depth=0, tracer=None):
    rule = self.rule(90)
    tree = ParseTree( NonTerminal(90, self.getAtomString(90)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 51:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(39, tracer) ) # comma
      tree.add( self.expect(18, tracer) ) # elipsis
      return tree
    return tree
  def _DEFINE_FUNC_PARAM(self, depth=0, tracer=None):
    rule = self.rule(91)
    tree = ParseTree( NonTerminal(91, self.getAtomString(91)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 7:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(18, tracer) ) # elipsis
      return tree
    elif rule == 136:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(59, tracer) ) # identifier
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _WARNING_LINE(self, depth=0, tracer=None):
    rule = self.rule(92)
    tree = ParseTree( NonTerminal(92, self.getAtomString(92)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 97:
      tree.astTransform = AstTransformNodeCreator('Warning', {'tokens': 1})
      tree.add( self.expect(69, tracer) ) # warning
      subtree = self.__GEN4(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN1(self, depth=0, tracer=None):
    rule = self.rule(93)
    tree = ParseTree( NonTerminal(93, self.getAtomString(93)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [55]):
      return tree
    if self.sym == None:
      return tree
    if rule == 60:
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
  def _UNDEF_LINE(self, depth=0, tracer=None):
    rule = self.rule(94)
    tree = ParseTree( NonTerminal(94, self.getAtomString(94)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 128:
      tree.astTransform = AstTransformNodeCreator('Undef', {'ident': 1})
      tree.add( self.expect(0, tracer) ) # undef
      tree.add( self.expect(59, tracer) ) # identifier
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN0(self, depth=0, tracer=None):
    rule = self.rule(95)
    tree = ParseTree( NonTerminal(95, self.getAtomString(95)), tracer )
    tree.list = 'tlist'
    if self.sym != None and (self.sym.getId() in [-1, 55, 16, 70]):
      return tree
    if self.sym == None:
      return tree
    if rule == 38:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PP_NODES(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(30, tracer) ) # separator
      subtree = self.__GEN0(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _IF_SECTION(self, depth=0, tracer=None):
    rule = self.rule(96)
    tree = ParseTree( NonTerminal(96, self.getAtomString(96)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 70:
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
      tree.add( self.expect(70, tracer) ) # endif
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PUNCTUATOR(self, depth=0, tracer=None):
    rule = self.rule(97)
    tree = ParseTree( NonTerminal(97, self.getAtomString(97)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 1:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(72, tracer) ) # poundpound
      return tree
    elif rule == 6:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(25, tracer) ) # assign
      return tree
    elif rule == 8:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(31, tracer) ) # decr
      return tree
    elif rule == 9:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(34, tracer) ) # pound
      return tree
    elif rule == 19:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(35, tracer) ) # incr
      return tree
    elif rule == 23:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(24, tracer) ) # colon
      return tree
    elif rule == 25:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(37, tracer) ) # bitnot
      return tree
    elif rule == 28:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(68, tracer) ) # lt
      return tree
    elif rule == 34:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(6, tracer) ) # subeq
      return tree
    elif rule == 35:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(42, tracer) ) # bitor
      return tree
    elif rule == 37:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(41, tracer) ) # tilde
      return tree
    elif rule == 39:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(39, tracer) ) # comma
      return tree
    elif rule == 42:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(38, tracer) ) # dot
      return tree
    elif rule == 43:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(46, tracer) ) # bitxor
      return tree
    elif rule == 50:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(48, tracer) ) # neq
      return tree
    elif rule == 53:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(54, tracer) ) # eq
      return tree
    elif rule == 55:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(40, tracer) ) # or
      return tree
    elif rule == 57:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(50, tracer) ) # bitoreq
      return tree
    elif rule == 67:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(57, tracer) ) # bitxoreq
      return tree
    elif rule == 68:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(9, tracer) ) # rshift
      return tree
    elif rule == 76:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(1, tracer) ) # rshifteq
      return tree
    elif rule == 77:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(43, tracer) ) # lbrace
      return tree
    elif rule == 78:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(20, tracer) ) # mul
      return tree
    elif rule == 79:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(52, tracer) ) # bitand
      return tree
    elif rule == 80:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(21, tracer) ) # exclamation_point
      return tree
    elif rule == 82:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(4, tracer) ) # lshift
      return tree
    elif rule == 83:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(53, tracer) ) # lsquare
      return tree
    elif rule == 90:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(67, tracer) ) # gteq
      return tree
    elif rule == 92:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(12, tracer) ) # sub
      return tree
    elif rule == 98:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(11, tracer) ) # addeq
      return tree
    elif rule == 99:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(66, tracer) ) # lshifteq
      return tree
    elif rule == 101:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(71, tracer) ) # rparen
      return tree
    elif rule == 103:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(49, tracer) ) # and
      return tree
    elif rule == 107:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(8, tracer) ) # arrow
      return tree
    elif rule == 108:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(29, tracer) ) # lparen
      return tree
    elif rule == 110:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(28, tracer) ) # questionmark
      return tree
    elif rule == 111:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(13, tracer) ) # mod
      return tree
    elif rule == 112:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(23, tracer) ) # div
      return tree
    elif rule == 114:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(15, tracer) ) # modeq
      return tree
    elif rule == 117:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(27, tracer) ) # add
      return tree
    elif rule == 118:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(33, tracer) ) # gt
      return tree
    elif rule == 119:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(60, tracer) ) # lteq
      return tree
    elif rule == 120:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(18, tracer) ) # elipsis
      return tree
    elif rule == 127:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(63, tracer) ) # rsquare
      return tree
    elif rule == 129:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(10, tracer) ) # semi
      return tree
    elif rule == 131:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(22, tracer) ) # diveq
      return tree
    elif rule == 134:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(47, tracer) ) # rbrace
      return tree
    elif rule == 137:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(26, tracer) ) # ampersand
      return tree
    elif rule == 139:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(19, tracer) ) # muleq
      return tree
    elif rule == 140:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(64, tracer) ) # bitandeq
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _DEFINE_LINE(self, depth=0, tracer=None):
    rule = self.rule(98)
    tree = ParseTree( NonTerminal(98, self.getAtomString(98)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 32:
      tree.astTransform = AstTransformNodeCreator('DefineFunction', {'body': 5, 'ident': 1, 'params': 3})
      tree.add( self.expect(3, tracer) ) # define_function
      tree.add( self.expect(59, tracer) ) # identifier
      tree.add( self.expect(29, tracer) ) # lparen
      subtree = self.__GEN2(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(71, tracer) ) # rparen
      subtree = self._REPLACEMENT_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 85:
      tree.astTransform = AstTransformNodeCreator('Define', {'body': 2, 'ident': 1})
      tree.add( self.expect(17, tracer) ) # define
      tree.add( self.expect(59, tracer) ) # identifier
      subtree = self._REPLACEMENT_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def __GEN2(self, depth=0, tracer=None):
    rule = self.rule(99)
    tree = ParseTree( NonTerminal(99, self.getAtomString(99)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [71]):
      return tree
    if self.sym == None:
      return tree
    if rule == 113:
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
  def _LINE_LINE(self, depth=0, tracer=None):
    rule = self.rule(100)
    tree = ParseTree( NonTerminal(100, self.getAtomString(100)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 54:
      tree.astTransform = AstTransformNodeCreator('Line', {'tokens': 1})
      tree.add( self.expect(32, tracer) ) # line
      subtree = self.__GEN4(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PP_TOKENS(self, depth=0, tracer=None):
    rule = self.rule(101)
    tree = ParseTree( NonTerminal(101, self.getAtomString(101)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 3:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(61, tracer) ) # header_local
      return tree
    elif rule == 13:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(59, tracer) ) # identifier
      return tree
    elif rule == 17:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(65, tracer) ) # pp_number
      return tree
    elif rule == 58:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PUNCTUATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 71:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(2, tracer) ) # string_literal
      return tree
    elif rule == 84:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(7, tracer) ) # defined
      return tree
    elif rule == 86:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(44, tracer) ) # header_global
      return tree
    elif rule == 96:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(58, tracer) ) # character_constant
      return tree
    elif rule == 100:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(73, tracer) ) # defined_separator
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _IF_PART(self, depth=0, tracer=None):
    rule = self.rule(102)
    tree = ParseTree( NonTerminal(102, self.getAtomString(102)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 104:
      tree.astTransform = AstTransformNodeCreator('IfNDef', {'nodes': 2, 'ident': 1})
      tree.add( self.expect(36, tracer) ) # ifndef
      tree.add( self.expect(59, tracer) ) # identifier
      subtree = self._PP_NODES_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 116:
      tree.astTransform = AstTransformNodeCreator('IfDef', {'nodes': 2, 'ident': 1})
      tree.add( self.expect(45, tracer) ) # ifdef
      tree.add( self.expect(59, tracer) ) # identifier
      subtree = self._PP_NODES_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 132:
      tree.astTransform = AstTransformNodeCreator('If', {'expr': 1, 'nodes': 2})
      tree.add( self.expect(14, tracer) ) # if
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
  def _ELSE_PART(self, depth=0, tracer=None):
    rule = self.rule(103)
    tree = ParseTree( NonTerminal(103, self.getAtomString(103)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [70]):
      return tree
    if self.sym == None:
      return tree
    if rule == 126:
      tree.astTransform = AstTransformNodeCreator('Else', {'nodes': 1})
      tree.add( self.expect(55, tracer) ) # else
      subtree = self._PP_NODES_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN3(self, depth=0, tracer=None):
    rule = self.rule(104)
    tree = ParseTree( NonTerminal(104, self.getAtomString(104)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [71]):
      return tree
    if self.sym == None:
      return tree
    if rule == 125:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(39, tracer) ) # comma
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
  def _PP_FILE(self, depth=0, tracer=None):
    rule = self.rule(105)
    tree = ParseTree( NonTerminal(105, self.getAtomString(105)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 115:
      tree.astTransform = AstTransformNodeCreator('PPFile', {'nodes': 0})
      subtree = self._PP_NODES_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  infixBp0 = {
    4: 10000,
    9: 10000,
    12: 11000,
    13: 12000,
    20: 12000,
    23: 12000,
    27: 11000,
    28: 2000,
    29: 15000,
    33: 9000,
    39: 1000,
    40: 3000,
    42: 7000,
    46: 6000,
    48: 8000,
    49: 4000,
    52: 5000,
    54: 8000,
    60: 9000,
    67: 9000,
    68: 9000,
    73: 14000,
  }
  prefixBp0 = {
    7: 13000,
    12: 13000,
    20: 13000,
    21: 13000,
    37: 13000,
    52: 13000,
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
    if self.sym.getId() == 59: # 'identifier'
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      return self.expect( 59, tracer )
    elif self.sym.getId() == 80: # _expr
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      return self.expect( 80, tracer )
    elif self.sym.getId() == 65: # 'pp_number'
      tree.astTransform = AstTransformSubstitution(0)
      return self.expect( 65, tracer )
    elif self.sym.getId() == 7: # 'defined'
      tree.astTransform = AstTransformNodeCreator('IsDefined', {'expr': 2})
      return self.expect( 7, tracer )
    elif self.sym.getId() == 58: # 'character_constant'
      tree.astTransform = AstTransformSubstitution(0)
      return self.expect( 58, tracer )
    elif self.sym.getId() == 21: # 'exclamation_point'
      tree.astTransform = AstTransformNodeCreator('Not', {'expr': 1})
      tree.add( self.expect(21, tracer) )
      tree.add( self.__EXPR( self.prefixBp0[21] ) )
      tree.isPrefix = True
    elif self.sym.getId() == 37: # 'bitnot'
      tree.astTransform = AstTransformNodeCreator('BitNOT', {'expr': 1})
      tree.add( self.expect(37, tracer) )
      tree.add( self.__EXPR( self.prefixBp0[37] ) )
      tree.isPrefix = True
    elif self.sym.getId() == 2: # 'string_literal'
      tree.astTransform = AstTransformSubstitution(0)
      return self.expect( 2, tracer )
    elif self.sym.getId() == 29: # 'lparen'
      tree.astTransform = AstTransformSubstitution(1)
      tree.add( self.expect(29, tracer) )
      tree.add( self.__EXPR() )
      tree.add( self.expect(71, tracer) )
    return tree
  def led0(self, left, tracer):
    tree = ParseTree( NonTerminal(80, '_expr') )
    if  self.sym.getId() == 52: # 'bitand'
      tree.astTransform = AstTransformNodeCreator('BitAND', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(52, tracer) )
      tree.add( self.__EXPR( self.infixBp0[52] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 54: # 'eq'
      tree.astTransform = AstTransformNodeCreator('Equals', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(54, tracer) )
      tree.add( self.__EXPR( self.infixBp0[54] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 28: # 'questionmark'
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(28, tracer) )
      tree.add( self.__EXPR() )
      tree.add( self.expect(24, tracer) )
      tree.add( self.__EXPR() )
    elif  self.sym.getId() == 60: # 'lteq'
      tree.astTransform = AstTransformNodeCreator('LessThanEq', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(60, tracer) )
      tree.add( self.__EXPR( self.infixBp0[60] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 73: # 'defined_separator'
      tree.astTransform = AstTransformNodeCreator('IsDefined', {'expr': 2})
      if left:
        tree.add(left)
      tree.add( self.expect(73, tracer) )
      tree.add( self._DEFINED_IDENTIFIER() )
    elif  self.sym.getId() == 42: # 'bitor'
      tree.astTransform = AstTransformNodeCreator('BitOR', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(42, tracer) )
      tree.add( self.__EXPR( self.infixBp0[42] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 48: # 'neq'
      tree.astTransform = AstTransformNodeCreator('NotEquals', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(48, tracer) )
      tree.add( self.__EXPR( self.infixBp0[48] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 67: # 'gteq'
      tree.astTransform = AstTransformNodeCreator('GreaterThanEq', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(67, tracer) )
      tree.add( self.__EXPR( self.infixBp0[67] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 27: # 'add'
      tree.astTransform = AstTransformNodeCreator('Add', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(27, tracer) )
      tree.add( self.__EXPR( self.infixBp0[27] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 46: # 'bitxor'
      tree.astTransform = AstTransformNodeCreator('BitXOR', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(46, tracer) )
      tree.add( self.__EXPR( self.infixBp0[46] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 39: # 'comma'
      tree.astTransform = AstTransformNodeCreator('Comma', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(39, tracer) )
      tree.add( self.__EXPR( self.infixBp0[39] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 20: # 'mul'
      tree.astTransform = AstTransformNodeCreator('Mul', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(20, tracer) )
      tree.add( self.__EXPR( self.infixBp0[20] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 12: # 'sub'
      tree.astTransform = AstTransformNodeCreator('Sub', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(12, tracer) )
      tree.add( self.__EXPR( self.infixBp0[12] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 4: # 'lshift'
      tree.astTransform = AstTransformNodeCreator('LeftShift', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(4, tracer) )
      tree.add( self.__EXPR( self.infixBp0[4] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 23: # 'div'
      tree.astTransform = AstTransformNodeCreator('Div', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(23, tracer) )
      tree.add( self.__EXPR( self.infixBp0[23] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 68: # 'lt'
      tree.astTransform = AstTransformNodeCreator('LessThan', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(68, tracer) )
      tree.add( self.__EXPR( self.infixBp0[68] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 49: # 'and'
      tree.astTransform = AstTransformNodeCreator('And', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(49, tracer) )
      tree.add( self.__EXPR( self.infixBp0[49] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 9: # 'rshift'
      tree.astTransform = AstTransformNodeCreator('RightShift', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(9, tracer) )
      tree.add( self.__EXPR( self.infixBp0[9] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 29: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(29, tracer) )
      tree.add( self.__GEN5() )
      tree.add( self.expect(71, tracer) )
    elif  self.sym.getId() == 13: # 'mod'
      tree.astTransform = AstTransformNodeCreator('Mod', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(13, tracer) )
      tree.add( self.__EXPR( self.infixBp0[13] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 33: # 'gt'
      tree.astTransform = AstTransformNodeCreator('GreaterThan', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(33, tracer) )
      tree.add( self.__EXPR( self.infixBp0[33] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 40: # 'or'
      tree.astTransform = AstTransformNodeCreator('Or', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(40, tracer) )
      tree.add( self.__EXPR( self.infixBp0[40] ) )
      tree.isInfix = True
    return tree
