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
      0: 10000,
      3: 10000,
      5: 14000,
      7: 12000,
      10: 11000,
      19: 12000,
      27: 2000,
      30: 5000,
      32: 3000,
      33: 12000,
      36: 1000,
      38: 4000,
      39: 7000,
      44: 8000,
      45: 6000,
      48: 8000,
      57: 9000,
      58: 11000,
      62: 9000,
      65: 15000,
      66: 9000,
      71: 9000,
    }
    self.prefixBp = {
      30: 13000,
      33: 13000,
      34: 13000,
      35: 13000,
      58: 13000,
      70: 13000,
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
    tree = ParseTree( NonTerminal(102, '_expr') )
    current = self.getCurrentToken()
    if not current:
      return tree
    elif current.getId() in [34]:
      tree.astTransform = AstTransformNodeCreator('BitNOT', {'expr': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(34) )
      tree.add( self.parent.parse__expr( self.getPrefixBp(34) ) )
      tree.isPrefix = True
    elif current.getId() in [70]:
      tree.astTransform = AstTransformNodeCreator('Not', {'expr': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(70) )
      tree.add( self.parent.parse__expr( self.getPrefixBp(70) ) )
      tree.isPrefix = True
    elif current.getId() in [69]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      return self.expect( 69 )
    elif current.getId() in [73]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      return self.expect( 73 )
    elif current.getId() in [35]:
      tree.astTransform = AstTransformNodeCreator('IsDefined', {'expr': 2})
      tree.nudMorphemeCount = 1
      return self.expect( 35 )
    elif current.getId() in [61]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      return self.expect( 61 )
    elif current.getId() in [9]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      return self.expect( 9 )
    elif current.getId() in [65]:
      tree.astTransform = AstTransformSubstitution(1)
      tree.nudMorphemeCount = 3
      tree.add( self.expect(65) )
      tree.add( self.parent.parse__expr() )
      tree.add( self.expect(11) )
    elif current.getId() in [61]:
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      tree.nudMorphemeCount = 1
      return self.expect( 61 )
    return tree
  def led(self, left):
    tree = ParseTree( NonTerminal(102, '_expr') )
    current = self.getCurrentToken()
    if current.getId() == 57: # 'lteq'
      tree.astTransform = AstTransformNodeCreator('LessThanEq', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(57) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(57) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 5: # 'defined_separator'
      tree.astTransform = AstTransformNodeCreator('IsDefined', {'expr': 2})
      if left:
        tree.add(left)
      tree.add( self.expect(5) )
      tree.add( self.parent.parse_defined_identifier() )
    elif current.getId() == 39: # 'bitor'
      tree.astTransform = AstTransformNodeCreator('BitOR', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(39) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(39) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 44: # 'neq'
      tree.astTransform = AstTransformNodeCreator('NotEquals', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(44) )
      modifier = 1
      tree.add( self.parent.parse__expr( self.getInfixBp(44) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 62: # 'gteq'
      tree.astTransform = AstTransformNodeCreator('GreaterThanEq', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(62) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(62) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 10: # 'add'
      tree.astTransform = AstTransformNodeCreator('Add', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(10) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(10) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 65: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(65) )
      tree.add( self.parent.parse__gen5() )
      tree.add( self.expect(11) )
    elif current.getId() == 45: # 'bitxor'
      tree.astTransform = AstTransformNodeCreator('BitXOR', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(45) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(45) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 36: # 'comma'
      tree.astTransform = AstTransformNodeCreator('Comma', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(36) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(36) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 33: # 'mul'
      tree.astTransform = AstTransformNodeCreator('Mul', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(33) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(33) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 58: # 'sub'
      tree.astTransform = AstTransformNodeCreator('Sub', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(58) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(58) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 0: # 'lshift'
      tree.astTransform = AstTransformNodeCreator('LeftShift', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(0) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(0) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 27: # 'questionmark'
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(27) )
      modifier = 1
      tree.add( self.parent.parse__expr( self.getInfixBp(27) - modifier ) )
      tree.add( self.expect(20) )
      modifier = 1
      tree.add( self.parent.parse__expr( self.getInfixBp(27) - modifier ) )
    elif current.getId() == 19: # 'div'
      tree.astTransform = AstTransformNodeCreator('Div', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(19) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(19) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 66: # 'lt'
      tree.astTransform = AstTransformNodeCreator('LessThan', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(66) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(66) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 38: # 'and'
      tree.astTransform = AstTransformNodeCreator('And', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(38) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(38) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 3: # 'rshift'
      tree.astTransform = AstTransformNodeCreator('RightShift', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(3) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(3) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 7: # 'mod'
      tree.astTransform = AstTransformNodeCreator('Mod', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(7) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(7) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 71: # 'gt'
      tree.astTransform = AstTransformNodeCreator('GreaterThan', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(71) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(71) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 32: # 'or'
      tree.astTransform = AstTransformNodeCreator('Or', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(32) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(32) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 30: # 'bitand'
      tree.astTransform = AstTransformNodeCreator('BitAND', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(30) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(30) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 48: # 'eq'
      tree.astTransform = AstTransformNodeCreator('Equals', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(48) )
      modifier = 1
      tree.add( self.parent.parse__expr( self.getInfixBp(48) - modifier ) )
      tree.isInfix = True
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
    0: 'lshift',
    1: 'subeq',
    2: 'tilde',
    3: 'rshift',
    4: 'addeq',
    5: 'defined_separator',
    6: 'elif',
    7: 'mod',
    8: 'modeq',
    9: 'pp_number',
    10: 'add',
    11: 'rparen',
    12: 'define',
    13: 'elipsis',
    14: 'muleq',
    15: 'else',
    16: 'csource',
    17: 'diveq',
    18: 'dot',
    19: 'div',
    20: 'colon',
    21: 'undef',
    22: 'assign',
    23: 'warning',
    24: 'ampersand',
    25: 'decr',
    26: 'ifdef',
    27: 'questionmark',
    28: 'separator',
    29: 'lshifteq',
    30: 'bitand',
    31: 'pound',
    32: 'or',
    33: 'mul',
    34: 'bitnot',
    35: 'defined',
    36: 'comma',
    37: 'poundpound',
    38: 'and',
    39: 'bitor',
    40: 'lbrace',
    41: 'pragma',
    42: 'header_global',
    43: 'include',
    44: 'neq',
    45: 'bitxor',
    46: 'rbrace',
    47: 'header_local',
    48: 'eq',
    49: '_expr',
    50: 'semi',
    51: 'bitoreq',
    52: 'line',
    53: 'lsquare',
    54: 'ifndef',
    55: 'incr',
    56: 'if',
    57: 'lteq',
    58: 'sub',
    59: 'bitxoreq',
    60: 'rsquare',
    61: 'identifier',
    62: 'gteq',
    63: 'arrow',
    64: 'bitandeq',
    65: 'lparen',
    66: 'lt',
    67: 'define_function',
    68: 'endif',
    69: 'character_constant',
    70: 'exclamation_point',
    71: 'gt',
    72: 'rshifteq',
    73: 'string_literal',
    74: 'error',
    'lshift': 0,
    'subeq': 1,
    'tilde': 2,
    'rshift': 3,
    'addeq': 4,
    'defined_separator': 5,
    'elif': 6,
    'mod': 7,
    'modeq': 8,
    'pp_number': 9,
    'add': 10,
    'rparen': 11,
    'define': 12,
    'elipsis': 13,
    'muleq': 14,
    'else': 15,
    'csource': 16,
    'diveq': 17,
    'dot': 18,
    'div': 19,
    'colon': 20,
    'undef': 21,
    'assign': 22,
    'warning': 23,
    'ampersand': 24,
    'decr': 25,
    'ifdef': 26,
    'questionmark': 27,
    'separator': 28,
    'lshifteq': 29,
    'bitand': 30,
    'pound': 31,
    'or': 32,
    'mul': 33,
    'bitnot': 34,
    'defined': 35,
    'comma': 36,
    'poundpound': 37,
    'and': 38,
    'bitor': 39,
    'lbrace': 40,
    'pragma': 41,
    'header_global': 42,
    'include': 43,
    'neq': 44,
    'bitxor': 45,
    'rbrace': 46,
    'header_local': 47,
    'eq': 48,
    '_expr': 49,
    'semi': 50,
    'bitoreq': 51,
    'line': 52,
    'lsquare': 53,
    'ifndef': 54,
    'incr': 55,
    'if': 56,
    'lteq': 57,
    'sub': 58,
    'bitxoreq': 59,
    'rsquare': 60,
    'identifier': 61,
    'gteq': 62,
    'arrow': 63,
    'bitandeq': 64,
    'lparen': 65,
    'lt': 66,
    'define_function': 67,
    'endif': 68,
    'character_constant': 69,
    'exclamation_point': 70,
    'gt': 71,
    'rshifteq': 72,
    'string_literal': 73,
    'error': 74,
  }
  # Quark - finite string set maps one string to exactly one int, and vice versa
  nonterminals = {
    75: 'if_section',
    76: 'if_part',
    77: 'pp_file',
    78: 'pp_nodes',
    79: 'elseif_part',
    80: 'error_line',
    81: '_gen3',
    82: 'define_line',
    83: 'include_type',
    84: '_gen4',
    85: '_gen5',
    86: 'pp_directive',
    87: '_gen1',
    88: 'warning_line',
    89: '_gen6',
    90: 'undef_line',
    91: 'replacement_list',
    92: 'define_func_param',
    93: 'defined_identifier',
    94: '_gen2',
    95: 'else_part',
    96: 'elipsis_opt',
    97: 'pp_tokens',
    98: '_gen0',
    99: 'control_line',
    100: 'punctuator',
    101: 'pp_nodes_list',
    102: '_expr',
    103: 'line_line',
    104: 'include_line',
    105: 'pragma_line',
    'if_section': 75,
    'if_part': 76,
    'pp_file': 77,
    'pp_nodes': 78,
    'elseif_part': 79,
    'error_line': 80,
    '_gen3': 81,
    'define_line': 82,
    'include_type': 83,
    '_gen4': 84,
    '_gen5': 85,
    'pp_directive': 86,
    '_gen1': 87,
    'warning_line': 88,
    '_gen6': 89,
    'undef_line': 90,
    'replacement_list': 91,
    'define_func_param': 92,
    'defined_identifier': 93,
    '_gen2': 94,
    'else_part': 95,
    'elipsis_opt': 96,
    'pp_tokens': 97,
    '_gen0': 98,
    'control_line': 99,
    'punctuator': 100,
    'pp_nodes_list': 101,
    '_expr': 102,
    'line_line': 103,
    'include_line': 104,
    'pragma_line': 105,
  }
  # table[nonterminal][terminal] = rule
  table = [
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 72, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 72, -1, 72, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 91, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 102, -1, 75, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 89, -1, -1, -1, 89, -1, -1, -1, -1, 89, -1, 89, -1, -1, 89, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 89, -1, 89, -1, -1, -1, -1, -1, -1, -1, -1, 89, -1, 89, -1, 89, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 89, -1, -1, -1, -1, -1, -1, 89],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 111, -1, -1, -1, 39, -1, -1, -1, -1, 111, -1, 111, -1, -1, 111, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 111, -1, 111, -1, -1, -1, -1, -1, -1, -1, -1, 111, -1, 111, -1, 111, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 111, -1, -1, -1, -1, -1, -1, 111],
    [-1, -1, -1, -1, -1, -1, 120, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 50],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 107, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 121, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 116, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 16, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 40, -1, -1, -1, -1, 81, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 9, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [106, 106, 106, 106, 106, 106, -1, 106, 106, 106, 106, 106, -1, 106, 106, -1, -1, 106, 106, 106, 106, -1, 106, -1, 106, 106, -1, 106, 109, 106, 106, 106, 106, 106, 106, 106, 106, 106, 106, 106, 106, -1, 106, -1, 106, 106, 106, 106, 106, -1, 106, 106, -1, 106, -1, 106, -1, 106, 106, 106, 106, 106, 106, 106, 106, 106, 106, -1, -1, 106, 106, 106, 106, 106, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, 124, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 124, 124, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 124, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 124, -1, -1, -1, 124, -1, -1, -1, 124, 124, -1, -1, 124, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 70, -1, -1, -1, -1, -1, -1, -1, -1, 70, -1, 70, -1, -1, 6, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 70, -1, 70, -1, -1, -1, -1, -1, -1, -1, -1, 70, -1, 6, -1, 6, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 70, -1, -1, -1, -1, -1, -1, 70],
    [-1, -1, -1, -1, -1, -1, 126, -1, -1, -1, -1, -1, -1, -1, -1, 74, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 61, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 84, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 42, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [60, 60, 60, 60, 60, 60, -1, 60, 60, 60, 60, 60, -1, 60, 60, -1, -1, 60, 60, 60, 60, -1, 60, -1, 60, 60, -1, 60, 24, 60, 60, 60, 60, 60, 60, 60, 60, 60, 60, 60, 60, -1, 60, -1, 60, 60, 60, 60, 60, -1, 60, 60, -1, 60, -1, 60, -1, 60, 60, 60, 60, 60, 60, 60, 60, 60, 60, -1, -1, 60, 60, 60, 60, 60, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 38, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 78, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 15, -1, -1, -1, 133, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 83, -1, 79, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 79, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 134, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 64, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 47, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [20, 20, 20, 20, 20, 54, -1, 20, 20, 95, 20, 20, -1, 20, 20, -1, -1, 20, 20, 20, 20, -1, 20, -1, 20, 20, -1, 20, -1, 20, 20, 20, 20, 20, 20, 104, 20, 20, 20, 20, 20, -1, 7, -1, 20, 20, 20, 22, 20, -1, 20, 20, -1, 20, -1, 20, -1, 20, 20, 20, 20, 129, 20, 20, 20, 20, 20, -1, -1, 65, 20, 20, 20, 98, -1],
    [-1, -1, -1, -1, -1, -1, 100, -1, -1, -1, -1, -1, 58, -1, -1, 100, 58, -1, -1, -1, -1, 58, -1, 58, -1, -1, 58, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 58, -1, 58, -1, -1, -1, -1, -1, -1, -1, -1, 58, -1, 58, -1, 58, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 58, 100, -1, -1, -1, -1, -1, 58],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 92, -1, -1, -1, -1, -1, -1, -1, -1, 105, -1, 31, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 77, -1, 137, -1, -1, -1, -1, -1, -1, -1, -1, 112, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 92, -1, -1, -1, -1, -1, -1, 132],
    [82, 90, 5, 96, 99, -1, -1, 108, 117, -1, 128, 4, -1, 56, 131, -1, -1, 67, 125, 68, 76, -1, 138, -1, 113, 85, -1, 88, -1, 0, 101, 114, 123, 1, 118, -1, 87, 73, 135, 140, 3, -1, -1, -1, 11, 13, 18, -1, 46, -1, 119, 26, -1, 27, -1, 69, -1, 17, 130, 36, 139, -1, 94, 2, 52, 57, 97, -1, -1, -1, 28, 80, 86, -1, -1],
    [-1, -1, -1, -1, -1, -1, 8, -1, -1, -1, -1, -1, 44, -1, -1, 8, 44, -1, -1, -1, -1, 44, -1, 44, -1, -1, 44, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 44, -1, 44, -1, -1, -1, -1, -1, -1, -1, -1, 44, -1, 44, -1, 44, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 44, 8, -1, -1, -1, -1, -1, 44],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 63, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 45, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 33, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  ]
  TERMINAL_LSHIFT = 0
  TERMINAL_SUBEQ = 1
  TERMINAL_TILDE = 2
  TERMINAL_RSHIFT = 3
  TERMINAL_ADDEQ = 4
  TERMINAL_DEFINED_SEPARATOR = 5
  TERMINAL_ELIF = 6
  TERMINAL_MOD = 7
  TERMINAL_MODEQ = 8
  TERMINAL_PP_NUMBER = 9
  TERMINAL_ADD = 10
  TERMINAL_RPAREN = 11
  TERMINAL_DEFINE = 12
  TERMINAL_ELIPSIS = 13
  TERMINAL_MULEQ = 14
  TERMINAL_ELSE = 15
  TERMINAL_CSOURCE = 16
  TERMINAL_DIVEQ = 17
  TERMINAL_DOT = 18
  TERMINAL_DIV = 19
  TERMINAL_COLON = 20
  TERMINAL_UNDEF = 21
  TERMINAL_ASSIGN = 22
  TERMINAL_WARNING = 23
  TERMINAL_AMPERSAND = 24
  TERMINAL_DECR = 25
  TERMINAL_IFDEF = 26
  TERMINAL_QUESTIONMARK = 27
  TERMINAL_SEPARATOR = 28
  TERMINAL_LSHIFTEQ = 29
  TERMINAL_BITAND = 30
  TERMINAL_POUND = 31
  TERMINAL_OR = 32
  TERMINAL_MUL = 33
  TERMINAL_BITNOT = 34
  TERMINAL_DEFINED = 35
  TERMINAL_COMMA = 36
  TERMINAL_POUNDPOUND = 37
  TERMINAL_AND = 38
  TERMINAL_BITOR = 39
  TERMINAL_LBRACE = 40
  TERMINAL_PRAGMA = 41
  TERMINAL_HEADER_GLOBAL = 42
  TERMINAL_INCLUDE = 43
  TERMINAL_NEQ = 44
  TERMINAL_BITXOR = 45
  TERMINAL_RBRACE = 46
  TERMINAL_HEADER_LOCAL = 47
  TERMINAL_EQ = 48
  TERMINAL__EXPR = 49
  TERMINAL_SEMI = 50
  TERMINAL_BITOREQ = 51
  TERMINAL_LINE = 52
  TERMINAL_LSQUARE = 53
  TERMINAL_IFNDEF = 54
  TERMINAL_INCR = 55
  TERMINAL_IF = 56
  TERMINAL_LTEQ = 57
  TERMINAL_SUB = 58
  TERMINAL_BITXOREQ = 59
  TERMINAL_RSQUARE = 60
  TERMINAL_IDENTIFIER = 61
  TERMINAL_GTEQ = 62
  TERMINAL_ARROW = 63
  TERMINAL_BITANDEQ = 64
  TERMINAL_LPAREN = 65
  TERMINAL_LT = 66
  TERMINAL_DEFINE_FUNCTION = 67
  TERMINAL_ENDIF = 68
  TERMINAL_CHARACTER_CONSTANT = 69
  TERMINAL_EXCLAMATION_POINT = 70
  TERMINAL_GT = 71
  TERMINAL_RSHIFTEQ = 72
  TERMINAL_STRING_LITERAL = 73
  TERMINAL_ERROR = 74
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
      raise SyntaxError( 'Syntax Error: Finished parsing without consuming all tokens.' )
    return tree
  def expect(self, terminalId):
    currentToken = self.tokens.current()
    if not currentToken:
      raise SyntaxError('No more tokens.  Expecting %s' % (self.terminals[terminalId]))
    if currentToken.getId() != terminalId:
      raise SyntaxError('Unexpected symbol when parsing %s.  Expected %s, got %s.' %(whosdaddy(), self.terminals[terminalId], currentToken if currentToken else 'None'))
    nextToken = self.tokens.advance()
    if nextToken and not self.isTerminal(nextToken.getId()):
      raise SyntaxError( 'Invalid symbol ID: %d (%s)' % (nextToken.getId(), nextToken) )
    return currentToken
  def parse_if_section(self):
    current = self.tokens.current()
    rule = self.table[0][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(75, self.nonterminals[75]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 72:
      tree.astTransform = AstTransformNodeCreator('IfSection', {'elif': 1, 'else': 2, 'if': 0})
      subtree = self.parse_if_part()
      tree.add( subtree )
      subtree = self.parse__gen1()
      tree.add( subtree )
      subtree = self.parse_else_part()
      tree.add( subtree )
      t = self.expect(68) # endif
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_if_part(self):
    current = self.tokens.current()
    rule = self.table[1][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(76, self.nonterminals[76]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 75:
      tree.astTransform = AstTransformNodeCreator('If', {'expr': 1, 'nodes': 2})
      t = self.expect(56) # if
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      subtree = self.parse_pp_nodes_list()
      tree.add( subtree )
      return tree
    elif rule == 91:
      tree.astTransform = AstTransformNodeCreator('IfDef', {'nodes': 2, 'ident': 1})
      t = self.expect(26) # ifdef
      tree.add(t)
      t = self.expect(61) # identifier
      tree.add(t)
      subtree = self.parse_pp_nodes_list()
      tree.add( subtree )
      return tree
    elif rule == 102:
      tree.astTransform = AstTransformNodeCreator('IfNDef', {'nodes': 2, 'ident': 1})
      t = self.expect(54) # ifndef
      tree.add(t)
      t = self.expect(61) # identifier
      tree.add(t)
      subtree = self.parse_pp_nodes_list()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_pp_file(self):
    current = self.tokens.current()
    rule = self.table[2][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(77, self.nonterminals[77]))
    tree.list = False
    if current == None:
      return tree
    if rule == 89:
      tree.astTransform = AstTransformNodeCreator('PPFile', {'nodes': 0})
      subtree = self.parse_pp_nodes_list()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_pp_nodes(self):
    current = self.tokens.current()
    rule = self.table[3][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(78, self.nonterminals[78]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 39:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(16) # csource
      tree.add(t)
      return tree
    elif rule == 111:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_pp_directive()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_elseif_part(self):
    current = self.tokens.current()
    rule = self.table[4][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(79, self.nonterminals[79]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 120:
      tree.astTransform = AstTransformNodeCreator('ElseIf', {'expr': 1, 'nodes': 2})
      t = self.expect(6) # elif
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      subtree = self.parse_pp_nodes_list()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_error_line(self):
    current = self.tokens.current()
    rule = self.table[5][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(80, self.nonterminals[80]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 50:
      tree.astTransform = AstTransformNodeCreator('Error', {'tokens': 1})
      t = self.expect(74) # error
      tree.add(t)
      subtree = self.parse__gen4()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen3(self):
    current = self.tokens.current()
    rule = self.table[6][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(81, self.nonterminals[81]))
    tree.list = 'slist'
    if current != None and (current.getId() in [11]):
      return tree
    if current == None:
      return tree
    if rule == 121:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(36) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse_define_func_param()
      tree.add( subtree )
      subtree = self.parse__gen3()
      tree.add( subtree )
      return tree
    return tree
  def parse_define_line(self):
    current = self.tokens.current()
    rule = self.table[7][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(82, self.nonterminals[82]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 16:
      tree.astTransform = AstTransformNodeCreator('DefineFunction', {'body': 5, 'ident': 1, 'params': 3})
      t = self.expect(67) # define_function
      tree.add(t)
      t = self.expect(61) # identifier
      tree.add(t)
      t = self.expect(65) # lparen
      tree.add(t)
      subtree = self.parse__gen2()
      tree.add( subtree )
      t = self.expect(11) # rparen
      tree.add(t)
      subtree = self.parse_replacement_list()
      tree.add( subtree )
      return tree
    elif rule == 116:
      tree.astTransform = AstTransformNodeCreator('Define', {'body': 2, 'ident': 1})
      t = self.expect(12) # define
      tree.add(t)
      t = self.expect(61) # identifier
      tree.add(t)
      subtree = self.parse_replacement_list()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_include_type(self):
    current = self.tokens.current()
    rule = self.table[8][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(83, self.nonterminals[83]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 9:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(61) # identifier
      tree.add(t)
      return tree
    elif rule == 40:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(42) # header_global
      tree.add(t)
      return tree
    elif rule == 81:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(47) # header_local
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen4(self):
    current = self.tokens.current()
    rule = self.table[9][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(84, self.nonterminals[84]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [28]):
      return tree
    if current == None:
      return tree
    if rule == 106:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_pp_tokens()
      tree.add( subtree )
      subtree = self.parse__gen4()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen5(self):
    current = self.tokens.current()
    rule = self.table[10][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(85, self.nonterminals[85]))
    tree.list = 'slist'
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 124:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr()
      tree.add( subtree )
      subtree = self.parse__gen6()
      tree.add( subtree )
      return tree
    return tree
  def parse_pp_directive(self):
    current = self.tokens.current()
    rule = self.table[11][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(86, self.nonterminals[86]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 6:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_if_section()
      tree.add( subtree )
      return tree
    elif rule == 70:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_control_line()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen1(self):
    current = self.tokens.current()
    rule = self.table[12][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(87, self.nonterminals[87]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [15]):
      return tree
    if current == None:
      return tree
    if rule == 126:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_elseif_part()
      tree.add( subtree )
      subtree = self.parse__gen1()
      tree.add( subtree )
      return tree
    return tree
  def parse_warning_line(self):
    current = self.tokens.current()
    rule = self.table[13][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(88, self.nonterminals[88]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 61:
      tree.astTransform = AstTransformNodeCreator('Warning', {'tokens': 1})
      t = self.expect(23) # warning
      tree.add(t)
      subtree = self.parse__gen4()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen6(self):
    current = self.tokens.current()
    rule = self.table[14][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(89, self.nonterminals[89]))
    tree.list = 'slist'
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 84:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(36) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse__expr()
      tree.add( subtree )
      subtree = self.parse__gen6()
      tree.add( subtree )
      return tree
    return tree
  def parse_undef_line(self):
    current = self.tokens.current()
    rule = self.table[15][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(90, self.nonterminals[90]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 42:
      tree.astTransform = AstTransformNodeCreator('Undef', {'ident': 1})
      t = self.expect(21) # undef
      tree.add(t)
      t = self.expect(61) # identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_replacement_list(self):
    current = self.tokens.current()
    rule = self.table[16][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(91, self.nonterminals[91]))
    tree.list = False
    if current != None and (current.getId() in [28]):
      return tree
    if current == None:
      return tree
    if rule == 60:
      tree.astTransform = AstTransformNodeCreator('ReplacementList', {'tokens': 0})
      subtree = self.parse__gen4()
      tree.add( subtree )
      return tree
    return tree
  def parse_define_func_param(self):
    current = self.tokens.current()
    rule = self.table[17][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(92, self.nonterminals[92]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 38:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(13) # elipsis
      tree.add(t)
      return tree
    elif rule == 78:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(61) # identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_defined_identifier(self):
    current = self.tokens.current()
    rule = self.table[18][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(93, self.nonterminals[93]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 15:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(61) # identifier
      tree.add(t)
      return tree
    elif rule == 133:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(65) # lparen
      tree.add(t)
      t = self.expect(61) # identifier
      tree.add(t)
      t = self.expect(11) # rparen
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen2(self):
    current = self.tokens.current()
    rule = self.table[19][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(94, self.nonterminals[94]))
    tree.list = 'slist'
    if current != None and (current.getId() in [11]):
      return tree
    if current == None:
      return tree
    if rule == 79:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_define_func_param()
      tree.add( subtree )
      subtree = self.parse__gen3()
      tree.add( subtree )
      return tree
    return tree
  def parse_else_part(self):
    current = self.tokens.current()
    rule = self.table[20][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(95, self.nonterminals[95]))
    tree.list = False
    if current != None and (current.getId() in [68]):
      return tree
    if current == None:
      return tree
    if rule == 134:
      tree.astTransform = AstTransformNodeCreator('Else', {'nodes': 1})
      t = self.expect(15) # else
      tree.add(t)
      subtree = self.parse_pp_nodes_list()
      tree.add( subtree )
      return tree
    return tree
  def parse_elipsis_opt(self):
    current = self.tokens.current()
    rule = self.table[21][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(96, self.nonterminals[96]))
    tree.list = False
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 47:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(36) # comma
      tree.add(t)
      t = self.expect(13) # elipsis
      tree.add(t)
      return tree
    return tree
  def parse_pp_tokens(self):
    current = self.tokens.current()
    rule = self.table[22][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(97, self.nonterminals[97]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 7:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(42) # header_global
      tree.add(t)
      return tree
    elif rule == 20:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_punctuator()
      tree.add( subtree )
      return tree
    elif rule == 22:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(47) # header_local
      tree.add(t)
      return tree
    elif rule == 54:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(5) # defined_separator
      tree.add(t)
      return tree
    elif rule == 65:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(69) # character_constant
      tree.add(t)
      return tree
    elif rule == 95:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(9) # pp_number
      tree.add(t)
      return tree
    elif rule == 98:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(73) # string_literal
      tree.add(t)
      return tree
    elif rule == 104:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(35) # defined
      tree.add(t)
      return tree
    elif rule == 129:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(61) # identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen0(self):
    current = self.tokens.current()
    rule = self.table[23][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(98, self.nonterminals[98]))
    tree.list = 'tlist'
    if current != None and (current.getId() in [6, 15, 68, -1]):
      return tree
    if current == None:
      return tree
    if rule == 58:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_pp_nodes()
      tree.add( subtree )
      t = self.expect(28) # separator
      tree.add(t)
      subtree = self.parse__gen0()
      tree.add( subtree )
      return tree
    return tree
  def parse_control_line(self):
    current = self.tokens.current()
    rule = self.table[24][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(99, self.nonterminals[99]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 31:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_warning_line()
      tree.add( subtree )
      return tree
    elif rule == 77:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_pragma_line()
      tree.add( subtree )
      return tree
    elif rule == 92:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_define_line()
      tree.add( subtree )
      return tree
    elif rule == 105:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_undef_line()
      tree.add( subtree )
      return tree
    elif rule == 112:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_line_line()
      tree.add( subtree )
      return tree
    elif rule == 132:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_error_line()
      tree.add( subtree )
      return tree
    elif rule == 137:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_include_line()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_punctuator(self):
    current = self.tokens.current()
    rule = self.table[25][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(100, self.nonterminals[100]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 0:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(29) # lshifteq
      tree.add(t)
      return tree
    elif rule == 1:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(33) # mul
      tree.add(t)
      return tree
    elif rule == 2:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(63) # arrow
      tree.add(t)
      return tree
    elif rule == 3:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(40) # lbrace
      tree.add(t)
      return tree
    elif rule == 4:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(11) # rparen
      tree.add(t)
      return tree
    elif rule == 5:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(2) # tilde
      tree.add(t)
      return tree
    elif rule == 11:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(44) # neq
      tree.add(t)
      return tree
    elif rule == 13:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(45) # bitxor
      tree.add(t)
      return tree
    elif rule == 17:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(57) # lteq
      tree.add(t)
      return tree
    elif rule == 18:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(46) # rbrace
      tree.add(t)
      return tree
    elif rule == 26:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(51) # bitoreq
      tree.add(t)
      return tree
    elif rule == 27:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(53) # lsquare
      tree.add(t)
      return tree
    elif rule == 28:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(70) # exclamation_point
      tree.add(t)
      return tree
    elif rule == 36:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(59) # bitxoreq
      tree.add(t)
      return tree
    elif rule == 46:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(48) # eq
      tree.add(t)
      return tree
    elif rule == 52:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(64) # bitandeq
      tree.add(t)
      return tree
    elif rule == 56:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(13) # elipsis
      tree.add(t)
      return tree
    elif rule == 57:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(65) # lparen
      tree.add(t)
      return tree
    elif rule == 67:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(17) # diveq
      tree.add(t)
      return tree
    elif rule == 68:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(19) # div
      tree.add(t)
      return tree
    elif rule == 69:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(55) # incr
      tree.add(t)
      return tree
    elif rule == 73:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(37) # poundpound
      tree.add(t)
      return tree
    elif rule == 76:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(20) # colon
      tree.add(t)
      return tree
    elif rule == 80:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(71) # gt
      tree.add(t)
      return tree
    elif rule == 82:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(0) # lshift
      tree.add(t)
      return tree
    elif rule == 85:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(25) # decr
      tree.add(t)
      return tree
    elif rule == 86:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(72) # rshifteq
      tree.add(t)
      return tree
    elif rule == 87:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(36) # comma
      tree.add(t)
      return tree
    elif rule == 88:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(27) # questionmark
      tree.add(t)
      return tree
    elif rule == 90:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(1) # subeq
      tree.add(t)
      return tree
    elif rule == 94:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(62) # gteq
      tree.add(t)
      return tree
    elif rule == 96:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(3) # rshift
      tree.add(t)
      return tree
    elif rule == 97:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(66) # lt
      tree.add(t)
      return tree
    elif rule == 99:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(4) # addeq
      tree.add(t)
      return tree
    elif rule == 101:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(30) # bitand
      tree.add(t)
      return tree
    elif rule == 108:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(7) # mod
      tree.add(t)
      return tree
    elif rule == 113:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(24) # ampersand
      tree.add(t)
      return tree
    elif rule == 114:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(31) # pound
      tree.add(t)
      return tree
    elif rule == 117:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(8) # modeq
      tree.add(t)
      return tree
    elif rule == 118:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(34) # bitnot
      tree.add(t)
      return tree
    elif rule == 119:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(50) # semi
      tree.add(t)
      return tree
    elif rule == 123:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(32) # or
      tree.add(t)
      return tree
    elif rule == 125:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(18) # dot
      tree.add(t)
      return tree
    elif rule == 128:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(10) # add
      tree.add(t)
      return tree
    elif rule == 130:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(58) # sub
      tree.add(t)
      return tree
    elif rule == 131:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(14) # muleq
      tree.add(t)
      return tree
    elif rule == 135:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(38) # and
      tree.add(t)
      return tree
    elif rule == 138:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(22) # assign
      tree.add(t)
      return tree
    elif rule == 139:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(60) # rsquare
      tree.add(t)
      return tree
    elif rule == 140:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(39) # bitor
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_pp_nodes_list(self):
    current = self.tokens.current()
    rule = self.table[26][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(101, self.nonterminals[101]))
    tree.list = False
    if current != None and (current.getId() in [6, 15, -1, 68]):
      return tree
    if current == None:
      return tree
    if rule == 44:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen0()
      tree.add( subtree )
      return tree
    return tree
  def parse_line_line(self):
    current = self.tokens.current()
    rule = self.table[28][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(103, self.nonterminals[103]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 63:
      tree.astTransform = AstTransformNodeCreator('Line', {'tokens': 1})
      t = self.expect(52) # line
      tree.add(t)
      subtree = self.parse__gen4()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_include_line(self):
    current = self.tokens.current()
    rule = self.table[29][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(104, self.nonterminals[104]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 45:
      tree.astTransform = AstTransformNodeCreator('Include', {'file': 1})
      t = self.expect(43) # include
      tree.add(t)
      subtree = self.parse_include_type()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_pragma_line(self):
    current = self.tokens.current()
    rule = self.table[30][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(105, self.nonterminals[105]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 33:
      tree.astTransform = AstTransformNodeCreator('Pragma', {'tokens': 1})
      t = self.expect(41) # pragma
      tree.add(t)
      subtree = self.parse__gen4()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__expr( self, rbp = 0):
    name = '_expr'
    if name not in self.expressionParsers:
      self.expressionParsers[name] = ExpressionParser__expr(self)
    return self.expressionParsers[name].parse(rbp)
