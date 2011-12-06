import sys
import inspect
def whoami():
  return inspect.stack()[1][3]
def whosdaddy():
  return inspect.stack()[2][3]
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
    self.nudMorphemeCount = 0
    self.isExprNud = False # true for rules like _expr := {_expr} + {...}
    self.listSeparator = None
    self.list = False
  def add( self, tree ):
    self.children.append( tree )
  def toAst( self ):
    if self.list == 'slist' or self.list == 'nlist':
      if len(self.children) == 0:
        return AstList()
      offset = 1 if self.children[0] == self.listSeparator else 0
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
               not self.isExprNud and \
               not self.isInfix:
            if idx < self.children[0].nudMorphemeCount:
              child = self.children[0].children[idx]
            else:
              index = idx - self.children[0].nudMorphemeCount + 1
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
class ParseTreePrettyPrintable:
  def __init__(self, ast, tokenFormat='type'):
    self.__dict__.update(locals())
  def __str__(self):
    return self._prettyPrint(self.ast, 0)
  def _prettyPrint(self, parsetree, indent = 0):
    indentStr = ''.join([' ' for x in range(indent)])
    if isinstance(parsetree, ParseTree):
      if len(parsetree.children) == 0:
        return '(%s: )' % (parsetree.nonterminal)
      string = '%s(%s:\n' % (indentStr, parsetree.nonterminal)
      string += ',\n'.join([ \
        '%s  %s' % (indentStr, self._prettyPrint(value, indent + 2).lstrip()) for value in parsetree.children \
      ])
      string += '\n%s)' % (indentStr)
      return string
    elif isinstance(parsetree, Terminal):
      return '%s%s' % (indentStr, parsetree.toString(self.tokenFormat))
    else:
      return '%s%s' % (indentStr, parsetree)
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
  TERMINAL_DEFINE = 0
  TERMINAL_SUBEQ = 1
  TERMINAL_TILDE = 2
  TERMINAL_IDENTIFIER = 3
  TERMINAL_RSHIFT = 4
  TERMINAL_ADDEQ = 5
  TERMINAL_SUB = 6
  TERMINAL_ELIF = 7
  TERMINAL_MOD = 8
  TERMINAL_MODEQ = 9
  TERMINAL_PP_NUMBER = 10
  TERMINAL_ADD = 11
  TERMINAL_UNDEF = 12
  TERMINAL_LINE = 13
  TERMINAL_ELIPSIS = 14
  TERMINAL_MULEQ = 15
  TERMINAL_ELSE = 16
  TERMINAL_DEFINED_SEPARATOR = 17
  TERMINAL__EXPR = 18
  TERMINAL_SEMI = 19
  TERMINAL_DIVEQ = 20
  TERMINAL_DOT = 21
  TERMINAL_DIV = 22
  TERMINAL_COLON = 23
  TERMINAL_ASSIGN = 24
  TERMINAL_LT = 25
  TERMINAL_AMPERSAND = 26
  TERMINAL_DECR = 27
  TERMINAL_DEFINED = 28
  TERMINAL_QUESTIONMARK = 29
  TERMINAL_IFDEF = 30
  TERMINAL_POUNDPOUND = 31
  TERMINAL_LSHIFTEQ = 32
  TERMINAL_BITAND = 33
  TERMINAL_POUND = 34
  TERMINAL_OR = 35
  TERMINAL_MUL = 36
  TERMINAL_BITNOT = 37
  TERMINAL_COMMA = 38
  TERMINAL_CHARACTER_CONSTANT = 39
  TERMINAL_AND = 40
  TERMINAL_BITOR = 41
  TERMINAL_IF = 42
  TERMINAL_LBRACE = 43
  TERMINAL_PRAGMA = 44
  TERMINAL_HEADER_GLOBAL = 45
  TERMINAL_GTEQ = 46
  TERMINAL_IFNDEF = 47
  TERMINAL_NEQ = 48
  TERMINAL_BITXOR = 49
  TERMINAL_RBRACE = 50
  TERMINAL_HEADER_LOCAL = 51
  TERMINAL_LSHIFT = 52
  TERMINAL_EQ = 53
  TERMINAL_BITOREQ = 54
  TERMINAL_LSQUARE = 55
  TERMINAL_INCR = 56
  TERMINAL_LTEQ = 57
  TERMINAL_DEFINE_FUNCTION = 58
  TERMINAL_BITXOREQ = 59
  TERMINAL_RSQUARE = 60
  TERMINAL_INCLUDE = 61
  TERMINAL_ERROR = 62
  TERMINAL_ARROW = 63
  TERMINAL_BITANDEQ = 64
  TERMINAL_LPAREN = 65
  TERMINAL_WARNING = 66
  TERMINAL_ENDIF = 67
  TERMINAL_RPAREN = 68
  TERMINAL_EXCLAMATION_POINT = 69
  TERMINAL_GT = 70
  TERMINAL_CSOURCE = 71
  TERMINAL_RSHIFTEQ = 72
  TERMINAL_STRING_LITERAL = 73
  TERMINAL_SEPARATOR = 74
  terminal_str = {
    0: 'define',
    1: 'subeq',
    2: 'tilde',
    3: 'identifier',
    4: 'rshift',
    5: 'addeq',
    6: 'sub',
    7: 'elif',
    8: 'mod',
    9: 'modeq',
    10: 'pp_number',
    11: 'add',
    12: 'undef',
    13: 'line',
    14: 'elipsis',
    15: 'muleq',
    16: 'else',
    17: 'defined_separator',
    18: '_expr',
    19: 'semi',
    20: 'diveq',
    21: 'dot',
    22: 'div',
    23: 'colon',
    24: 'assign',
    25: 'lt',
    26: 'ampersand',
    27: 'decr',
    28: 'defined',
    29: 'questionmark',
    30: 'ifdef',
    31: 'poundpound',
    32: 'lshifteq',
    33: 'bitand',
    34: 'pound',
    35: 'or',
    36: 'mul',
    37: 'bitnot',
    38: 'comma',
    39: 'character_constant',
    40: 'and',
    41: 'bitor',
    42: 'if',
    43: 'lbrace',
    44: 'pragma',
    45: 'header_global',
    46: 'gteq',
    47: 'ifndef',
    48: 'neq',
    49: 'bitxor',
    50: 'rbrace',
    51: 'header_local',
    52: 'lshift',
    53: 'eq',
    54: 'bitoreq',
    55: 'lsquare',
    56: 'incr',
    57: 'lteq',
    58: 'define_function',
    59: 'bitxoreq',
    60: 'rsquare',
    61: 'include',
    62: 'error',
    63: 'arrow',
    64: 'bitandeq',
    65: 'lparen',
    66: 'warning',
    67: 'endif',
    68: 'rparen',
    69: 'exclamation_point',
    70: 'gt',
    71: 'csource',
    72: 'rshifteq',
    73: 'string_literal',
    74: 'separator',
  }
  nonterminal_str = {
    75: 'if_section',
    76: 'defined_identifier',
    77: 'elipsis_opt',
    78: '_gen6',
    79: 'define_line',
    80: 'elseif_part',
    81: 'error_line',
    82: '_gen3',
    83: 'include_type',
    84: '_expr',
    85: '_gen4',
    86: 'pp_nodes_list',
    87: 'pp_directive',
    88: 'warning_line',
    89: 'if_part',
    90: 'define_func_param',
    91: 'pragma_line',
    92: '_gen2',
    93: 'pp_file',
    94: 'pp_tokens',
    95: 'include_line',
    96: '_gen0',
    97: '_gen1',
    98: 'else_part',
    99: 'control_line',
    100: 'punctuator',
    101: 'undef_line',
    102: 'replacement_list',
    103: 'line_line',
    104: '_gen5',
    105: 'pp_nodes',
  }
  str_terminal = {
    'define': 0,
    'subeq': 1,
    'tilde': 2,
    'identifier': 3,
    'rshift': 4,
    'addeq': 5,
    'sub': 6,
    'elif': 7,
    'mod': 8,
    'modeq': 9,
    'pp_number': 10,
    'add': 11,
    'undef': 12,
    'line': 13,
    'elipsis': 14,
    'muleq': 15,
    'else': 16,
    'defined_separator': 17,
    '_expr': 18,
    'semi': 19,
    'diveq': 20,
    'dot': 21,
    'div': 22,
    'colon': 23,
    'assign': 24,
    'lt': 25,
    'ampersand': 26,
    'decr': 27,
    'defined': 28,
    'questionmark': 29,
    'ifdef': 30,
    'poundpound': 31,
    'lshifteq': 32,
    'bitand': 33,
    'pound': 34,
    'or': 35,
    'mul': 36,
    'bitnot': 37,
    'comma': 38,
    'character_constant': 39,
    'and': 40,
    'bitor': 41,
    'if': 42,
    'lbrace': 43,
    'pragma': 44,
    'header_global': 45,
    'gteq': 46,
    'ifndef': 47,
    'neq': 48,
    'bitxor': 49,
    'rbrace': 50,
    'header_local': 51,
    'lshift': 52,
    'eq': 53,
    'bitoreq': 54,
    'lsquare': 55,
    'incr': 56,
    'lteq': 57,
    'define_function': 58,
    'bitxoreq': 59,
    'rsquare': 60,
    'include': 61,
    'error': 62,
    'arrow': 63,
    'bitandeq': 64,
    'lparen': 65,
    'warning': 66,
    'endif': 67,
    'rparen': 68,
    'exclamation_point': 69,
    'gt': 70,
    'csource': 71,
    'rshifteq': 72,
    'string_literal': 73,
    'separator': 74,
  }
  str_nonterminal = {
    'if_section': 75,
    'defined_identifier': 76,
    'elipsis_opt': 77,
    '_gen6': 78,
    'define_line': 79,
    'elseif_part': 80,
    'error_line': 81,
    '_gen3': 82,
    'include_type': 83,
    '_expr': 84,
    '_gen4': 85,
    'pp_nodes_list': 86,
    'pp_directive': 87,
    'warning_line': 88,
    'if_part': 89,
    'define_func_param': 90,
    'pragma_line': 91,
    '_gen2': 92,
    'pp_file': 93,
    'pp_tokens': 94,
    'include_line': 95,
    '_gen0': 96,
    '_gen1': 97,
    'else_part': 98,
    'control_line': 99,
    'punctuator': 100,
    'undef_line': 101,
    'replacement_list': 102,
    'line_line': 103,
    '_gen5': 104,
    'pp_nodes': 105,
  }
  terminal_count = 75
  nonterminal_count = 31
  parse_table = [
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 76, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 76, -1, -1, -1, -1, 76, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 91, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 36, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 34, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 136, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [22, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 2, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, 56, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 26, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 16, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 119, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 6, -1, -1, -1, -1, -1, 51, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, 122, 122, 122, 122, 122, 122, -1, 122, 122, 122, 122, -1, -1, 122, 122, -1, 122, -1, 122, 122, 122, 122, 122, 122, 122, 122, 122, 122, 122, -1, 122, 122, 122, 122, 122, 122, 122, 122, 122, 122, 122, -1, 122, -1, 122, 122, -1, 122, 122, 122, 122, 122, 122, 122, 122, 122, 122, -1, 122, 122, -1, -1, 122, 122, 122, -1, -1, 122, 122, 122, -1, 122, 122, 45],
    [129, -1, -1, -1, -1, -1, -1, 118, -1, -1, -1, -1, 129, 129, -1, -1, 118, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 129, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 129, -1, 129, -1, -1, 129, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 129, -1, -1, 129, 129, -1, -1, -1, 129, 118, -1, -1, -1, 129, -1, -1, -1],
    [3, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 3, 3, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 87, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 87, -1, 3, -1, -1, 87, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 3, -1, -1, 3, 3, -1, -1, -1, 3, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 38, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 139, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 7, -1, -1, -1, -1, 107, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 104, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 59, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 111, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 12, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 12, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 108, -1, -1, -1, -1, -1, -1],
    [19, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 19, 19, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 19, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 19, -1, 19, -1, -1, 19, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 19, -1, -1, 19, 19, -1, -1, -1, 19, -1, -1, -1, -1, 19, -1, -1, -1],
    [-1, 29, 29, 121, 29, 29, 29, -1, 29, 29, 79, 29, -1, -1, 29, 29, -1, 133, -1, 29, 29, 29, 29, 29, 29, 29, 29, 29, 134, 29, -1, 29, 29, 29, 29, 29, 29, 29, 29, 83, 29, 29, -1, 29, -1, 78, 29, -1, 29, 29, 29, 97, 29, 29, 29, 29, 29, 29, -1, 29, 29, -1, -1, 29, 29, 29, -1, -1, 29, 29, 29, -1, 29, 30, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 124, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [33, -1, -1, -1, -1, -1, -1, 37, -1, -1, -1, -1, 33, 33, -1, -1, 37, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 33, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 33, -1, 33, -1, -1, 33, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 33, -1, -1, 33, 33, -1, -1, -1, 33, 37, -1, -1, -1, 33, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, 72, -1, -1, -1, -1, -1, -1, -1, -1, 62, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 69, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 132, -1, -1, -1, -1, -1, -1, -1],
    [80, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 94, 32, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 15, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 80, -1, -1, 116, 28, -1, -1, -1, 71, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, 18, 24, -1, 27, 53, 35, -1, 39, 43, -1, 46, -1, -1, 52, 81, -1, -1, -1, 88, 0, 58, 60, 8, 65, 4, 93, 13, -1, 10, -1, 31, 67, 42, 47, 54, 63, 57, 61, -1, 64, 66, -1, 74, -1, -1, 128, -1, 84, 20, 90, -1, 17, 5, 102, 137, 40, 9, -1, 114, 105, -1, -1, 85, 130, 73, -1, -1, 49, 11, 89, -1, 92, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 127, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, 86, 86, 86, 86, 86, 86, -1, 86, 86, 86, 86, -1, -1, 86, 86, -1, 86, -1, 86, 86, 86, 86, 86, 86, 86, 86, 86, 86, 86, -1, 86, 86, 86, 86, 86, 86, 86, 86, 86, 86, 86, -1, 86, -1, 86, 86, -1, 86, 86, 86, 86, 86, 86, 86, 86, 86, 86, -1, 86, 86, -1, -1, 86, 86, 86, -1, -1, 86, 86, 86, -1, 86, 86, 86],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 70, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 21, -1, -1, -1, -1, -1, -1, 21, -1, -1, -1, -1, -1, -1, -1, 21, -1, -1, -1, -1, -1, -1, -1, -1, -1, 21, -1, -1, -1, -1, -1, -1, -1, -1, 21, -1, 21, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 21, -1, -1, -1, 21, -1, -1, -1, 21, -1],
    [41, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 41, 41, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 41, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 41, -1, 41, -1, -1, 41, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 41, -1, -1, 41, 41, -1, -1, -1, 41, -1, -1, -1, -1, 68, -1, -1, -1],
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
      raise SyntaxError('Unexpected symbol when parsing %s.  Expected %s, got %s.' %(whosdaddy(), self.terminal_str[s], self.sym if self.sym else 'None'), tracer)
  def rule(self, n):
    if self.sym == None: return -1
    return self.parse_table[n - 75][self.sym.getId()]
  def call(self, nt_str):
    return getattr(self, nt_str)()
  def _IF_SECTION(self, depth=0, tracer=None):
    rule = self.rule(75)
    tree = ParseTree( NonTerminal(75, self.getAtomString(75)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 76:
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
      t = self.expect(67, tracer) # endif
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _DEFINED_IDENTIFIER(self, depth=0, tracer=None):
    rule = self.rule(76)
    tree = ParseTree( NonTerminal(76, self.getAtomString(76)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 36:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(65, tracer) # lparen
      tree.add(t)
      t = self.expect(3, tracer) # identifier
      tree.add(t)
      t = self.expect(68, tracer) # rparen
      tree.add(t)
      return tree
    elif rule == 91:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(3, tracer) # identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _ELIPSIS_OPT(self, depth=0, tracer=None):
    rule = self.rule(77)
    tree = ParseTree( NonTerminal(77, self.getAtomString(77)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 34:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(38, tracer) # comma
      tree.add(t)
      t = self.expect(14, tracer) # elipsis
      tree.add(t)
      return tree
    return tree
  def __GEN6(self, depth=0, tracer=None):
    rule = self.rule(78)
    tree = ParseTree( NonTerminal(78, self.getAtomString(78)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 136:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(38, tracer) # comma
      tree.add(t)
      tree.listSeparator = t
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
  def _DEFINE_LINE(self, depth=0, tracer=None):
    rule = self.rule(79)
    tree = ParseTree( NonTerminal(79, self.getAtomString(79)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 2:
      tree.astTransform = AstTransformNodeCreator('DefineFunction', {'body': 5, 'ident': 1, 'params': 3})
      t = self.expect(58, tracer) # define_function
      tree.add(t)
      t = self.expect(3, tracer) # identifier
      tree.add(t)
      t = self.expect(65, tracer) # lparen
      tree.add(t)
      subtree = self.__GEN2(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(68, tracer) # rparen
      tree.add(t)
      subtree = self._REPLACEMENT_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 22:
      tree.astTransform = AstTransformNodeCreator('Define', {'body': 2, 'ident': 1})
      t = self.expect(0, tracer) # define
      tree.add(t)
      t = self.expect(3, tracer) # identifier
      tree.add(t)
      subtree = self._REPLACEMENT_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _ELSEIF_PART(self, depth=0, tracer=None):
    rule = self.rule(80)
    tree = ParseTree( NonTerminal(80, self.getAtomString(80)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 56:
      tree.astTransform = AstTransformNodeCreator('ElseIf', {'expr': 1, 'nodes': 2})
      t = self.expect(7, tracer) # elif
      tree.add(t)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._PP_NODES_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _ERROR_LINE(self, depth=0, tracer=None):
    rule = self.rule(81)
    tree = ParseTree( NonTerminal(81, self.getAtomString(81)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 26:
      tree.astTransform = AstTransformNodeCreator('Error', {'tokens': 1})
      t = self.expect(62, tracer) # error
      tree.add(t)
      subtree = self.__GEN4(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN3(self, depth=0, tracer=None):
    rule = self.rule(82)
    tree = ParseTree( NonTerminal(82, self.getAtomString(82)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [68]):
      return tree
    if self.sym == None:
      return tree
    if rule == 16:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(38, tracer) # comma
      tree.add(t)
      tree.listSeparator = t
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
  def _INCLUDE_TYPE(self, depth=0, tracer=None):
    rule = self.rule(83)
    tree = ParseTree( NonTerminal(83, self.getAtomString(83)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 1:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(3, tracer) # identifier
      tree.add(t)
      return tree
    elif rule == 6:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(45, tracer) # header_global
      tree.add(t)
      return tree
    elif rule == 51:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(51, tracer) # header_local
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN4(self, depth=0, tracer=None):
    rule = self.rule(85)
    tree = ParseTree( NonTerminal(85, self.getAtomString(85)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [74]):
      return tree
    if self.sym == None:
      return tree
    if rule == 122:
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
  def _PP_NODES_LIST(self, depth=0, tracer=None):
    rule = self.rule(86)
    tree = ParseTree( NonTerminal(86, self.getAtomString(86)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [-1, 7, 16, 67]):
      return tree
    if self.sym == None:
      return tree
    if rule == 129:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN0(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _PP_DIRECTIVE(self, depth=0, tracer=None):
    rule = self.rule(87)
    tree = ParseTree( NonTerminal(87, self.getAtomString(87)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 3:
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
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _WARNING_LINE(self, depth=0, tracer=None):
    rule = self.rule(88)
    tree = ParseTree( NonTerminal(88, self.getAtomString(88)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 38:
      tree.astTransform = AstTransformNodeCreator('Warning', {'tokens': 1})
      t = self.expect(66, tracer) # warning
      tree.add(t)
      subtree = self.__GEN4(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _IF_PART(self, depth=0, tracer=None):
    rule = self.rule(89)
    tree = ParseTree( NonTerminal(89, self.getAtomString(89)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 7:
      tree.astTransform = AstTransformNodeCreator('If', {'expr': 1, 'nodes': 2})
      t = self.expect(42, tracer) # if
      tree.add(t)
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._PP_NODES_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 107:
      tree.astTransform = AstTransformNodeCreator('IfNDef', {'nodes': 2, 'ident': 1})
      t = self.expect(47, tracer) # ifndef
      tree.add(t)
      t = self.expect(3, tracer) # identifier
      tree.add(t)
      subtree = self._PP_NODES_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 139:
      tree.astTransform = AstTransformNodeCreator('IfDef', {'nodes': 2, 'ident': 1})
      t = self.expect(30, tracer) # ifdef
      tree.add(t)
      t = self.expect(3, tracer) # identifier
      tree.add(t)
      subtree = self._PP_NODES_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _DEFINE_FUNC_PARAM(self, depth=0, tracer=None):
    rule = self.rule(90)
    tree = ParseTree( NonTerminal(90, self.getAtomString(90)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 59:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(14, tracer) # elipsis
      tree.add(t)
      return tree
    elif rule == 104:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(3, tracer) # identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _PRAGMA_LINE(self, depth=0, tracer=None):
    rule = self.rule(91)
    tree = ParseTree( NonTerminal(91, self.getAtomString(91)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 111:
      tree.astTransform = AstTransformNodeCreator('Pragma', {'tokens': 1})
      t = self.expect(44, tracer) # pragma
      tree.add(t)
      subtree = self.__GEN4(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN2(self, depth=0, tracer=None):
    rule = self.rule(92)
    tree = ParseTree( NonTerminal(92, self.getAtomString(92)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [68]):
      return tree
    if self.sym == None:
      return tree
    if rule == 12:
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
  def _PP_FILE(self, depth=0, tracer=None):
    rule = self.rule(93)
    tree = ParseTree( NonTerminal(93, self.getAtomString(93)), tracer )
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 19:
      tree.astTransform = AstTransformNodeCreator('PPFile', {'nodes': 0})
      subtree = self._PP_NODES_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _PP_TOKENS(self, depth=0, tracer=None):
    rule = self.rule(94)
    tree = ParseTree( NonTerminal(94, self.getAtomString(94)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 29:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PUNCTUATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 30:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(73, tracer) # string_literal
      tree.add(t)
      return tree
    elif rule == 78:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(45, tracer) # header_global
      tree.add(t)
      return tree
    elif rule == 79:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(10, tracer) # pp_number
      tree.add(t)
      return tree
    elif rule == 83:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(39, tracer) # character_constant
      tree.add(t)
      return tree
    elif rule == 97:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(51, tracer) # header_local
      tree.add(t)
      return tree
    elif rule == 121:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(3, tracer) # identifier
      tree.add(t)
      return tree
    elif rule == 133:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(17, tracer) # defined_separator
      tree.add(t)
      return tree
    elif rule == 134:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(28, tracer) # defined
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _INCLUDE_LINE(self, depth=0, tracer=None):
    rule = self.rule(95)
    tree = ParseTree( NonTerminal(95, self.getAtomString(95)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 124:
      tree.astTransform = AstTransformNodeCreator('Include', {'file': 1})
      t = self.expect(61, tracer) # include
      tree.add(t)
      subtree = self._INCLUDE_TYPE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN0(self, depth=0, tracer=None):
    rule = self.rule(96)
    tree = ParseTree( NonTerminal(96, self.getAtomString(96)), tracer )
    tree.list = 'tlist'
    if self.sym != None and (self.sym.getId() in [-1, 67, 16, 7]):
      return tree
    if self.sym == None:
      return tree
    if rule == 33:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PP_NODES(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(74, tracer) # separator
      tree.add(t)
      subtree = self.__GEN0(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN1(self, depth=0, tracer=None):
    rule = self.rule(97)
    tree = ParseTree( NonTerminal(97, self.getAtomString(97)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [16]):
      return tree
    if self.sym == None:
      return tree
    if rule == 72:
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
  def _ELSE_PART(self, depth=0, tracer=None):
    rule = self.rule(98)
    tree = ParseTree( NonTerminal(98, self.getAtomString(98)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [67]):
      return tree
    if self.sym == None:
      return tree
    if rule == 69:
      tree.astTransform = AstTransformNodeCreator('Else', {'nodes': 1})
      t = self.expect(16, tracer) # else
      tree.add(t)
      subtree = self._PP_NODES_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _CONTROL_LINE(self, depth=0, tracer=None):
    rule = self.rule(99)
    tree = ParseTree( NonTerminal(99, self.getAtomString(99)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 15:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PRAGMA_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 28:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ERROR_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 32:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._LINE_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 71:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._WARNING_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 80:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DEFINE_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 94:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._UNDEF_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 116:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._INCLUDE_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _PUNCTUATOR(self, depth=0, tracer=None):
    rule = self.rule(100)
    tree = ParseTree( NonTerminal(100, self.getAtomString(100)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 0:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(20, tracer) # diveq
      tree.add(t)
      return tree
    elif rule == 4:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(25, tracer) # lt
      tree.add(t)
      return tree
    elif rule == 5:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(53, tracer) # eq
      tree.add(t)
      return tree
    elif rule == 8:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(23, tracer) # colon
      tree.add(t)
      return tree
    elif rule == 9:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(57, tracer) # lteq
      tree.add(t)
      return tree
    elif rule == 10:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(29, tracer) # questionmark
      tree.add(t)
      return tree
    elif rule == 11:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(69, tracer) # exclamation_point
      tree.add(t)
      return tree
    elif rule == 13:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(27, tracer) # decr
      tree.add(t)
      return tree
    elif rule == 17:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(52, tracer) # lshift
      tree.add(t)
      return tree
    elif rule == 18:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(1, tracer) # subeq
      tree.add(t)
      return tree
    elif rule == 20:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(49, tracer) # bitxor
      tree.add(t)
      return tree
    elif rule == 24:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(2, tracer) # tilde
      tree.add(t)
      return tree
    elif rule == 27:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(4, tracer) # rshift
      tree.add(t)
      return tree
    elif rule == 31:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(31, tracer) # poundpound
      tree.add(t)
      return tree
    elif rule == 35:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(6, tracer) # sub
      tree.add(t)
      return tree
    elif rule == 39:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(8, tracer) # mod
      tree.add(t)
      return tree
    elif rule == 40:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(56, tracer) # incr
      tree.add(t)
      return tree
    elif rule == 42:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(33, tracer) # bitand
      tree.add(t)
      return tree
    elif rule == 43:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(9, tracer) # modeq
      tree.add(t)
      return tree
    elif rule == 46:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(11, tracer) # add
      tree.add(t)
      return tree
    elif rule == 47:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(34, tracer) # pound
      tree.add(t)
      return tree
    elif rule == 49:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(68, tracer) # rparen
      tree.add(t)
      return tree
    elif rule == 52:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(14, tracer) # elipsis
      tree.add(t)
      return tree
    elif rule == 53:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(5, tracer) # addeq
      tree.add(t)
      return tree
    elif rule == 54:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(35, tracer) # or
      tree.add(t)
      return tree
    elif rule == 57:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(37, tracer) # bitnot
      tree.add(t)
      return tree
    elif rule == 58:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(21, tracer) # dot
      tree.add(t)
      return tree
    elif rule == 60:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(22, tracer) # div
      tree.add(t)
      return tree
    elif rule == 61:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(38, tracer) # comma
      tree.add(t)
      return tree
    elif rule == 63:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(36, tracer) # mul
      tree.add(t)
      return tree
    elif rule == 64:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(40, tracer) # and
      tree.add(t)
      return tree
    elif rule == 65:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(24, tracer) # assign
      tree.add(t)
      return tree
    elif rule == 66:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(41, tracer) # bitor
      tree.add(t)
      return tree
    elif rule == 67:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(32, tracer) # lshifteq
      tree.add(t)
      return tree
    elif rule == 73:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(65, tracer) # lparen
      tree.add(t)
      return tree
    elif rule == 74:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(43, tracer) # lbrace
      tree.add(t)
      return tree
    elif rule == 81:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(15, tracer) # muleq
      tree.add(t)
      return tree
    elif rule == 84:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(48, tracer) # neq
      tree.add(t)
      return tree
    elif rule == 85:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(63, tracer) # arrow
      tree.add(t)
      return tree
    elif rule == 88:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(19, tracer) # semi
      tree.add(t)
      return tree
    elif rule == 89:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(70, tracer) # gt
      tree.add(t)
      return tree
    elif rule == 90:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(50, tracer) # rbrace
      tree.add(t)
      return tree
    elif rule == 92:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(72, tracer) # rshifteq
      tree.add(t)
      return tree
    elif rule == 93:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(26, tracer) # ampersand
      tree.add(t)
      return tree
    elif rule == 102:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(54, tracer) # bitoreq
      tree.add(t)
      return tree
    elif rule == 105:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(60, tracer) # rsquare
      tree.add(t)
      return tree
    elif rule == 114:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(59, tracer) # bitxoreq
      tree.add(t)
      return tree
    elif rule == 128:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(46, tracer) # gteq
      tree.add(t)
      return tree
    elif rule == 130:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(64, tracer) # bitandeq
      tree.add(t)
      return tree
    elif rule == 137:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(55, tracer) # lsquare
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _UNDEF_LINE(self, depth=0, tracer=None):
    rule = self.rule(101)
    tree = ParseTree( NonTerminal(101, self.getAtomString(101)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 127:
      tree.astTransform = AstTransformNodeCreator('Undef', {'ident': 1})
      t = self.expect(12, tracer) # undef
      tree.add(t)
      t = self.expect(3, tracer) # identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def _REPLACEMENT_LIST(self, depth=0, tracer=None):
    rule = self.rule(102)
    tree = ParseTree( NonTerminal(102, self.getAtomString(102)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() in [74]):
      return tree
    if self.sym == None:
      return tree
    if rule == 86:
      tree.astTransform = AstTransformNodeCreator('ReplacementList', {'tokens': 0})
      subtree = self.__GEN4(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _LINE_LINE(self, depth=0, tracer=None):
    rule = self.rule(103)
    tree = ParseTree( NonTerminal(103, self.getAtomString(103)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 70:
      tree.astTransform = AstTransformNodeCreator('Line', {'tokens': 1})
      t = self.expect(13, tracer) # line
      tree.add(t)
      subtree = self.__GEN4(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  def __GEN5(self, depth=0, tracer=None):
    rule = self.rule(104)
    tree = ParseTree( NonTerminal(104, self.getAtomString(104)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 21:
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
    rule = self.rule(105)
    tree = ParseTree( NonTerminal(105, self.getAtomString(105)), tracer )
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 41:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PP_DIRECTIVE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 68:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(71, tracer) # csource
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()), tracer)
  infixBp0 = {
    4: 10000,
    6: 11000,
    8: 12000,
    11: 11000,
    17: 14000,
    22: 12000,
    25: 9000,
    29: 2000,
    33: 5000,
    35: 3000,
    36: 12000,
    38: 1000,
    40: 4000,
    41: 7000,
    46: 9000,
    48: 8000,
    49: 6000,
    52: 10000,
    53: 8000,
    57: 9000,
    65: 15000,
    70: 9000,
  }
  prefixBp0 = {
    6: 13000,
    28: 13000,
    33: 13000,
    36: 13000,
    37: 13000,
    69: 13000,
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
    tree = ParseTree( NonTerminal(84, '_expr') )
    if not self.sym:
      return tree
    elif self.sym.getId() in [39]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      return self.expect( 39, tracer )
    elif self.sym.getId() in [69]:
      tree.astTransform = AstTransformNodeCreator('Not', {'expr': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(69, tracer) )
      tree.add( self.__EXPR( self.prefixBp0[69] ) )
      tree.isPrefix = True
    elif self.sym.getId() in [3]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      return self.expect( 3, tracer )
    elif self.sym.getId() in [73]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      return self.expect( 73, tracer )
    elif self.sym.getId() in [10]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      return self.expect( 10, tracer )
    elif self.sym.getId() in [3]:
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      tree.nudMorphemeCount = 1
      return self.expect( 3, tracer )
    elif self.sym.getId() in [37]:
      tree.astTransform = AstTransformNodeCreator('BitNOT', {'expr': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(37, tracer) )
      tree.add( self.__EXPR( self.prefixBp0[37] ) )
      tree.isPrefix = True
    elif self.sym.getId() in [28]:
      tree.astTransform = AstTransformNodeCreator('IsDefined', {'expr': 2})
      tree.nudMorphemeCount = 1
      return self.expect( 28, tracer )
    elif self.sym.getId() in [65]:
      tree.astTransform = AstTransformSubstitution(1)
      tree.nudMorphemeCount = 3
      tree.add( self.expect(65, tracer) )
      tree.add( self.__EXPR() )
      tree.add( self.expect(68, tracer) )
    return tree
  def led0(self, left, tracer):
    tree = ParseTree( NonTerminal(84, '_expr') )
    if  self.sym.getId() == 57: # 'lteq'
      tree.astTransform = AstTransformNodeCreator('LessThanEq', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(57, tracer) )
      modifier = 0
      tree.add( self.__EXPR( self.infixBp0[57] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 17: # 'defined_separator'
      tree.astTransform = AstTransformNodeCreator('IsDefined', {'expr': 2})
      if left:
        tree.add(left)
      tree.add( self.expect(17, tracer) )
      tree.add( self._DEFINED_IDENTIFIER() )
    elif  self.sym.getId() == 41: # 'bitor'
      tree.astTransform = AstTransformNodeCreator('BitOR', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(41, tracer) )
      modifier = 0
      tree.add( self.__EXPR( self.infixBp0[41] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 48: # 'neq'
      tree.astTransform = AstTransformNodeCreator('NotEquals', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(48, tracer) )
      modifier = 1
      tree.add( self.__EXPR( self.infixBp0[48] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 46: # 'gteq'
      tree.astTransform = AstTransformNodeCreator('GreaterThanEq', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(46, tracer) )
      modifier = 0
      tree.add( self.__EXPR( self.infixBp0[46] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 11: # 'add'
      tree.astTransform = AstTransformNodeCreator('Add', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(11, tracer) )
      modifier = 0
      tree.add( self.__EXPR( self.infixBp0[11] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 65: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(65, tracer) )
      tree.add( self.__GEN5() )
      tree.add( self.expect(68, tracer) )
    elif  self.sym.getId() == 49: # 'bitxor'
      tree.astTransform = AstTransformNodeCreator('BitXOR', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(49, tracer) )
      modifier = 0
      tree.add( self.__EXPR( self.infixBp0[49] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 38: # 'comma'
      tree.astTransform = AstTransformNodeCreator('Comma', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(38, tracer) )
      modifier = 0
      tree.add( self.__EXPR( self.infixBp0[38] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 36: # 'mul'
      tree.astTransform = AstTransformNodeCreator('Mul', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(36, tracer) )
      modifier = 0
      tree.add( self.__EXPR( self.infixBp0[36] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 6: # 'sub'
      tree.astTransform = AstTransformNodeCreator('Sub', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(6, tracer) )
      modifier = 0
      tree.add( self.__EXPR( self.infixBp0[6] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 52: # 'lshift'
      tree.astTransform = AstTransformNodeCreator('LeftShift', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(52, tracer) )
      modifier = 0
      tree.add( self.__EXPR( self.infixBp0[52] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 29: # 'questionmark'
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(29, tracer) )
      modifier = 1
      tree.add( self.__EXPR( self.infixBp0[29] - modifier ) )
      tree.add( self.expect(23, tracer) )
      modifier = 1
      tree.add( self.__EXPR( self.infixBp0[29] - modifier ) )
    elif  self.sym.getId() == 22: # 'div'
      tree.astTransform = AstTransformNodeCreator('Div', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(22, tracer) )
      modifier = 0
      tree.add( self.__EXPR( self.infixBp0[22] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 25: # 'lt'
      tree.astTransform = AstTransformNodeCreator('LessThan', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(25, tracer) )
      modifier = 0
      tree.add( self.__EXPR( self.infixBp0[25] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 40: # 'and'
      tree.astTransform = AstTransformNodeCreator('And', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(40, tracer) )
      modifier = 0
      tree.add( self.__EXPR( self.infixBp0[40] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 4: # 'rshift'
      tree.astTransform = AstTransformNodeCreator('RightShift', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(4, tracer) )
      modifier = 0
      tree.add( self.__EXPR( self.infixBp0[4] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 8: # 'mod'
      tree.astTransform = AstTransformNodeCreator('Mod', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(8, tracer) )
      modifier = 0
      tree.add( self.__EXPR( self.infixBp0[8] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 70: # 'gt'
      tree.astTransform = AstTransformNodeCreator('GreaterThan', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(70, tracer) )
      modifier = 0
      tree.add( self.__EXPR( self.infixBp0[70] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 35: # 'or'
      tree.astTransform = AstTransformNodeCreator('Or', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(35, tracer) )
      modifier = 0
      tree.add( self.__EXPR( self.infixBp0[35] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 33: # 'bitand'
      tree.astTransform = AstTransformNodeCreator('BitAND', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(33, tracer) )
      modifier = 0
      tree.add( self.__EXPR( self.infixBp0[33] - modifier ) )
      tree.isInfix = True
    elif  self.sym.getId() == 53: # 'eq'
      tree.astTransform = AstTransformNodeCreator('Equals', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(53, tracer) )
      modifier = 1
      tree.add( self.__EXPR( self.infixBp0[53] - modifier ) )
      tree.isInfix = True
    return tree
