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
  def __init__(self, message):
    self.__dict__.update(locals())
  def __str__(self):
    return self.message
class ExpressionParser__expr:
  def __init__(self, parent):
    self.__dict__.update(locals())
    self.infixBp = {
      0: 14000,
      5: 10000,
      9: 10000,
      11: 12000,
      13: 11000,
      15: 1000,
      17: 12000,
      18: 9000,
      20: 12000,
      29: 2000,
      31: 11000,
      34: 5000,
      37: 3000,
      41: 4000,
      43: 7000,
      47: 8000,
      48: 6000,
      52: 8000,
      58: 9000,
      61: 9000,
      64: 15000,
      70: 9000,
    }
    self.prefixBp = {
      10: 13000,
      17: 13000,
      31: 13000,
      34: 13000,
      38: 13000,
      63: 13000,
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
    tree = ParseTree( NonTerminal(85, '_expr') )
    current = self.getCurrentToken()
    if not current:
      return tree
    elif current.getId() in [73]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self.expect(73) )
    elif current.getId() in [60]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self.expect(60) )
    elif current.getId() in [64]:
      tree.astTransform = AstTransformSubstitution(1)
      tree.nudMorphemeCount = 3
      tree.add( self.expect(64) )
      tree.add( self.parent.parse__expr() )
      tree.add( self.expect(69) )
    elif current.getId() in [6]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self.expect(6) )
    elif current.getId() in [10]:
      tree.astTransform = AstTransformNodeCreator('IsDefined', {'expr': 2})
      tree.nudMorphemeCount = 1
      tree.add( self.expect(10) )
    elif current.getId() in [38]:
      tree.astTransform = AstTransformNodeCreator('BitNOT', {'expr': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(38) )
      tree.add( self.parent.parse__expr( self.getPrefixBp(38) ) )
      tree.isPrefix = True
    elif current.getId() in [63]:
      tree.astTransform = AstTransformNodeCreator('Not', {'expr': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(63) )
      tree.add( self.parent.parse__expr( self.getPrefixBp(63) ) )
      tree.isPrefix = True
    elif current.getId() in [66]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self.expect(66) )
    elif current.getId() in [60]:
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      tree.nudMorphemeCount = 1
      tree.add( self.expect(60) )
    return tree
  def led(self, left):
    tree = ParseTree( NonTerminal(85, '_expr') )
    current = self.getCurrentToken()
    if current.getId() == 0: # 'defined_separator'
      tree.astTransform = AstTransformNodeCreator('IsDefined', {'expr': 2})
      tree.add(left)
      tree.add( self.expect(0) )
      tree.add( self.parent.parse_defined_identifier() )
    elif current.getId() == 9: # 'lshift'
      tree.astTransform = AstTransformNodeCreator('LeftShift', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(9) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(9) - modifier ) )
    elif current.getId() == 43: # 'bitor'
      tree.astTransform = AstTransformNodeCreator('BitOR', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(43) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(43) - modifier ) )
    elif current.getId() == 37: # 'or'
      tree.astTransform = AstTransformNodeCreator('Or', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(37) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(37) - modifier ) )
    elif current.getId() == 47: # 'neq'
      tree.astTransform = AstTransformNodeCreator('NotEquals', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(47) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(47) - modifier ) )
    elif current.getId() == 61: # 'gteq'
      tree.astTransform = AstTransformNodeCreator('GreaterThanEq', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(61) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(61) - modifier ) )
    elif current.getId() == 13: # 'add'
      tree.astTransform = AstTransformNodeCreator('Add', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(13) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(13) - modifier ) )
    elif current.getId() == 48: # 'bitxor'
      tree.astTransform = AstTransformNodeCreator('BitXOR', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(48) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(48) - modifier ) )
    elif current.getId() == 15: # 'comma'
      tree.astTransform = AstTransformNodeCreator('Comma', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(15) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(15) - modifier ) )
    elif current.getId() == 29: # 'questionmark'
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      tree.isExprNud = True
      tree.add(left)
      tree.add( self.expect(29) )
      modifier = 1
      tree.add( self.parent.parse__expr( self.getInfixBp(29) - modifier ) )
      tree.add( self.expect(23) )
      modifier = 1
      tree.add( self.parent.parse__expr( self.getInfixBp(29) - modifier ) )
    elif current.getId() == 17: # 'mul'
      tree.astTransform = AstTransformNodeCreator('Mul', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(17) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(17) - modifier ) )
    elif current.getId() == 31: # 'sub'
      tree.astTransform = AstTransformNodeCreator('Sub', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(31) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(31) - modifier ) )
    elif current.getId() == 20: # 'div'
      tree.astTransform = AstTransformNodeCreator('Div', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(20) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(20) - modifier ) )
    elif current.getId() == 18: # 'lt'
      tree.astTransform = AstTransformNodeCreator('LessThan', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(18) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(18) - modifier ) )
    elif current.getId() == 41: # 'and'
      tree.astTransform = AstTransformNodeCreator('And', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(41) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(41) - modifier ) )
    elif current.getId() == 5: # 'rshift'
      tree.astTransform = AstTransformNodeCreator('RightShift', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(5) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(5) - modifier ) )
    elif current.getId() == 11: # 'mod'
      tree.astTransform = AstTransformNodeCreator('Mod', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(11) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(11) - modifier ) )
    elif current.getId() == 70: # 'gt'
      tree.astTransform = AstTransformNodeCreator('GreaterThan', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(70) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(70) - modifier ) )
    elif current.getId() == 64: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      tree.add(left)
      tree.add( self.expect(64) )
      tree.add( self.parent.parse__gen5() )
      tree.add( self.expect(69) )
    elif current.getId() == 34: # 'bitand'
      tree.astTransform = AstTransformNodeCreator('BitAND', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(34) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(34) - modifier ) )
    elif current.getId() == 52: # 'eq'
      tree.astTransform = AstTransformNodeCreator('Equals', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(52) )
      modifier = 1
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(52) - modifier ) )
    elif current.getId() == 58: # 'lteq'
      tree.astTransform = AstTransformNodeCreator('LessThanEq', {'right': 2, 'left': 0})
      tree.add(left)
      tree.add( self.expect(58) )
      modifier = 0
      tree.isInfix = True
      tree.add( self.parent.parse__expr( self.getInfixBp(58) - modifier ) )
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
    0: 'defined_separator',
    1: 'define',
    2: 'subeq',
    3: 'tilde',
    4: 'elif',
    5: 'rshift',
    6: 'pp_number',
    7: 'addeq',
    8: 'ifndef',
    9: 'lshift',
    10: 'defined',
    11: 'mod',
    12: 'modeq',
    13: 'add',
    14: 'elipsis',
    15: 'comma',
    16: 'muleq',
    17: 'mul',
    18: 'lt',
    19: 'diveq',
    20: 'div',
    21: 'ifdef',
    22: 'line',
    23: 'colon',
    24: 'assign',
    25: 'if',
    26: 'ampersand',
    27: 'endif',
    28: 'decr',
    29: 'questionmark',
    30: 'separator',
    31: 'sub',
    32: 'else',
    33: 'incr',
    34: 'bitand',
    35: 'poundpound',
    36: 'pound',
    37: 'or',
    38: 'bitnot',
    39: 'pragma',
    40: 'dot',
    41: 'and',
    42: '_expr',
    43: 'bitor',
    44: 'lbrace',
    45: 'header_global',
    46: 'semi',
    47: 'neq',
    48: 'bitxor',
    49: 'rbrace',
    50: 'header_local',
    51: 'define_function',
    52: 'eq',
    53: 'bitoreq',
    54: 'csource',
    55: 'include',
    56: 'lsquare',
    57: 'arrow',
    58: 'lteq',
    59: 'bitxoreq',
    60: 'identifier',
    61: 'gteq',
    62: 'bitandeq',
    63: 'exclamation_point',
    64: 'lparen',
    65: 'warning',
    66: 'character_constant',
    67: 'lshifteq',
    68: 'error',
    69: 'rparen',
    70: 'gt',
    71: 'undef',
    72: 'rshifteq',
    73: 'string_literal',
    74: 'rsquare',
    'defined_separator': 0,
    'define': 1,
    'subeq': 2,
    'tilde': 3,
    'elif': 4,
    'rshift': 5,
    'pp_number': 6,
    'addeq': 7,
    'ifndef': 8,
    'lshift': 9,
    'defined': 10,
    'mod': 11,
    'modeq': 12,
    'add': 13,
    'elipsis': 14,
    'comma': 15,
    'muleq': 16,
    'mul': 17,
    'lt': 18,
    'diveq': 19,
    'div': 20,
    'ifdef': 21,
    'line': 22,
    'colon': 23,
    'assign': 24,
    'if': 25,
    'ampersand': 26,
    'endif': 27,
    'decr': 28,
    'questionmark': 29,
    'separator': 30,
    'sub': 31,
    'else': 32,
    'incr': 33,
    'bitand': 34,
    'poundpound': 35,
    'pound': 36,
    'or': 37,
    'bitnot': 38,
    'pragma': 39,
    'dot': 40,
    'and': 41,
    '_expr': 42,
    'bitor': 43,
    'lbrace': 44,
    'header_global': 45,
    'semi': 46,
    'neq': 47,
    'bitxor': 48,
    'rbrace': 49,
    'header_local': 50,
    'define_function': 51,
    'eq': 52,
    'bitoreq': 53,
    'csource': 54,
    'include': 55,
    'lsquare': 56,
    'arrow': 57,
    'lteq': 58,
    'bitxoreq': 59,
    'identifier': 60,
    'gteq': 61,
    'bitandeq': 62,
    'exclamation_point': 63,
    'lparen': 64,
    'warning': 65,
    'character_constant': 66,
    'lshifteq': 67,
    'error': 68,
    'rparen': 69,
    'gt': 70,
    'undef': 71,
    'rshifteq': 72,
    'string_literal': 73,
    'rsquare': 74,
  }
  # Quark - finite string set maps one string to exactly one int, and vice versa
  nonterminals = {
    75: 'if_part',
    76: 'pp_tokens',
    77: 'else_part',
    78: 'elseif_part',
    79: 'define_func_param',
    80: 'error_line',
    81: 'include_type',
    82: 'defined_identifier',
    83: '_gen4',
    84: 'elipsis_opt',
    85: '_expr',
    86: 'pp_directive',
    87: 'include_line',
    88: 'pragma_line',
    89: 'warning_line',
    90: '_gen6',
    91: 'pp_file',
    92: 'if_section',
    93: '_gen2',
    94: 'pp_nodes',
    95: 'undef_line',
    96: '_gen0',
    97: 'punctuator',
    98: 'control_line',
    99: '_gen1',
    100: 'pp_nodes_list',
    101: 'replacement_list',
    102: 'line_line',
    103: 'define_line',
    104: '_gen3',
    105: '_gen5',
    'if_part': 75,
    'pp_tokens': 76,
    'else_part': 77,
    'elseif_part': 78,
    'define_func_param': 79,
    'error_line': 80,
    'include_type': 81,
    'defined_identifier': 82,
    '_gen4': 83,
    'elipsis_opt': 84,
    '_expr': 85,
    'pp_directive': 86,
    'include_line': 87,
    'pragma_line': 88,
    'warning_line': 89,
    '_gen6': 90,
    'pp_file': 91,
    'if_section': 92,
    '_gen2': 93,
    'pp_nodes': 94,
    'undef_line': 95,
    '_gen0': 96,
    'punctuator': 97,
    'control_line': 98,
    '_gen1': 99,
    'pp_nodes_list': 100,
    'replacement_list': 101,
    'line_line': 102,
    'define_line': 103,
    '_gen3': 104,
    '_gen5': 105,
  }
  # table[nonterminal][terminal] = rule
  table = [
    [-1, -1, -1, -1, -1, -1, -1, -1, 30, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 39, -1, -1, -1, 134, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [52, -1, 82, 82, -1, 82, 103, 82, -1, 82, 0, 82, 82, 82, 82, 82, 82, 82, 82, 82, 82, -1, -1, 82, 82, -1, 82, -1, 82, 82, -1, 82, -1, 82, 82, 82, 82, 82, 82, -1, 82, 82, -1, 82, 82, 8, 82, 82, 82, 82, 16, -1, 82, 82, -1, -1, 82, 82, 82, 82, 138, 82, 82, 82, 82, -1, 71, 82, -1, 82, 82, -1, 82, 139, 82],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 137, -1, -1, -1, -1, 128, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, 97, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 99, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 70, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 32, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 48, -1, -1, -1, -1, 13, -1, -1, -1, -1, -1, -1, -1, -1, -1, 56, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 132, -1, -1, -1, 47, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [105, -1, 105, 105, -1, 105, 105, 105, -1, 105, 105, 105, 105, 105, 105, 105, 105, 105, 105, 105, 105, -1, -1, 105, 105, -1, 105, -1, 105, 105, 108, 105, -1, 105, 105, 105, 105, 105, 105, -1, 105, 105, -1, 105, 105, 105, 105, 105, 105, 105, 105, -1, 105, 105, -1, -1, 105, 105, 105, 105, 105, 105, 105, 105, 105, -1, 105, 105, -1, 105, 105, -1, 105, 105, 105],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 53, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, 135, -1, -1, -1, -1, -1, -1, 26, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 26, 135, -1, -1, 26, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 135, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 135, -1, -1, -1, 135, -1, -1, -1, -1, -1, -1, -1, -1, -1, 135, -1, -1, 135, -1, -1, 135, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 3, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 5, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 77, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 121, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, 64, -1, -1, -1, -1, -1, -1, 64, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 64, 64, -1, -1, 64, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 64, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 64, -1, -1, 64, 64, -1, -1, -1, -1, -1, -1, -1, -1, -1, 64, -1, -1, 64, -1, -1, 64, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, 23, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 23, -1, -1, -1, 23, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 74, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 74, -1, -1, -1, -1, -1, -1, -1, -1, 83, -1, -1, -1, -1, -1],
    [-1, 84, -1, -1, -1, -1, -1, -1, 84, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 84, 84, -1, -1, 84, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 84, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 84, -1, -1, 20, 84, -1, -1, -1, -1, -1, -1, -1, -1, -1, 84, -1, -1, 84, -1, -1, 84, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 86, -1, -1, -1],
    [-1, 96, -1, -1, 66, -1, -1, -1, 96, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 96, 96, -1, -1, 96, -1, 66, -1, -1, -1, -1, 66, -1, -1, -1, -1, -1, -1, 96, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 96, -1, -1, 96, 96, -1, -1, -1, -1, -1, -1, -1, -1, -1, 96, -1, -1, 96, -1, -1, 96, -1, -1, -1],
    [-1, -1, 72, 79, -1, 89, -1, 91, -1, 69, -1, 102, 104, 110, 116, 141, 123, 111, 51, 36, 61, -1, -1, 67, 50, -1, 1, -1, 117, 131, -1, 95, -1, 94, 114, 125, 115, 109, 119, -1, 42, 129, -1, 136, 2, -1, 130, 10, 12, 76, -1, -1, 126, 21, -1, -1, 24, 45, 28, 31, -1, 41, 34, 14, 62, -1, -1, 118, -1, 60, 7, -1, 120, -1, 33],
    [-1, 90, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 92, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 106, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 90, -1, -1, -1, 107, -1, -1, -1, -1, -1, -1, -1, -1, -1, 15, -1, -1, 78, -1, -1, 65, -1, -1, -1],
    [-1, -1, -1, -1, 68, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 127, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, 100, -1, -1, 63, -1, -1, -1, 100, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 100, 100, -1, -1, 100, -1, 63, -1, -1, -1, -1, 63, -1, -1, -1, -1, -1, -1, 100, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 100, -1, -1, 100, 100, -1, -1, -1, -1, -1, -1, -1, -1, -1, 100, -1, -1, 100, -1, -1, 100, -1, -1, -1],
    [122, -1, 122, 122, -1, 122, 122, 122, -1, 122, 122, 122, 122, 122, 122, 122, 122, 122, 122, 122, 122, -1, -1, 122, 122, -1, 122, -1, 122, 122, 18, 122, -1, 122, 122, 122, 122, 122, 122, -1, 122, 122, -1, 122, 122, 122, 122, 122, 122, 122, 122, -1, 122, 122, -1, -1, 122, 122, 122, 122, 122, 122, 122, 122, 122, -1, 122, 122, -1, 122, 122, -1, 122, 122, 122],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 112, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, 140, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 55, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 87, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 81, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, 113, -1, -1, -1, 113, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 113, -1, -1, -1, 113, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 113, -1, -1, 113, 113, -1, 113, -1, -1, -1, -1, -1, -1, 113, -1],
  ]
  TERMINAL_DEFINED_SEPARATOR = 0
  TERMINAL_DEFINE = 1
  TERMINAL_SUBEQ = 2
  TERMINAL_TILDE = 3
  TERMINAL_ELIF = 4
  TERMINAL_RSHIFT = 5
  TERMINAL_PP_NUMBER = 6
  TERMINAL_ADDEQ = 7
  TERMINAL_IFNDEF = 8
  TERMINAL_LSHIFT = 9
  TERMINAL_DEFINED = 10
  TERMINAL_MOD = 11
  TERMINAL_MODEQ = 12
  TERMINAL_ADD = 13
  TERMINAL_ELIPSIS = 14
  TERMINAL_COMMA = 15
  TERMINAL_MULEQ = 16
  TERMINAL_MUL = 17
  TERMINAL_LT = 18
  TERMINAL_DIVEQ = 19
  TERMINAL_DIV = 20
  TERMINAL_IFDEF = 21
  TERMINAL_LINE = 22
  TERMINAL_COLON = 23
  TERMINAL_ASSIGN = 24
  TERMINAL_IF = 25
  TERMINAL_AMPERSAND = 26
  TERMINAL_ENDIF = 27
  TERMINAL_DECR = 28
  TERMINAL_QUESTIONMARK = 29
  TERMINAL_SEPARATOR = 30
  TERMINAL_SUB = 31
  TERMINAL_ELSE = 32
  TERMINAL_INCR = 33
  TERMINAL_BITAND = 34
  TERMINAL_POUNDPOUND = 35
  TERMINAL_POUND = 36
  TERMINAL_OR = 37
  TERMINAL_BITNOT = 38
  TERMINAL_PRAGMA = 39
  TERMINAL_DOT = 40
  TERMINAL_AND = 41
  TERMINAL__EXPR = 42
  TERMINAL_BITOR = 43
  TERMINAL_LBRACE = 44
  TERMINAL_HEADER_GLOBAL = 45
  TERMINAL_SEMI = 46
  TERMINAL_NEQ = 47
  TERMINAL_BITXOR = 48
  TERMINAL_RBRACE = 49
  TERMINAL_HEADER_LOCAL = 50
  TERMINAL_DEFINE_FUNCTION = 51
  TERMINAL_EQ = 52
  TERMINAL_BITOREQ = 53
  TERMINAL_CSOURCE = 54
  TERMINAL_INCLUDE = 55
  TERMINAL_LSQUARE = 56
  TERMINAL_ARROW = 57
  TERMINAL_LTEQ = 58
  TERMINAL_BITXOREQ = 59
  TERMINAL_IDENTIFIER = 60
  TERMINAL_GTEQ = 61
  TERMINAL_BITANDEQ = 62
  TERMINAL_EXCLAMATION_POINT = 63
  TERMINAL_LPAREN = 64
  TERMINAL_WARNING = 65
  TERMINAL_CHARACTER_CONSTANT = 66
  TERMINAL_LSHIFTEQ = 67
  TERMINAL_ERROR = 68
  TERMINAL_RPAREN = 69
  TERMINAL_GT = 70
  TERMINAL_UNDEF = 71
  TERMINAL_RSHIFTEQ = 72
  TERMINAL_STRING_LITERAL = 73
  TERMINAL_RSQUARE = 74
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
  def parse_if_part(self):
    current = self.tokens.current()
    rule = self.table[0][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(75, self.nonterminals[75]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 30:
      tree.astTransform = AstTransformNodeCreator('IfNDef', {'nodes': 2, 'ident': 1})
      t = self.expect(8) # ifndef
      tree.add(t)
      t = self.expect(60) # identifier
      tree.add(t)
      subtree = self.parse_pp_nodes_list()
      tree.add( subtree )
      return tree
    elif rule == 39:
      tree.astTransform = AstTransformNodeCreator('IfDef', {'nodes': 2, 'ident': 1})
      t = self.expect(21) # ifdef
      tree.add(t)
      t = self.expect(60) # identifier
      tree.add(t)
      subtree = self.parse_pp_nodes_list()
      tree.add( subtree )
      return tree
    elif rule == 134:
      tree.astTransform = AstTransformNodeCreator('If', {'expr': 1, 'nodes': 2})
      t = self.expect(25) # if
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      subtree = self.parse_pp_nodes_list()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_pp_tokens(self):
    current = self.tokens.current()
    rule = self.table[1][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(76, self.nonterminals[76]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 0:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(10) # defined
      tree.add(t)
      return tree
    elif rule == 8:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(45) # header_global
      tree.add(t)
      return tree
    elif rule == 16:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(50) # header_local
      tree.add(t)
      return tree
    elif rule == 52:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(0) # defined_separator
      tree.add(t)
      return tree
    elif rule == 71:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(66) # character_constant
      tree.add(t)
      return tree
    elif rule == 82:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_punctuator()
      tree.add( subtree )
      return tree
    elif rule == 103:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(6) # pp_number
      tree.add(t)
      return tree
    elif rule == 138:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(60) # identifier
      tree.add(t)
      return tree
    elif rule == 139:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(73) # string_literal
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_else_part(self):
    current = self.tokens.current()
    rule = self.table[2][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(77, self.nonterminals[77]))
    tree.list = False
    if current != None and (current.getId() in [27]):
      return tree
    if current == None:
      return tree
    if rule == 128:
      tree.astTransform = AstTransformNodeCreator('Else', {'nodes': 1})
      t = self.expect(32) # else
      tree.add(t)
      subtree = self.parse_pp_nodes_list()
      tree.add( subtree )
      return tree
    return tree
  def parse_elseif_part(self):
    current = self.tokens.current()
    rule = self.table[3][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(78, self.nonterminals[78]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 97:
      tree.astTransform = AstTransformNodeCreator('ElseIf', {'expr': 1, 'nodes': 2})
      t = self.expect(4) # elif
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      subtree = self.parse_pp_nodes_list()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_define_func_param(self):
    current = self.tokens.current()
    rule = self.table[4][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(79, self.nonterminals[79]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 70:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(60) # identifier
      tree.add(t)
      return tree
    elif rule == 99:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(14) # elipsis
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_error_line(self):
    current = self.tokens.current()
    rule = self.table[5][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(80, self.nonterminals[80]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 32:
      tree.astTransform = AstTransformNodeCreator('Error', {'tokens': 1})
      t = self.expect(68) # error
      tree.add(t)
      subtree = self.parse__gen4()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_include_type(self):
    current = self.tokens.current()
    rule = self.table[6][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(81, self.nonterminals[81]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 13:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(50) # header_local
      tree.add(t)
      return tree
    elif rule == 48:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(45) # header_global
      tree.add(t)
      return tree
    elif rule == 56:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(60) # identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_defined_identifier(self):
    current = self.tokens.current()
    rule = self.table[7][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(82, self.nonterminals[82]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 47:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(64) # lparen
      tree.add(t)
      t = self.expect(60) # identifier
      tree.add(t)
      t = self.expect(69) # rparen
      tree.add(t)
      return tree
    elif rule == 132:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(60) # identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen4(self):
    current = self.tokens.current()
    rule = self.table[8][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(83, self.nonterminals[83]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [30]):
      return tree
    if current == None:
      return tree
    if rule == 105:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_pp_tokens()
      tree.add( subtree )
      subtree = self.parse__gen4()
      tree.add( subtree )
      return tree
    return tree
  def parse_elipsis_opt(self):
    current = self.tokens.current()
    rule = self.table[9][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(84, self.nonterminals[84]))
    tree.list = False
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 53:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(15) # comma
      tree.add(t)
      t = self.expect(14) # elipsis
      tree.add(t)
      return tree
    return tree
  def parse_pp_directive(self):
    current = self.tokens.current()
    rule = self.table[11][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(86, self.nonterminals[86]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 26:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_if_section()
      tree.add( subtree )
      return tree
    elif rule == 135:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_control_line()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_include_line(self):
    current = self.tokens.current()
    rule = self.table[12][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(87, self.nonterminals[87]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 3:
      tree.astTransform = AstTransformNodeCreator('Include', {'file': 1})
      t = self.expect(55) # include
      tree.add(t)
      subtree = self.parse_include_type()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_pragma_line(self):
    current = self.tokens.current()
    rule = self.table[13][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(88, self.nonterminals[88]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 5:
      tree.astTransform = AstTransformNodeCreator('Pragma', {'tokens': 1})
      t = self.expect(39) # pragma
      tree.add(t)
      subtree = self.parse__gen4()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_warning_line(self):
    current = self.tokens.current()
    rule = self.table[14][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(89, self.nonterminals[89]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 77:
      tree.astTransform = AstTransformNodeCreator('Warning', {'tokens': 1})
      t = self.expect(65) # warning
      tree.add(t)
      subtree = self.parse__gen4()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen6(self):
    current = self.tokens.current()
    rule = self.table[15][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(90, self.nonterminals[90]))
    tree.list = 'slist'
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 121:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(15) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse__expr()
      tree.add( subtree )
      subtree = self.parse__gen6()
      tree.add( subtree )
      return tree
    return tree
  def parse_pp_file(self):
    current = self.tokens.current()
    rule = self.table[16][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(91, self.nonterminals[91]))
    tree.list = False
    if current == None:
      return tree
    if rule == 64:
      tree.astTransform = AstTransformNodeCreator('PPFile', {'nodes': 0})
      subtree = self.parse_pp_nodes_list()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_if_section(self):
    current = self.tokens.current()
    rule = self.table[17][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(92, self.nonterminals[92]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 23:
      tree.astTransform = AstTransformNodeCreator('IfSection', {'elif': 1, 'else': 2, 'if': 0})
      subtree = self.parse_if_part()
      tree.add( subtree )
      subtree = self.parse__gen1()
      tree.add( subtree )
      subtree = self.parse_else_part()
      tree.add( subtree )
      t = self.expect(27) # endif
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen2(self):
    current = self.tokens.current()
    rule = self.table[18][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(93, self.nonterminals[93]))
    tree.list = 'slist'
    if current != None and (current.getId() in [69]):
      return tree
    if current == None:
      return tree
    if rule == 74:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_define_func_param()
      tree.add( subtree )
      subtree = self.parse__gen3()
      tree.add( subtree )
      return tree
    return tree
  def parse_pp_nodes(self):
    current = self.tokens.current()
    rule = self.table[19][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(94, self.nonterminals[94]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 20:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(54) # csource
      tree.add(t)
      return tree
    elif rule == 84:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_pp_directive()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_undef_line(self):
    current = self.tokens.current()
    rule = self.table[20][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(95, self.nonterminals[95]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 86:
      tree.astTransform = AstTransformNodeCreator('Undef', {'ident': 1})
      t = self.expect(71) # undef
      tree.add(t)
      t = self.expect(60) # identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen0(self):
    current = self.tokens.current()
    rule = self.table[21][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(96, self.nonterminals[96]))
    tree.list = 'tlist'
    if current != None and (current.getId() in [-1, 27, 4, 32]):
      return tree
    if current == None:
      return tree
    if rule == 96:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_pp_nodes()
      tree.add( subtree )
      t = self.expect(30) # separator
      tree.add(t)
      subtree = self.parse__gen0()
      tree.add( subtree )
      return tree
    return tree
  def parse_punctuator(self):
    current = self.tokens.current()
    rule = self.table[22][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(97, self.nonterminals[97]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 1:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(26) # ampersand
      tree.add(t)
      return tree
    elif rule == 2:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(44) # lbrace
      tree.add(t)
      return tree
    elif rule == 7:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(70) # gt
      tree.add(t)
      return tree
    elif rule == 10:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(47) # neq
      tree.add(t)
      return tree
    elif rule == 12:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(48) # bitxor
      tree.add(t)
      return tree
    elif rule == 14:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(63) # exclamation_point
      tree.add(t)
      return tree
    elif rule == 21:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(53) # bitoreq
      tree.add(t)
      return tree
    elif rule == 24:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(56) # lsquare
      tree.add(t)
      return tree
    elif rule == 28:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(58) # lteq
      tree.add(t)
      return tree
    elif rule == 31:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(59) # bitxoreq
      tree.add(t)
      return tree
    elif rule == 33:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(74) # rsquare
      tree.add(t)
      return tree
    elif rule == 34:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(62) # bitandeq
      tree.add(t)
      return tree
    elif rule == 36:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(19) # diveq
      tree.add(t)
      return tree
    elif rule == 41:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(61) # gteq
      tree.add(t)
      return tree
    elif rule == 42:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(40) # dot
      tree.add(t)
      return tree
    elif rule == 45:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(57) # arrow
      tree.add(t)
      return tree
    elif rule == 50:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(24) # assign
      tree.add(t)
      return tree
    elif rule == 51:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(18) # lt
      tree.add(t)
      return tree
    elif rule == 60:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(69) # rparen
      tree.add(t)
      return tree
    elif rule == 61:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(20) # div
      tree.add(t)
      return tree
    elif rule == 62:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(64) # lparen
      tree.add(t)
      return tree
    elif rule == 67:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(23) # colon
      tree.add(t)
      return tree
    elif rule == 69:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(9) # lshift
      tree.add(t)
      return tree
    elif rule == 72:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(2) # subeq
      tree.add(t)
      return tree
    elif rule == 76:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(49) # rbrace
      tree.add(t)
      return tree
    elif rule == 79:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(3) # tilde
      tree.add(t)
      return tree
    elif rule == 89:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(5) # rshift
      tree.add(t)
      return tree
    elif rule == 91:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(7) # addeq
      tree.add(t)
      return tree
    elif rule == 94:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(33) # incr
      tree.add(t)
      return tree
    elif rule == 95:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(31) # sub
      tree.add(t)
      return tree
    elif rule == 102:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(11) # mod
      tree.add(t)
      return tree
    elif rule == 104:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(12) # modeq
      tree.add(t)
      return tree
    elif rule == 109:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(37) # or
      tree.add(t)
      return tree
    elif rule == 110:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(13) # add
      tree.add(t)
      return tree
    elif rule == 111:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(17) # mul
      tree.add(t)
      return tree
    elif rule == 114:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(34) # bitand
      tree.add(t)
      return tree
    elif rule == 115:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(36) # pound
      tree.add(t)
      return tree
    elif rule == 116:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(14) # elipsis
      tree.add(t)
      return tree
    elif rule == 117:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(28) # decr
      tree.add(t)
      return tree
    elif rule == 118:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(67) # lshifteq
      tree.add(t)
      return tree
    elif rule == 119:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(38) # bitnot
      tree.add(t)
      return tree
    elif rule == 120:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(72) # rshifteq
      tree.add(t)
      return tree
    elif rule == 123:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(16) # muleq
      tree.add(t)
      return tree
    elif rule == 125:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(35) # poundpound
      tree.add(t)
      return tree
    elif rule == 126:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(52) # eq
      tree.add(t)
      return tree
    elif rule == 129:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(41) # and
      tree.add(t)
      return tree
    elif rule == 130:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(46) # semi
      tree.add(t)
      return tree
    elif rule == 131:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(29) # questionmark
      tree.add(t)
      return tree
    elif rule == 136:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(43) # bitor
      tree.add(t)
      return tree
    elif rule == 141:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(15) # comma
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_control_line(self):
    current = self.tokens.current()
    rule = self.table[23][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(98, self.nonterminals[98]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 15:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_warning_line()
      tree.add( subtree )
      return tree
    elif rule == 65:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_undef_line()
      tree.add( subtree )
      return tree
    elif rule == 78:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_error_line()
      tree.add( subtree )
      return tree
    elif rule == 90:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_define_line()
      tree.add( subtree )
      return tree
    elif rule == 92:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_line_line()
      tree.add( subtree )
      return tree
    elif rule == 106:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_pragma_line()
      tree.add( subtree )
      return tree
    elif rule == 107:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_include_line()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen1(self):
    current = self.tokens.current()
    rule = self.table[24][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(99, self.nonterminals[99]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [32]):
      return tree
    if current == None:
      return tree
    if rule == 68:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_elseif_part()
      tree.add( subtree )
      subtree = self.parse__gen1()
      tree.add( subtree )
      return tree
    return tree
  def parse_pp_nodes_list(self):
    current = self.tokens.current()
    rule = self.table[25][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(100, self.nonterminals[100]))
    tree.list = False
    if current != None and (current.getId() in [4, 32, 27, -1]):
      return tree
    if current == None:
      return tree
    if rule == 100:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen0()
      tree.add( subtree )
      return tree
    return tree
  def parse_replacement_list(self):
    current = self.tokens.current()
    rule = self.table[26][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(101, self.nonterminals[101]))
    tree.list = False
    if current != None and (current.getId() in [30]):
      return tree
    if current == None:
      return tree
    if rule == 122:
      tree.astTransform = AstTransformNodeCreator('ReplacementList', {'tokens': 0})
      subtree = self.parse__gen4()
      tree.add( subtree )
      return tree
    return tree
  def parse_line_line(self):
    current = self.tokens.current()
    rule = self.table[27][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(102, self.nonterminals[102]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 112:
      tree.astTransform = AstTransformNodeCreator('Line', {'tokens': 1})
      t = self.expect(22) # line
      tree.add(t)
      subtree = self.parse__gen4()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_define_line(self):
    current = self.tokens.current()
    rule = self.table[28][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(103, self.nonterminals[103]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 55:
      tree.astTransform = AstTransformNodeCreator('DefineFunction', {'body': 5, 'ident': 1, 'params': 3})
      t = self.expect(51) # define_function
      tree.add(t)
      t = self.expect(60) # identifier
      tree.add(t)
      t = self.expect(64) # lparen
      tree.add(t)
      subtree = self.parse__gen2()
      tree.add( subtree )
      t = self.expect(69) # rparen
      tree.add(t)
      subtree = self.parse_replacement_list()
      tree.add( subtree )
      return tree
    elif rule == 140:
      tree.astTransform = AstTransformNodeCreator('Define', {'body': 2, 'ident': 1})
      t = self.expect(1) # define
      tree.add(t)
      t = self.expect(60) # identifier
      tree.add(t)
      subtree = self.parse_replacement_list()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen3(self):
    current = self.tokens.current()
    rule = self.table[29][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(104, self.nonterminals[104]))
    tree.list = 'slist'
    if current != None and (current.getId() in [69]):
      return tree
    if current == None:
      return tree
    if rule == 87:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(15) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse_define_func_param()
      tree.add( subtree )
      subtree = self.parse__gen3()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen5(self):
    current = self.tokens.current()
    rule = self.table[30][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(105, self.nonterminals[105]))
    tree.list = 'slist'
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 113:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr()
      tree.add( subtree )
      subtree = self.parse__gen6()
      tree.add( subtree )
      return tree
    return tree
  def parse__expr( self, rbp = 0):
    name = '_expr'
    if name not in self.expressionParsers:
      self.expressionParsers[name] = ExpressionParser__expr(self)
    return self.expressionParsers[name].parse(rbp)
