import sys
import inspect
def whoami():
  return inspect.stack()[1][3]
def whosdaddy():
  return inspect.stack()[2][3]
def parse( iterator, entry ):
  p = Parser()
  return p.parse(iterator, entry)
class Terminal:
  def __init__(self, id):
    self.id=id
    self.str=Parser.terminals[id]
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
  def __init__(self, nonterminal):
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
          elif len(self.children) == 1 and not isinstance(self.children[0], ParseTree) and not isinstance(self.children[0], list):
            return self.children[0]
          else:
            child = self.children[idx]
          parameters[name] = child.toAst()
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
      string = '%s(%s:\n' % ('', parsetree.nonterminal)
      string += ',\n'.join([ \
        '%s  %s' % (indentStr, self._prettyPrint(value, indent + 2)) for value in parsetree.children \
      ])
      string += '\n%s)' % (indentStr)
      return string
    elif isinstance(parsetree, Terminal):
      return parsetree.toString(self.tokenFormat)
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
        return 'None'
      string = '[\n'
      string += ',\n'.join([self._prettyPrint(element, indent + 2) for element in ast])
      string += '\n%s]' % (indentStr)
      return string
    elif isinstance(ast, Terminal):
      return '%s%s' % (indentStr, ast.toString(self.tokenFormat))
    return 'None'
class SyntaxError(Exception):
  def __init__(self, message):
    self.__dict__.update(locals())
  def __str__(self):
    return self.message
class ExpressionParser__expr:
  def __init__(self, parent):
    self.__dict__.update(locals())
    self.infixBp = {
      3: 10000,
      7: 10000,
      10: 9000,
      11: 12000,
      21: 11000,
      22: 12000,
      29: 2000,
      35: 5000,
      37: 3000,
      38: 9000,
      41: 1000,
      44: 4000,
      45: 7000,
      49: 8000,
      50: 6000,
      52: 12000,
      54: 8000,
      57: 9000,
      60: 9000,
      66: 15000,
      68: 11000,
      72: 14000,
    }
    self.prefixBp = {
      2: 13000,
      5: 13000,
      35: 13000,
      39: 13000,
      52: 13000,
      68: 13000,
    }
  def getInfixBp(self, tokenId):
    try:
      return self.infixBp[tokenId]
    except:
      return 0
  def getPrefixBp(self, tokenId):
    try:
      return self.prefixBp[tokenId]
    except:
      return 0
  def getCurrentToken(self):
    return self.parent.tokens.current()
  def expect(self, token):
    return self.parent.expect(token)
  def parse(self, rbp = 0):
    left = self.nud()
    if isinstance(left, ParseTree):
      left.isExpr = True
      left.isNud = True
    while self.getCurrentToken() and rbp < self.getInfixBp(self.getCurrentToken().getId()):
      left = self.led(left)
    if left:
      left.isExpr = True
    return left
  def nud(self):
    tree = ParseTree( NonTerminal(79, '_expr') )
    current = self.getCurrentToken()
    if not current:
      return tree
    elif current.getId() in [39]:
      tree.astTransform = AstTransformNodeCreator('BitNOT', {'expr': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(39) )
      tree.add( self.parent.parse__expr( self.getPrefixBp(39) ) )
      tree.isPrefix = True
    elif current.getId() in [66]:
      tree.astTransform = AstTransformSubstitution(1)
      tree.nudMorphemeCount = 3
      tree.add( self.expect(66) )
      tree.add( self.parent.parse__expr() )
      tree.add( self.expect(71) )
    elif current.getId() in [40]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self.expect(40) )
    elif current.getId() in [40]:
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      tree.nudMorphemeCount = 1
      tree.add( self.expect(40) )
    elif current.getId() in [5]:
      tree.astTransform = AstTransformNodeCreator('IsDefined', {'expr': 2})
      tree.nudMorphemeCount = 1
      tree.add( self.expect(5) )
    elif current.getId() in [13]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self.expect(13) )
    elif current.getId() in [19]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self.expect(19) )
    elif current.getId() in [2]:
      tree.astTransform = AstTransformNodeCreator('Not', {'expr': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(2) )
      tree.add( self.parent.parse__expr( self.getPrefixBp(2) ) )
      tree.isPrefix = True
    elif current.getId() in [23]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self.expect(23) )
    return tree
  def led(self, left):
    tree = ParseTree( NonTerminal(79, '_expr') )
    current = self.getCurrentToken()
    if current.getId() == 29: # 'questionmark'
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      tree.isExprNud = True 
      tree.add(left)
      tree.add( self.expect(29) )
      modifier = 1
      tree.add( self.parent.parse__expr( self.getInfixBp(29) - modifier ) )
      tree.add( self.expect(24) )
      modifier = 1
      tree.add( self.parent.parse__expr( self.getInfixBp(29) - modifier ) )
      return tree
    if current.getId() == 38: # 'lt'
      tree.astTransform = AstTransformNodeCreator('LessThan', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(38) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(38) - modifier ) )
      return tree
    if current.getId() == 37: # 'or'
      tree.astTransform = AstTransformNodeCreator('Or', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(37) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(37) - modifier ) )
      return tree
    if current.getId() == 54: # 'eq'
      tree.astTransform = AstTransformNodeCreator('Equals', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(54) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(54) - modifier ) )
      return tree
    if current.getId() == 49: # 'neq'
      tree.astTransform = AstTransformNodeCreator('NotEquals', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(49) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(49) - modifier ) )
      return tree
    if current.getId() == 22: # 'div'
      tree.astTransform = AstTransformNodeCreator('Div', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(22) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(22) - modifier ) )
      return tree
    if current.getId() == 41: # 'comma'
      tree.astTransform = AstTransformNodeCreator('Comma', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(41) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(41) - modifier ) )
      return tree
    if current.getId() == 35: # 'bitand'
      tree.astTransform = AstTransformNodeCreator('BitAND', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(35) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(35) - modifier ) )
      return tree
    if current.getId() == 21: # 'add'
      tree.astTransform = AstTransformNodeCreator('Add', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(21) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(21) - modifier ) )
      return tree
    if current.getId() == 7: # 'rshift'
      tree.astTransform = AstTransformNodeCreator('RightShift', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(7) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(7) - modifier ) )
      return tree
    if current.getId() == 68: # 'sub'
      tree.astTransform = AstTransformNodeCreator('Sub', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(68) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(68) - modifier ) )
      return tree
    if current.getId() == 60: # 'lteq'
      tree.astTransform = AstTransformNodeCreator('LessThanEq', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(60) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(60) - modifier ) )
      return tree
    if current.getId() == 44: # 'and'
      tree.astTransform = AstTransformNodeCreator('And', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(44) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(44) - modifier ) )
      return tree
    if current.getId() == 66: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      tree.add(left)
      tree.add( self.expect(66) )
      tree.add( self.parent.parse__gen5() )
      tree.add( self.expect(71) )
      return tree
    if current.getId() == 3: # 'lshift'
      tree.astTransform = AstTransformNodeCreator('LeftShift', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(3) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(3) - modifier ) )
      return tree
    if current.getId() == 10: # 'gteq'
      tree.astTransform = AstTransformNodeCreator('GreaterThanEq', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(10) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(10) - modifier ) )
      return tree
    if current.getId() == 72: # 'defined_separator'
      tree.astTransform = AstTransformNodeCreator('IsDefined', {'expr': 2})
      tree.add(left)
      tree.add( self.expect(72) )
      tree.add( self.parent.parse_defined_identifier() )
      return tree
    if current.getId() == 52: # 'mul'
      tree.astTransform = AstTransformNodeCreator('Mul', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(52) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(52) - modifier ) )
      return tree
    if current.getId() == 50: # 'bitxor'
      tree.astTransform = AstTransformNodeCreator('BitXOR', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(50) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(50) - modifier ) )
      return tree
    if current.getId() == 45: # 'bitor'
      tree.astTransform = AstTransformNodeCreator('BitOR', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(45) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(45) - modifier ) )
      return tree
    if current.getId() == 11: # 'mod'
      tree.astTransform = AstTransformNodeCreator('Mod', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(11) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(11) - modifier ) )
      return tree
    if current.getId() == 57: # 'gt'
      tree.astTransform = AstTransformNodeCreator('GreaterThan', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(57) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(57) - modifier ) )
      return tree
    return tree
