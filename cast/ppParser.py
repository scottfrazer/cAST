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
  TERMINAL_ADD = 1
  TERMINAL_ADDEQ = 38
  TERMINAL_AMPERSAND = 10
  TERMINAL_AND = 27
  TERMINAL_ARROW = 17
  TERMINAL_ASSIGN = 15
  TERMINAL_BITAND = 28
  TERMINAL_BITANDEQ = 72
  TERMINAL_BITNOT = 32
  TERMINAL_BITOR = 9
  TERMINAL_BITOREQ = 43
  TERMINAL_BITXOR = 35
  TERMINAL_BITXOREQ = 52
  TERMINAL_CHARACTER_CONSTANT = 63
  TERMINAL_COLON = 20
  TERMINAL_COMMA = 55
  TERMINAL_CSOURCE = 14
  TERMINAL_DECR = 44
  TERMINAL_DEFINE = 71
  TERMINAL_DEFINE_FUNCTION = 34
  TERMINAL_DEFINED = 30
  TERMINAL_DEFINED_SEPARATOR = 42
  TERMINAL_DIV = 68
  TERMINAL_DOT = 22
  TERMINAL_ELIF = 0
  TERMINAL_ELIPSIS = 12
  TERMINAL_ELSE = 18
  TERMINAL_ENDIF = 60
  TERMINAL_EQ = 45
  TERMINAL_ERROR = 53
  TERMINAL_EXCLAMATION_POINT = 54
  TERMINAL_GT = 57
  TERMINAL_GTEQ = 56
  TERMINAL_HEADER_GLOBAL = 36
  TERMINAL_HEADER_LOCAL = 41
  TERMINAL_IDENTIFIER = 51
  TERMINAL_IF = 66
  TERMINAL_IFDEF = 58
  TERMINAL_IFNDEF = 46
  TERMINAL_INCLUDE = 37
  TERMINAL_INCR = 4
  TERMINAL_LBRACE = 25
  TERMINAL_LINE = 65
  TERMINAL_LPAREN = 13
  TERMINAL_LSHIFT = 2
  TERMINAL_LSHIFTEQ = 31
  TERMINAL_LSQUARE = 33
  TERMINAL_LT = 70
  TERMINAL_LTEQ = 11
  TERMINAL_MOD = 3
  TERMINAL_MODEQ = 7
  TERMINAL_MUL = 5
  TERMINAL_MULEQ = 62
  TERMINAL_NEQ = 40
  TERMINAL_OR = 23
  TERMINAL_POUND = 26
  TERMINAL_POUNDPOUND = 19
  TERMINAL_PP_NUMBER = 8
  TERMINAL_PRAGMA = 47
  TERMINAL_QUESTIONMARK = 24
  TERMINAL_RBRACE = 29
  TERMINAL_RPAREN = 50
  TERMINAL_RSHIFT = 6
  TERMINAL_RSHIFTEQ = 48
  TERMINAL_RSQUARE = 39
  TERMINAL_SEMI = 16
  TERMINAL_SEPARATOR = 21
  TERMINAL_STRING_LITERAL = 69
  TERMINAL_SUB = 67
  TERMINAL_SUBEQ = 49
  TERMINAL_TILDE = 61
  TERMINAL_UNDEF = 64
  TERMINAL_WARNING = 59
  terminal_str = {
    1: 'add',
    38: 'addeq',
    10: 'ampersand',
    27: 'and',
    17: 'arrow',
    15: 'assign',
    28: 'bitand',
    72: 'bitandeq',
    32: 'bitnot',
    9: 'bitor',
    43: 'bitoreq',
    35: 'bitxor',
    52: 'bitxoreq',
    63: 'character_constant',
    20: 'colon',
    55: 'comma',
    14: 'csource',
    44: 'decr',
    71: 'define',
    34: 'define_function',
    30: 'defined',
    42: 'defined_separator',
    68: 'div',
    22: 'dot',
    0: 'elif',
    12: 'elipsis',
    18: 'else',
    60: 'endif',
    45: 'eq',
    53: 'error',
    54: 'exclamation_point',
    57: 'gt',
    56: 'gteq',
    36: 'header_global',
    41: 'header_local',
    51: 'identifier',
    66: 'if',
    58: 'ifdef',
    46: 'ifndef',
    37: 'include',
    4: 'incr',
    25: 'lbrace',
    65: 'line',
    13: 'lparen',
    2: 'lshift',
    31: 'lshifteq',
    33: 'lsquare',
    70: 'lt',
    11: 'lteq',
    3: 'mod',
    7: 'modeq',
    5: 'mul',
    62: 'muleq',
    40: 'neq',
    23: 'or',
    26: 'pound',
    19: 'poundpound',
    8: 'pp_number',
    47: 'pragma',
    24: 'questionmark',
    29: 'rbrace',
    50: 'rparen',
    6: 'rshift',
    48: 'rshifteq',
    39: 'rsquare',
    16: 'semi',
    21: 'separator',
    69: 'string_literal',
    67: 'sub',
    49: 'subeq',
    61: 'tilde',
    64: 'undef',
    59: 'warning',
  }
  nonterminal_str = {
    103: '_expr',
    101: '_gen0',
    92: '_gen1',
    83: '_gen2',
    76: '_gen3',
    77: '_gen4',
    74: '_gen5',
    95: '_gen6',
    85: 'control_line',
    80: 'define_func_param',
    100: 'define_line',
    75: 'defined_identifier',
    84: 'elipsis_opt',
    98: 'else_part',
    102: 'elseif_part',
    73: 'error_line',
    104: 'identifier',
    89: 'if_part',
    86: 'if_section',
    97: 'include_line',
    94: 'include_type',
    88: 'line_line',
    96: 'pp_directive',
    93: 'pp_file',
    78: 'pp_nodes',
    87: 'pp_nodes_list',
    81: 'pp_tokens',
    90: 'pragma_line',
    91: 'punctuator',
    82: 'replacement_list',
    99: 'undef_line',
    79: 'warning_line',
  }
  str_terminal = {
    'add': 1,
    'addeq': 38,
    'ampersand': 10,
    'and': 27,
    'arrow': 17,
    'assign': 15,
    'bitand': 28,
    'bitandeq': 72,
    'bitnot': 32,
    'bitor': 9,
    'bitoreq': 43,
    'bitxor': 35,
    'bitxoreq': 52,
    'character_constant': 63,
    'colon': 20,
    'comma': 55,
    'csource': 14,
    'decr': 44,
    'define': 71,
    'define_function': 34,
    'defined': 30,
    'defined_separator': 42,
    'div': 68,
    'dot': 22,
    'elif': 0,
    'elipsis': 12,
    'else': 18,
    'endif': 60,
    'eq': 45,
    'error': 53,
    'exclamation_point': 54,
    'gt': 57,
    'gteq': 56,
    'header_global': 36,
    'header_local': 41,
    'identifier': 51,
    'if': 66,
    'ifdef': 58,
    'ifndef': 46,
    'include': 37,
    'incr': 4,
    'lbrace': 25,
    'line': 65,
    'lparen': 13,
    'lshift': 2,
    'lshifteq': 31,
    'lsquare': 33,
    'lt': 70,
    'lteq': 11,
    'mod': 3,
    'modeq': 7,
    'mul': 5,
    'muleq': 62,
    'neq': 40,
    'or': 23,
    'pound': 26,
    'poundpound': 19,
    'pp_number': 8,
    'pragma': 47,
    'questionmark': 24,
    'rbrace': 29,
    'rparen': 50,
    'rshift': 6,
    'rshifteq': 48,
    'rsquare': 39,
    'semi': 16,
    'separator': 21,
    'string_literal': 69,
    'sub': 67,
    'subeq': 49,
    'tilde': 61,
    'undef': 64,
    'warning': 59,
  }
  str_nonterminal = {
    '_expr': 103,
    '_gen0': 101,
    '_gen1': 92,
    '_gen2': 83,
    '_gen3': 76,
    '_gen4': 77,
    '_gen5': 74,
    '_gen6': 95,
    'control_line': 85,
    'define_func_param': 80,
    'define_line': 100,
    'defined_identifier': 75,
    'elipsis_opt': 84,
    'else_part': 98,
    'elseif_part': 102,
    'error_line': 73,
    'identifier': 104,
    'if_part': 89,
    'if_section': 86,
    'include_line': 97,
    'include_type': 94,
    'line_line': 88,
    'pp_directive': 96,
    'pp_file': 93,
    'pp_nodes': 78,
    'pp_nodes_list': 87,
    'pp_tokens': 81,
    'pragma_line': 90,
    'punctuator': 91,
    'replacement_list': 82,
    'undef_line': 99,
    'warning_line': 79,
  }
  terminal_count = 73
  nonterminal_count = 32
  parse_table = [
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 86, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 3, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 72, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 44, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, 61, 61, 61, 61, 61, 61, 61, 61, 61, 61, 61, 61, 61, -1, 61, 61, 61, -1, 61, 61, -1, 61, 61, 61, 61, 61, 61, 61, 61, 61, 61, 61, 61, -1, 61, 61, -1, 61, 61, 61, 61, 61, 61, 61, 61, -1, -1, 61, 61, 61, 61, 61, -1, 61, 61, 61, 61, -1, -1, -1, 61, 61, 61, -1, -1, -1, 61, 61, 61, 61, -1, 61],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 12, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 48, -1, -1, 48, -1, -1, -1, -1, -1, -1, -1, -1, 48, 48, -1, -1, -1, -1, -1, 48, -1, -1, -1, -1, 48, 48, -1, -1, -1, -1, 48, 48, 48, -1, -1, -1, -1, 48, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 11, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 64, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 50, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, 79, 79, 79, 79, 79, 79, 79, 29, 79, 79, 79, 79, 79, -1, 79, 79, 79, -1, 79, 79, -1, 79, 79, 79, 79, 79, 79, 79, 79, 23, 79, 79, 79, -1, 79, 27, -1, 79, 79, 79, 19, 80, 79, 79, 79, -1, -1, 79, 79, 79, 56, 79, -1, 79, 79, 79, 79, -1, -1, -1, 79, 79, 76, -1, -1, -1, 79, 79, 62, 79, -1, 79],
  [-1, 111, 111, 111, 111, 111, 111, 111, 111, 111, 111, 111, 111, 111, -1, 111, 111, 111, -1, 111, 111, -1, 111, 111, 111, 111, 111, 111, 111, 111, 111, 111, 111, 111, -1, 111, 111, -1, 111, 111, 111, 111, 111, 111, 111, 111, -1, -1, 111, 111, 111, 111, 111, -1, 111, 111, 111, 111, -1, -1, -1, 111, 111, 111, -1, -1, -1, 111, 111, 111, 111, -1, 111],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 17, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 17, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 90, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 8, -1, -1, 2, -1, -1, -1, -1, -1, -1, -1, -1, -1, 94, -1, -1, -1, -1, -1, 93, -1, -1, -1, -1, -1, 5, -1, -1, -1, -1, 108, 66, -1, -1, -1, -1, -1, 8, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 52, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 52, -1, -1, -1, -1, -1, -1, -1, 52, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 105, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 105, -1, -1, 105, -1, -1, -1, -1, -1, -1, -1, -1, 105, 105, -1, -1, -1, -1, -1, 105, -1, -1, -1, -1, 105, 105, -1, -1, -1, -1, 105, 105, 105, -1, -1, -1, -1, 105, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 65, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 98, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 37, -1, -1, -1, -1, -1, -1, -1, 38, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 67, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, 110, 43, 95, 54, 109, 53, 41, -1, 6, 106, 36, 9, 42, -1, 26, 34, 28, -1, 88, 58, -1, 68, 71, 83, 49, 7, 25, 89, 0, 32, 24, 10, 15, -1, 30, -1, -1, 60, 40, 59, -1, -1, 100, 47, 73, -1, -1, 21, 78, 74, -1, 22, -1, 97, 69, 104, 39, -1, -1, -1, 63, 107, -1, -1, -1, -1, 35, 85, -1, 75, -1, 14],
  [91, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 102, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 102, -1, -1, 102, -1, -1, -1, -1, -1, -1, -1, -1, 102, 102, -1, -1, -1, -1, -1, 102, -1, -1, -1, -1, 102, 102, -1, -1, -1, -1, 102, 102, 102, -1, -1, -1, -1, 102, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 55, -1, -1, -1, -1, 70, -1, -1, -1, -1, -1, -1, -1, -1, -1, 18, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 82, -1, -1, 82, -1, -1, -1, -1, -1, -1, -1, -1, 96, 82, -1, -1, -1, -1, -1, 82, -1, -1, -1, -1, 96, 82, -1, -1, -1, -1, 82, 82, 96, -1, -1, -1, -1, 82, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 101, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 31, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 84, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 51, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 4, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 81, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 81, -1, -1, 81, -1, -1, -1, -1, -1, -1, -1, -1, 81, 81, -1, -1, -1, -1, -1, 81, -1, -1, -1, -1, 81, 81, -1, -1, -1, -1, 81, 81, 81, -1, -1, -1, -1, 81, -1],
  [45, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 103, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1]
  ]
  def terminal(self, str):
    return self.str_terminal[str]
  def terminalNames(self):
    return list(self.str_terminal.keys())
  def isTerminal(self, id):
    return 0 <= id <= 72
  def isNonTerminal(self, id):
    return 73 <= id <= 104
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
    return self.parse_table[n - 73][self.sym.getId()]
  def call(self, nt_str):
    return getattr(self, nt_str)()
  def __GEN0(self, depth = 0):
    rule = self.rule(101)
    if depth is not False:
      tracer = DebugTracer("__GEN0", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(101, self.getAtomString(101)), tracer )
    tree.list = 'tlist'
    if self.sym != None and (self.sym.getId() == 18 or self.sym.getId() == 60 or self.sym.getId() == 21 or self.sym.getId() == 0):
      return tree
    if self.sym != None and (self.sym.getId() == 18 or self.sym.getId() == 60 or self.sym.getId() == 21 or self.sym.getId() == 0):
      return tree
    if self.sym != None and (self.sym.getId() == 18 or self.sym.getId() == 60 or self.sym.getId() == 21 or self.sym.getId() == 0):
      return tree
    if self.sym != None and (self.sym.getId() == 18 or self.sym.getId() == 60 or self.sym.getId() == 21 or self.sym.getId() == 0):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 81:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PP_NODES(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(21, tracer) ) # separator
      subtree = self.__GEN0(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def __GEN1(self, depth = 0):
    rule = self.rule(92)
    if depth is not False:
      tracer = DebugTracer("__GEN1", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(92, self.getAtomString(92)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() == 18 or self.sym.getId() == 21):
      return tree
    if self.sym != None and (self.sym.getId() == 18 or self.sym.getId() == 21):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 91:
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
  def __GEN2(self, depth = 0):
    rule = self.rule(83)
    if depth is not False:
      tracer = DebugTracer("__GEN2", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(83, self.getAtomString(83)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() == 50):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 17:
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
  def __GEN3(self, depth = 0):
    rule = self.rule(76)
    if depth is not False:
      tracer = DebugTracer("__GEN3", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(76, self.getAtomString(76)), tracer )
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() == 50):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 44:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(55, tracer) ) # comma
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
  def __GEN4(self, depth = 0):
    rule = self.rule(77)
    if depth is not False:
      tracer = DebugTracer("__GEN4", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(77, self.getAtomString(77)), tracer )
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() == 21):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 61:
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
  def __GEN5(self, depth = 0):
    rule = self.rule(74)
    if depth is not False:
      tracer = DebugTracer("__GEN5", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(74, self.getAtomString(74)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
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
  def _CONTROL_LINE(self, depth = 0):
    rule = self.rule(85)
    if depth is not False:
      tracer = DebugTracer("_CONTROL_LINE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(85, self.getAtomString(85)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 2:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._INCLUDE_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 5:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._WARNING_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 8:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._DEFINE_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 66:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._LINE_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 93:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._ERROR_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 94:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PRAGMA_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 108:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._UNDEF_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _DEFINE_FUNC_PARAM(self, depth = 0):
    rule = self.rule(80)
    if depth is not False:
      tracer = DebugTracer("_DEFINE_FUNC_PARAM", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(80, self.getAtomString(80)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 50:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(51, tracer) ) # identifier
      return tree
    elif rule == 64:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(12, tracer) ) # elipsis
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _DEFINE_LINE(self, depth = 0):
    rule = self.rule(100)
    if depth is not False:
      tracer = DebugTracer("_DEFINE_LINE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(100, self.getAtomString(100)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 4:
      tree.astTransform = AstTransformNodeCreator('Define', {'body': 2, 'ident': 1})
      tree.add( self.expect(71, tracer) ) # define
      tree.add( self.expect(51, tracer) ) # identifier
      subtree = self._REPLACEMENT_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 51:
      tree.astTransform = AstTransformNodeCreator('DefineFunction', {'body': 5, 'ident': 1, 'params': 3})
      tree.add( self.expect(34, tracer) ) # define_function
      tree.add( self.expect(51, tracer) ) # identifier
      tree.add( self.expect(13, tracer) ) # lparen
      subtree = self.__GEN2(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      tree.add( self.expect(50, tracer) ) # rparen
      subtree = self._REPLACEMENT_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _DEFINED_IDENTIFIER(self, depth = 0):
    rule = self.rule(75)
    if depth is not False:
      tracer = DebugTracer("_DEFINED_IDENTIFIER", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(75, self.getAtomString(75)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 3:
      tree.astTransform = AstTransformSubstitution(1)
      tree.add( self.expect(13, tracer) ) # lparen
      tree.add( self.expect(51, tracer) ) # identifier
      tree.add( self.expect(50, tracer) ) # rparen
      return tree
    elif rule == 72:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(51, tracer) ) # identifier
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _ELIPSIS_OPT(self, depth = 0):
    rule = self.rule(84)
    if depth is not False:
      tracer = DebugTracer("_ELIPSIS_OPT", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(84, self.getAtomString(84)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 90:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(55, tracer) ) # comma
      tree.add( self.expect(12, tracer) ) # elipsis
      return tree
    return tree
  def _ELSE_PART(self, depth = 0):
    rule = self.rule(98)
    if depth is not False:
      tracer = DebugTracer("_ELSE_PART", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(98, self.getAtomString(98)), tracer )
    tree.list = False
    if self.sym != None and (self.sym.getId() == 60):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 31:
      tree.astTransform = AstTransformNodeCreator('Else', {'nodes': 1})
      tree.add( self.expect(18, tracer) ) # else
      subtree = self._PP_NODES_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _ELSEIF_PART(self, depth = 0):
    rule = self.rule(102)
    if depth is not False:
      tracer = DebugTracer("_ELSEIF_PART", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(102, self.getAtomString(102)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 45:
      tree.astTransform = AstTransformNodeCreator('ElseIf', {'expr': 1, 'nodes': 2})
      tree.add( self.expect(0, tracer) ) # elif
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
  def _ERROR_LINE(self, depth = 0):
    rule = self.rule(73)
    if depth is not False:
      tracer = DebugTracer("_ERROR_LINE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(73, self.getAtomString(73)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 86:
      tree.astTransform = AstTransformNodeCreator('Error', {'tokens': 1})
      tree.add( self.expect(53, tracer) ) # error
      subtree = self.__GEN4(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _IDENTIFIER(self, depth = 0):
    rule = self.rule(104)
    if depth is not False:
      tracer = DebugTracer("_IDENTIFIER", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(104, self.getAtomString(104)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 103:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(51, tracer) ) # identifier
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _IF_PART(self, depth = 0):
    rule = self.rule(89)
    if depth is not False:
      tracer = DebugTracer("_IF_PART", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(89, self.getAtomString(89)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 37:
      tree.astTransform = AstTransformNodeCreator('IfDef', {'nodes': 2, 'ident': 1})
      tree.add( self.expect(58, tracer) ) # ifdef
      tree.add( self.expect(51, tracer) ) # identifier
      subtree = self._PP_NODES_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 38:
      tree.astTransform = AstTransformNodeCreator('If', {'expr': 1, 'nodes': 2})
      tree.add( self.expect(66, tracer) ) # if
      subtree = self.__EXPR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self._PP_NODES_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 98:
      tree.astTransform = AstTransformNodeCreator('IfNDef', {'nodes': 2, 'ident': 1})
      tree.add( self.expect(46, tracer) ) # ifndef
      tree.add( self.expect(51, tracer) ) # identifier
      subtree = self._PP_NODES_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _IF_SECTION(self, depth = 0):
    rule = self.rule(86)
    if depth is not False:
      tracer = DebugTracer("_IF_SECTION", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(86, self.getAtomString(86)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 52:
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
      tree.add( self.expect(60, tracer) ) # endif
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _INCLUDE_LINE(self, depth = 0):
    rule = self.rule(97)
    if depth is not False:
      tracer = DebugTracer("_INCLUDE_LINE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(97, self.getAtomString(97)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 101:
      tree.astTransform = AstTransformNodeCreator('Include', {'file': 1})
      tree.add( self.expect(37, tracer) ) # include
      subtree = self._INCLUDE_TYPE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _INCLUDE_TYPE(self, depth = 0):
    rule = self.rule(94)
    if depth is not False:
      tracer = DebugTracer("_INCLUDE_TYPE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(94, self.getAtomString(94)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 18:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(51, tracer) ) # identifier
      return tree
    elif rule == 55:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(36, tracer) ) # header_global
      return tree
    elif rule == 70:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(41, tracer) ) # header_local
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
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 65:
      tree.astTransform = AstTransformNodeCreator('Line', {'tokens': 1})
      tree.add( self.expect(65, tracer) ) # line
      subtree = self.__GEN4(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PP_DIRECTIVE(self, depth = 0):
    rule = self.rule(96)
    if depth is not False:
      tracer = DebugTracer("_PP_DIRECTIVE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(96, self.getAtomString(96)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 82:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._CONTROL_LINE(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 96:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._IF_SECTION(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PP_FILE(self, depth = 0):
    rule = self.rule(93)
    if depth is not False:
      tracer = DebugTracer("_PP_FILE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(93, self.getAtomString(93)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 102:
      tree.astTransform = AstTransformNodeCreator('PPFile', {'nodes': 0})
      subtree = self._PP_NODES_LIST(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PP_NODES(self, depth = 0):
    rule = self.rule(78)
    if depth is not False:
      tracer = DebugTracer("_PP_NODES", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(78, self.getAtomString(78)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 12:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(14, tracer) ) # csource
      return tree
    elif rule == 48:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PP_DIRECTIVE(depth)
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
    if self.sym != None and (self.sym.getId() == 18 or self.sym.getId() == 60 or self.sym.getId() == 21 or self.sym.getId() == 0):
      return tree
    if self.sym != None and (self.sym.getId() == 18 or self.sym.getId() == 60 or self.sym.getId() == 21 or self.sym.getId() == 0):
      return tree
    if self.sym != None and (self.sym.getId() == 18 or self.sym.getId() == 60 or self.sym.getId() == 21 or self.sym.getId() == 0):
      return tree
    if self.sym != None and (self.sym.getId() == 18 or self.sym.getId() == 60 or self.sym.getId() == 21 or self.sym.getId() == 0):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 105:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.__GEN0(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _PP_TOKENS(self, depth = 0):
    rule = self.rule(81)
    if depth is not False:
      tracer = DebugTracer("_PP_TOKENS", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(81, self.getAtomString(81)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 19:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(41, tracer) ) # header_local
      return tree
    elif rule == 23:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(30, tracer) ) # defined
      return tree
    elif rule == 27:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(36, tracer) ) # header_global
      return tree
    elif rule == 29:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(8, tracer) ) # pp_number
      return tree
    elif rule == 56:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(51, tracer) ) # identifier
      return tree
    elif rule == 62:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(69, tracer) ) # string_literal
      return tree
    elif rule == 76:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(63, tracer) ) # character_constant
      return tree
    elif rule == 79:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self._PUNCTUATOR(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 80:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(42, tracer) ) # defined_separator
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PRAGMA_LINE(self, depth = 0):
    rule = self.rule(90)
    if depth is not False:
      tracer = DebugTracer("_PRAGMA_LINE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(90, self.getAtomString(90)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 67:
      tree.astTransform = AstTransformNodeCreator('Pragma', {'tokens': 1})
      tree.add( self.expect(47, tracer) ) # pragma
      subtree = self.__GEN4(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _PUNCTUATOR(self, depth = 0):
    rule = self.rule(91)
    if depth is not False:
      tracer = DebugTracer("_PUNCTUATOR", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(91, self.getAtomString(91)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 0:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(29, tracer) ) # rbrace
      return tree
    elif rule == 6:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(9, tracer) ) # bitor
      return tree
    elif rule == 7:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(26, tracer) ) # pound
      return tree
    elif rule == 9:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(12, tracer) ) # elipsis
      return tree
    elif rule == 10:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(32, tracer) ) # bitnot
      return tree
    elif rule == 14:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(72, tracer) ) # bitandeq
      return tree
    elif rule == 15:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(33, tracer) ) # lsquare
      return tree
    elif rule == 21:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(48, tracer) ) # rshifteq
      return tree
    elif rule == 22:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(52, tracer) ) # bitxoreq
      return tree
    elif rule == 24:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(31, tracer) ) # lshifteq
      return tree
    elif rule == 25:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(27, tracer) ) # and
      return tree
    elif rule == 26:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(15, tracer) ) # assign
      return tree
    elif rule == 28:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(17, tracer) ) # arrow
      return tree
    elif rule == 30:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(35, tracer) ) # bitxor
      return tree
    elif rule == 32:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(30, tracer) ) # defined
      return tree
    elif rule == 34:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(16, tracer) ) # semi
      return tree
    elif rule == 35:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(67, tracer) ) # sub
      return tree
    elif rule == 36:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(11, tracer) ) # lteq
      return tree
    elif rule == 39:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(57, tracer) ) # gt
      return tree
    elif rule == 40:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(39, tracer) ) # rsquare
      return tree
    elif rule == 41:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(7, tracer) ) # modeq
      return tree
    elif rule == 42:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(13, tracer) ) # lparen
      return tree
    elif rule == 43:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(2, tracer) ) # lshift
      return tree
    elif rule == 46:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(35, tracer) ) # bitxor
      return tree
    elif rule == 47:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(44, tracer) ) # decr
      return tree
    elif rule == 49:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(25, tracer) ) # lbrace
      return tree
    elif rule == 53:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(6, tracer) ) # rshift
      return tree
    elif rule == 54:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(4, tracer) ) # incr
      return tree
    elif rule == 57:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(9, tracer) ) # bitor
      return tree
    elif rule == 58:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(20, tracer) ) # colon
      return tree
    elif rule == 59:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(40, tracer) ) # neq
      return tree
    elif rule == 60:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(38, tracer) ) # addeq
      return tree
    elif rule == 63:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(61, tracer) ) # tilde
      return tree
    elif rule == 68:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(22, tracer) ) # dot
      return tree
    elif rule == 69:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(55, tracer) ) # comma
      return tree
    elif rule == 71:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(23, tracer) ) # or
      return tree
    elif rule == 73:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(45, tracer) ) # eq
      return tree
    elif rule == 74:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(50, tracer) ) # rparen
      return tree
    elif rule == 75:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(70, tracer) ) # lt
      return tree
    elif rule == 78:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(49, tracer) ) # subeq
      return tree
    elif rule == 83:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(24, tracer) ) # questionmark
      return tree
    elif rule == 85:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(68, tracer) ) # div
      return tree
    elif rule == 88:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(19, tracer) ) # poundpound
      return tree
    elif rule == 89:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(28, tracer) ) # bitand
      return tree
    elif rule == 95:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(3, tracer) ) # mod
      return tree
    elif rule == 97:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(54, tracer) ) # exclamation_point
      return tree
    elif rule == 100:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(43, tracer) ) # bitoreq
      return tree
    elif rule == 104:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(56, tracer) ) # gteq
      return tree
    elif rule == 106:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(10, tracer) ) # ampersand
      return tree
    elif rule == 107:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(62, tracer) ) # muleq
      return tree
    elif rule == 109:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(5, tracer) ) # mul
      return tree
    elif rule == 110:
      tree.astTransform = AstTransformSubstitution(0)
      tree.add( self.expect(1, tracer) ) # add
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
    if self.sym != None and (self.sym.getId() == 21):
      return tree
    if self.sym == None or self.sym.getId() in []:
      return tree
    if rule == 111:
      tree.astTransform = AstTransformNodeCreator('ReplacementList', {'tokens': 0})
      subtree = self.__GEN4(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def _UNDEF_LINE(self, depth = 0):
    rule = self.rule(99)
    if depth is not False:
      tracer = DebugTracer("_UNDEF_LINE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(99, self.getAtomString(99)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 84:
      tree.astTransform = AstTransformNodeCreator('Undef', {'ident': 1})
      tree.add( self.expect(64, tracer) ) # undef
      tree.add( self.expect(51, tracer) ) # identifier
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  def _WARNING_LINE(self, depth = 0):
    rule = self.rule(79)
    if depth is not False:
      tracer = DebugTracer("_WARNING_LINE", str(self.sym), rule, depth)
      depth = depth + 1
    else:
      tracer = None
    tree = ParseTree( NonTerminal(79, self.getAtomString(79)), tracer )
    tree.list = False
    if self.sym == None or self.sym.getId() in []:
      raise SyntaxError('Error: unexpected end of file', tracer)
    if rule == 11:
      tree.astTransform = AstTransformNodeCreator('Warning', {'tokens': 1})
      tree.add( self.expect(59, tracer) ) # warning
      subtree = self.__GEN4(depth)
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol', tracer)
  infixBp0 = {
    1: 11000,
    2: 10000,
    3: 12000,
    5: 12000,
    6: 10000,
    9: 7000,
    11: 9000,
    13: 15000,
    23: 3000,
    24: 2000,
    27: 4000,
    28: 5000,
    35: 6000,
    40: 8000,
    42: 14000,
    45: 8000,
    55: 1000,
    56: 9000,
    57: 9000,
    67: 11000,
    68: 12000,
    70: 9000,
  }
  prefixBp0 = {
    5: 13000,
    28: 13000,
    30: 13000,
    32: 13000,
    54: 13000,
    67: 13000,
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
    tree = ParseTree( NonTerminal(103, '_expr') )
    if self.sym.getId() == 51: # 'identifier'
      tree.astTransform = AstTransformSubstitution(0)
      return self.expect( 51, tracer )
    elif self.sym.getId() == 30: # 'defined'
      tree.astTransform = AstTransformNodeCreator('IsDefined', {'expr': 2})
      return self.expect( 30, tracer )
    elif self.sym.getId() == 8: # 'pp_number'
      tree.astTransform = AstTransformSubstitution(0)
      return self.expect( 8, tracer )
    elif self.sym.getId() == 63: # 'character_constant'
      tree.astTransform = AstTransformSubstitution(0)
      return self.expect( 63, tracer )
    elif self.sym.getId() == 69: # 'string_literal'
      tree.astTransform = AstTransformSubstitution(0)
      return self.expect( 69, tracer )
    elif self.sym.getId() == 32: # 'bitnot'
      tree.astTransform = AstTransformNodeCreator('BitNOT', {'expr': 1})
      tree.add( self.expect(32, tracer) )
      tree.add( self.__EXPR( self.prefixBp0[32] ) )
      tree.isPrefix = True
    elif self.sym.getId() == 54: # 'exclamation_point'
      tree.astTransform = AstTransformNodeCreator('Not', {'expr': 1})
      tree.add( self.expect(54, tracer) )
      tree.add( self.__EXPR( self.prefixBp0[54] ) )
      tree.isPrefix = True
    elif self.sym.getId() == 13: # 'lparen'
      tree.astTransform = AstTransformSubstitution(1)
      tree.add( self.expect(13, tracer) )
      tree.add( self.__EXPR() )
      tree.add( self.expect(50, tracer) )
    elif self.sym.getId() == 103: # _expr
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      return self.expect( 103, tracer )
    return tree
  def led0(self, left, tracer):
    tree = ParseTree( NonTerminal(103, '_expr') )
    if  self.sym.getId() == 45: # 'eq'
      tree.astTransform = AstTransformNodeCreator('Equals', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(45, tracer) )
      tree.add( self.__EXPR( self.infixBp0[45] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 11: # 'lteq'
      tree.astTransform = AstTransformNodeCreator('LessThanEq', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(11, tracer) )
      tree.add( self.__EXPR( self.infixBp0[11] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 42: # 'defined_separator'
      tree.astTransform = AstTransformNodeCreator('IsDefined', {'expr': 2})
      if left:
        tree.add(left)
      tree.add( self.expect(42, tracer) )
      tree.add( self._DEFINED_IDENTIFIER() )
    elif  self.sym.getId() == 9: # 'bitor'
      tree.astTransform = AstTransformNodeCreator('BitOR', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(9, tracer) )
      tree.add( self.__EXPR( self.infixBp0[9] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 40: # 'neq'
      tree.astTransform = AstTransformNodeCreator('NotEquals', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(40, tracer) )
      tree.add( self.__EXPR( self.infixBp0[40] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 56: # 'gteq'
      tree.astTransform = AstTransformNodeCreator('GreaterThanEq', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(56, tracer) )
      tree.add( self.__EXPR( self.infixBp0[56] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 1: # 'add'
      tree.astTransform = AstTransformNodeCreator('Add', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(1, tracer) )
      tree.add( self.__EXPR( self.infixBp0[1] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 35: # 'bitxor'
      tree.astTransform = AstTransformNodeCreator('BitXOR', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(35, tracer) )
      tree.add( self.__EXPR( self.infixBp0[35] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 55: # 'comma'
      tree.astTransform = AstTransformNodeCreator('Comma', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(55, tracer) )
      tree.add( self.__EXPR( self.infixBp0[55] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 5: # 'mul'
      tree.astTransform = AstTransformNodeCreator('Mul', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(5, tracer) )
      tree.add( self.__EXPR( self.infixBp0[5] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 67: # 'sub'
      tree.astTransform = AstTransformNodeCreator('Sub', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(67, tracer) )
      tree.add( self.__EXPR( self.infixBp0[67] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 2: # 'lshift'
      tree.astTransform = AstTransformNodeCreator('LeftShift', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(2, tracer) )
      tree.add( self.__EXPR( self.infixBp0[2] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 68: # 'div'
      tree.astTransform = AstTransformNodeCreator('Div', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(68, tracer) )
      tree.add( self.__EXPR( self.infixBp0[68] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 13: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(13, tracer) )
      ls = AstList()
      if self.sym.getId() not in [50]:
        while 1:
          ls.append( self.__EXPR() )
          if self.sym.getId() != 55:
            break
          self.expect(55, tracer)
      tree.add( ls )
      tree.add( self.expect(50, tracer) )
    elif  self.sym.getId() == 70: # 'lt'
      tree.astTransform = AstTransformNodeCreator('LessThan', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(70, tracer) )
      tree.add( self.__EXPR( self.infixBp0[70] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 27: # 'and'
      tree.astTransform = AstTransformNodeCreator('And', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(27, tracer) )
      tree.add( self.__EXPR( self.infixBp0[27] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 6: # 'rshift'
      tree.astTransform = AstTransformNodeCreator('RightShift', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(6, tracer) )
      tree.add( self.__EXPR( self.infixBp0[6] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 3: # 'mod'
      tree.astTransform = AstTransformNodeCreator('Mod', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(3, tracer) )
      tree.add( self.__EXPR( self.infixBp0[3] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 57: # 'gt'
      tree.astTransform = AstTransformNodeCreator('GreaterThan', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(57, tracer) )
      tree.add( self.__EXPR( self.infixBp0[57] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 24: # 'questionmark'
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(24, tracer) )
      tree.add( self.__EXPR() )
      tree.add( self.expect(20, tracer) )
      tree.add( self.__EXPR() )
    elif  self.sym.getId() == 23: # 'or'
      tree.astTransform = AstTransformNodeCreator('Or', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(23, tracer) )
      tree.add( self.__EXPR( self.infixBp0[23] ) )
      tree.isInfix = True
    elif  self.sym.getId() == 28: # 'bitand'
      tree.astTransform = AstTransformNodeCreator('BitAND', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(28, tracer) )
      tree.add( self.__EXPR( self.infixBp0[28] ) )
      tree.isInfix = True
    return tree
