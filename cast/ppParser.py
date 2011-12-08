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
  def __init__(self, message):
    self.__dict__.update(locals())
  def __str__(self):
    return self.message
class ExpressionParser__expr:
  def __init__(self, parent):
    self.__dict__.update(locals())
    self.infixBp = {
      4: 10000,
      8: 11000,
      11: 12000,
      13: 11000,
      17: 10000,
      18: 12000,
      22: 12000,
      30: 2000,
      34: 5000,
      37: 3000,
      40: 1000,
      41: 4000,
      42: 7000,
      47: 8000,
      48: 6000,
      49: 9000,
      53: 8000,
      58: 9000,
      61: 14000,
      62: 9000,
      66: 15000,
      67: 9000,
    }
    self.prefixBp = {
      8: 13000,
      18: 13000,
      23: 13000,
      34: 13000,
      38: 13000,
      65: 13000,
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
    return self.parent.sym
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
    tree = ParseTree( NonTerminal(86, '_expr') )
    current = self.getCurrentToken()
    if not current:
      return tree
    elif current.getId() in [66]:
      tree.astTransform = AstTransformSubstitution(1)
      tree.nudMorphemeCount = 3
      tree.add( self.expect(66) )
      tree.add( self.parent.parse__expr() )
      tree.add( self.expect(70) )
    elif current.getId() in [44]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      return self.expect( 44 )
    elif current.getId() in [65]:
      tree.astTransform = AstTransformNodeCreator('Not', {'expr': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(65) )
      tree.add( self.parent.parse__expr( self.getPrefixBp(65) ) )
      tree.isPrefix = True
    elif current.getId() in [74]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      return self.expect( 74 )
    elif current.getId() in [23]:
      tree.astTransform = AstTransformNodeCreator('IsDefined', {'expr': 2})
      tree.nudMorphemeCount = 1
      return self.expect( 23 )
    elif current.getId() in [38]:
      tree.astTransform = AstTransformNodeCreator('BitNOT', {'expr': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(38) )
      tree.add( self.parent.parse__expr( self.getPrefixBp(38) ) )
      tree.isPrefix = True
    elif current.getId() in [6]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      return self.expect( 6 )
    elif current.getId() in [44]:
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      tree.nudMorphemeCount = 1
      return self.expect( 44 )
    elif current.getId() in [26]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      return self.expect( 26 )
    return tree
  def led(self, left):
    tree = ParseTree( NonTerminal(86, '_expr') )
    current = self.getCurrentToken()
    if current.getId() == 61: # 'defined_separator'
      tree.astTransform = AstTransformNodeCreator('IsDefined', {'expr': 2})
      if left:
        tree.add(left)
      tree.add( self.expect(61) )
      tree.add( self.parent.parse_defined_identifier() )
    elif current.getId() == 17: # 'lshift'
      tree.astTransform = AstTransformNodeCreator('LeftShift', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(17) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(17) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 42: # 'bitor'
      tree.astTransform = AstTransformNodeCreator('BitOR', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(42) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(42) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 37: # 'or'
      tree.astTransform = AstTransformNodeCreator('Or', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(37) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(37) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 47: # 'neq'
      tree.astTransform = AstTransformNodeCreator('NotEquals', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(47) )
      modifier = 1
      tree.add( self.parent.parse__expr( self.getInfixBp(47) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 62: # 'gteq'
      tree.astTransform = AstTransformNodeCreator('GreaterThanEq', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(62) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(62) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 13: # 'add'
      tree.astTransform = AstTransformNodeCreator('Add', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(13) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(13) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 48: # 'bitxor'
      tree.astTransform = AstTransformNodeCreator('BitXOR', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(48) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(48) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 40: # 'comma'
      tree.astTransform = AstTransformNodeCreator('Comma', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(40) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(40) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 30: # 'questionmark'
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(30) )
      modifier = 1
      tree.add( self.parent.parse__expr( self.getInfixBp(30) - modifier ) )
      tree.add( self.expect(24) )
      modifier = 1
      tree.add( self.parent.parse__expr( self.getInfixBp(30) - modifier ) )
    elif current.getId() == 18: # 'mul'
      tree.astTransform = AstTransformNodeCreator('Mul', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(18) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(18) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 8: # 'sub'
      tree.astTransform = AstTransformNodeCreator('Sub', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(8) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(8) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 22: # 'div'
      tree.astTransform = AstTransformNodeCreator('Div', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(22) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(22) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 67: # 'lt'
      tree.astTransform = AstTransformNodeCreator('LessThan', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(67) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(67) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 41: # 'and'
      tree.astTransform = AstTransformNodeCreator('And', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(41) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(41) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 4: # 'rshift'
      tree.astTransform = AstTransformNodeCreator('RightShift', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(4) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(4) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 11: # 'mod'
      tree.astTransform = AstTransformNodeCreator('Mod', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(11) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(11) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 49: # 'gt'
      tree.astTransform = AstTransformNodeCreator('GreaterThan', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(49) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(49) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 66: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(66) )
      tree.add( self.parent.parse__gen5() )
      tree.add( self.expect(70) )
    elif current.getId() == 34: # 'bitand'
      tree.astTransform = AstTransformNodeCreator('BitAND', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(34) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(34) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 53: # 'eq'
      tree.astTransform = AstTransformNodeCreator('Equals', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(53) )
      modifier = 1
      tree.add( self.parent.parse__expr( self.getInfixBp(53) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 58: # 'lteq'
      tree.astTransform = AstTransformNodeCreator('LessThanEq', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(58) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(58) - modifier ) )
      tree.isInfix = True
    return tree
class Parser:
  # Quark - finite string set maps one string to exactly one int, and vice versa
  terminals = {
    0: 'define',
    1: 'subeq',
    2: 'tilde',
    3: 'elif',
    4: 'rshift',
    5: '_expr',
    6: 'pp_number',
    7: 'addeq',
    8: 'sub',
    9: 'line',
    10: 'if',
    11: 'mod',
    12: 'modeq',
    13: 'add',
    14: 'elipsis',
    15: 'dot',
    16: 'muleq',
    17: 'lshift',
    18: 'mul',
    19: 'semi',
    20: 'warning',
    21: 'diveq',
    22: 'div',
    23: 'defined',
    24: 'colon',
    25: 'assign',
    26: 'character_constant',
    27: 'ampersand',
    28: 'lshifteq',
    29: 'decr',
    30: 'questionmark',
    31: 'separator',
    32: 'else',
    33: 'incr',
    34: 'bitand',
    35: 'poundpound',
    36: 'pound',
    37: 'or',
    38: 'bitnot',
    39: 'pragma',
    40: 'comma',
    41: 'and',
    42: 'bitor',
    43: 'lbrace',
    44: 'identifier',
    45: 'header_global',
    46: 'csource',
    47: 'neq',
    48: 'bitxor',
    49: 'gt',
    50: 'rbrace',
    51: 'header_local',
    52: 'define_function',
    53: 'eq',
    54: 'bitoreq',
    55: 'rsquare',
    56: 'lsquare',
    57: 'arrow',
    58: 'lteq',
    59: 'bitxoreq',
    60: 'include',
    61: 'defined_separator',
    62: 'gteq',
    63: 'ifndef',
    64: 'bitandeq',
    65: 'exclamation_point',
    66: 'lparen',
    67: 'lt',
    68: 'endif',
    69: 'error',
    70: 'rparen',
    71: 'undef',
    72: 'ifdef',
    73: 'rshifteq',
    74: 'string_literal',
    'define': 0,
    'subeq': 1,
    'tilde': 2,
    'elif': 3,
    'rshift': 4,
    '_expr': 5,
    'pp_number': 6,
    'addeq': 7,
    'sub': 8,
    'line': 9,
    'if': 10,
    'mod': 11,
    'modeq': 12,
    'add': 13,
    'elipsis': 14,
    'dot': 15,
    'muleq': 16,
    'lshift': 17,
    'mul': 18,
    'semi': 19,
    'warning': 20,
    'diveq': 21,
    'div': 22,
    'defined': 23,
    'colon': 24,
    'assign': 25,
    'character_constant': 26,
    'ampersand': 27,
    'lshifteq': 28,
    'decr': 29,
    'questionmark': 30,
    'separator': 31,
    'else': 32,
    'incr': 33,
    'bitand': 34,
    'poundpound': 35,
    'pound': 36,
    'or': 37,
    'bitnot': 38,
    'pragma': 39,
    'comma': 40,
    'and': 41,
    'bitor': 42,
    'lbrace': 43,
    'identifier': 44,
    'header_global': 45,
    'csource': 46,
    'neq': 47,
    'bitxor': 48,
    'gt': 49,
    'rbrace': 50,
    'header_local': 51,
    'define_function': 52,
    'eq': 53,
    'bitoreq': 54,
    'rsquare': 55,
    'lsquare': 56,
    'arrow': 57,
    'lteq': 58,
    'bitxoreq': 59,
    'include': 60,
    'defined_separator': 61,
    'gteq': 62,
    'ifndef': 63,
    'bitandeq': 64,
    'exclamation_point': 65,
    'lparen': 66,
    'lt': 67,
    'endif': 68,
    'error': 69,
    'rparen': 70,
    'undef': 71,
    'ifdef': 72,
    'rshifteq': 73,
    'string_literal': 74,
  }
  # Quark - finite string set maps one string to exactly one int, and vice versa
  nonterminals = {
    75: 'if_part',
    76: 'elseif_part',
    77: 'if_section',
    78: 'error_line',
    79: 'else_part',
    80: 'include_type',
    81: 'pp_tokens',
    82: '_gen4',
    83: 'pp_directive',
    84: 'pragma_line',
    85: 'warning_line',
    86: '_expr',
    87: 'punctuator',
    88: 'include_line',
    89: 'pp_file',
    90: 'define_func_param',
    91: '_gen2',
    92: '_gen6',
    93: 'pp_nodes',
    94: 'elipsis_opt',
    95: 'undef_line',
    96: 'defined_identifier',
    97: 'define_line',
    98: 'control_line',
    99: 'pp_nodes_list',
    100: 'replacement_list',
    101: 'line_line',
    102: '_gen1',
    103: '_gen3',
    104: '_gen0',
    105: '_gen5',
    'if_part': 75,
    'elseif_part': 76,
    'if_section': 77,
    'error_line': 78,
    'else_part': 79,
    'include_type': 80,
    'pp_tokens': 81,
    '_gen4': 82,
    'pp_directive': 83,
    'pragma_line': 84,
    'warning_line': 85,
    '_expr': 86,
    'punctuator': 87,
    'include_line': 88,
    'pp_file': 89,
    'define_func_param': 90,
    '_gen2': 91,
    '_gen6': 92,
    'pp_nodes': 93,
    'elipsis_opt': 94,
    'undef_line': 95,
    'defined_identifier': 96,
    'define_line': 97,
    'control_line': 98,
    'pp_nodes_list': 99,
    'replacement_list': 100,
    'line_line': 101,
    '_gen1': 102,
    '_gen3': 103,
    '_gen0': 104,
    '_gen5': 105,
  }
  # table[nonterminal][terminal] = rule
  table = [
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 99, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 125, -1, -1, -1, -1, -1, -1, -1, -1, 25, -1, -1],
    [-1, -1, -1, 33, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 135, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 135, -1, -1, -1, -1, -1, -1, -1, -1, 135, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 95, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 46, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 113, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 39, 9, -1, -1, -1, -1, -1, 101, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, 30, 30, -1, 30, -1, 124, 30, 30, -1, -1, 30, 30, 30, 30, 30, 30, 30, 30, 30, -1, 30, 30, 136, 30, 30, 140, 30, 30, 30, 30, -1, -1, 30, 30, 30, 30, 30, 30, -1, 30, 30, 30, 30, 110, 70, -1, 30, 30, 30, 30, 86, -1, 30, 30, 30, 30, 30, 30, 30, -1, 104, 30, -1, 30, 30, 30, 30, -1, -1, 30, -1, -1, 30, 89],
    [-1, 115, 115, -1, 115, -1, 115, 115, 115, -1, -1, 115, 115, 115, 115, 115, 115, 115, 115, 115, -1, 115, 115, 115, 115, 115, 115, 115, 115, 115, 115, 42, -1, 115, 115, 115, 115, 115, 115, -1, 115, 115, 115, 115, 115, 115, -1, 115, 115, 115, 115, 115, -1, 115, 115, 115, 115, 115, 115, 115, -1, 115, 115, -1, 115, 115, 115, 115, -1, -1, 115, -1, -1, 115, 115],
    [91, -1, -1, -1, -1, -1, -1, -1, -1, 91, 41, -1, -1, -1, -1, -1, -1, -1, -1, -1, 91, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 91, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 91, -1, -1, -1, -1, -1, -1, -1, 91, -1, -1, 41, -1, -1, -1, -1, -1, 91, -1, 91, 41, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 102, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 111, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, 13, 17, -1, 23, -1, -1, 11, 29, -1, -1, 84, 40, 47, 53, 106, 56, 8, 60, 63, -1, 68, 31, -1, 7, 43, -1, 141, 87, 122, 4, -1, -1, 32, 21, 28, 38, 127, 50, -1, 52, 57, 62, 83, -1, -1, -1, 74, 76, 20, 15, -1, -1, 58, 96, 65, 45, 64, 67, 139, -1, -1, 116, -1, 120, 138, 37, 133, -1, -1, 77, -1, -1, 88, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 114, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [1, -1, -1, -1, -1, -1, -1, -1, -1, 1, 1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 1, -1, -1, -1, -1, -1, -1, 1, -1, -1, -1, -1, -1, 1, -1, -1, -1, -1, -1, -1, -1, 1, -1, -1, 1, -1, -1, -1, -1, -1, 1, -1, 1, 1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 34, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 69, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 12, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 12, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 18, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 19, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [131, -1, -1, -1, -1, -1, -1, -1, -1, 131, 131, -1, -1, -1, -1, -1, -1, -1, -1, -1, 131, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 131, -1, -1, -1, -1, -1, -1, 93, -1, -1, -1, -1, -1, 131, -1, -1, -1, -1, -1, -1, -1, 131, -1, -1, 131, -1, -1, -1, -1, -1, 131, -1, 131, 131, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 118, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 98, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 59, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 82, -1, -1, -1, -1, -1, -1, -1, -1],
    [71, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 73, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [55, -1, -1, -1, -1, -1, -1, -1, -1, 121, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 2, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 134, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 55, -1, -1, -1, -1, -1, -1, -1, 0, -1, -1, -1, -1, -1, -1, -1, -1, 85, -1, 79, -1, -1, -1],
    [75, -1, -1, 5, -1, -1, -1, -1, -1, 75, 75, -1, -1, -1, -1, -1, -1, -1, -1, -1, 75, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 5, -1, -1, -1, -1, -1, -1, 75, -1, -1, -1, -1, -1, -1, 75, -1, -1, -1, -1, -1, 75, -1, -1, -1, -1, -1, -1, -1, 75, -1, -1, 75, -1, -1, -1, -1, 5, 75, -1, 75, 75, -1, -1],
    [-1, 130, 130, -1, 130, -1, 130, 130, 130, -1, -1, 130, 130, 130, 130, 130, 130, 130, 130, 130, -1, 130, 130, 130, 130, 130, 130, 130, 130, 130, 130, 10, -1, 130, 130, 130, 130, 130, 130, -1, 130, 130, 130, 130, 130, 130, -1, 130, 130, 130, 130, 130, -1, 130, 130, 130, 130, 130, 130, 130, -1, 130, 130, -1, 130, 130, 130, 130, -1, -1, 130, -1, -1, 130, 130],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, 51, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 66, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 81, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 14, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 16, -1, -1, -1, -1],
    [61, -1, -1, 36, -1, -1, -1, -1, -1, 61, 61, -1, -1, -1, -1, -1, -1, -1, -1, -1, 61, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 36, -1, -1, -1, -1, -1, -1, 61, -1, -1, -1, -1, -1, -1, 61, -1, -1, -1, -1, -1, 61, -1, -1, -1, -1, -1, -1, -1, 61, -1, -1, 61, -1, -1, -1, -1, 36, 61, -1, 61, 61, -1, -1],
    [-1, -1, -1, -1, -1, 80, 80, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 80, -1, -1, 80, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 80, -1, -1, -1, -1, -1, 80, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 80, 80, -1, -1, -1, -1, -1, -1, -1, 80],
  ]
  TERMINAL_DEFINE = 0
  TERMINAL_SUBEQ = 1
  TERMINAL_TILDE = 2
  TERMINAL_ELIF = 3
  TERMINAL_RSHIFT = 4
  TERMINAL__EXPR = 5
  TERMINAL_PP_NUMBER = 6
  TERMINAL_ADDEQ = 7
  TERMINAL_SUB = 8
  TERMINAL_LINE = 9
  TERMINAL_IF = 10
  TERMINAL_MOD = 11
  TERMINAL_MODEQ = 12
  TERMINAL_ADD = 13
  TERMINAL_ELIPSIS = 14
  TERMINAL_DOT = 15
  TERMINAL_MULEQ = 16
  TERMINAL_LSHIFT = 17
  TERMINAL_MUL = 18
  TERMINAL_SEMI = 19
  TERMINAL_WARNING = 20
  TERMINAL_DIVEQ = 21
  TERMINAL_DIV = 22
  TERMINAL_DEFINED = 23
  TERMINAL_COLON = 24
  TERMINAL_ASSIGN = 25
  TERMINAL_CHARACTER_CONSTANT = 26
  TERMINAL_AMPERSAND = 27
  TERMINAL_LSHIFTEQ = 28
  TERMINAL_DECR = 29
  TERMINAL_QUESTIONMARK = 30
  TERMINAL_SEPARATOR = 31
  TERMINAL_ELSE = 32
  TERMINAL_INCR = 33
  TERMINAL_BITAND = 34
  TERMINAL_POUNDPOUND = 35
  TERMINAL_POUND = 36
  TERMINAL_OR = 37
  TERMINAL_BITNOT = 38
  TERMINAL_PRAGMA = 39
  TERMINAL_COMMA = 40
  TERMINAL_AND = 41
  TERMINAL_BITOR = 42
  TERMINAL_LBRACE = 43
  TERMINAL_IDENTIFIER = 44
  TERMINAL_HEADER_GLOBAL = 45
  TERMINAL_CSOURCE = 46
  TERMINAL_NEQ = 47
  TERMINAL_BITXOR = 48
  TERMINAL_GT = 49
  TERMINAL_RBRACE = 50
  TERMINAL_HEADER_LOCAL = 51
  TERMINAL_DEFINE_FUNCTION = 52
  TERMINAL_EQ = 53
  TERMINAL_BITOREQ = 54
  TERMINAL_RSQUARE = 55
  TERMINAL_LSQUARE = 56
  TERMINAL_ARROW = 57
  TERMINAL_LTEQ = 58
  TERMINAL_BITXOREQ = 59
  TERMINAL_INCLUDE = 60
  TERMINAL_DEFINED_SEPARATOR = 61
  TERMINAL_GTEQ = 62
  TERMINAL_IFNDEF = 63
  TERMINAL_BITANDEQ = 64
  TERMINAL_EXCLAMATION_POINT = 65
  TERMINAL_LPAREN = 66
  TERMINAL_LT = 67
  TERMINAL_ENDIF = 68
  TERMINAL_ERROR = 69
  TERMINAL_RPAREN = 70
  TERMINAL_UNDEF = 71
  TERMINAL_IFDEF = 72
  TERMINAL_RSHIFTEQ = 73
  TERMINAL_STRING_LITERAL = 74
  def __init__(self):
    self.iterator = None
    self.sym = None
    self.expressionParsers = dict()
  def isTerminal(self, id):
    return 0 <= id <= 74
  def isNonTerminal(self, id):
    return 75 <= id <= 105
  def getsym(self):
    try:
      return next( self.iterator )
    except StopIteration:
      return None
  def parse(self, iterator):
    self.iterator = iter(iterator)
    self.sym = self.getsym()
    self.start = 'PP_FILE'
    tree = self.parse_pp_file()
    if self.sym != None:
      raise SyntaxError( 'Syntax Error: Finished parsing without consuming all tokens.' )
    self.iterator = None
    self.sym = None
    return tree
  def next(self):
    self.sym = self.getsym()
    if self.sym is not None and not self.isTerminal(self.sym.getId()):
      self.sym = None
      raise SyntaxError( 'Invalid symbol ID: %d (%s)' % (self.sym.getId(), self.sym) )
    return self.sym
  def expect(self, s):
    if self.sym and s == self.sym.getId():
      symbol = self.sym
      self.sym = self.next()
      return symbol
    else:
      raise SyntaxError('Unexpected symbol when parsing %s.  Expected %s, got %s.' %(whosdaddy(), self.terminals[s], self.sym if self.sym else 'None'))
  def rule(self, n):
    if self.sym == None: return -1
    return self.table[n - 75][self.sym.getId()]
  def call(self, nt_str):
    return getattr(self, nt_str)()
  def parse_if_part(self, depth=0, tracer=None):
    rule = self.rule(75)
    tree = ParseTree( NonTerminal(75, self.nonterminals[75]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 25:
      tree.astTransform = AstTransformNodeCreator('IfDef', {'nodes': 2, 'ident': 1})
      t = self.expect(72) # ifdef
      tree.add(t)
      t = self.expect(44) # identifier
      tree.add(t)
      subtree = self.parse_pp_nodes_list()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 99:
      tree.astTransform = AstTransformNodeCreator('If', {'expr': 1, 'nodes': 2})
      t = self.expect(10) # if
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse_pp_nodes_list()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 125:
      tree.astTransform = AstTransformNodeCreator('IfNDef', {'nodes': 2, 'ident': 1})
      t = self.expect(63) # ifndef
      tree.add(t)
      t = self.expect(44) # identifier
      tree.add(t)
      subtree = self.parse_pp_nodes_list()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_elseif_part(self, depth=0, tracer=None):
    rule = self.rule(76)
    tree = ParseTree( NonTerminal(76, self.nonterminals[76]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 33:
      tree.astTransform = AstTransformNodeCreator('ElseIf', {'expr': 1, 'nodes': 2})
      t = self.expect(3) # elif
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse_pp_nodes_list()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_if_section(self, depth=0, tracer=None):
    rule = self.rule(77)
    tree = ParseTree( NonTerminal(77, self.nonterminals[77]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 135:
      tree.astTransform = AstTransformNodeCreator('IfSection', {'elif': 1, 'else': 2, 'if': 0})
      subtree = self.parse_if_part()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen1()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse_else_part()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(68) # endif
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_error_line(self, depth=0, tracer=None):
    rule = self.rule(78)
    tree = ParseTree( NonTerminal(78, self.nonterminals[78]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 95:
      tree.astTransform = AstTransformNodeCreator('Error', {'tokens': 1})
      t = self.expect(69) # error
      tree.add(t)
      subtree = self.parse__gen4()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_else_part(self, depth=0, tracer=None):
    rule = self.rule(79)
    tree = ParseTree( NonTerminal(79, self.nonterminals[79]))
    tree.list = False
    if self.sym != None and (self.sym.getId() in [68]):
      return tree
    if self.sym == None:
      return tree
    if rule == 46:
      tree.astTransform = AstTransformNodeCreator('Else', {'nodes': 1})
      t = self.expect(32) # else
      tree.add(t)
      subtree = self.parse_pp_nodes_list()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def parse_include_type(self, depth=0, tracer=None):
    rule = self.rule(80)
    tree = ParseTree( NonTerminal(80, self.nonterminals[80]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 9:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(45) # header_global
      tree.add(t)
      return tree
    elif rule == 39:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(44) # identifier
      tree.add(t)
      return tree
    elif rule == 101:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(51) # header_local
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_pp_tokens(self, depth=0, tracer=None):
    rule = self.rule(81)
    tree = ParseTree( NonTerminal(81, self.nonterminals[81]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 30:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_punctuator()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 70:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(45) # header_global
      tree.add(t)
      return tree
    elif rule == 86:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(51) # header_local
      tree.add(t)
      return tree
    elif rule == 89:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(74) # string_literal
      tree.add(t)
      return tree
    elif rule == 104:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(61) # defined_separator
      tree.add(t)
      return tree
    elif rule == 110:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(44) # identifier
      tree.add(t)
      return tree
    elif rule == 124:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(6) # pp_number
      tree.add(t)
      return tree
    elif rule == 136:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(23) # defined
      tree.add(t)
      return tree
    elif rule == 140:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(26) # character_constant
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse__gen4(self, depth=0, tracer=None):
    rule = self.rule(82)
    tree = ParseTree( NonTerminal(82, self.nonterminals[82]))
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [31]):
      return tree
    if self.sym == None:
      return tree
    if rule == 115:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_pp_tokens()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen4()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def parse_pp_directive(self, depth=0, tracer=None):
    rule = self.rule(83)
    tree = ParseTree( NonTerminal(83, self.nonterminals[83]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 41:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_if_section()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 91:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_control_line()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_pragma_line(self, depth=0, tracer=None):
    rule = self.rule(84)
    tree = ParseTree( NonTerminal(84, self.nonterminals[84]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 102:
      tree.astTransform = AstTransformNodeCreator('Pragma', {'tokens': 1})
      t = self.expect(39) # pragma
      tree.add(t)
      subtree = self.parse__gen4()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_warning_line(self, depth=0, tracer=None):
    rule = self.rule(85)
    tree = ParseTree( NonTerminal(85, self.nonterminals[85]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 111:
      tree.astTransform = AstTransformNodeCreator('Warning', {'tokens': 1})
      t = self.expect(20) # warning
      tree.add(t)
      subtree = self.parse__gen4()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_punctuator(self, depth=0, tracer=None):
    rule = self.rule(87)
    tree = ParseTree( NonTerminal(87, self.nonterminals[87]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 4:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(30) # questionmark
      tree.add(t)
      return tree
    elif rule == 7:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(24) # colon
      tree.add(t)
      return tree
    elif rule == 8:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(17) # lshift
      tree.add(t)
      return tree
    elif rule == 11:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(7) # addeq
      tree.add(t)
      return tree
    elif rule == 13:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(1) # subeq
      tree.add(t)
      return tree
    elif rule == 15:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(50) # rbrace
      tree.add(t)
      return tree
    elif rule == 17:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(2) # tilde
      tree.add(t)
      return tree
    elif rule == 20:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(49) # gt
      tree.add(t)
      return tree
    elif rule == 21:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(34) # bitand
      tree.add(t)
      return tree
    elif rule == 23:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(4) # rshift
      tree.add(t)
      return tree
    elif rule == 28:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(35) # poundpound
      tree.add(t)
      return tree
    elif rule == 29:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(8) # sub
      tree.add(t)
      return tree
    elif rule == 31:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(22) # div
      tree.add(t)
      return tree
    elif rule == 32:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(33) # incr
      tree.add(t)
      return tree
    elif rule == 37:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(66) # lparen
      tree.add(t)
      return tree
    elif rule == 38:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(36) # pound
      tree.add(t)
      return tree
    elif rule == 40:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(12) # modeq
      tree.add(t)
      return tree
    elif rule == 43:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(25) # assign
      tree.add(t)
      return tree
    elif rule == 45:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(56) # lsquare
      tree.add(t)
      return tree
    elif rule == 47:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(13) # add
      tree.add(t)
      return tree
    elif rule == 50:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(38) # bitnot
      tree.add(t)
      return tree
    elif rule == 52:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(40) # comma
      tree.add(t)
      return tree
    elif rule == 53:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(14) # elipsis
      tree.add(t)
      return tree
    elif rule == 56:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(16) # muleq
      tree.add(t)
      return tree
    elif rule == 57:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(41) # and
      tree.add(t)
      return tree
    elif rule == 58:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(53) # eq
      tree.add(t)
      return tree
    elif rule == 60:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(18) # mul
      tree.add(t)
      return tree
    elif rule == 62:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(42) # bitor
      tree.add(t)
      return tree
    elif rule == 63:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(19) # semi
      tree.add(t)
      return tree
    elif rule == 64:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(57) # arrow
      tree.add(t)
      return tree
    elif rule == 65:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(55) # rsquare
      tree.add(t)
      return tree
    elif rule == 67:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(58) # lteq
      tree.add(t)
      return tree
    elif rule == 68:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(21) # diveq
      tree.add(t)
      return tree
    elif rule == 74:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(47) # neq
      tree.add(t)
      return tree
    elif rule == 76:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(48) # bitxor
      tree.add(t)
      return tree
    elif rule == 77:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(70) # rparen
      tree.add(t)
      return tree
    elif rule == 83:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(43) # lbrace
      tree.add(t)
      return tree
    elif rule == 84:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(11) # mod
      tree.add(t)
      return tree
    elif rule == 87:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(28) # lshifteq
      tree.add(t)
      return tree
    elif rule == 88:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(73) # rshifteq
      tree.add(t)
      return tree
    elif rule == 96:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(54) # bitoreq
      tree.add(t)
      return tree
    elif rule == 106:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(15) # dot
      tree.add(t)
      return tree
    elif rule == 116:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(62) # gteq
      tree.add(t)
      return tree
    elif rule == 120:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(64) # bitandeq
      tree.add(t)
      return tree
    elif rule == 122:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(29) # decr
      tree.add(t)
      return tree
    elif rule == 127:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(37) # or
      tree.add(t)
      return tree
    elif rule == 133:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(67) # lt
      tree.add(t)
      return tree
    elif rule == 138:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(65) # exclamation_point
      tree.add(t)
      return tree
    elif rule == 139:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(59) # bitxoreq
      tree.add(t)
      return tree
    elif rule == 141:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(27) # ampersand
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_include_line(self, depth=0, tracer=None):
    rule = self.rule(88)
    tree = ParseTree( NonTerminal(88, self.nonterminals[88]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 114:
      tree.astTransform = AstTransformNodeCreator('Include', {'file': 1})
      t = self.expect(60) # include
      tree.add(t)
      subtree = self.parse_include_type()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_pp_file(self, depth=0, tracer=None):
    rule = self.rule(89)
    tree = ParseTree( NonTerminal(89, self.nonterminals[89]))
    tree.list = False
    if self.sym == None:
      return tree
    if rule == 1:
      tree.astTransform = AstTransformNodeCreator('PPFile', {'nodes': 0})
      subtree = self.parse_pp_nodes_list()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_define_func_param(self, depth=0, tracer=None):
    rule = self.rule(90)
    tree = ParseTree( NonTerminal(90, self.nonterminals[90]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 34:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(14) # elipsis
      tree.add(t)
      return tree
    elif rule == 69:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(44) # identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse__gen2(self, depth=0, tracer=None):
    rule = self.rule(91)
    tree = ParseTree( NonTerminal(91, self.nonterminals[91]))
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [70]):
      return tree
    if self.sym == None:
      return tree
    if rule == 12:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_define_func_param()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen3()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def parse__gen6(self, depth=0, tracer=None):
    rule = self.rule(92)
    tree = ParseTree( NonTerminal(92, self.nonterminals[92]))
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 19:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(40) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse__expr()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen6()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def parse_pp_nodes(self, depth=0, tracer=None):
    rule = self.rule(93)
    tree = ParseTree( NonTerminal(93, self.nonterminals[93]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 93:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(46) # csource
      tree.add(t)
      return tree
    elif rule == 131:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_pp_directive()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_elipsis_opt(self, depth=0, tracer=None):
    rule = self.rule(94)
    tree = ParseTree( NonTerminal(94, self.nonterminals[94]))
    tree.list = False
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 118:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(40) # comma
      tree.add(t)
      t = self.expect(14) # elipsis
      tree.add(t)
      return tree
    return tree
  def parse_undef_line(self, depth=0, tracer=None):
    rule = self.rule(95)
    tree = ParseTree( NonTerminal(95, self.nonterminals[95]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 98:
      tree.astTransform = AstTransformNodeCreator('Undef', {'ident': 1})
      t = self.expect(71) # undef
      tree.add(t)
      t = self.expect(44) # identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_defined_identifier(self, depth=0, tracer=None):
    rule = self.rule(96)
    tree = ParseTree( NonTerminal(96, self.nonterminals[96]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 59:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(44) # identifier
      tree.add(t)
      return tree
    elif rule == 82:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(66) # lparen
      tree.add(t)
      t = self.expect(44) # identifier
      tree.add(t)
      t = self.expect(70) # rparen
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_define_line(self, depth=0, tracer=None):
    rule = self.rule(97)
    tree = ParseTree( NonTerminal(97, self.nonterminals[97]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 71:
      tree.astTransform = AstTransformNodeCreator('Define', {'body': 2, 'ident': 1})
      t = self.expect(0) # define
      tree.add(t)
      t = self.expect(44) # identifier
      tree.add(t)
      subtree = self.parse_replacement_list()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 73:
      tree.astTransform = AstTransformNodeCreator('DefineFunction', {'body': 5, 'ident': 1, 'params': 3})
      t = self.expect(52) # define_function
      tree.add(t)
      t = self.expect(44) # identifier
      tree.add(t)
      t = self.expect(66) # lparen
      tree.add(t)
      subtree = self.parse__gen2()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(70) # rparen
      tree.add(t)
      subtree = self.parse_replacement_list()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_control_line(self, depth=0, tracer=None):
    rule = self.rule(98)
    tree = ParseTree( NonTerminal(98, self.nonterminals[98]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 0:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_include_line()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 2:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_warning_line()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 55:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_define_line()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 79:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_undef_line()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 85:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_error_line()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 121:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_line_line()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    elif rule == 134:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_pragma_line()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse_pp_nodes_list(self, depth=0, tracer=None):
    rule = self.rule(99)
    tree = ParseTree( NonTerminal(99, self.nonterminals[99]))
    tree.list = False
    if self.sym != None and (self.sym.getId() in [68, 3, 32, -1]):
      return tree
    if self.sym == None:
      return tree
    if rule == 75:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen0()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def parse_replacement_list(self, depth=0, tracer=None):
    rule = self.rule(100)
    tree = ParseTree( NonTerminal(100, self.nonterminals[100]))
    tree.list = False
    if self.sym != None and (self.sym.getId() in [31]):
      return tree
    if self.sym == None:
      return tree
    if rule == 130:
      tree.astTransform = AstTransformNodeCreator('ReplacementList', {'tokens': 0})
      subtree = self.parse__gen4()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def parse_line_line(self, depth=0, tracer=None):
    rule = self.rule(101)
    tree = ParseTree( NonTerminal(101, self.nonterminals[101]))
    tree.list = False
    if self.sym == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 51:
      tree.astTransform = AstTransformNodeCreator('Line', {'tokens': 1})
      t = self.expect(9) # line
      tree.add(t)
      subtree = self.parse__gen4()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (self.sym, whoami()))
  def parse__gen1(self, depth=0, tracer=None):
    rule = self.rule(102)
    tree = ParseTree( NonTerminal(102, self.nonterminals[102]))
    tree.list = 'nlist'
    if self.sym != None and (self.sym.getId() in [32]):
      return tree
    if self.sym == None:
      return tree
    if rule == 66:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_elseif_part()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen1()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def parse__gen3(self, depth=0, tracer=None):
    rule = self.rule(103)
    tree = ParseTree( NonTerminal(103, self.nonterminals[103]))
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in [70]):
      return tree
    if self.sym == None:
      return tree
    if rule == 14:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(40) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse_define_func_param()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen3()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def parse__gen0(self, depth=0, tracer=None):
    rule = self.rule(104)
    tree = ParseTree( NonTerminal(104, self.nonterminals[104]))
    tree.list = 'tlist'
    if self.sym != None and (self.sym.getId() in [32, 3, -1, 68]):
      return tree
    if self.sym == None:
      return tree
    if rule == 61:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_pp_nodes()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      t = self.expect(31) # separator
      tree.add(t)
      subtree = self.parse__gen0()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def parse__gen5(self, depth=0, tracer=None):
    rule = self.rule(105)
    tree = ParseTree( NonTerminal(105, self.nonterminals[105]))
    tree.list = 'slist'
    if self.sym != None and (self.sym.getId() in []):
      return tree
    if self.sym == None:
      return tree
    if rule == 80:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      subtree = self.parse__gen6()
      tree.add( subtree )
      if tracer and isinstance(subtree, ParseTree):
        tracer.add( subtree.tracer )
      return tree
    return tree
  def parse__expr( self, rbp = 0):
    name = '_expr'
    if name not in self.expressionParsers:
      self.expressionParsers[name] = ExpressionParser__expr(self)
    return self.expressionParsers[name].parse(rbp)