class TokenStream:
  def __init__(self, iterable):
    self.iterable = iter(iterable)
    self.advance()
  def advance(self):
    try:
      self.token = next(self.iterable)
    except StopIteration:
      self.token = None
    return self.token
  def current(self):
    return self.token
class Parser:
  # Quark - finite string set maps one string to exactly one int, and vice versa
  terminals = {
    0: 'if',
    1: 'arrow',
    2: 'exclamation_point',
    3: 'lshift',
    4: 'subeq',
    5: 'defined',
    6: 'rshifteq',
    7: 'rshift',
    8: 'addeq',
    9: 'define_function',
    10: 'gteq',
    11: 'mod',
    12: 'modeq',
    13: 'string_literal',
    14: 'elif',
    15: 'elipsis',
    16: 'muleq',
    17: 'else',
    18: 'csource',
    19: 'character_constant',
    20: 'diveq',
    21: 'add',
    22: 'div',
    23: 'pp_number',
    24: 'colon',
    25: 'ifndef',
    26: 'assign',
    27: 'define',
    28: 'ampersand',
    29: 'questionmark',
    30: 'poundpound',
    31: '_expr',
    32: 'decr',
    33: 'incr',
    34: 'dot',
    35: 'bitand',
    36: 'pound',
    37: 'or',
    38: 'lt',
    39: 'bitnot',
    40: 'identifier',
    41: 'comma',
    42: 'tilde',
    43: 'ifdef',
    44: 'and',
    45: 'bitor',
    46: 'lbrace',
    47: 'lshifteq',
    48: 'header_global',
    49: 'neq',
    50: 'bitxor',
    51: 'rbrace',
    52: 'mul',
    53: 'header_local',
    54: 'eq',
    55: 'separator',
    56: 'bitoreq',
    57: 'gt',
    58: 'line',
    59: 'lsquare',
    60: 'lteq',
    61: 'pragma',
    62: 'bitxoreq',
    63: 'rsquare',
    64: 'error',
    65: 'bitandeq',
    66: 'lparen',
    67: 'semi',
    68: 'sub',
    69: 'warning',
    70: 'endif',
    71: 'rparen',
    72: 'defined_separator',
    73: 'undef',
    74: 'include',
    'if': 0,
    'arrow': 1,
    'exclamation_point': 2,
    'lshift': 3,
    'subeq': 4,
    'defined': 5,
    'rshifteq': 6,
    'rshift': 7,
    'addeq': 8,
    'define_function': 9,
    'gteq': 10,
    'mod': 11,
    'modeq': 12,
    'string_literal': 13,
    'elif': 14,
    'elipsis': 15,
    'muleq': 16,
    'else': 17,
    'csource': 18,
    'character_constant': 19,
    'diveq': 20,
    'add': 21,
    'div': 22,
    'pp_number': 23,
    'colon': 24,
    'ifndef': 25,
    'assign': 26,
    'define': 27,
    'ampersand': 28,
    'questionmark': 29,
    'poundpound': 30,
    '_expr': 31,
    'decr': 32,
    'incr': 33,
    'dot': 34,
    'bitand': 35,
    'pound': 36,
    'or': 37,
    'lt': 38,
    'bitnot': 39,
    'identifier': 40,
    'comma': 41,
    'tilde': 42,
    'ifdef': 43,
    'and': 44,
    'bitor': 45,
    'lbrace': 46,
    'lshifteq': 47,
    'header_global': 48,
    'neq': 49,
    'bitxor': 50,
    'rbrace': 51,
    'mul': 52,
    'header_local': 53,
    'eq': 54,
    'separator': 55,
    'bitoreq': 56,
    'gt': 57,
    'line': 58,
    'lsquare': 59,
    'lteq': 60,
    'pragma': 61,
    'bitxoreq': 62,
    'rsquare': 63,
    'error': 64,
    'bitandeq': 65,
    'lparen': 66,
    'semi': 67,
    'sub': 68,
    'warning': 69,
    'endif': 70,
    'rparen': 71,
    'defined_separator': 72,
    'undef': 73,
    'include': 74,
  }
  # Quark - finite string set maps one string to exactly one int, and vice versa
  nonterminals = {
    75: '_gen5',
    76: 'elipsis_opt',
    77: 'pragma_line',
    78: 'pp_nodes_list',
    79: '_expr',
    80: 'include_line',
    81: '_gen6',
    82: 'define_func_param',
    83: 'elseif_part',
    84: 'replacement_list',
    85: 'error_line',
    86: '_gen3',
    87: 'include_type',
    88: '_gen4',
    89: 'line_line',
    90: 'pp_directive',
    91: '_gen1',
    92: 'warning_line',
    93: '_gen2',
    94: '_gen0',
    95: 'define_line',
    96: 'if_section',
    97: 'pp_nodes',
    98: 'pp_file',
    99: 'if_part',
    100: 'else_part',
    101: 'pp_tokens',
    102: 'defined_identifier',
    103: 'control_line',
    104: 'punctuator',
    105: 'undef_line',
    '_gen5': 75,
    'elipsis_opt': 76,
    'pragma_line': 77,
    'pp_nodes_list': 78,
    '_expr': 79,
    'include_line': 80,
    '_gen6': 81,
    'define_func_param': 82,
    'elseif_part': 83,
    'replacement_list': 84,
    'error_line': 85,
    '_gen3': 86,
    'include_type': 87,
    '_gen4': 88,
    'line_line': 89,
    'pp_directive': 90,
    '_gen1': 91,
    'warning_line': 92,
    '_gen2': 93,
    '_gen0': 94,
    'define_line': 95,
    'if_section': 96,
    'pp_nodes': 97,
    'pp_file': 98,
    'if_part': 99,
    'else_part': 100,
    'pp_tokens': 101,
    'defined_identifier': 102,
    'control_line': 103,
    'punctuator': 104,
    'undef_line': 105,
  }
  # table[nonterminal][terminal] = rule
  table = [
    [-1, -1, 10, -1, -1, 10, -1, -1, -1, -1, -1, -1, -1, 10, -1, -1, -1, -1, -1, 10, -1, -1, -1, 10, -1, -1, -1, -1, -1, -1, -1, 10, -1, -1, -1, -1, -1, -1, -1, 10, 10, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 10, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 67, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 23, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [59, -1, -1, -1, -1, -1, -1, -1, -1, 59, -1, -1, -1, -1, 59, -1, -1, 59, 59, -1, -1, -1, -1, -1, -1, 59, -1, 59, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 59, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 59, -1, -1, 59, -1, -1, 59, -1, -1, -1, -1, 59, 59, -1, -1, 59, 59],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 135],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 12, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 106, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 115, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 113, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, 94, 94, 94, 94, 94, 94, 94, 94, -1, 94, 94, 94, 94, -1, 94, 94, -1, -1, 94, 94, 94, 94, 94, 94, -1, 94, -1, 94, 94, 94, -1, 94, 94, 94, 94, 94, 94, 94, 94, 94, 94, 94, -1, 94, 94, 94, 94, 94, 94, 94, 94, 94, 94, 94, 80, 94, 94, -1, 94, 94, -1, 94, 94, -1, 94, 94, 94, 94, -1, -1, 94, 94, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 60, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 6, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 7, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 91, -1, -1, -1, -1, -1, -1, -1, 4, -1, -1, -1, -1, 102, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, 31, 31, 31, 31, 31, 31, 31, 31, -1, 31, 31, 31, 31, -1, 31, 31, -1, -1, 31, 31, 31, 31, 31, 31, -1, 31, -1, 31, 31, 31, -1, 31, 31, 31, 31, 31, 31, 31, 31, 31, 31, 31, -1, 31, 31, 31, 31, 31, 31, 31, 31, 31, 31, 31, 34, 31, 31, -1, 31, 31, -1, 31, 31, -1, 31, 31, 31, 31, -1, -1, 31, 31, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 20, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [30, -1, -1, -1, -1, -1, -1, -1, -1, 107, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 30, -1, 107, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 30, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 107, -1, -1, 107, -1, -1, 107, -1, -1, -1, -1, 107, -1, -1, -1, 107, 107],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 43, -1, -1, 46, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 76, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 5, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 5, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 141, -1, -1, -1],
    [25, -1, -1, -1, -1, -1, -1, -1, -1, 25, -1, -1, -1, -1, 88, -1, -1, 88, 25, -1, -1, -1, -1, -1, -1, 25, -1, 25, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 25, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 25, -1, -1, 25, -1, -1, 25, -1, -1, -1, -1, 25, 88, -1, -1, 25, 25],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, 83, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 56, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [104, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 104, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 104, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [93, -1, -1, -1, -1, -1, -1, -1, -1, 93, -1, -1, -1, -1, -1, -1, -1, -1, 81, -1, -1, -1, -1, -1, -1, 93, -1, 93, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 93, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 93, -1, -1, 93, -1, -1, 93, -1, -1, -1, -1, 93, -1, -1, -1, 93, 93],
    [57, -1, -1, -1, -1, -1, -1, -1, -1, 57, -1, -1, -1, -1, -1, -1, -1, -1, 57, -1, -1, -1, -1, -1, -1, 57, -1, 57, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 57, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 57, -1, -1, 57, -1, -1, 57, -1, -1, -1, -1, 57, -1, -1, -1, 57, 57],
    [39, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 51, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 15, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 119, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 21, -1, -1, -1, -1],
    [-1, 97, 97, 97, 97, 87, 97, 97, 97, -1, 97, 97, 97, 73, -1, 97, 97, -1, -1, 75, 97, 97, 97, 44, 97, -1, 97, -1, 97, 97, 97, -1, 97, 97, 97, 97, 97, 97, 97, 97, 131, 97, 97, -1, 97, 97, 97, 97, 85, 97, 97, 97, 97, 134, 97, -1, 97, 97, -1, 97, 97, -1, 97, 97, -1, 97, 97, 97, 97, -1, -1, 97, 0, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 28, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 40, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, 126, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 126, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 55, -1, -1, 41, -1, -1, 52, -1, -1, -1, -1, 79, -1, -1, -1, 70, 128],
    [-1, 16, 9, 29, 22, -1, 90, 139, 36, -1, 1, 114, 45, -1, -1, 62, 98, -1, -1, -1, 64, 49, 38, -1, 138, -1, 99, -1, 103, 129, 117, -1, 111, 122, 53, 33, 133, 42, 58, 140, -1, 86, 24, -1, 68, 3, 72, 63, -1, 32, 89, 108, 66, -1, 84, -1, 47, 27, -1, 11, 121, -1, 124, 110, -1, 8, 71, 78, 37, -1, -1, 125, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 26, -1],
  ]
  TERMINAL_IF = 0
  TERMINAL_ARROW = 1
  TERMINAL_EXCLAMATION_POINT = 2
  TERMINAL_LSHIFT = 3
  TERMINAL_SUBEQ = 4
  TERMINAL_DEFINED = 5
  TERMINAL_RSHIFTEQ = 6
  TERMINAL_RSHIFT = 7
  TERMINAL_ADDEQ = 8
  TERMINAL_DEFINE_FUNCTION = 9
  TERMINAL_GTEQ = 10
  TERMINAL_MOD = 11
  TERMINAL_MODEQ = 12
  TERMINAL_STRING_LITERAL = 13
  TERMINAL_ELIF = 14
  TERMINAL_ELIPSIS = 15
  TERMINAL_MULEQ = 16
  TERMINAL_ELSE = 17
  TERMINAL_CSOURCE = 18
  TERMINAL_CHARACTER_CONSTANT = 19
  TERMINAL_DIVEQ = 20
  TERMINAL_ADD = 21
  TERMINAL_DIV = 22
  TERMINAL_PP_NUMBER = 23
  TERMINAL_COLON = 24
  TERMINAL_IFNDEF = 25
  TERMINAL_ASSIGN = 26
  TERMINAL_DEFINE = 27
  TERMINAL_AMPERSAND = 28
  TERMINAL_QUESTIONMARK = 29
  TERMINAL_POUNDPOUND = 30
  TERMINAL__EXPR = 31
  TERMINAL_DECR = 32
  TERMINAL_INCR = 33
  TERMINAL_DOT = 34
  TERMINAL_BITAND = 35
  TERMINAL_POUND = 36
  TERMINAL_OR = 37
  TERMINAL_LT = 38
  TERMINAL_BITNOT = 39
  TERMINAL_IDENTIFIER = 40
  TERMINAL_COMMA = 41
  TERMINAL_TILDE = 42
  TERMINAL_IFDEF = 43
  TERMINAL_AND = 44
  TERMINAL_BITOR = 45
  TERMINAL_LBRACE = 46
  TERMINAL_LSHIFTEQ = 47
  TERMINAL_HEADER_GLOBAL = 48
  TERMINAL_NEQ = 49
  TERMINAL_BITXOR = 50
  TERMINAL_RBRACE = 51
  TERMINAL_MUL = 52
  TERMINAL_HEADER_LOCAL = 53
  TERMINAL_EQ = 54
  TERMINAL_SEPARATOR = 55
  TERMINAL_BITOREQ = 56
  TERMINAL_GT = 57
  TERMINAL_LINE = 58
  TERMINAL_LSQUARE = 59
  TERMINAL_LTEQ = 60
  TERMINAL_PRAGMA = 61
  TERMINAL_BITXOREQ = 62
  TERMINAL_RSQUARE = 63
  TERMINAL_ERROR = 64
  TERMINAL_BITANDEQ = 65
  TERMINAL_LPAREN = 66
  TERMINAL_SEMI = 67
  TERMINAL_SUB = 68
  TERMINAL_WARNING = 69
  TERMINAL_ENDIF = 70
  TERMINAL_RPAREN = 71
  TERMINAL_DEFINED_SEPARATOR = 72
  TERMINAL_UNDEF = 73
  TERMINAL_INCLUDE = 74
  def __init__(self, tokens=None):
    self.__dict__.update(locals())
    self.expressionParsers = dict()
  def isTerminal(self, id):
    return 0 <= id <= 74
  def isNonTerminal(self, id):
    return 75 <= id <= 105
  def parse(self, tokens):
    self.tokens = tokens
    self.start = 'PP_FILE'
    tree = self.parse_pp_file()
    if self.tokens.current() != None:
      raise SyntaxError( 'Finished parsing without consuming all tokens.' )
    return tree
  def expect(self, terminalId):
    currentToken = self.tokens.current()
    if not currentToken:
      raise SyntaxError( 'No more tokens.  Expecting %s' % (self.terminals[terminalId]) )
    if currentToken.getId() != terminalId:
      raise SyntaxError( 'Unexpected symbol when parsing %s.  Expected %s, got %s.' %(whosdaddy(), self.terminals[terminalId], currentToken if currentToken else 'None') )
    nextToken = self.tokens.advance()
    if nextToken and not self.isTerminal(nextToken.getId()):
      raise SyntaxError( 'Invalid symbol ID: %d (%s)' % (nextToken.getId(), nextToken) )
    return currentToken
  def parse__gen5(self):
    current = self.tokens.current()
    rule = self.table[0][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(75, self.nonterminals[75]))
    tree.list = 'slist'
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 10:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr()
      tree.add( subtree )
      subtree = self.parse__gen6()
      tree.add( subtree )
      return tree
    return tree
  def parse_elipsis_opt(self):
    current = self.tokens.current()
    rule = self.table[1][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(76, self.nonterminals[76]))
    tree.list = False
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 67:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(41) # comma
      tree.add(t)
      t = self.expect(15) # elipsis
      tree.add(t)
      return tree
    return tree
  def parse_pragma_line(self):
    current = self.tokens.current()
    rule = self.table[2][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(77, self.nonterminals[77]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 23:
      tree.astTransform = AstTransformNodeCreator('Pragma', {'tokens': 1})
      t = self.expect(61) # pragma
      tree.add(t)
      subtree = self.parse__gen4()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_pp_nodes_list(self):
    current = self.tokens.current()
    rule = self.table[3][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(78, self.nonterminals[78]))
    tree.list = False
    if current != None and (current.getId() in [-1, 14, 17, 70]):
      return tree
    if current == None:
      return tree
    if rule == 59:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen0()
      tree.add( subtree )
      return tree
    return tree
  def parse_include_line(self):
    current = self.tokens.current()
    rule = self.table[5][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(80, self.nonterminals[80]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 135:
      tree.astTransform = AstTransformNodeCreator('Include', {'file': 1})
      t = self.expect(74) # include
      tree.add(t)
      subtree = self.parse_include_type()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen6(self):
    current = self.tokens.current()
    rule = self.table[6][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(81, self.nonterminals[81]))
    tree.list = 'slist'
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 12:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(41) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse__expr()
      tree.add( subtree )
      subtree = self.parse__gen6()
      tree.add( subtree )
      return tree
    return tree
  def parse_define_func_param(self):
    current = self.tokens.current()
    rule = self.table[7][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(82, self.nonterminals[82]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 106:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(15) # elipsis
      tree.add(t)
      return tree
    elif rule == 115:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(40) # identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_elseif_part(self):
    current = self.tokens.current()
    rule = self.table[8][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(83, self.nonterminals[83]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 113:
      tree.astTransform = AstTransformNodeCreator('ElseIf', {'expr': 1, 'nodes': 2})
      t = self.expect(14) # elif
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      subtree = self.parse_pp_nodes_list()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_replacement_list(self):
    current = self.tokens.current()
    rule = self.table[9][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(84, self.nonterminals[84]))
    tree.list = False
    if current != None and (current.getId() in [55]):
      return tree
    if current == None:
      return tree
    if rule == 94:
      tree.astTransform = AstTransformNodeCreator('ReplacementList', {'tokens': 0})
      subtree = self.parse__gen4()
      tree.add( subtree )
      return tree
    return tree
  def parse_error_line(self):
    current = self.tokens.current()
    rule = self.table[10][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(85, self.nonterminals[85]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 60:
      tree.astTransform = AstTransformNodeCreator('Error', {'tokens': 1})
      t = self.expect(64) # error
      tree.add(t)
      subtree = self.parse__gen4()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen3(self):
    current = self.tokens.current()
    rule = self.table[11][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(86, self.nonterminals[86]))
    tree.list = 'slist'
    if current != None and (current.getId() in [71]):
      return tree
    if current == None:
      return tree
    if rule == 6:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(41) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse_define_func_param()
      tree.add( subtree )
      subtree = self.parse__gen3()
      tree.add( subtree )
      return tree
    return tree
  def parse_include_type(self):
    current = self.tokens.current()
    rule = self.table[12][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(87, self.nonterminals[87]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 4:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(48) # header_global
      tree.add(t)
      return tree
    elif rule == 91:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(40) # identifier
      tree.add(t)
      return tree
    elif rule == 102:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(53) # header_local
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen4(self):
    current = self.tokens.current()
    rule = self.table[13][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(88, self.nonterminals[88]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [55]):
      return tree
    if current == None:
      return tree
    if rule == 31:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_pp_tokens()
      tree.add( subtree )
      subtree = self.parse__gen4()
      tree.add( subtree )
      return tree
    return tree
  def parse_line_line(self):
    current = self.tokens.current()
    rule = self.table[14][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(89, self.nonterminals[89]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 20:
      tree.astTransform = AstTransformNodeCreator('Line', {'tokens': 1})
      t = self.expect(58) # line
      tree.add(t)
      subtree = self.parse__gen4()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_pp_directive(self):
    current = self.tokens.current()
    rule = self.table[15][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(90, self.nonterminals[90]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 30:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_if_section()
      tree.add( subtree )
      return tree
    elif rule == 107:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_control_line()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen1(self):
    current = self.tokens.current()
    rule = self.table[16][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(91, self.nonterminals[91]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [17]):
      return tree
    if current == None:
      return tree
    if rule == 43:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_elseif_part()
      tree.add( subtree )
      subtree = self.parse__gen1()
      tree.add( subtree )
      return tree
    return tree
  def parse_warning_line(self):
    current = self.tokens.current()
    rule = self.table[17][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(92, self.nonterminals[92]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 76:
      tree.astTransform = AstTransformNodeCreator('Warning', {'tokens': 1})
      t = self.expect(69) # warning
      tree.add(t)
      subtree = self.parse__gen4()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen2(self):
    current = self.tokens.current()
    rule = self.table[18][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(93, self.nonterminals[93]))
    tree.list = 'slist'
    if current != None and (current.getId() in [71]):
      return tree
    if current == None:
      return tree
    if rule == 5:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_define_func_param()
      tree.add( subtree )
      subtree = self.parse__gen3()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen0(self):
    current = self.tokens.current()
    rule = self.table[19][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(94, self.nonterminals[94]))
    tree.list = 'tlist'
    if current != None and (current.getId() in [-1, 70, 14, 17]):
      return tree
    if current == None:
      return tree
    if rule == 25:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_pp_nodes()
      tree.add( subtree )
      t = self.expect(55) # separator
      tree.add(t)
      subtree = self.parse__gen0()
      tree.add( subtree )
      return tree
    return tree
  def parse_define_line(self):
    current = self.tokens.current()
    rule = self.table[20][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(95, self.nonterminals[95]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 56:
      tree.astTransform = AstTransformNodeCreator('Define', {'body': 2, 'ident': 1})
      t = self.expect(27) # define
      tree.add(t)
      t = self.expect(40) # identifier
      tree.add(t)
      subtree = self.parse_replacement_list()
      tree.add( subtree )
      return tree
    elif rule == 83:
      tree.astTransform = AstTransformNodeCreator('DefineFunction', {'body': 5, 'ident': 1, 'params': 3})
      t = self.expect(9) # define_function
      tree.add(t)
      t = self.expect(40) # identifier
      tree.add(t)
      t = self.expect(66) # lparen
      tree.add(t)
      subtree = self.parse__gen2()
      tree.add( subtree )
      t = self.expect(71) # rparen
      tree.add(t)
      subtree = self.parse_replacement_list()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_if_section(self):
    current = self.tokens.current()
    rule = self.table[21][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(96, self.nonterminals[96]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 104:
      tree.astTransform = AstTransformNodeCreator('IfSection', {'elif': 1, 'else': 2, 'if': 0})
      subtree = self.parse_if_part()
      tree.add( subtree )
      subtree = self.parse__gen1()
      tree.add( subtree )
      subtree = self.parse_else_part()
      tree.add( subtree )
      t = self.expect(70) # endif
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_pp_nodes(self):
    current = self.tokens.current()
    rule = self.table[22][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(97, self.nonterminals[97]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 81:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(18) # csource
      tree.add(t)
      return tree
    elif rule == 93:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_pp_directive()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_pp_file(self):
    current = self.tokens.current()
    rule = self.table[23][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(98, self.nonterminals[98]))
    tree.list = False
    if current == None:
      return tree
    if rule == 57:
      tree.astTransform = AstTransformNodeCreator('PPFile', {'nodes': 0})
      subtree = self.parse_pp_nodes_list()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_if_part(self):
    current = self.tokens.current()
    rule = self.table[24][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(99, self.nonterminals[99]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 15:
      tree.astTransform = AstTransformNodeCreator('IfDef', {'nodes': 2, 'ident': 1})
      t = self.expect(43) # ifdef
      tree.add(t)
      t = self.expect(40) # identifier
      tree.add(t)
      subtree = self.parse_pp_nodes_list()
      tree.add( subtree )
      return tree
    elif rule == 39:
      tree.astTransform = AstTransformNodeCreator('If', {'expr': 1, 'nodes': 2})
      t = self.expect(0) # if
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      subtree = self.parse_pp_nodes_list()
      tree.add( subtree )
      return tree
    elif rule == 51:
      tree.astTransform = AstTransformNodeCreator('IfNDef', {'nodes': 2, 'ident': 1})
      t = self.expect(25) # ifndef
      tree.add(t)
      t = self.expect(40) # identifier
      tree.add(t)
      subtree = self.parse_pp_nodes_list()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_else_part(self):
    current = self.tokens.current()
    rule = self.table[25][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(100, self.nonterminals[100]))
    tree.list = False
    if current != None and (current.getId() in [70]):
      return tree
    if current == None:
      return tree
    if rule == 119:
      tree.astTransform = AstTransformNodeCreator('Else', {'nodes': 1})
      t = self.expect(17) # else
      tree.add(t)
      subtree = self.parse_pp_nodes_list()
      tree.add( subtree )
      return tree
    return tree
  def parse_pp_tokens(self):
    current = self.tokens.current()
    rule = self.table[26][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(101, self.nonterminals[101]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 0:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(72) # defined_separator
      tree.add(t)
      return tree
    elif rule == 44:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(23) # pp_number
      tree.add(t)
      return tree
    elif rule == 73:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(13) # string_literal
      tree.add(t)
      return tree
    elif rule == 75:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(19) # character_constant
      tree.add(t)
      return tree
    elif rule == 85:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(48) # header_global
      tree.add(t)
      return tree
    elif rule == 87:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(5) # defined
      tree.add(t)
      return tree
    elif rule == 97:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_punctuator()
      tree.add( subtree )
      return tree
    elif rule == 131:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(40) # identifier
      tree.add(t)
      return tree
    elif rule == 134:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(53) # header_local
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_defined_identifier(self):
    current = self.tokens.current()
    rule = self.table[27][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(102, self.nonterminals[102]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 28:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(40) # identifier
      tree.add(t)
      return tree
    elif rule == 40:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(66) # lparen
      tree.add(t)
      t = self.expect(40) # identifier
      tree.add(t)
      t = self.expect(71) # rparen
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_control_line(self):
    current = self.tokens.current()
    rule = self.table[28][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(103, self.nonterminals[103]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 41:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_pragma_line()
      tree.add( subtree )
      return tree
    elif rule == 52:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_error_line()
      tree.add( subtree )
      return tree
    elif rule == 55:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_line_line()
      tree.add( subtree )
      return tree
    elif rule == 70:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_undef_line()
      tree.add( subtree )
      return tree
    elif rule == 79:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_warning_line()
      tree.add( subtree )
      return tree
    elif rule == 126:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_define_line()
      tree.add( subtree )
      return tree
    elif rule == 128:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_include_line()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_punctuator(self):
    current = self.tokens.current()
    rule = self.table[29][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(104, self.nonterminals[104]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 1:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(10) # gteq
      tree.add(t)
      return tree
    elif rule == 3:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(45) # bitor
      tree.add(t)
      return tree
    elif rule == 8:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(65) # bitandeq
      tree.add(t)
      return tree
    elif rule == 9:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(2) # exclamation_point
      tree.add(t)
      return tree
    elif rule == 11:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(59) # lsquare
      tree.add(t)
      return tree
    elif rule == 16:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(1) # arrow
      tree.add(t)
      return tree
    elif rule == 22:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(4) # subeq
      tree.add(t)
      return tree
    elif rule == 24:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(42) # tilde
      tree.add(t)
      return tree
    elif rule == 27:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(57) # gt
      tree.add(t)
      return tree
    elif rule == 29:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(3) # lshift
      tree.add(t)
      return tree
    elif rule == 32:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(49) # neq
      tree.add(t)
      return tree
    elif rule == 33:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(35) # bitand
      tree.add(t)
      return tree
    elif rule == 36:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(8) # addeq
      tree.add(t)
      return tree
    elif rule == 37:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(68) # sub
      tree.add(t)
      return tree
    elif rule == 38:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(22) # div
      tree.add(t)
      return tree
    elif rule == 42:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(37) # or
      tree.add(t)
      return tree
    elif rule == 45:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(12) # modeq
      tree.add(t)
      return tree
    elif rule == 47:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(56) # bitoreq
      tree.add(t)
      return tree
    elif rule == 49:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(21) # add
      tree.add(t)
      return tree
    elif rule == 53:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(34) # dot
      tree.add(t)
      return tree
    elif rule == 58:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(38) # lt
      tree.add(t)
      return tree
    elif rule == 62:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(15) # elipsis
      tree.add(t)
      return tree
    elif rule == 63:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(47) # lshifteq
      tree.add(t)
      return tree
    elif rule == 64:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(20) # diveq
      tree.add(t)
      return tree
    elif rule == 66:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(52) # mul
      tree.add(t)
      return tree
    elif rule == 68:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(44) # and
      tree.add(t)
      return tree
    elif rule == 71:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(66) # lparen
      tree.add(t)
      return tree
    elif rule == 72:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(46) # lbrace
      tree.add(t)
      return tree
    elif rule == 78:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(67) # semi
      tree.add(t)
      return tree
    elif rule == 84:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(54) # eq
      tree.add(t)
      return tree
    elif rule == 86:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(41) # comma
      tree.add(t)
      return tree
    elif rule == 89:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(50) # bitxor
      tree.add(t)
      return tree
    elif rule == 90:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(6) # rshifteq
      tree.add(t)
      return tree
    elif rule == 98:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(16) # muleq
      tree.add(t)
      return tree
    elif rule == 99:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(26) # assign
      tree.add(t)
      return tree
    elif rule == 103:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(28) # ampersand
      tree.add(t)
      return tree
    elif rule == 108:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(51) # rbrace
      tree.add(t)
      return tree
    elif rule == 110:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(63) # rsquare
      tree.add(t)
      return tree
    elif rule == 111:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(32) # decr
      tree.add(t)
      return tree
    elif rule == 114:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(11) # mod
      tree.add(t)
      return tree
    elif rule == 117:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(30) # poundpound
      tree.add(t)
      return tree
    elif rule == 121:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(60) # lteq
      tree.add(t)
      return tree
    elif rule == 122:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(33) # incr
      tree.add(t)
      return tree
    elif rule == 124:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(62) # bitxoreq
      tree.add(t)
      return tree
    elif rule == 125:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(71) # rparen
      tree.add(t)
      return tree
    elif rule == 129:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(29) # questionmark
      tree.add(t)
      return tree
    elif rule == 133:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(36) # pound
      tree.add(t)
      return tree
    elif rule == 138:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(24) # colon
      tree.add(t)
      return tree
    elif rule == 139:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(7) # rshift
      tree.add(t)
      return tree
    elif rule == 140:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(39) # bitnot
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_undef_line(self):
    current = self.tokens.current()
    rule = self.table[30][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(105, self.nonterminals[105]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 26:
      tree.astTransform = AstTransformNodeCreator('Undef', {'ident': 1})
      t = self.expect(73) # undef
      tree.add(t)
      t = self.expect(40) # identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__expr( self, rbp = 0):
    name = '_expr'
    if name not in self.expressionParsers:
      self.expressionParsers[name] = ExpressionParser__expr(self)
    return self.expressionParsers[name].parse(rbp)
