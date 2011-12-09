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
      3: 16000,
      4: 3000,
      5: 9000,
      6: 15000,
      8: 5000,
      10: 8000,
      13: 9000,
      14: 1000,
      15: 1000,
      17: 15000,
      21: 1000,
      22: 12000,
      29: 2000,
      35: 15000,
      38: 9000,
      46: 11000,
      54: 6000,
      56: 9000,
      60: 15000,
      61: 1000,
      63: 1000,
      64: 1000,
      71: 15000,
      72: 11000,
      74: 1000,
      76: 8000,
      82: 7000,
      83: 4000,
      87: 1000,
      88: 1000,
      90: 12000,
      91: 14000,
      92: 10000,
      96: 15000,
      102: 12000,
      103: 1000,
      110: 1000,
      114: 10000,
    }
    self.prefixBp = {
      6: 13000,
      8: 13000,
      31: 13000,
      41: 13000,
      60: 13000,
      72: 13000,
      102: 13000,
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
    tree = ParseTree( NonTerminal(221, '_expr') )
    current = self.getCurrentToken()
    if not current:
      return tree
    if current.getId() in [27]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      return self.expect( 27 )
    elif current.getId() in [6]:
      tree.astTransform = AstTransformNodeCreator('PreIncr', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(6) )
      tree.add( self.parent.parse__expr( self.getPrefixBp(6) ) )
      tree.isPrefix = True
    elif current.getId() in [71]:
      tree.astTransform = AstTransformSubstitution(2)
      tree.nudMorphemeCount = 3
      tree.add( self.expect(71) )
      tree.add( self.parent.parse__expr() )
      tree.add( self.expect(43) )
    elif current.getId() in [80]:
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      tree.nudMorphemeCount = 1
      return self.expect( 80 )
    elif current.getId() in [70]:
      tree.astTransform = AstTransformNodeCreator('SizeOf', {'var': 1})
      tree.nudMorphemeCount = 1
      return self.expect( 70 )
    elif current.getId() in [80]:
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      tree.nudMorphemeCount = 1
      return self.expect( 80 )
    elif current.getId() in [44, 77, 107, 93, 48, 84]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self.parent.parse_constant() )
    elif current.getId() in [80]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      return self.expect( 80 )
    elif current.getId() in [60]:
      tree.astTransform = AstTransformNodeCreator('PreDecr', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(60) )
      tree.add( self.parent.parse__expr( self.getPrefixBp(60) ) )
      tree.isPrefix = True
    elif current.getId() in [102]:
      tree.astTransform = AstTransformNodeCreator('Dereference', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(102) )
      tree.add( self.parent.parse__expr( self.getPrefixBp(102) ) )
      tree.isPrefix = True
    elif current.getId() in [86]:
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 1, 'initializer': 4})
      tree.nudMorphemeCount = 3
      tree.add( self.expect(86) )
      tree.add( self.parent.parse_type_name() )
      tree.add( self.expect(43) )
    elif current.getId() in [8]:
      tree.astTransform = AstTransformNodeCreator('AddressOf', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(8) )
      tree.add( self.parent.parse__expr( self.getPrefixBp(8) ) )
      tree.isPrefix = True
    return tree
  def led(self, left):
    tree = ParseTree( NonTerminal(221, '_expr') )
    current = self.getCurrentToken()
    if current.getId() == 61: # 'bitandeq'
      tree.astTransform = AstTransformNodeCreator('ANDAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(61) )
      modifier = 1
      tree.add( self.parent.parse__expr( self.getInfixBp(61) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 90: # 'mod'
      tree.astTransform = AstTransformNodeCreator('Mod', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(90) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(90) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 3: # 'comma'
      tree.astTransform = AstTransformNodeCreator('Comma', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(3) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(3) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 5: # 'gt'
      tree.astTransform = AstTransformNodeCreator('GreaterThan', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(5) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(5) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 72: # 'sub'
      tree.astTransform = AstTransformNodeCreator('Sub', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(72) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(72) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 87: # 'rshifteq'
      tree.astTransform = AstTransformNodeCreator('RightShiftAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(87) )
      modifier = 1
      tree.add( self.parent.parse__expr( self.getInfixBp(87) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 71: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(71) )
      tree.add( self.parent.parse__gen40() )
      tree.add( self.expect(43) )
    elif current.getId() == 82: # 'bitor'
      tree.astTransform = AstTransformNodeCreator('BitOR', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(82) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(82) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 60: # 'decr'
      tree.astTransform = AstTransformNodeCreator('PostDecr', {'var': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(60) )
    elif current.getId() == 102: # 'asterisk'
      tree.astTransform = AstTransformNodeCreator('Mul', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(102) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(102) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 96: # 'lsquare'
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(96) )
      tree.add( self.parent.parse__gen40() )
      tree.add( self.expect(105) )
    elif current.getId() == 92: # 'rshift'
      tree.astTransform = AstTransformNodeCreator('RightShift', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(92) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(92) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 38: # 'gteq'
      tree.astTransform = AstTransformNodeCreator('GreaterThanEq', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(38) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(38) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 21: # 'bitoreq'
      tree.astTransform = AstTransformNodeCreator('ORAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(21) )
      modifier = 1
      tree.add( self.parent.parse__expr( self.getInfixBp(21) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 8: # 'bitand'
      tree.astTransform = AstTransformNodeCreator('BitAND', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(8) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(8) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 74: # 'modeq'
      tree.astTransform = AstTransformNodeCreator('ModAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(74) )
      modifier = 1
      tree.add( self.parent.parse__expr( self.getInfixBp(74) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 56: # 'lteq'
      tree.astTransform = AstTransformNodeCreator('LessThanEq', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(56) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(56) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 46: # 'add'
      tree.astTransform = AstTransformNodeCreator('Add', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(46) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(46) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 54: # 'bitxor'
      tree.astTransform = AstTransformNodeCreator('BitXOR', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(54) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(54) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 63: # 'addeq'
      tree.astTransform = AstTransformNodeCreator('AddAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(63) )
      modifier = 1
      tree.add( self.parent.parse__expr( self.getInfixBp(63) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 29: # 'questionmark'
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(29) )
      modifier = 1
      tree.add( self.parent.parse__expr( self.getInfixBp(29) - modifier ) )
      tree.add( self.expect(33) )
      modifier = 1
      tree.add( self.parent.parse__expr( self.getInfixBp(29) - modifier ) )
    elif current.getId() == 14: # 'diveq'
      tree.astTransform = AstTransformNodeCreator('DivideAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(14) )
      modifier = 1
      tree.add( self.parent.parse__expr( self.getInfixBp(14) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 13: # 'lt'
      tree.astTransform = AstTransformNodeCreator('LessThan', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(13) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(13) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 103: # 'assign'
      tree.astTransform = AstTransformNodeCreator('Assign', {'var': 0, 'value': 2})
      if left:
        tree.add(left)
      tree.add( self.expect(103) )
      modifier = 1
      tree.add( self.parent.parse__expr( self.getInfixBp(103) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 35: # 'dot'
      tree.astTransform = AstTransformNodeCreator('MemberSelect', {'member': 2, 'object': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(35) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(35) - modifier ) )
    elif current.getId() == 10: # 'eq'
      tree.astTransform = AstTransformNodeCreator('Equals', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(10) )
      modifier = 1
      tree.add( self.parent.parse__expr( self.getInfixBp(10) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 114: # 'lshift'
      tree.astTransform = AstTransformNodeCreator('LeftShift', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(114) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(114) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 64: # 'muleq'
      tree.astTransform = AstTransformNodeCreator('MultiplyAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(64) )
      modifier = 1
      tree.add( self.parent.parse__expr( self.getInfixBp(64) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 53: # 'sizeof_separator'
      tree.astTransform = AstTransformNodeCreator('SizeOf', {'var': 1})
      if left:
        tree.add(left)
      tree.add( self.expect(53) )
      tree.add( self.parent.parse_sizeof_body() )
    elif current.getId() == 88: # 'bitxoreq'
      tree.astTransform = AstTransformNodeCreator('XORAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(88) )
      modifier = 1
      tree.add( self.parent.parse__expr( self.getInfixBp(88) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 17: # 'arrow'
      tree.astTransform = AstTransformNodeCreator('DerefMemberSelect', {'member': 2, 'object': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(17) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(17) - modifier ) )
    elif current.getId() == 15: # 'subeq'
      tree.astTransform = AstTransformNodeCreator('SubtractAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(15) )
      modifier = 1
      tree.add( self.parent.parse__expr( self.getInfixBp(15) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 110: # 'lshifteq'
      tree.astTransform = AstTransformNodeCreator('LeftShiftAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(110) )
      modifier = 1
      tree.add( self.parent.parse__expr( self.getInfixBp(110) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 91: # 'lbrace'
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 1, 'initializer': 4})
      if left:
        tree.add(left)
      tree.add( self.expect(91) )
      tree.add( self.parent.parse__gen12() )
      tree.add( self.parent.parse_trailing_comma_opt() )
      tree.add( self.expect(49) )
    elif current.getId() == 22: # 'div'
      tree.astTransform = AstTransformNodeCreator('Div', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(22) )
      modifier = 0
      tree.add( self.parent.parse__expr( self.getInfixBp(22) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 6: # 'incr'
      tree.astTransform = AstTransformNodeCreator('PostIncr', {'var': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(6) )
    return tree
class ExpressionParser__expr_sans_comma:
  def __init__(self, parent):
    self.__dict__.update(locals())
    self.infixBp = {
      4: 3000,
      5: 9000,
      6: 15000,
      8: 5000,
      10: 8000,
      13: 9000,
      14: 1000,
      15: 1000,
      17: 15000,
      21: 1000,
      22: 12000,
      29: 2000,
      35: 15000,
      38: 9000,
      46: 11000,
      54: 6000,
      56: 9000,
      60: 15000,
      61: 1000,
      63: 1000,
      64: 1000,
      71: 15000,
      72: 11000,
      74: 1000,
      76: 8000,
      82: 7000,
      83: 4000,
      87: 1000,
      88: 1000,
      90: 12000,
      91: 14000,
      92: 10000,
      96: 15000,
      102: 12000,
      103: 1000,
      110: 1000,
      114: 10000,
    }
    self.prefixBp = {
      6: 13000,
      8: 13000,
      31: 13000,
      41: 13000,
      60: 13000,
      72: 13000,
      102: 13000,
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
    tree = ParseTree( NonTerminal(129, '_expr_sans_comma') )
    current = self.getCurrentToken()
    if not current:
      return tree
    elif current.getId() in [71]:
      tree.astTransform = AstTransformSubstitution(2)
      tree.nudMorphemeCount = 3
      tree.add( self.expect(71) )
      tree.add( self.parent.parse__expr_sans_comma() )
      tree.add( self.expect(43) )
    elif current.getId() in [70]:
      tree.astTransform = AstTransformNodeCreator('SizeOf', {'var': 1})
      tree.nudMorphemeCount = 1
      return self.expect( 70 )
    elif current.getId() in [60]:
      tree.astTransform = AstTransformNodeCreator('PreDecr', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(60) )
      tree.add( self.parent.parse__expr_sans_comma( self.getPrefixBp(60) ) )
      tree.isPrefix = True
    elif current.getId() in [102]:
      tree.astTransform = AstTransformNodeCreator('Dereference', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(102) )
      tree.add( self.parent.parse__expr_sans_comma( self.getPrefixBp(102) ) )
      tree.isPrefix = True
    elif current.getId() in [8]:
      tree.astTransform = AstTransformNodeCreator('AddressOf', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(8) )
      tree.add( self.parent.parse__expr_sans_comma( self.getPrefixBp(8) ) )
      tree.isPrefix = True
    elif current.getId() in [80]:
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      tree.nudMorphemeCount = 1
      return self.expect( 80 )
    elif current.getId() in [80]:
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      tree.nudMorphemeCount = 1
      return self.expect( 80 )
    elif current.getId() in [27]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      return self.expect( 27 )
    elif current.getId() in [44, 77, 107, 93, 48, 84]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      tree.add( self.parent.parse_constant() )
    elif current.getId() in [80]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      return self.expect( 80 )
    elif current.getId() in [86]:
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 1, 'initializer': 4})
      tree.nudMorphemeCount = 3
      tree.add( self.expect(86) )
      tree.add( self.parent.parse_type_name() )
      tree.add( self.expect(43) )
    elif current.getId() in [6]:
      tree.astTransform = AstTransformNodeCreator('PreIncr', {'var': 1})
      tree.nudMorphemeCount = 2
      tree.add( self.expect(6) )
      tree.add( self.parent.parse__expr_sans_comma( self.getPrefixBp(6) ) )
      tree.isPrefix = True
    return tree
  def led(self, left):
    tree = ParseTree( NonTerminal(129, '_expr_sans_comma') )
    current = self.getCurrentToken()
    if current.getId() == 102: # 'asterisk'
      tree.astTransform = AstTransformNodeCreator('Mul', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(102) )
      modifier = 0
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(102) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 72: # 'sub'
      tree.astTransform = AstTransformNodeCreator('Sub', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(72) )
      modifier = 0
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(72) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 15: # 'subeq'
      tree.astTransform = AstTransformNodeCreator('SubtractAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(15) )
      modifier = 1
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(15) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 53: # 'sizeof_separator'
      tree.astTransform = AstTransformNodeCreator('SizeOf', {'var': 1})
      if left:
        tree.add(left)
      tree.add( self.expect(53) )
      tree.add( self.parent.parse_sizeof_body() )
    elif current.getId() == 74: # 'modeq'
      tree.astTransform = AstTransformNodeCreator('ModAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(74) )
      modifier = 1
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(74) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 92: # 'rshift'
      tree.astTransform = AstTransformNodeCreator('RightShift', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(92) )
      modifier = 0
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(92) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 22: # 'div'
      tree.astTransform = AstTransformNodeCreator('Div', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(22) )
      modifier = 0
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(22) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 87: # 'rshifteq'
      tree.astTransform = AstTransformNodeCreator('RightShiftAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(87) )
      modifier = 1
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(87) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 13: # 'lt'
      tree.astTransform = AstTransformNodeCreator('LessThan', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(13) )
      modifier = 0
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(13) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 61: # 'bitandeq'
      tree.astTransform = AstTransformNodeCreator('ANDAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(61) )
      modifier = 1
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(61) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 71: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('FuncCall', {'params': 2, 'name': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(71) )
      tree.add( self.parent.parse__gen40() )
      tree.add( self.expect(43) )
    elif current.getId() == 60: # 'decr'
      tree.astTransform = AstTransformNodeCreator('PostDecr', {'var': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(60) )
    elif current.getId() == 8: # 'bitand'
      tree.astTransform = AstTransformNodeCreator('BitAND', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(8) )
      modifier = 0
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(8) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 90: # 'mod'
      tree.astTransform = AstTransformNodeCreator('Mod', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(90) )
      modifier = 0
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(90) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 14: # 'diveq'
      tree.astTransform = AstTransformNodeCreator('DivideAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(14) )
      modifier = 1
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(14) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 5: # 'gt'
      tree.astTransform = AstTransformNodeCreator('GreaterThan', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(5) )
      modifier = 0
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(5) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 96: # 'lsquare'
      tree.astTransform = AstTransformNodeCreator('ArrayIndex', {'params': 2, 'name': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(96) )
      tree.add( self.parent.parse__gen40() )
      tree.add( self.expect(105) )
    elif current.getId() == 6: # 'incr'
      tree.astTransform = AstTransformNodeCreator('PostIncr', {'var': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(6) )
    elif current.getId() == 54: # 'bitxor'
      tree.astTransform = AstTransformNodeCreator('BitXOR', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(54) )
      modifier = 0
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(54) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 82: # 'bitor'
      tree.astTransform = AstTransformNodeCreator('BitOR', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(82) )
      modifier = 0
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(82) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 10: # 'eq'
      tree.astTransform = AstTransformNodeCreator('Equals', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(10) )
      modifier = 1
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(10) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 21: # 'bitoreq'
      tree.astTransform = AstTransformNodeCreator('ORAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(21) )
      modifier = 1
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(21) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 56: # 'lteq'
      tree.astTransform = AstTransformNodeCreator('LessThanEq', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(56) )
      modifier = 0
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(56) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 63: # 'addeq'
      tree.astTransform = AstTransformNodeCreator('AddAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(63) )
      modifier = 1
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(63) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 88: # 'bitxoreq'
      tree.astTransform = AstTransformNodeCreator('XORAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(88) )
      modifier = 1
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(88) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 91: # 'lbrace'
      tree.astTransform = AstTransformNodeCreator('TypeInitializion', {'type': 1, 'initializer': 4})
      if left:
        tree.add(left)
      tree.add( self.expect(91) )
      tree.add( self.parent.parse__gen12() )
      tree.add( self.parent.parse_trailing_comma_opt() )
      tree.add( self.expect(49) )
    elif current.getId() == 103: # 'assign'
      tree.astTransform = AstTransformNodeCreator('Assign', {'var': 0, 'value': 2})
      if left:
        tree.add(left)
      tree.add( self.expect(103) )
      modifier = 1
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(103) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 64: # 'muleq'
      tree.astTransform = AstTransformNodeCreator('MultiplyAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(64) )
      modifier = 1
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(64) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 38: # 'gteq'
      tree.astTransform = AstTransformNodeCreator('GreaterThanEq', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(38) )
      modifier = 0
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(38) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 110: # 'lshifteq'
      tree.astTransform = AstTransformNodeCreator('LeftShiftAssign', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(110) )
      modifier = 1
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(110) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 46: # 'add'
      tree.astTransform = AstTransformNodeCreator('Add', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(46) )
      modifier = 0
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(46) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 29: # 'questionmark'
      tree.astTransform = AstTransformNodeCreator('TernaryOperator', {'true': 2, 'false': 4, 'cond': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(29) )
      modifier = 1
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(29) - modifier ) )
      tree.add( self.expect(33) )
      modifier = 1
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(29) - modifier ) )
    elif current.getId() == 35: # 'dot'
      tree.astTransform = AstTransformNodeCreator('MemberSelect', {'member': 2, 'object': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(35) )
      modifier = 0
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(35) - modifier ) )
    elif current.getId() == 114: # 'lshift'
      tree.astTransform = AstTransformNodeCreator('LeftShift', {'right': 2, 'left': 0})
      if left:
        tree.add(left)
      tree.add( self.expect(114) )
      modifier = 0
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(114) - modifier ) )
      tree.isInfix = True
    elif current.getId() == 17: # 'arrow'
      tree.astTransform = AstTransformNodeCreator('DerefMemberSelect', {'member': 2, 'object': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(17) )
      modifier = 0
      tree.add( self.parent.parse__expr_sans_comma( self.getInfixBp(17) - modifier ) )
    return tree
class ExpressionParser__direct_declarator:
  def __init__(self, parent):
    self.__dict__.update(locals())
    self.infixBp = {
      71: 1000,
      96: 1000,
    }
    self.prefixBp = {
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
    tree = ParseTree( NonTerminal(240, '_direct_declarator') )
    current = self.getCurrentToken()
    if not current:
      return tree
    elif current.getId() in [71]:
      tree.astTransform = AstTransformSubstitution(1)
      tree.nudMorphemeCount = 3
      tree.add( self.expect(71) )
      tree.add( self.parent.parse_declarator() )
      tree.add( self.expect(43) )
    elif current.getId() in [80]:
      tree.astTransform = AstTransformSubstitution(0)
      tree.nudMorphemeCount = 1
      return self.expect( 80 )
    return tree
  def led(self, left):
    tree = ParseTree( NonTerminal(240, '_direct_declarator') )
    current = self.getCurrentToken()
    if current.getId() == 71: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('FunctionSignature', {'params': 2, 'declarator': 0})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(71) )
      tree.add( self.parent.parse_direct_declarator_parameter_list() )
      tree.add( self.expect(43) )
    elif current.getId() == 96: # 'lsquare'
      tree.astTransform = AstTransformNodeCreator('Array', {'name': 0, 'size': 2})
      tree.isExprNud = True
      if left:
        tree.add(left)
      tree.add( self.expect(96) )
      tree.add( self.parent.parse_direct_declarator_expr() )
      tree.add( self.expect(105) )
    return tree
class ExpressionParser__direct_abstract_declarator:
  def __init__(self, parent):
    self.__dict__.update(locals())
    self.infixBp = {
      71: 1000,
      96: 1000,
    }
    self.prefixBp = {
      71: 2000,
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
    tree = ParseTree( NonTerminal(136, '_direct_abstract_declarator') )
    current = self.getCurrentToken()
    if not current:
      return tree
    elif current.getId() in [71]:
      tree.astTransform = AstTransformSubstitution(1)
      tree.nudMorphemeCount = 3
      tree.add( self.expect(71) )
      tree.add( self.parent.parse_abstract_declarator() )
      tree.add( self.expect(43) )
    return tree
  def led(self, left):
    tree = ParseTree( NonTerminal(136, '_direct_abstract_declarator') )
    current = self.getCurrentToken()
    if current.getId() == 71: # 'lparen'
      tree.astTransform = AstTransformNodeCreator('AbstractFunction', {'object': 0, 'params': 2})
      if left:
        tree.add(left)
      tree.add( self.expect(71) )
      tree.add( self.parent.parse__gen42() )
      tree.add( self.expect(43) )
    elif current.getId() == 96: # 'lsquare'
      tree.astTransform = AstTransformNodeCreator('AbstractArray', {'object': 0, 'size': 2})
      if left:
        tree.add(left)
      tree.add( self.expect(96) )
      tree.add( self.parent.parse_direct_abstract_declarator_expr() )
      tree.add( self.expect(105) )
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
    0: 'auto',
    1: 'while',
    2: '_expr_sans_comma',
    3: 'comma',
    4: 'or',
    5: 'gt',
    6: 'incr',
    7: 'register',
    8: 'bitand',
    9: 'inline',
    10: 'eq',
    11: 'pp_number',
    12: 'typedef_identifier',
    13: 'lt',
    14: 'diveq',
    15: 'subeq',
    16: 'const',
    17: 'arrow',
    18: 'label_hint',
    19: 'struct',
    20: 'enum',
    21: 'bitoreq',
    22: 'div',
    23: 'char',
    24: 'defined_separator',
    25: 'do',
    26: 'union',
    27: 'string_literal',
    28: 'restrict',
    29: 'questionmark',
    30: 'universal_character_name',
    31: 'bitnot',
    32: 'elipsis',
    33: 'colon',
    34: 'exclamation_point',
    35: 'dot',
    36: 'volatile',
    37: 'int',
    38: 'gteq',
    39: 'if',
    40: 'void',
    41: 'not',
    42: 'long',
    43: 'rparen',
    44: 'integer_constant',
    45: 'defined',
    46: 'add',
    47: 'imaginary',
    48: 'floating_constant',
    49: 'rbrace',
    50: 'return',
    51: 'complex',
    52: 'signed',
    53: 'sizeof_separator',
    54: 'bitxor',
    55: 'double',
    56: 'lteq',
    57: 'function_definition_hint',
    58: 'goto',
    59: 'short',
    60: 'decr',
    61: 'bitandeq',
    62: '_expr',
    63: 'addeq',
    64: 'muleq',
    65: 'break',
    66: 'continue',
    67: 'pound',
    68: 'poundpound',
    69: 'endif',
    70: 'sizeof',
    71: 'lparen',
    72: 'sub',
    73: 'tilde',
    74: 'modeq',
    75: 'bool',
    76: 'neq',
    77: 'hexadecimal_floating_constant',
    78: 'declarator_hint',
    79: 'float',
    80: 'identifier',
    81: 'unsigned',
    82: 'bitor',
    83: 'and',
    84: 'enumeration_constant',
    85: '_direct_declarator',
    86: 'lparen_cast',
    87: 'rshifteq',
    88: 'bitxoreq',
    89: 'default',
    90: 'mod',
    91: 'lbrace',
    92: 'rshift',
    93: 'decimal_floating_constant',
    94: 'case',
    95: 'ampersand',
    96: 'lsquare',
    97: 'extern',
    98: 'typedef',
    99: 'else',
    100: 'external_declaration_hint',
    101: 'function_prototype_hint',
    102: 'asterisk',
    103: 'assign',
    104: 'comma_va_args',
    105: 'rsquare',
    106: 'static',
    107: 'character_constant',
    108: 'switch',
    109: 'for',
    110: 'lshifteq',
    111: '_direct_abstract_declarator',
    112: 'trailing_comma',
    113: 'semi',
    114: 'lshift',
    115: 'else_if',
    'auto': 0,
    'while': 1,
    '_expr_sans_comma': 2,
    'comma': 3,
    'or': 4,
    'gt': 5,
    'incr': 6,
    'register': 7,
    'bitand': 8,
    'inline': 9,
    'eq': 10,
    'pp_number': 11,
    'typedef_identifier': 12,
    'lt': 13,
    'diveq': 14,
    'subeq': 15,
    'const': 16,
    'arrow': 17,
    'label_hint': 18,
    'struct': 19,
    'enum': 20,
    'bitoreq': 21,
    'div': 22,
    'char': 23,
    'defined_separator': 24,
    'do': 25,
    'union': 26,
    'string_literal': 27,
    'restrict': 28,
    'questionmark': 29,
    'universal_character_name': 30,
    'bitnot': 31,
    'elipsis': 32,
    'colon': 33,
    'exclamation_point': 34,
    'dot': 35,
    'volatile': 36,
    'int': 37,
    'gteq': 38,
    'if': 39,
    'void': 40,
    'not': 41,
    'long': 42,
    'rparen': 43,
    'integer_constant': 44,
    'defined': 45,
    'add': 46,
    'imaginary': 47,
    'floating_constant': 48,
    'rbrace': 49,
    'return': 50,
    'complex': 51,
    'signed': 52,
    'sizeof_separator': 53,
    'bitxor': 54,
    'double': 55,
    'lteq': 56,
    'function_definition_hint': 57,
    'goto': 58,
    'short': 59,
    'decr': 60,
    'bitandeq': 61,
    '_expr': 62,
    'addeq': 63,
    'muleq': 64,
    'break': 65,
    'continue': 66,
    'pound': 67,
    'poundpound': 68,
    'endif': 69,
    'sizeof': 70,
    'lparen': 71,
    'sub': 72,
    'tilde': 73,
    'modeq': 74,
    'bool': 75,
    'neq': 76,
    'hexadecimal_floating_constant': 77,
    'declarator_hint': 78,
    'float': 79,
    'identifier': 80,
    'unsigned': 81,
    'bitor': 82,
    'and': 83,
    'enumeration_constant': 84,
    '_direct_declarator': 85,
    'lparen_cast': 86,
    'rshifteq': 87,
    'bitxoreq': 88,
    'default': 89,
    'mod': 90,
    'lbrace': 91,
    'rshift': 92,
    'decimal_floating_constant': 93,
    'case': 94,
    'ampersand': 95,
    'lsquare': 96,
    'extern': 97,
    'typedef': 98,
    'else': 99,
    'external_declaration_hint': 100,
    'function_prototype_hint': 101,
    'asterisk': 102,
    'assign': 103,
    'comma_va_args': 104,
    'rsquare': 105,
    'static': 106,
    'character_constant': 107,
    'switch': 108,
    'for': 109,
    'lshifteq': 110,
    '_direct_abstract_declarator': 111,
    'trailing_comma': 112,
    'semi': 113,
    'lshift': 114,
    'else_if': 115,
  }
  # Quark - finite string set maps one string to exactly one int, and vice versa
  nonterminals = {
    116: 'keyword',
    117: 'compound_statement',
    118: 'parameter_declaration_sub',
    119: '_gen42',
    120: 'struct_declarator_body',
    121: 'misc',
    122: 'else_if_statement',
    123: 'constant',
    124: '_gen23',
    125: '_gen21',
    126: 'init_declarator_list',
    127: 'for_cond',
    128: 'for_incr',
    129: '_expr_sans_comma',
    130: 'parameter_declaration_sub_sub',
    131: 'punctuator',
    132: 'enum_specifier_sub',
    133: 'direct_abstract_declarator_opt',
    134: 'storage_class_specifier',
    135: 'direct_declarator_modifier_list_opt',
    136: '_direct_abstract_declarator',
    137: '_gen33',
    138: 'type_specifier',
    139: '_gen36',
    140: 'else_statement',
    141: '_gen40',
    142: '_gen29',
    143: 'type_qualifier',
    144: '_gen41',
    145: 'external_declarator',
    146: 'enum_specifier_body',
    147: '_gen22',
    148: 'function_specifier',
    149: '_gen30',
    150: 'pointer',
    151: '_gen9',
    152: 'initializer_list_item',
    153: '_gen10',
    154: 'token',
    155: 'pointer_sub',
    156: 'parameter_type_list',
    157: '_gen34',
    158: '_gen18',
    159: '_gen24',
    160: 'expression_opt',
    161: 'identifier',
    162: 'declarator_initializer',
    163: '_gen11',
    164: '_gen14',
    165: 'enumerator',
    166: 'direct_abstract_declarator_expr',
    167: 'translation_unit',
    168: 'enumeration_constant',
    169: 'enumerator_assignment',
    170: 'static_opt',
    171: '_gen16',
    172: 'initializer',
    173: 'union_specifier',
    174: 'type_name',
    175: 'declaration_specifier',
    176: '_gen31',
    177: 'enum_specifier',
    178: 'block_item',
    179: 'for_init',
    180: 'external_function',
    181: 'direct_declarator_modifier',
    182: 'typedef_name',
    183: '_gen12',
    184: 'struct_declaration',
    185: '_gen13',
    186: 'direct_declarator_expr',
    187: '_gen8',
    188: 'external_declaration_sub_sub',
    189: 'statement',
    190: 'labeled_statement',
    191: '_gen26',
    192: '_gen3',
    193: '_gen4',
    194: '_gen17',
    195: 'direct_declarator_parameter_list',
    196: 'trailing_comma_opt',
    197: 'parameter_declaration',
    198: '_gen27',
    199: '_gen28',
    200: 'designation',
    201: 'sizeof_body',
    202: 'struct_specifier',
    203: '_gen25',
    204: 'abstract_declarator',
    205: 'else_if_statement_list',
    206: '_gen37',
    207: 'va_args',
    208: 'expression_statement',
    209: 'external_prototype',
    210: 'designator',
    211: 'iteration_statement',
    212: '_gen15',
    213: 'selection_statement',
    214: '_gen38',
    215: 'declarator',
    216: 'declaration_list',
    217: '_gen5',
    218: 'jump_statement',
    219: '_gen32',
    220: 'pointer_opt',
    221: '_expr',
    222: 'specifier_qualifier',
    223: '_gen39',
    224: 'pp',
    225: 'direct_declarator_size',
    226: 'init_declarator',
    227: '_gen6',
    228: 'external_declaration',
    229: 'struct_declarator',
    230: '_gen19',
    231: '_gen20',
    232: 'struct_or_union_sub',
    233: 'type_qualifier_list_opt',
    234: '_gen1',
    235: '_gen2',
    236: '_gen0',
    237: 'block_item_list',
    238: '_gen35',
    239: '_gen7',
    240: '_direct_declarator',
    241: 'declaration',
    242: 'external_declaration_sub',
    243: 'struct_or_union_body',
    'keyword': 116,
    'compound_statement': 117,
    'parameter_declaration_sub': 118,
    '_gen42': 119,
    'struct_declarator_body': 120,
    'misc': 121,
    'else_if_statement': 122,
    'constant': 123,
    '_gen23': 124,
    '_gen21': 125,
    'init_declarator_list': 126,
    'for_cond': 127,
    'for_incr': 128,
    '_expr_sans_comma': 129,
    'parameter_declaration_sub_sub': 130,
    'punctuator': 131,
    'enum_specifier_sub': 132,
    'direct_abstract_declarator_opt': 133,
    'storage_class_specifier': 134,
    'direct_declarator_modifier_list_opt': 135,
    '_direct_abstract_declarator': 136,
    '_gen33': 137,
    'type_specifier': 138,
    '_gen36': 139,
    'else_statement': 140,
    '_gen40': 141,
    '_gen29': 142,
    'type_qualifier': 143,
    '_gen41': 144,
    'external_declarator': 145,
    'enum_specifier_body': 146,
    '_gen22': 147,
    'function_specifier': 148,
    '_gen30': 149,
    'pointer': 150,
    '_gen9': 151,
    'initializer_list_item': 152,
    '_gen10': 153,
    'token': 154,
    'pointer_sub': 155,
    'parameter_type_list': 156,
    '_gen34': 157,
    '_gen18': 158,
    '_gen24': 159,
    'expression_opt': 160,
    'identifier': 161,
    'declarator_initializer': 162,
    '_gen11': 163,
    '_gen14': 164,
    'enumerator': 165,
    'direct_abstract_declarator_expr': 166,
    'translation_unit': 167,
    'enumeration_constant': 168,
    'enumerator_assignment': 169,
    'static_opt': 170,
    '_gen16': 171,
    'initializer': 172,
    'union_specifier': 173,
    'type_name': 174,
    'declaration_specifier': 175,
    '_gen31': 176,
    'enum_specifier': 177,
    'block_item': 178,
    'for_init': 179,
    'external_function': 180,
    'direct_declarator_modifier': 181,
    'typedef_name': 182,
    '_gen12': 183,
    'struct_declaration': 184,
    '_gen13': 185,
    'direct_declarator_expr': 186,
    '_gen8': 187,
    'external_declaration_sub_sub': 188,
    'statement': 189,
    'labeled_statement': 190,
    '_gen26': 191,
    '_gen3': 192,
    '_gen4': 193,
    '_gen17': 194,
    'direct_declarator_parameter_list': 195,
    'trailing_comma_opt': 196,
    'parameter_declaration': 197,
    '_gen27': 198,
    '_gen28': 199,
    'designation': 200,
    'sizeof_body': 201,
    'struct_specifier': 202,
    '_gen25': 203,
    'abstract_declarator': 204,
    'else_if_statement_list': 205,
    '_gen37': 206,
    'va_args': 207,
    'expression_statement': 208,
    'external_prototype': 209,
    'designator': 210,
    'iteration_statement': 211,
    '_gen15': 212,
    'selection_statement': 213,
    '_gen38': 214,
    'declarator': 215,
    'declaration_list': 216,
    '_gen5': 217,
    'jump_statement': 218,
    '_gen32': 219,
    'pointer_opt': 220,
    '_expr': 221,
    'specifier_qualifier': 222,
    '_gen39': 223,
    'pp': 224,
    'direct_declarator_size': 225,
    'init_declarator': 226,
    '_gen6': 227,
    'external_declaration': 228,
    'struct_declarator': 229,
    '_gen19': 230,
    '_gen20': 231,
    'struct_or_union_sub': 232,
    'type_qualifier_list_opt': 233,
    '_gen1': 234,
    '_gen2': 235,
    '_gen0': 236,
    'block_item_list': 237,
    '_gen35': 238,
    '_gen7': 239,
    '_direct_declarator': 240,
    'declaration': 241,
    'external_declaration_sub': 242,
    'struct_or_union_body': 243,
  }
  # table[nonterminal][terminal] = rule
  table = [
    [392, 120, -1, -1, -1, -1, -1, 249, -1, 213, -1, -1, -1, -1, -1, -1, 131, -1, -1, 369, 344, -1, -1, 320, -1, 96, 312, -1, 34, -1, -1, -1, -1, -1, -1, -1, 25, 307, -1, 321, 167, -1, 73, -1, -1, -1, -1, 419, -1, -1, 52, 159, 273, -1, -1, 217, -1, -1, 385, 414, -1, -1, -1, -1, -1, 318, 315, -1, -1, -1, 193, -1, -1, -1, -1, 299, -1, -1, -1, 306, -1, 322, -1, -1, -1, -1, -1, -1, -1, 242, -1, -1, -1, -1, 166, -1, -1, 49, 290, 258, -1, -1, -1, -1, -1, -1, 189, -1, 271, 282, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 316, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 178, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 178, -1, -1, -1, -1, -1, -1, -1, -1, 178, -1, -1, -1, -1, 178, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 178, -1, 178, -1, -1, -1, -1, -1, -1, 178, -1, -1, -1, -1],
    [147, -1, -1, -1, -1, -1, -1, 147, -1, 147, -1, -1, 147, -1, -1, -1, 147, -1, -1, 147, 147, -1, -1, 147, -1, -1, 147, -1, 147, -1, -1, -1, -1, -1, -1, -1, 147, 147, -1, -1, 147, -1, 147, -1, -1, -1, -1, 147, -1, -1, -1, 147, 147, -1, -1, 147, -1, -1, -1, 147, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 147, -1, -1, -1, 147, -1, 147, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 147, 147, -1, -1, -1, -1, -1, -1, -1, 147, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 223, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 208, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 109, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 149],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 64, -1, -1, -1, 15, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 302, -1, -1, -1, -1, -1, -1, 88, -1, -1, -1, -1, -1, -1, -1, -1, 266, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 396, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 35, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 20, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 16, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 20, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 183, -1, -1, -1, -1, -1, -1, -1, -1, 183, -1, -1, -1, -1, 183, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 183, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 403, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 353, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 232, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 323, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 163, -1, -1, -1, -1, -1, -1, -1, -1, 163, -1, -1, -1, -1, 163, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 323, -1, -1, -1, -1, -1, -1, 323, -1, -1, -1, -1],
    [-1, -1, -1, 233, 277, 317, 381, -1, -1, -1, 97, -1, -1, 328, -1, 313, -1, 334, -1, -1, -1, 86, 267, -1, -1, -1, -1, -1, -1, 340, -1, -1, 93, 339, 350, 335, -1, -1, 100, -1, -1, -1, -1, 171, -1, -1, 379, -1, -1, 285, -1, -1, -1, -1, 26, -1, 326, -1, -1, -1, 66, 12, -1, 201, 221, -1, -1, 153, 239, -1, -1, 327, 99, 107, 194, -1, 238, -1, -1, -1, -1, -1, 209, 308, -1, -1, -1, 31, 91, -1, 18, 309, 300, -1, -1, 144, 188, -1, -1, -1, -1, -1, -1, 67, -1, 336, -1, -1, -1, -1, 17, -1, -1, 127, 365, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 314, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 123, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 148, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 148, -1, -1, -1, -1],
    [152, -1, -1, -1, -1, -1, -1, 394, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 330, 40, -1, -1, -1, -1, -1, -1, -1, 112, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, 220, -1, 220, -1, -1, -1, -1, -1, -1, -1, 220, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 220, 220, -1, -1, -1, -1, -1, -1, -1, 220, -1, -1, -1, -1, -1, -1, -1, 220, -1, -1, -1, 220, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 220, -1, 220, -1, -1, -1, -1, -1, -1, -1, 220, 220, -1, -1, -1, -1, -1, 220, -1, -1, 220, -1, -1, -1, 220, -1, 220, -1, -1, -1, -1, -1, -1, 220, -1, -1, -1, -1, -1, -1, -1, -1, 220, -1, -1, -1, 220, 220, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 244, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 241, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 244, -1, -1, -1, -1, -1, -1, 241, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 50, -1, -1, -1, -1, -1, -1, 80, 378, -1, -1, 8, -1, -1, 263, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 184, -1, -1, 105, -1, 247, -1, -1, -1, -1, 74, -1, -1, -1, 292, 254, -1, -1, 409, -1, -1, -1, 146, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 222, -1, -1, -1, 259, -1, 200, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [169, 169, -1, -1, -1, -1, 169, 169, 169, 169, -1, -1, 169, -1, -1, -1, 169, -1, 169, 169, 169, -1, -1, 169, -1, 169, 169, 169, 169, -1, -1, -1, -1, -1, -1, -1, 169, 169, -1, 169, 169, -1, 169, -1, 169, -1, -1, 169, 169, 102, 169, 169, 169, -1, -1, 169, -1, -1, 169, 169, 169, -1, 169, -1, -1, 169, 169, -1, -1, -1, 169, 169, -1, -1, -1, 169, -1, 169, -1, 169, 169, 169, -1, -1, 169, -1, 169, -1, -1, 169, -1, 169, -1, 169, 169, -1, -1, 169, 169, -1, -1, -1, 169, -1, -1, -1, 169, 169, 169, 169, -1, -1, -1, 169, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 95, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 60, -1, -1, -1, 60, -1, 60, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 60, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 60, -1, -1, -1, 60, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 60, -1, -1, -1, -1, -1, -1, -1, -1, -1, 60, 60, -1, -1, -1, -1, -1, 60, -1, -1, 60, -1, -1, -1, 60, -1, 60, -1, -1, -1, -1, -1, -1, 60, -1, -1, -1, -1, -1, -1, -1, -1, 60, -1, -1, -1, -1, 60, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 364, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 7, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 22, -1, -1, -1, -1, -1, -1, -1, 391, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 253, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 181, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 32, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [342, -1, -1, 342, -1, -1, -1, 342, -1, 342, -1, -1, 342, -1, -1, -1, 342, -1, -1, 342, 342, -1, -1, 342, -1, -1, 342, -1, 342, -1, -1, -1, -1, 342, -1, -1, 342, 342, -1, -1, 342, -1, 342, -1, -1, -1, -1, 342, -1, -1, -1, 342, 342, -1, -1, 342, -1, 342, -1, 342, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 342, -1, -1, -1, 342, -1, -1, 342, 342, 342, 342, -1, -1, -1, 342, -1, -1, -1, -1, -1, 43, -1, -1, -1, -1, -1, 342, 342, -1, -1, 342, 342, -1, 342, -1, 342, -1, -1, -1, -1, 342, -1, 342, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, 380, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 337, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 278, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 278, -1, -1, -1, -1, -1, -1, -1, -1, 278, -1, -1, -1, -1, 278, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 278, -1, 278, -1, -1, -1, -1, -1, -1, 278, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 54, -1, -1, -1, -1, -1, -1, -1, -1, 54, -1, -1, -1, -1, 54, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 54, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 77, -1, -1, -1, 77, -1, 77, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 77, -1, -1, -1, -1, -1, -1, -1, 77, -1, -1, -1, -1, -1, -1, -1, -1, 77, -1, -1, -1, 77, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 77, -1, -1, -1, -1, -1, -1, -1, -1, -1, 77, 77, -1, -1, -1, -1, -1, 77, -1, -1, 77, -1, -1, -1, 77, -1, 77, -1, -1, -1, -1, 77, -1, 77, -1, -1, 77, -1, -1, -1, -1, -1, 77, 77, -1, -1, -1, 77, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 57, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 13, -1, -1],
    [370, 370, -1, 234, 234, 234, 234, 370, -1, 370, 234, 106, -1, 234, -1, 234, 370, 234, -1, 370, 370, 234, 234, 370, -1, 370, 370, 280, 370, 234, -1, -1, 234, 234, 234, 234, 370, 370, 234, 370, 370, -1, 370, 234, 48, -1, 234, 370, 48, 234, 370, 370, 370, -1, 234, 370, 234, -1, 370, 370, 234, 234, -1, 234, 234, 370, 370, 234, 234, -1, 370, 234, 234, 234, 234, 370, 234, 48, -1, 370, 197, 370, 234, 234, 48, -1, -1, 234, 234, 370, 234, 234, 234, 48, 370, 234, 234, 370, 370, 370, -1, -1, -1, 234, -1, 234, 370, 48, 370, 370, 234, -1, -1, 234, 234, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 332, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [33, -1, -1, -1, -1, -1, -1, 33, -1, 33, -1, -1, 33, -1, -1, -1, 33, -1, -1, 33, 33, -1, -1, 33, -1, -1, 33, -1, 33, -1, -1, -1, -1, -1, -1, -1, 33, 33, -1, -1, 33, -1, 33, -1, -1, -1, -1, 33, -1, -1, -1, 33, 33, -1, -1, 33, -1, -1, -1, 33, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 33, -1, -1, -1, 33, -1, 33, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 33, 33, -1, -1, -1, -1, -1, -1, -1, 33, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 279, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 279, -1, -1, -1, -1, -1, -1, -1, -1, 279, -1, -1, -1, -1, 279, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 29, -1, 279, -1, -1, -1, -1, -1, -1, 279, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 11, -1, -1, -1, 11, -1, -1, 11, 11, -1, -1, 11, -1, -1, 11, -1, 11, -1, -1, -1, -1, 103, -1, -1, 11, 11, -1, -1, 11, -1, 11, -1, -1, -1, -1, 11, -1, -1, -1, 11, 11, -1, -1, 11, -1, -1, -1, 11, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 103, -1, -1, -1, 11, -1, -1, -1, 11, 103, 11, -1, -1, -1, 103, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 103, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 68, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 70, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, 4, -1, 4, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 4, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 30, 4, -1, -1, -1, 4, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 4, -1, 4, -1, -1, -1, -1, -1, -1, -1, 4, 4, -1, -1, -1, -1, -1, 4, -1, -1, 4, -1, -1, -1, 4, -1, 4, -1, -1, -1, -1, -1, -1, 4, -1, -1, -1, -1, -1, -1, -1, -1, 4, -1, -1, -1, -1, 4, -1, -1, -1, -1, -1, 30, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 199, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 94, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 75, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 72, -1, -1, -1, -1, -1, -1, -1, -1, -1, 75, -1, -1],
    [-1, -1, 203, -1, -1, -1, 203, -1, 203, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 203, -1, -1, -1, -1, -1, -1, -1, 128, -1, -1, -1, -1, -1, -1, -1, -1, 203, -1, -1, -1, 203, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 203, -1, -1, -1, -1, -1, -1, -1, -1, -1, 203, 203, -1, -1, -1, -1, -1, 203, -1, -1, 203, -1, -1, -1, 203, -1, 203, -1, -1, -1, -1, 203, -1, 203, -1, -1, 128, -1, -1, -1, -1, -1, 203, 128, -1, -1, -1, 203, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 291, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, 224, -1, 224, -1, -1, -1, -1, -1, -1, -1, 224, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 224, 224, -1, -1, -1, -1, -1, -1, -1, 224, -1, -1, -1, -1, -1, -1, -1, 224, -1, -1, -1, 224, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 224, -1, 224, -1, -1, -1, -1, -1, -1, -1, 224, 224, -1, -1, -1, -1, -1, 224, -1, -1, 224, -1, -1, -1, 224, -1, 224, -1, -1, -1, -1, -1, -1, 224, -1, -1, -1, -1, -1, -1, -1, -1, 121, -1, -1, -1, 224, 224, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 362, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 132, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 113, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 210, -1, -1, -1, -1, -1, -1, -1, -1, 113, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, 164, -1, 164, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 164, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 164, -1, -1, -1, 164, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 164, -1, 164, -1, -1, -1, -1, -1, -1, -1, 164, 164, -1, -1, -1, -1, -1, 164, -1, -1, 164, -1, -1, -1, 164, -1, 164, -1, -1, -1, -1, -1, -1, 164, -1, -1, -1, -1, -1, -1, -1, -1, 164, -1, -1, -1, 349, 164, -1, -1, -1, -1, -1, -1, -1, -1],
    [21, -1, -1, 21, -1, -1, -1, 21, -1, 21, -1, -1, 21, -1, -1, -1, 21, -1, -1, 21, 21, -1, -1, 21, -1, -1, 21, -1, 21, -1, -1, -1, -1, 21, -1, -1, 21, 21, -1, -1, 21, -1, 21, -1, -1, -1, -1, 21, -1, -1, -1, 21, 21, -1, -1, 21, -1, 21, -1, 21, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 21, -1, -1, -1, 21, -1, -1, 21, 21, 21, 21, -1, -1, -1, 21, -1, -1, -1, -1, -1, 186, -1, -1, -1, -1, -1, 21, 21, -1, -1, 21, 21, -1, 21, -1, 21, -1, -1, -1, -1, 21, -1, 21, -1, -1],
    [-1, -1, 92, -1, -1, -1, 92, -1, 92, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 92, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 92, -1, -1, -1, 92, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 92, -1, -1, -1, -1, -1, -1, -1, -1, -1, 92, 92, -1, -1, -1, -1, -1, 92, -1, -1, 92, -1, -1, -1, 92, -1, 92, -1, -1, -1, -1, 287, -1, 92, -1, -1, -1, -1, -1, -1, -1, -1, 92, -1, -1, -1, -1, 92, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 251, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 85, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 219, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [175, -1, -1, -1, -1, -1, -1, 175, -1, 360, -1, -1, 198, -1, -1, -1, 331, -1, -1, 198, 198, -1, -1, 198, -1, -1, 198, -1, 331, -1, -1, -1, -1, -1, -1, -1, 331, 198, -1, -1, 198, -1, 198, -1, -1, -1, -1, 198, -1, -1, -1, 198, 198, -1, -1, 198, -1, -1, -1, 198, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 198, -1, -1, -1, 198, -1, 198, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 175, 175, -1, -1, -1, -1, -1, -1, -1, 175, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 393, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 192, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [230, 9, -1, -1, -1, -1, 9, 230, 9, 230, -1, -1, 230, -1, -1, -1, 230, -1, 9, 230, 230, -1, -1, 230, -1, 9, 230, 9, 230, -1, -1, -1, -1, -1, -1, -1, 230, 230, -1, 9, 230, -1, 230, -1, 9, -1, -1, 230, 9, -1, 9, 230, 230, -1, -1, 230, -1, -1, 9, 230, 9, -1, 9, -1, -1, 9, 9, -1, -1, -1, 9, 9, -1, -1, -1, 230, -1, 9, -1, 230, 9, 230, -1, -1, 9, -1, 9, -1, -1, 9, -1, 9, -1, 9, 9, -1, -1, 230, 230, -1, -1, -1, 9, -1, -1, -1, 230, 9, 9, 9, -1, -1, -1, 9, -1, -1],
    [303, -1, -1, -1, -1, -1, 141, 303, 141, 303, -1, -1, 303, -1, -1, -1, 303, -1, -1, 303, 303, -1, -1, 303, -1, -1, 303, 141, 303, -1, -1, -1, -1, -1, -1, -1, 303, 303, -1, -1, 303, -1, 303, -1, 141, -1, -1, 303, 141, -1, -1, 303, 303, -1, -1, 303, -1, -1, -1, 303, 141, -1, 141, -1, -1, -1, -1, -1, -1, -1, 141, 141, -1, -1, -1, 303, -1, 141, -1, 303, 141, 303, -1, -1, 141, -1, 141, -1, -1, -1, -1, -1, -1, 141, -1, -1, -1, 303, 303, -1, -1, -1, 141, -1, -1, -1, 303, 141, -1, -1, -1, -1, -1, 114, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 44, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 310, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 310, -1, -1, -1, -1, -1, -1, -1, 310, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 104, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 176, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, 324, -1, -1, -1, 324, -1, 324, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 324, -1, -1, -1, -1, -1, -1, -1, 324, -1, -1, -1, -1, -1, -1, -1, -1, 324, -1, -1, -1, 324, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 324, -1, -1, -1, -1, -1, -1, -1, -1, -1, 324, 324, -1, -1, -1, -1, -1, 324, -1, -1, 324, -1, -1, -1, 324, -1, 324, -1, -1, -1, -1, 324, -1, 324, -1, -1, 324, -1, -1, -1, -1, -1, 324, 324, -1, -1, -1, 324, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 413, -1, -1, -1, 413, -1, -1, 413, 413, -1, -1, 413, -1, -1, 413, -1, 413, -1, -1, -1, -1, 413, -1, -1, 413, 413, -1, -1, 413, -1, 413, -1, -1, -1, -1, 413, -1, -1, -1, 413, 413, -1, -1, 413, -1, -1, -1, 413, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 413, -1, -1, -1, 413, -1, -1, -1, 413, 413, 413, -1, -1, -1, 413, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 413, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 110, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 347, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, 174, -1, 174, -1, -1, -1, -1, -1, -1, -1, 174, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 174, 174, -1, -1, -1, -1, -1, -1, -1, 174, -1, -1, -1, -1, -1, -1, -1, 174, -1, -1, -1, 174, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 174, -1, 174, -1, -1, -1, -1, -1, -1, -1, 174, 174, -1, -1, -1, -1, -1, 174, -1, -1, 174, -1, -1, -1, 174, -1, 174, -1, -1, -1, -1, -1, -1, 174, -1, -1, -1, -1, -1, -1, -1, -1, 174, -1, -1, -1, 174, 174, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 125, -1, -1, -1, -1, -1, -1, -1, -1, 125, -1, -1, -1, -1, 125, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 125, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 23, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 71, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 357, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, 206, -1, -1, -1, -1, 304, -1, 304, -1, -1, -1, -1, -1, -1, -1, -1, -1, 47, -1, -1, -1, -1, -1, -1, 206, -1, 304, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 264, -1, -1, -1, -1, 304, -1, -1, -1, 304, -1, 269, -1, -1, -1, -1, -1, -1, -1, 269, -1, 304, -1, 304, -1, -1, 269, 269, -1, -1, -1, 304, 304, -1, -1, -1, -1, -1, 304, -1, -1, 304, -1, -1, -1, 304, -1, 304, -1, -1, 47, -1, 3, -1, 304, 47, -1, -1, -1, -1, -1, -1, -1, 304, -1, -1, -1, -1, 304, 264, 206, -1, -1, -1, 304, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 235, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 294, -1, -1, -1, -1, 170, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, 412, -1, 412, -1, -1, -1, -1, -1, -1, -1, 410, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 412, 410, -1, -1, -1, -1, -1, -1, -1, 410, -1, -1, -1, -1, -1, -1, -1, 412, -1, -1, -1, 412, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 412, -1, 412, -1, -1, -1, -1, -1, -1, -1, 412, 412, -1, -1, -1, -1, -1, 412, -1, -1, 412, -1, -1, -1, 412, -1, 412, -1, -1, -1, -1, -1, -1, 412, -1, -1, -1, -1, -1, -1, -1, -1, 412, -1, -1, -1, 410, 412, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 333, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 333, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 423, -1, -1],
    [-1, -1, -1, 338, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 341, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 373, -1, -1, -1, 373, -1, -1, 373, 373, -1, -1, 373, -1, -1, 373, -1, 373, -1, -1, -1, -1, 373, -1, -1, 373, 373, -1, -1, 373, -1, 373, -1, -1, -1, -1, 373, -1, 288, -1, 373, 373, -1, -1, 373, -1, -1, -1, 373, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 373, -1, -1, -1, 373, -1, -1, -1, 373, 373, 373, -1, -1, -1, 373, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 373, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [276, -1, -1, -1, -1, -1, -1, 276, -1, 276, -1, -1, 276, -1, -1, -1, 276, -1, -1, 276, 276, -1, -1, 276, -1, -1, 276, -1, 276, -1, -1, -1, -1, -1, -1, -1, 276, 276, -1, -1, 276, -1, 276, -1, -1, -1, -1, 276, -1, -1, -1, 276, 276, -1, -1, 276, -1, -1, -1, 276, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 276, -1, -1, -1, 276, 260, 276, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 276, 276, -1, -1, -1, -1, -1, -1, -1, 276, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 138, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 262, -1, -1, -1],
    [1, -1, -1, -1, -1, -1, -1, 1, -1, 1, -1, -1, 1, -1, -1, -1, 1, -1, -1, 1, 1, -1, -1, 1, -1, -1, 1, -1, 1, -1, -1, -1, -1, -1, -1, -1, 1, 1, -1, -1, 1, -1, 1, -1, -1, -1, -1, 1, -1, -1, -1, 1, 1, -1, -1, 1, -1, -1, -1, 1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 1, -1, -1, -1, 1, -1, 1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 1, 1, -1, -1, -1, -1, -1, -1, -1, 1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [58, -1, -1, -1, -1, -1, -1, 58, -1, 58, -1, -1, 58, -1, -1, -1, 58, -1, -1, 58, 58, -1, -1, 58, -1, -1, 58, -1, 58, -1, -1, -1, -1, -1, -1, -1, 58, 58, -1, -1, 58, -1, 58, -1, -1, -1, -1, 58, -1, -1, -1, 58, 58, -1, -1, 58, -1, -1, -1, 58, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 58, -1, -1, -1, 58, -1, 58, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 58, 58, -1, -1, -1, -1, -1, -1, -1, 58, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 155, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 39, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 117, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 117, -1, -1, -1, -1, -1, -1, 117, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 38, -1, -1, -1, -1, -1, -1, -1, -1, 129, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 191, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 407, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 343, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 343, -1, -1, -1, -1, -1, -1, -1, 343, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 407, -1, -1, -1, -1, -1, -1, -1, -1, 407, -1, -1, -1, -1, 407, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 407, -1, 407, -1, 407, -1, -1, -1, -1, 407, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 204, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 204, -1, -1, -1, -1, -1, -1, -1, -1, 204, -1, -1, -1, -1],
    [359, 359, -1, -1, -1, -1, 359, 359, 359, 359, -1, -1, 359, -1, -1, -1, 359, -1, 359, 359, 359, -1, -1, 359, -1, 359, 359, 359, 359, -1, -1, -1, -1, -1, -1, -1, 359, 359, -1, 359, 359, -1, 359, -1, 359, -1, -1, 359, 359, 359, 359, 359, 359, -1, -1, 359, -1, -1, 359, 359, 359, -1, 359, -1, -1, 359, 359, -1, -1, 359, 359, 359, -1, -1, -1, 359, -1, 359, -1, 359, 359, 359, -1, -1, 359, -1, 359, -1, -1, 359, -1, 359, -1, 359, 359, -1, -1, 359, 359, 359, -1, -1, 359, -1, -1, -1, 359, 359, 359, 359, -1, -1, -1, 359, -1, 359],
    [137, 137, -1, -1, -1, -1, 137, 137, 137, 137, -1, -1, 137, -1, -1, -1, 137, -1, 137, 137, 137, -1, -1, 137, -1, 137, 137, 137, 137, -1, -1, -1, -1, -1, -1, -1, 137, 137, -1, 137, 137, -1, 137, -1, 137, -1, -1, 137, 137, 137, 137, 137, 137, -1, -1, 137, -1, -1, 137, 137, 137, -1, 137, -1, -1, 137, 137, -1, -1, 137, 137, 137, -1, -1, -1, 137, -1, 137, -1, 137, 137, 137, -1, -1, 137, -1, 137, -1, -1, 137, -1, 137, -1, 137, 137, -1, -1, 137, 137, 137, -1, -1, 137, -1, -1, -1, 137, 137, 137, 137, -1, -1, -1, 137, -1, 137],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 118, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, 298, -1, 298, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 298, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 298, -1, -1, -1, 298, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 298, -1, 298, -1, -1, -1, -1, -1, -1, -1, 298, 298, -1, -1, -1, -1, -1, 298, -1, -1, 298, -1, -1, -1, 298, -1, 298, -1, -1, -1, -1, -1, -1, 298, -1, -1, -1, -1, -1, -1, -1, -1, 298, -1, -1, -1, -1, 298, -1, -1, -1, -1, -1, 298, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 185, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 408, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 143, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, 158, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 274, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 205, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 245, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 245, -1, -1, -1, -1, -1, -1, 352, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 111, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 142, -1, -1, -1, -1, -1, -1, -1],
    [151, 151, -1, -1, -1, -1, 151, 151, 151, 151, -1, -1, 151, -1, -1, -1, 151, -1, 151, 151, 151, -1, -1, 151, -1, 151, 151, 151, 151, -1, -1, -1, -1, -1, -1, -1, 151, 151, -1, 151, 151, -1, 151, -1, 151, -1, -1, 151, 151, 151, 151, 151, 151, -1, -1, 151, -1, -1, 151, 151, 151, -1, 151, -1, -1, 151, 151, -1, -1, 151, 151, 151, -1, -1, -1, 151, -1, 151, -1, 151, 151, 151, -1, -1, 151, -1, 151, -1, -1, 151, -1, 151, -1, 151, 151, -1, -1, 151, 151, 401, -1, -1, 151, -1, -1, -1, 151, 151, 151, 151, -1, -1, -1, 151, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 374, -1, -1, -1, -1, -1, -1, -1, -1, 374, -1, -1, -1, -1, 374, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 374, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [351, -1, -1, 351, -1, -1, -1, 351, -1, 351, -1, -1, 351, -1, -1, -1, 351, -1, -1, 351, 351, -1, -1, 351, -1, -1, 351, -1, 351, -1, -1, -1, -1, -1, -1, -1, 351, 351, -1, -1, 351, -1, 351, -1, -1, -1, -1, 351, -1, -1, -1, 351, 351, -1, -1, 351, -1, -1, -1, 351, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 351, -1, -1, -1, 351, -1, 351, -1, -1, -1, -1, -1, -1, -1, -1, -1, 351, -1, -1, -1, -1, -1, 351, 351, -1, -1, -1, -1, -1, -1, -1, 351, -1, -1, -1, -1, -1, -1, 351, -1, -1],
    [377, -1, -1, 377, -1, -1, -1, 377, -1, 377, -1, -1, 377, -1, -1, -1, 377, -1, -1, 377, 377, -1, -1, 377, -1, -1, 377, -1, 377, -1, -1, -1, -1, -1, -1, -1, 377, 377, -1, -1, 377, -1, 377, -1, -1, -1, -1, 377, -1, -1, -1, 377, 377, -1, -1, 377, -1, -1, -1, 377, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 377, -1, -1, -1, 377, -1, 377, -1, -1, -1, -1, -1, -1, -1, -1, -1, 377, -1, -1, -1, -1, -1, 377, 377, -1, -1, -1, -1, -1, -1, -1, 377, -1, -1, -1, -1, -1, -1, 377, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 248, -1, -1, -1, -1, -1, -1, -1, 61, -1, -1, -1, -1, -1, -1, 133, 55, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 69, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 69, -1, -1, -1, -1, -1, -1, -1, -1, 69, -1, -1, -1, -1, 69, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 69, -1, 69, -1, -1, -1, -1, -1, -1, 69, -1, -1, -1, -1],
    [-1, -1, -1, 42, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 42, -1, -1, -1, -1, -1, -1, -1, -1, 42, -1, -1, -1, -1, 42, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 42, -1, 42, -1, -1, -1, -1, -1, -1, 42, -1, -1, -1, -1],
    [-1, -1, 275, 59, -1, -1, 275, -1, 275, -1, -1, -1, -1, -1, -1, -1, -1, 295, -1, -1, -1, -1, -1, -1, -1, -1, -1, 275, -1, 295, -1, -1, -1, 295, -1, 295, -1, -1, -1, -1, -1, -1, -1, 295, 275, -1, -1, -1, 275, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 275, -1, -1, -1, -1, -1, -1, -1, -1, -1, 275, 275, -1, -1, -1, -1, -1, 275, -1, -1, 275, -1, -1, -1, 275, -1, 275, -1, -1, -1, -1, 356, -1, 275, -1, -1, 356, -1, -1, -1, -1, -1, 275, 356, -1, 295, -1, 275, -1, -1, -1, -1, 295, 295, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 145, -1, -1, -1, 177, -1, -1, 145, 145, -1, -1, 145, -1, -1, 145, -1, 177, -1, -1, -1, -1, -1, -1, -1, 177, 145, -1, -1, 145, -1, 145, -1, -1, -1, -1, 145, -1, -1, -1, 145, 145, -1, -1, 145, -1, -1, -1, 145, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 145, -1, -1, -1, 145, -1, 145, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [136, 136, -1, -1, -1, -1, 136, 136, 136, 136, -1, -1, 136, -1, -1, -1, 136, -1, 136, 136, 136, -1, -1, 136, -1, 136, 136, 136, 136, -1, -1, -1, -1, -1, -1, -1, 136, 136, -1, 136, 136, -1, 136, -1, 136, -1, -1, 136, 136, 136, 136, 136, 136, -1, -1, 136, -1, -1, 136, 136, 136, -1, 136, -1, -1, 136, 136, -1, -1, 136, 136, 136, -1, -1, -1, 136, -1, 136, -1, 136, 136, 136, -1, -1, 136, -1, 136, -1, -1, 136, -1, 136, -1, 136, 136, -1, -1, 136, 136, 136, -1, -1, 136, -1, -1, -1, 136, 136, 136, 136, -1, -1, -1, 136, -1, 168],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 227, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 289, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 296, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, 348, -1, 348, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 348, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 348, -1, -1, -1, 348, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 348, -1, 348, -1, -1, -1, -1, -1, -1, -1, 348, 348, -1, -1, -1, -1, -1, 348, -1, -1, 348, -1, -1, -1, 348, -1, 348, -1, -1, -1, -1, -1, -1, 348, -1, -1, -1, -1, -1, -1, -1, -1, 14, -1, -1, -1, -1, 348, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 284, -1, -1, -1, -1, -1, -1, -1, -1, 284, -1, -1, -1, -1, 284, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 284, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 404, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 399, -1, -1, -1, -1, -1, -1, -1, -1, 399, -1, -1, -1, -1, 399, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 399, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 404, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 78, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 382, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 225, -1, -1, -1, -1, -1, -1, -1, -1, 225, -1, -1, -1, -1, 225, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 225, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 416, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 416, -1, -1, -1, -1, -1, -1, -1, -1, 416, -1, -1, -1, -1, 416, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 416, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 79, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 411, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 28, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 255, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, 84, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 84, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 84, -1, -1, -1, -1, -1, -1, -1, 84, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 84, -1, -1, -1, -1, -1, -1, -1, -1, 84, -1, -1, -1, -1, 84, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 84, -1, 84, -1, 84, -1, -1, -1, -1, 84, -1, -1, -1, -1],
    [63, -1, -1, -1, -1, -1, -1, 63, -1, 63, -1, -1, 63, -1, -1, -1, 63, -1, -1, 63, 63, -1, -1, 63, -1, -1, 63, -1, 63, -1, -1, -1, -1, -1, -1, -1, 63, 63, -1, -1, 63, -1, 63, -1, -1, -1, -1, 63, -1, -1, -1, 63, 63, -1, -1, 63, -1, -1, -1, 63, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 63, -1, -1, -1, 63, -1, 63, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 63, 63, -1, -1, -1, -1, -1, -1, -1, 63, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [161, -1, -1, 417, -1, -1, -1, 161, -1, 161, -1, -1, 161, -1, -1, -1, 161, -1, -1, 161, 161, -1, -1, 161, -1, -1, 161, -1, 161, -1, -1, -1, -1, -1, -1, -1, 161, 161, -1, -1, 161, -1, 161, -1, -1, -1, -1, 161, -1, -1, -1, 161, 161, -1, -1, 161, -1, 417, -1, 161, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 417, -1, -1, -1, 161, -1, -1, 417, 161, 417, 161, -1, -1, -1, 417, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 161, 161, -1, -1, 417, 417, -1, 417, -1, 161, -1, -1, -1, -1, 417, -1, 417, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 89, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [246, 246, -1, -1, -1, -1, 246, 246, 246, 246, -1, -1, 246, -1, -1, -1, 246, -1, 246, 246, 246, -1, -1, 246, -1, 246, 246, 246, 246, -1, -1, -1, -1, -1, -1, -1, 246, 246, -1, 246, 246, -1, 246, -1, 246, -1, -1, 246, 246, 246, 246, 246, 246, -1, -1, 246, -1, -1, 246, 246, 246, -1, 246, -1, -1, 246, 246, -1, -1, -1, 246, 246, -1, -1, -1, 246, -1, 246, -1, 246, 246, 246, -1, -1, 246, -1, 246, -1, -1, 246, -1, 246, -1, 246, 246, -1, -1, 246, 246, -1, -1, -1, 246, -1, -1, -1, 246, 246, 246, 246, -1, -1, -1, 246, -1, -1],
    [257, 257, -1, -1, -1, -1, 257, 257, 257, 257, -1, -1, 257, -1, -1, -1, 257, -1, 257, 257, 257, -1, -1, 257, -1, 257, 257, 257, 257, -1, -1, -1, -1, -1, -1, -1, 257, 257, -1, 257, 257, -1, 257, -1, 257, -1, -1, 257, 257, 257, 257, 257, 257, -1, -1, 257, -1, -1, 257, 257, 257, -1, 257, -1, -1, 257, 257, -1, -1, -1, 257, 257, -1, -1, -1, 257, -1, 257, -1, 257, 257, 257, -1, -1, 257, -1, 257, -1, -1, 257, -1, 257, -1, 257, 257, -1, -1, 257, 257, -1, -1, -1, 257, -1, -1, -1, 257, 257, 257, 257, -1, -1, -1, 257, -1, -1],
    [2, -1, -1, 6, -1, -1, -1, 2, -1, 2, -1, -1, 2, -1, -1, -1, 2, -1, -1, 2, 2, -1, -1, 2, -1, -1, 2, -1, 2, -1, -1, -1, -1, -1, -1, -1, 2, 2, -1, -1, 2, -1, 2, -1, -1, -1, -1, 2, -1, -1, -1, 2, 2, -1, -1, 2, -1, -1, -1, 2, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 2, -1, -1, -1, 2, -1, 2, -1, -1, -1, -1, -1, -1, -1, -1, -1, 6, -1, -1, -1, -1, -1, 2, 2, -1, -1, -1, -1, -1, -1, -1, 2, -1, -1, -1, -1, -1, -1, 6, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [98, -1, -1, -1, -1, -1, -1, 98, -1, 98, -1, -1, 98, -1, -1, -1, 98, -1, -1, 98, 98, -1, -1, 98, -1, -1, 98, -1, 98, -1, -1, -1, -1, -1, -1, -1, 98, 98, -1, -1, 98, -1, 98, -1, -1, -1, -1, 98, -1, -1, -1, 98, 98, -1, -1, 98, -1, -1, -1, 98, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 98, -1, -1, -1, 98, -1, 98, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 98, 98, -1, -1, -1, -1, -1, -1, -1, 98, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 135, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 116, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 116, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 116, -1, -1],
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 65, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
  ]
  TERMINAL_AUTO = 0
  TERMINAL_WHILE = 1
  TERMINAL__EXPR_SANS_COMMA = 2
  TERMINAL_COMMA = 3
  TERMINAL_OR = 4
  TERMINAL_GT = 5
  TERMINAL_INCR = 6
  TERMINAL_REGISTER = 7
  TERMINAL_BITAND = 8
  TERMINAL_INLINE = 9
  TERMINAL_EQ = 10
  TERMINAL_PP_NUMBER = 11
  TERMINAL_TYPEDEF_IDENTIFIER = 12
  TERMINAL_LT = 13
  TERMINAL_DIVEQ = 14
  TERMINAL_SUBEQ = 15
  TERMINAL_CONST = 16
  TERMINAL_ARROW = 17
  TERMINAL_LABEL_HINT = 18
  TERMINAL_STRUCT = 19
  TERMINAL_ENUM = 20
  TERMINAL_BITOREQ = 21
  TERMINAL_DIV = 22
  TERMINAL_CHAR = 23
  TERMINAL_DEFINED_SEPARATOR = 24
  TERMINAL_DO = 25
  TERMINAL_UNION = 26
  TERMINAL_STRING_LITERAL = 27
  TERMINAL_RESTRICT = 28
  TERMINAL_QUESTIONMARK = 29
  TERMINAL_UNIVERSAL_CHARACTER_NAME = 30
  TERMINAL_BITNOT = 31
  TERMINAL_ELIPSIS = 32
  TERMINAL_COLON = 33
  TERMINAL_EXCLAMATION_POINT = 34
  TERMINAL_DOT = 35
  TERMINAL_VOLATILE = 36
  TERMINAL_INT = 37
  TERMINAL_GTEQ = 38
  TERMINAL_IF = 39
  TERMINAL_VOID = 40
  TERMINAL_NOT = 41
  TERMINAL_LONG = 42
  TERMINAL_RPAREN = 43
  TERMINAL_INTEGER_CONSTANT = 44
  TERMINAL_DEFINED = 45
  TERMINAL_ADD = 46
  TERMINAL_IMAGINARY = 47
  TERMINAL_FLOATING_CONSTANT = 48
  TERMINAL_RBRACE = 49
  TERMINAL_RETURN = 50
  TERMINAL_COMPLEX = 51
  TERMINAL_SIGNED = 52
  TERMINAL_SIZEOF_SEPARATOR = 53
  TERMINAL_BITXOR = 54
  TERMINAL_DOUBLE = 55
  TERMINAL_LTEQ = 56
  TERMINAL_FUNCTION_DEFINITION_HINT = 57
  TERMINAL_GOTO = 58
  TERMINAL_SHORT = 59
  TERMINAL_DECR = 60
  TERMINAL_BITANDEQ = 61
  TERMINAL__EXPR = 62
  TERMINAL_ADDEQ = 63
  TERMINAL_MULEQ = 64
  TERMINAL_BREAK = 65
  TERMINAL_CONTINUE = 66
  TERMINAL_POUND = 67
  TERMINAL_POUNDPOUND = 68
  TERMINAL_ENDIF = 69
  TERMINAL_SIZEOF = 70
  TERMINAL_LPAREN = 71
  TERMINAL_SUB = 72
  TERMINAL_TILDE = 73
  TERMINAL_MODEQ = 74
  TERMINAL_BOOL = 75
  TERMINAL_NEQ = 76
  TERMINAL_HEXADECIMAL_FLOATING_CONSTANT = 77
  TERMINAL_DECLARATOR_HINT = 78
  TERMINAL_FLOAT = 79
  TERMINAL_IDENTIFIER = 80
  TERMINAL_UNSIGNED = 81
  TERMINAL_BITOR = 82
  TERMINAL_AND = 83
  TERMINAL_ENUMERATION_CONSTANT = 84
  TERMINAL__DIRECT_DECLARATOR = 85
  TERMINAL_LPAREN_CAST = 86
  TERMINAL_RSHIFTEQ = 87
  TERMINAL_BITXOREQ = 88
  TERMINAL_DEFAULT = 89
  TERMINAL_MOD = 90
  TERMINAL_LBRACE = 91
  TERMINAL_RSHIFT = 92
  TERMINAL_DECIMAL_FLOATING_CONSTANT = 93
  TERMINAL_CASE = 94
  TERMINAL_AMPERSAND = 95
  TERMINAL_LSQUARE = 96
  TERMINAL_EXTERN = 97
  TERMINAL_TYPEDEF = 98
  TERMINAL_ELSE = 99
  TERMINAL_EXTERNAL_DECLARATION_HINT = 100
  TERMINAL_FUNCTION_PROTOTYPE_HINT = 101
  TERMINAL_ASTERISK = 102
  TERMINAL_ASSIGN = 103
  TERMINAL_COMMA_VA_ARGS = 104
  TERMINAL_RSQUARE = 105
  TERMINAL_STATIC = 106
  TERMINAL_CHARACTER_CONSTANT = 107
  TERMINAL_SWITCH = 108
  TERMINAL_FOR = 109
  TERMINAL_LSHIFTEQ = 110
  TERMINAL__DIRECT_ABSTRACT_DECLARATOR = 111
  TERMINAL_TRAILING_COMMA = 112
  TERMINAL_SEMI = 113
  TERMINAL_LSHIFT = 114
  TERMINAL_ELSE_IF = 115
  def __init__(self, tokens=None):
    self.__dict__.update(locals())
    self.expressionParsers = dict()
  def isTerminal(self, id):
    return 0 <= id <= 115
  def isNonTerminal(self, id):
    return 116 <= id <= 243
  def parse(self, tokens):
    self.tokens = tokens
    self.start = 'TRANSLATION_UNIT'
    tree = self.parse_translation_unit()
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
  def parse_keyword(self):
    current = self.tokens.current()
    rule = self.table[0][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(116, self.nonterminals[116]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 25:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(36) # volatile
      tree.add(t)
      return tree
    elif rule == 34:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(28) # restrict
      tree.add(t)
      return tree
    elif rule == 49:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(97) # extern
      tree.add(t)
      return tree
    elif rule == 52:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(50) # return
      tree.add(t)
      return tree
    elif rule == 73:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(42) # long
      tree.add(t)
      return tree
    elif rule == 96:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(25) # do
      tree.add(t)
      return tree
    elif rule == 120:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(1) # while
      tree.add(t)
      return tree
    elif rule == 131:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(16) # const
      tree.add(t)
      return tree
    elif rule == 159:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(51) # complex
      tree.add(t)
      return tree
    elif rule == 166:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(94) # case
      tree.add(t)
      return tree
    elif rule == 167:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(40) # void
      tree.add(t)
      return tree
    elif rule == 189:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(106) # static
      tree.add(t)
      return tree
    elif rule == 193:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(70) # sizeof
      tree.add(t)
      return tree
    elif rule == 213:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(9) # inline
      tree.add(t)
      return tree
    elif rule == 217:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(55) # double
      tree.add(t)
      return tree
    elif rule == 242:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(89) # default
      tree.add(t)
      return tree
    elif rule == 249:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(7) # register
      tree.add(t)
      return tree
    elif rule == 258:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(99) # else
      tree.add(t)
      return tree
    elif rule == 271:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(108) # switch
      tree.add(t)
      return tree
    elif rule == 273:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(52) # signed
      tree.add(t)
      return tree
    elif rule == 282:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(109) # for
      tree.add(t)
      return tree
    elif rule == 290:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(98) # typedef
      tree.add(t)
      return tree
    elif rule == 299:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(75) # bool
      tree.add(t)
      return tree
    elif rule == 306:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(79) # float
      tree.add(t)
      return tree
    elif rule == 307:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(37) # int
      tree.add(t)
      return tree
    elif rule == 312:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(26) # union
      tree.add(t)
      return tree
    elif rule == 315:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(66) # continue
      tree.add(t)
      return tree
    elif rule == 318:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(65) # break
      tree.add(t)
      return tree
    elif rule == 320:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(23) # char
      tree.add(t)
      return tree
    elif rule == 321:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(39) # if
      tree.add(t)
      return tree
    elif rule == 322:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(81) # unsigned
      tree.add(t)
      return tree
    elif rule == 344:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(20) # enum
      tree.add(t)
      return tree
    elif rule == 369:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(19) # struct
      tree.add(t)
      return tree
    elif rule == 385:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(58) # goto
      tree.add(t)
      return tree
    elif rule == 392:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(0) # auto
      tree.add(t)
      return tree
    elif rule == 414:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(59) # short
      tree.add(t)
      return tree
    elif rule == 419:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(47) # imaginary
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_compound_statement(self):
    current = self.tokens.current()
    rule = self.table[1][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(117, self.nonterminals[117]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 316:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(91) # lbrace
      tree.add(t)
      subtree = self.parse__gen35()
      tree.add( subtree )
      t = self.expect(49) # rbrace
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_parameter_declaration_sub(self):
    current = self.tokens.current()
    rule = self.table[2][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(118, self.nonterminals[118]))
    tree.list = False
    if current == None:
      return tree
    if rule == 178:
      tree.astTransform = AstTransformNodeCreator('ParameterSub', {'name_and_size': 1, 'pointer': 0})
      subtree = self.parse_pointer_opt()
      tree.add( subtree )
      subtree = self.parse_parameter_declaration_sub_sub()
      tree.add( subtree )
      return tree
    elif current.getId() in [85, 71, 80]:
      tree.astTransform = AstTransformNodeCreator('ParameterSub', {'name_and_size': 1, 'pointer': 0})
      subtree = self.parse_pointer_opt()
      tree.add( subtree )
      subtree = self.parse_parameter_declaration_sub_sub()
      tree.add( subtree )
    elif current.getId() in [111, 71]:
      tree.astTransform = AstTransformNodeCreator('ParameterSub', {'name_and_size': 1, 'pointer': 0})
      subtree = self.parse_pointer_opt()
      tree.add( subtree )
      subtree = self.parse_parameter_declaration_sub_sub()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen42(self):
    current = self.tokens.current()
    rule = self.table[3][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(119, self.nonterminals[119]))
    tree.list = False
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 147:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_parameter_type_list()
      tree.add( subtree )
      return tree
    return tree
  def parse_struct_declarator_body(self):
    current = self.tokens.current()
    rule = self.table[4][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(120, self.nonterminals[120]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 223:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(33) # colon
      tree.add(t)
      subtree = self.parse_declarator()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_misc(self):
    current = self.tokens.current()
    rule = self.table[5][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(121, self.nonterminals[121]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 109:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(69) # endif
      tree.add(t)
      return tree
    elif rule == 208:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(30) # universal_character_name
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_else_if_statement(self):
    current = self.tokens.current()
    rule = self.table[6][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(122, self.nonterminals[122]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 149:
      tree.astTransform = AstTransformNodeCreator('ElseIf', {'statement': 4, 'condition': 2})
      t = self.expect(115) # else_if
      tree.add(t)
      t = self.expect(71) # lparen
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      t = self.expect(43) # rparen
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      t = self.expect(69) # endif
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_constant(self):
    current = self.tokens.current()
    rule = self.table[7][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(123, self.nonterminals[123]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 15:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(48) # floating_constant
      tree.add(t)
      return tree
    elif rule == 64:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(44) # integer_constant
      tree.add(t)
      return tree
    elif rule == 88:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(84) # enumeration_constant
      tree.add(t)
      return tree
    elif rule == 266:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(93) # decimal_floating_constant
      tree.add(t)
      return tree
    elif rule == 302:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(77) # hexadecimal_floating_constant
      tree.add(t)
      return tree
    elif rule == 396:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(107) # character_constant
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen23(self):
    current = self.tokens.current()
    rule = self.table[8][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(124, self.nonterminals[124]))
    tree.list = 'slist'
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 35:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_enumerator()
      tree.add( subtree )
      subtree = self.parse__gen24()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen21(self):
    current = self.tokens.current()
    rule = self.table[9][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(125, self.nonterminals[125]))
    tree.list = False
    if current != None and (current.getId() in [113, 3]):
      return tree
    if current == None:
      return tree
    if rule == 16:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_struct_declarator_body()
      tree.add( subtree )
      return tree
    return tree
  def parse_init_declarator_list(self):
    current = self.tokens.current()
    rule = self.table[10][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(126, self.nonterminals[126]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 183:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen9()
      tree.add( subtree )
      return tree
    elif current.getId() in [85, 71, 80]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen9()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_for_cond(self):
    current = self.tokens.current()
    rule = self.table[11][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(127, self.nonterminals[127]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 403:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(113) # semi
      tree.add(t)
      subtree = self.parse_expression_opt()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_for_incr(self):
    current = self.tokens.current()
    rule = self.table[12][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(128, self.nonterminals[128]))
    tree.list = False
    if current != None and (current.getId() in [43]):
      return tree
    if current == None:
      return tree
    if rule == 232:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(113) # semi
      tree.add(t)
      subtree = self.parse_expression_opt()
      tree.add( subtree )
      return tree
    return tree
  def parse_parameter_declaration_sub_sub(self):
    current = self.tokens.current()
    rule = self.table[14][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(130, self.nonterminals[130]))
    tree.list = False
    if current == None:
      return tree
    if rule == 163:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__direct_declarator()
      tree.add( subtree )
      return tree
    elif rule == 323:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen33()
      tree.add( subtree )
      return tree
    elif current.getId() in [85, 71, 80]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__direct_declarator()
      tree.add( subtree )
    elif current.getId() in [111, 71]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen33()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_punctuator(self):
    current = self.tokens.current()
    rule = self.table[15][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(131, self.nonterminals[131]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 12:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(61) # bitandeq
      tree.add(t)
      return tree
    elif rule == 17:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(110) # lshifteq
      tree.add(t)
      return tree
    elif rule == 18:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(90) # mod
      tree.add(t)
      return tree
    elif rule == 26:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(54) # bitxor
      tree.add(t)
      return tree
    elif rule == 31:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(87) # rshifteq
      tree.add(t)
      return tree
    elif rule == 66:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(60) # decr
      tree.add(t)
      return tree
    elif rule == 67:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(103) # assign
      tree.add(t)
      return tree
    elif rule == 86:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(21) # bitoreq
      tree.add(t)
      return tree
    elif rule == 91:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(88) # bitxoreq
      tree.add(t)
      return tree
    elif rule == 93:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(32) # elipsis
      tree.add(t)
      return tree
    elif rule == 97:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(10) # eq
      tree.add(t)
      return tree
    elif rule == 99:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(72) # sub
      tree.add(t)
      return tree
    elif rule == 100:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(38) # gteq
      tree.add(t)
      return tree
    elif rule == 107:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(73) # tilde
      tree.add(t)
      return tree
    elif rule == 127:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(113) # semi
      tree.add(t)
      return tree
    elif rule == 144:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(95) # ampersand
      tree.add(t)
      return tree
    elif rule == 153:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(67) # pound
      tree.add(t)
      return tree
    elif rule == 171:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(43) # rparen
      tree.add(t)
      return tree
    elif rule == 188:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(96) # lsquare
      tree.add(t)
      return tree
    elif rule == 194:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(74) # modeq
      tree.add(t)
      return tree
    elif rule == 201:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(63) # addeq
      tree.add(t)
      return tree
    elif rule == 209:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(82) # bitor
      tree.add(t)
      return tree
    elif rule == 221:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(64) # muleq
      tree.add(t)
      return tree
    elif rule == 233:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(3) # comma
      tree.add(t)
      return tree
    elif rule == 238:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(76) # neq
      tree.add(t)
      return tree
    elif rule == 239:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(68) # poundpound
      tree.add(t)
      return tree
    elif rule == 267:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(22) # div
      tree.add(t)
      return tree
    elif rule == 277:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(4) # or
      tree.add(t)
      return tree
    elif rule == 285:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(49) # rbrace
      tree.add(t)
      return tree
    elif rule == 300:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(92) # rshift
      tree.add(t)
      return tree
    elif rule == 308:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(83) # and
      tree.add(t)
      return tree
    elif rule == 309:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(91) # lbrace
      tree.add(t)
      return tree
    elif rule == 313:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(15) # subeq
      tree.add(t)
      return tree
    elif rule == 317:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(5) # gt
      tree.add(t)
      return tree
    elif rule == 326:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(56) # lteq
      tree.add(t)
      return tree
    elif rule == 327:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(71) # lparen
      tree.add(t)
      return tree
    elif rule == 328:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(13) # lt
      tree.add(t)
      return tree
    elif rule == 334:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(17) # arrow
      tree.add(t)
      return tree
    elif rule == 335:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(35) # dot
      tree.add(t)
      return tree
    elif rule == 336:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(105) # rsquare
      tree.add(t)
      return tree
    elif rule == 339:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(33) # colon
      tree.add(t)
      return tree
    elif rule == 340:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(29) # questionmark
      tree.add(t)
      return tree
    elif rule == 350:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(34) # exclamation_point
      tree.add(t)
      return tree
    elif rule == 365:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(114) # lshift
      tree.add(t)
      return tree
    elif rule == 379:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(46) # add
      tree.add(t)
      return tree
    elif rule == 381:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(6) # incr
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_enum_specifier_sub(self):
    current = self.tokens.current()
    rule = self.table[16][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(132, self.nonterminals[132]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 123:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_enum_specifier_body()
      tree.add( subtree )
      return tree
    elif rule == 314:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_identifier()
      tree.add( subtree )
      subtree = self.parse__gen22()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_direct_abstract_declarator_opt(self):
    current = self.tokens.current()
    rule = self.table[17][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(133, self.nonterminals[133]))
    tree.list = False
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 148:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__direct_abstract_declarator()
      tree.add( subtree )
      return tree
    elif current.getId() in [111, 71]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__direct_abstract_declarator()
      tree.add( subtree )
    return tree
  def parse_storage_class_specifier(self):
    current = self.tokens.current()
    rule = self.table[18][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(134, self.nonterminals[134]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 40:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(98) # typedef
      tree.add(t)
      return tree
    elif rule == 112:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(106) # static
      tree.add(t)
      return tree
    elif rule == 152:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(0) # auto
      tree.add(t)
      return tree
    elif rule == 330:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(97) # extern
      tree.add(t)
      return tree
    elif rule == 394:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(7) # register
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_direct_declarator_modifier_list_opt(self):
    current = self.tokens.current()
    rule = self.table[19][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(135, self.nonterminals[135]))
    tree.list = False
    if current != None and (current.getId() in [62, 70, 80, 86, 107, 8, 71, 84, 93, 44, 60, 6, 102, 77, 27, 48]):
      return tree
    if current == None:
      return tree
    if rule == 220:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen26()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen33(self):
    current = self.tokens.current()
    rule = self.table[21][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(137, self.nonterminals[137]))
    tree.list = False
    if current != None and (current.getId() in [3, 104]):
      return tree
    if current == None:
      return tree
    if rule == 241:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__direct_abstract_declarator()
      tree.add( subtree )
      return tree
    elif current.getId() in [111, 71]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__direct_abstract_declarator()
      tree.add( subtree )
    return tree
  def parse_type_specifier(self):
    current = self.tokens.current()
    rule = self.table[22][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(138, self.nonterminals[138]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 8:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(23) # char
      tree.add(t)
      return tree
    elif rule == 50:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_typedef_name()
      tree.add( subtree )
      return tree
    elif rule == 74:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(47) # imaginary
      tree.add(t)
      return tree
    elif rule == 80:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_struct_specifier()
      tree.add( subtree )
      return tree
    elif rule == 105:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(40) # void
      tree.add(t)
      return tree
    elif rule == 146:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(59) # short
      tree.add(t)
      return tree
    elif rule == 184:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(37) # int
      tree.add(t)
      return tree
    elif rule == 200:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(81) # unsigned
      tree.add(t)
      return tree
    elif rule == 222:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(75) # bool
      tree.add(t)
      return tree
    elif rule == 247:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(42) # long
      tree.add(t)
      return tree
    elif rule == 254:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(52) # signed
      tree.add(t)
      return tree
    elif rule == 259:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(79) # float
      tree.add(t)
      return tree
    elif rule == 263:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_union_specifier()
      tree.add( subtree )
      return tree
    elif rule == 292:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(51) # complex
      tree.add(t)
      return tree
    elif rule == 378:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_enum_specifier()
      tree.add( subtree )
      return tree
    elif rule == 409:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(55) # double
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen36(self):
    current = self.tokens.current()
    rule = self.table[23][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(139, self.nonterminals[139]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [49]):
      return tree
    if current == None:
      return tree
    if rule == 169:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_block_item()
      tree.add( subtree )
      subtree = self.parse__gen36()
      tree.add( subtree )
      return tree
    elif current.getId() in [62, 48, 70, 80, 86, 107, 8, 71, 84, 93, 44, 60, 27, 77, 6, 102]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_block_item()
      tree.add( subtree )
      subtree = self.parse__gen36()
      tree.add( subtree )
    return tree
  def parse_else_statement(self):
    current = self.tokens.current()
    rule = self.table[24][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(140, self.nonterminals[140]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 95:
      tree.astTransform = AstTransformNodeCreator('Else', {'statement': 1})
      t = self.expect(99) # else
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      t = self.expect(69) # endif
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen40(self):
    current = self.tokens.current()
    rule = self.table[25][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(141, self.nonterminals[141]))
    tree.list = 'slist'
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 60:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr_sans_comma()
      tree.add( subtree )
      subtree = self.parse__gen41()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen29(self):
    current = self.tokens.current()
    rule = self.table[26][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(142, self.nonterminals[142]))
    tree.list = False
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 364:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_va_args()
      tree.add( subtree )
      return tree
    return tree
  def parse_type_qualifier(self):
    current = self.tokens.current()
    rule = self.table[27][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(143, self.nonterminals[143]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 7:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(16) # const
      tree.add(t)
      return tree
    elif rule == 22:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(28) # restrict
      tree.add(t)
      return tree
    elif rule == 391:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(36) # volatile
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen41(self):
    current = self.tokens.current()
    rule = self.table[28][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(144, self.nonterminals[144]))
    tree.list = 'slist'
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 253:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(3) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse__expr_sans_comma()
      tree.add( subtree )
      subtree = self.parse__gen41()
      tree.add( subtree )
      return tree
    return tree
  def parse_external_declarator(self):
    current = self.tokens.current()
    rule = self.table[29][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(145, self.nonterminals[145]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 181:
      tree.astTransform = AstTransformNodeCreator('ExternalDeclarator', {'init_declarator': 1})
      t = self.expect(78) # declarator_hint
      tree.add(t)
      subtree = self.parse__gen6()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_enum_specifier_body(self):
    current = self.tokens.current()
    rule = self.table[30][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(146, self.nonterminals[146]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 32:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(91) # lbrace
      tree.add(t)
      subtree = self.parse__gen23()
      tree.add( subtree )
      subtree = self.parse_trailing_comma_opt()
      tree.add( subtree )
      t = self.expect(49) # rbrace
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen22(self):
    current = self.tokens.current()
    rule = self.table[31][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(147, self.nonterminals[147]))
    tree.list = False
    if current != None and (current.getId() in [55, 80, 57, 59, 3, 52, 12, 0, 113, 40, 19, 71, 16, 75, 26, 23, 28, 51, 85, 33, 111, 36, 37, 20, 81, 97, 42, 98, 101, 102, 7, 78, 106, 47, 79, 104, 9]):
      return tree
    if current == None:
      return tree
    if rule == 43:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_enum_specifier_body()
      tree.add( subtree )
      return tree
    return tree
  def parse_function_specifier(self):
    current = self.tokens.current()
    rule = self.table[32][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(148, self.nonterminals[148]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 380:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(9) # inline
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen30(self):
    current = self.tokens.current()
    rule = self.table[33][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(149, self.nonterminals[149]))
    tree.list = 'slist'
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 337:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_identifier()
      tree.add( subtree )
      subtree = self.parse__gen31()
      tree.add( subtree )
      return tree
    return tree
  def parse_pointer(self):
    current = self.tokens.current()
    rule = self.table[34][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(150, self.nonterminals[150]))
    tree.list = False
    if current == None:
      return tree
    if rule == 278:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen34()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen9(self):
    current = self.tokens.current()
    rule = self.table[35][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(151, self.nonterminals[151]))
    tree.list = 'slist'
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 54:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_init_declarator()
      tree.add( subtree )
      subtree = self.parse__gen10()
      tree.add( subtree )
      return tree
    elif current.getId() in [85, 71, 80]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_init_declarator()
      tree.add( subtree )
      subtree = self.parse__gen10()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_initializer_list_item(self):
    current = self.tokens.current()
    rule = self.table[36][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(152, self.nonterminals[152]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 77:
      tree.astTransform = AstTransformNodeCreator('Initialization', {'designation': 0, 'initializer': 1})
      subtree = self.parse__gen14()
      tree.add( subtree )
      subtree = self.parse_initializer()
      tree.add( subtree )
      return tree
    elif rule == 375:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(44) # integer_constant
      tree.add(t)
      return tree
    elif current.getId() in [80, 2, 44, 84, 86, 107, 8, 71, 70, 93, 48, 60, 102, 77, 6, 27]:
      tree.astTransform = AstTransformNodeCreator('Initialization', {'designation': 0, 'initializer': 1})
      subtree = self.parse__gen14()
      tree.add( subtree )
      subtree = self.parse_initializer()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen10(self):
    current = self.tokens.current()
    rule = self.table[37][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(153, self.nonterminals[153]))
    tree.list = 'slist'
    if current != None and (current.getId() in [113]):
      return tree
    if current == None:
      return tree
    if rule == 57:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(3) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse_init_declarator()
      tree.add( subtree )
      subtree = self.parse__gen10()
      tree.add( subtree )
      return tree
    return tree
  def parse_token(self):
    current = self.tokens.current()
    rule = self.table[38][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(154, self.nonterminals[154]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 48:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_constant()
      tree.add( subtree )
      return tree
    elif rule == 106:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(11) # pp_number
      tree.add(t)
      return tree
    elif rule == 197:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(80) # identifier
      tree.add(t)
      return tree
    elif rule == 234:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_punctuator()
      tree.add( subtree )
      return tree
    elif rule == 280:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(27) # string_literal
      tree.add(t)
      return tree
    elif rule == 370:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_keyword()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_pointer_sub(self):
    current = self.tokens.current()
    rule = self.table[39][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(155, self.nonterminals[155]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 332:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(102) # asterisk
      tree.add(t)
      subtree = self.parse_type_qualifier_list_opt()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_parameter_type_list(self):
    current = self.tokens.current()
    rule = self.table[40][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(156, self.nonterminals[156]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 33:
      tree.astTransform = AstTransformNodeCreator('ParameterTypeList', {'parameter_declarations': 0, 'va_args': 1})
      subtree = self.parse__gen27()
      tree.add( subtree )
      subtree = self.parse__gen29()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen34(self):
    current = self.tokens.current()
    rule = self.table[41][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(157, self.nonterminals[157]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [80, 85, 3, 111, 71, 104]):
      return tree
    if current == None:
      return tree
    if rule == 29:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_pointer_sub()
      tree.add( subtree )
      subtree = self.parse__gen34()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen18(self):
    current = self.tokens.current()
    rule = self.table[42][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(158, self.nonterminals[158]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [80, 102, 85, 33, 71]):
      return tree
    if current == None:
      return tree
    if rule == 11:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_specifier_qualifier()
      tree.add( subtree )
      subtree = self.parse__gen18()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen24(self):
    current = self.tokens.current()
    rule = self.table[43][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(159, self.nonterminals[159]))
    tree.list = 'slist'
    if current != None and (current.getId() in [112]):
      return tree
    if current == None:
      return tree
    if rule == 68:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(3) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse_enumerator()
      tree.add( subtree )
      subtree = self.parse__gen24()
      tree.add( subtree )
      return tree
    return tree
  def parse_expression_opt(self):
    current = self.tokens.current()
    rule = self.table[44][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(160, self.nonterminals[160]))
    tree.list = False
    if current != None and (current.getId() in [113, 43]):
      return tree
    if current == None:
      return tree
    if rule == 4:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr()
      tree.add( subtree )
      return tree
    elif current.getId() in [62, 48, 70, 80, 86, 107, 8, 71, 84, 93, 44, 60, 27, 77, 6, 102]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr()
      tree.add( subtree )
    return tree
  def parse_identifier(self):
    current = self.tokens.current()
    rule = self.table[45][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(161, self.nonterminals[161]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 199:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(80) # identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_declarator_initializer(self):
    current = self.tokens.current()
    rule = self.table[46][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(162, self.nonterminals[162]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 94:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(103) # assign
      tree.add(t)
      subtree = self.parse_initializer()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen11(self):
    current = self.tokens.current()
    rule = self.table[47][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(163, self.nonterminals[163]))
    tree.list = False
    if current != None and (current.getId() in [113, 3]):
      return tree
    if current == None:
      return tree
    if rule == 72:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declarator_initializer()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen14(self):
    current = self.tokens.current()
    rule = self.table[48][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(164, self.nonterminals[164]))
    tree.list = False
    if current != None and (current.getId() in [80, 2, 44, 84, 86, 91, 8, 71, 70, 93, 48, 107, 60, 102, 77, 6, 27]):
      return tree
    if current == None:
      return tree
    if rule == 128:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_designation()
      tree.add( subtree )
      return tree
    return tree
  def parse_enumerator(self):
    current = self.tokens.current()
    rule = self.table[49][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(165, self.nonterminals[165]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 291:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_enumeration_constant()
      tree.add( subtree )
      subtree = self.parse_enumerator_assignment()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_direct_abstract_declarator_expr(self):
    current = self.tokens.current()
    rule = self.table[50][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(166, self.nonterminals[166]))
    tree.list = False
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 121:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(102) # asterisk
      tree.add(t)
      return tree
    elif rule == 224:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_type_qualifier_list_opt()
      tree.add( subtree )
      subtree = self.parse_static_opt()
      tree.add( subtree )
      subtree = self.parse__expr()
      tree.add( subtree )
      return tree
    elif current.getId() in [62, 48, 70, 80, 86, 107, 8, 71, 84, 93, 44, 60, 27, 77, 6, 102]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_type_qualifier_list_opt()
      tree.add( subtree )
      subtree = self.parse_static_opt()
      tree.add( subtree )
      subtree = self.parse__expr()
      tree.add( subtree )
    return tree
  def parse_translation_unit(self):
    current = self.tokens.current()
    rule = self.table[51][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(167, self.nonterminals[167]))
    tree.list = False
    if current == None:
      return tree
    if rule == 362:
      tree.astTransform = AstTransformNodeCreator('TranslationUnit', {'external_declarations': 0})
      subtree = self.parse__gen0()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_enumeration_constant(self):
    current = self.tokens.current()
    rule = self.table[52][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(168, self.nonterminals[168]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 132:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(80) # identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_enumerator_assignment(self):
    current = self.tokens.current()
    rule = self.table[53][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(169, self.nonterminals[169]))
    tree.list = False
    if current != None and (current.getId() in [3, 112]):
      return tree
    if current == None:
      return tree
    if rule == 210:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(103) # assign
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      return tree
    return tree
  def parse_static_opt(self):
    current = self.tokens.current()
    rule = self.table[54][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(170, self.nonterminals[170]))
    tree.list = False
    if current != None and (current.getId() in [62, 70, 80, 86, 107, 8, 27, 71, 84, 93, 44, 60, 102, 77, 6, 48]):
      return tree
    if current == None:
      return tree
    if rule == 349:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(106) # static
      tree.add(t)
      return tree
    return tree
  def parse__gen16(self):
    current = self.tokens.current()
    rule = self.table[55][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(171, self.nonterminals[171]))
    tree.list = False
    if current != None and (current.getId() in [55, 80, 57, 59, 3, 52, 12, 0, 113, 40, 19, 71, 16, 75, 26, 23, 28, 51, 85, 33, 111, 36, 37, 20, 81, 97, 42, 98, 101, 102, 7, 78, 106, 47, 79, 104, 9]):
      return tree
    if current == None:
      return tree
    if rule == 186:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_struct_or_union_body()
      tree.add( subtree )
      return tree
    return tree
  def parse_initializer(self):
    current = self.tokens.current()
    rule = self.table[56][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(172, self.nonterminals[172]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 92:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr_sans_comma()
      tree.add( subtree )
      return tree
    elif rule == 287:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(91) # lbrace
      tree.add(t)
      subtree = self.parse__gen12()
      tree.add( subtree )
      subtree = self.parse_trailing_comma_opt()
      tree.add( subtree )
      t = self.expect(49) # rbrace
      tree.add(t)
      return tree
    elif current.getId() in [80, 2, 44, 84, 86, 107, 8, 71, 70, 93, 48, 60, 102, 77, 6, 27]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr_sans_comma()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_union_specifier(self):
    current = self.tokens.current()
    rule = self.table[57][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(173, self.nonterminals[173]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 251:
      tree.astTransform = AstTransformNodeCreator('Union', {'definition': 1})
      t = self.expect(26) # union
      tree.add(t)
      subtree = self.parse_struct_or_union_sub()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_type_name(self):
    current = self.tokens.current()
    rule = self.table[58][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(174, self.nonterminals[174]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 85:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(23) # char
      tree.add(t)
      return tree
    elif rule == 219:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(37) # int
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_declaration_specifier(self):
    current = self.tokens.current()
    rule = self.table[59][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(175, self.nonterminals[175]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 175:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_storage_class_specifier()
      tree.add( subtree )
      return tree
    elif rule == 198:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_type_specifier()
      tree.add( subtree )
      return tree
    elif rule == 331:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_type_qualifier()
      tree.add( subtree )
      return tree
    elif rule == 360:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_function_specifier()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen31(self):
    current = self.tokens.current()
    rule = self.table[60][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(176, self.nonterminals[176]))
    tree.list = 'slist'
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 393:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(3) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse_identifier()
      tree.add( subtree )
      subtree = self.parse__gen31()
      tree.add( subtree )
      return tree
    return tree
  def parse_enum_specifier(self):
    current = self.tokens.current()
    rule = self.table[61][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(177, self.nonterminals[177]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 192:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(20) # enum
      tree.add(t)
      subtree = self.parse_enum_specifier_sub()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_block_item(self):
    current = self.tokens.current()
    rule = self.table[62][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(178, self.nonterminals[178]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 9:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_statement()
      tree.add( subtree )
      return tree
    elif rule == 230:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declaration()
      tree.add( subtree )
      return tree
    elif current.getId() in [62, 48, 70, 80, 86, 107, 8, 71, 84, 93, 44, 60, 27, 77, 6, 102]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_statement()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_for_init(self):
    current = self.tokens.current()
    rule = self.table[63][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(179, self.nonterminals[179]))
    tree.list = False
    if current != None and (current.getId() in [113]):
      return tree
    if current == None:
      return tree
    if rule == 141:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr()
      tree.add( subtree )
      return tree
    elif rule == 303:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declaration()
      tree.add( subtree )
      subtree = self.parse_expression_opt()
      tree.add( subtree )
      return tree
    elif current.getId() in [62, 48, 70, 80, 86, 107, 8, 71, 84, 93, 44, 60, 27, 77, 6, 102]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr()
      tree.add( subtree )
    return tree
  def parse_external_function(self):
    current = self.tokens.current()
    rule = self.table[64][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(180, self.nonterminals[180]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 44:
      tree.astTransform = AstTransformNodeCreator('FunctionDefinition', {'body': 3, 'declaration_list': 2, 'signature': 1})
      t = self.expect(57) # function_definition_hint
      tree.add(t)
      subtree = self.parse_declarator()
      tree.add( subtree )
      subtree = self.parse__gen5()
      tree.add( subtree )
      subtree = self.parse_compound_statement()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_direct_declarator_modifier(self):
    current = self.tokens.current()
    rule = self.table[65][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(181, self.nonterminals[181]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 104:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(106) # static
      tree.add(t)
      return tree
    elif rule == 310:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_type_qualifier()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_typedef_name(self):
    current = self.tokens.current()
    rule = self.table[66][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(182, self.nonterminals[182]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 176:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(12) # typedef_identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen12(self):
    current = self.tokens.current()
    rule = self.table[67][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(183, self.nonterminals[183]))
    tree.list = 'slist'
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 324:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_initializer_list_item()
      tree.add( subtree )
      subtree = self.parse__gen13()
      tree.add( subtree )
      return tree
    elif current.getId() in [80, 2, 44, 84, 86, 107, 8, 71, 70, 93, 48, 60, 102, 77, 6, 27]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_initializer_list_item()
      tree.add( subtree )
      subtree = self.parse__gen13()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_struct_declaration(self):
    current = self.tokens.current()
    rule = self.table[68][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(184, self.nonterminals[184]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 413:
      tree.astTransform = AstTransformNodeCreator('StructOrUnionDeclaration', {'specifier_qualifiers': 0, 'declarators': 1})
      subtree = self.parse__gen18()
      tree.add( subtree )
      subtree = self.parse__gen19()
      tree.add( subtree )
      t = self.expect(113) # semi
      tree.add(t)
      return tree
    elif current.getId() in [85, 71, 80]:
      tree.astTransform = AstTransformNodeCreator('StructOrUnionDeclaration', {'specifier_qualifiers': 0, 'declarators': 1})
      subtree = self.parse__gen18()
      tree.add( subtree )
      subtree = self.parse__gen19()
      tree.add( subtree )
      tree.add( self.expect(113) ) # semi
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen13(self):
    current = self.tokens.current()
    rule = self.table[69][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(185, self.nonterminals[185]))
    tree.list = 'slist'
    if current != None and (current.getId() in [112]):
      return tree
    if current == None:
      return tree
    if rule == 110:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(3) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse_initializer_list_item()
      tree.add( subtree )
      subtree = self.parse__gen13()
      tree.add( subtree )
      return tree
    return tree
  def parse_direct_declarator_expr(self):
    current = self.tokens.current()
    rule = self.table[70][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(186, self.nonterminals[186]))
    tree.list = False
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 174:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_direct_declarator_modifier_list_opt()
      tree.add( subtree )
      subtree = self.parse_direct_declarator_size()
      tree.add( subtree )
      return tree
    elif current.getId() in [62, 48, 70, 80, 86, 107, 8, 71, 84, 93, 44, 60, 27, 77, 6, 102]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_direct_declarator_modifier_list_opt()
      tree.add( subtree )
      subtree = self.parse_direct_declarator_size()
      tree.add( subtree )
    return tree
  def parse__gen8(self):
    current = self.tokens.current()
    rule = self.table[71][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(187, self.nonterminals[187]))
    tree.list = False
    if current != None and (current.getId() in [113]):
      return tree
    if current == None:
      return tree
    if rule == 125:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_init_declarator_list()
      tree.add( subtree )
      return tree
    elif current.getId() in [85, 71, 80]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_init_declarator_list()
      tree.add( subtree )
    return tree
  def parse_external_declaration_sub_sub(self):
    current = self.tokens.current()
    rule = self.table[72][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(188, self.nonterminals[188]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 71:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_external_declarator()
      tree.add( subtree )
      return tree
    elif rule == 357:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_external_prototype()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_statement(self):
    current = self.tokens.current()
    rule = self.table[73][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(189, self.nonterminals[189]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 3:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_compound_statement()
      tree.add( subtree )
      return tree
    elif rule == 47:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_labeled_statement()
      tree.add( subtree )
      return tree
    elif rule == 206:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_iteration_statement()
      tree.add( subtree )
      return tree
    elif rule == 264:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_selection_statement()
      tree.add( subtree )
      return tree
    elif rule == 269:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_jump_statement()
      tree.add( subtree )
      return tree
    elif rule == 304:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_expression_statement()
      tree.add( subtree )
      return tree
    elif current.getId() in [62, 48, 70, 80, 86, 107, 8, 71, 84, 93, 44, 60, 27, 77, 6, 102]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_expression_statement()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_labeled_statement(self):
    current = self.tokens.current()
    rule = self.table[74][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(190, self.nonterminals[190]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 170:
      tree.astTransform = AstTransformNodeCreator('Case', {'expr': 1, 'statement': 3})
      t = self.expect(94) # case
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      t = self.expect(33) # colon
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      return tree
    elif rule == 235:
      tree.astTransform = AstTransformNodeCreator('Label', {'name': 0, 'statement': 1})
      t = self.expect(18) # label_hint
      tree.add(t)
      t = self.expect(80) # identifier
      tree.add(t)
      t = self.expect(33) # colon
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      return tree
    elif rule == 294:
      tree.astTransform = AstTransformNodeCreator('DefaultCase', {'statement': 2})
      t = self.expect(89) # default
      tree.add(t)
      t = self.expect(33) # colon
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen26(self):
    current = self.tokens.current()
    rule = self.table[75][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(191, self.nonterminals[191]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [62, 48, 70, 80, 86, 107, 8, 71, 84, 93, 44, 60, 102, 77, 6, 27]):
      return tree
    if current == None:
      return tree
    if rule == 410:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_direct_declarator_modifier()
      tree.add( subtree )
      subtree = self.parse__gen26()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen3(self):
    current = self.tokens.current()
    rule = self.table[76][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(192, self.nonterminals[192]))
    tree.list = 'slist'
    if current != None and (current.getId() in [113]):
      return tree
    if current == None:
      return tree
    if rule == 333:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_external_declaration_sub_sub()
      tree.add( subtree )
      subtree = self.parse__gen4()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen4(self):
    current = self.tokens.current()
    rule = self.table[77][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(193, self.nonterminals[193]))
    tree.list = 'slist'
    if current != None and (current.getId() in [113]):
      return tree
    if current == None:
      return tree
    if rule == 338:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(3) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse_external_declaration_sub_sub()
      tree.add( subtree )
      subtree = self.parse__gen4()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen17(self):
    current = self.tokens.current()
    rule = self.table[78][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(194, self.nonterminals[194]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [49]):
      return tree
    if current == None:
      return tree
    if rule == 373:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_struct_declaration()
      tree.add( subtree )
      subtree = self.parse__gen17()
      tree.add( subtree )
      return tree
    elif current.getId() in [85, 71, 80]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_struct_declaration()
      tree.add( subtree )
      subtree = self.parse__gen17()
      tree.add( subtree )
    return tree
  def parse_direct_declarator_parameter_list(self):
    current = self.tokens.current()
    rule = self.table[79][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(195, self.nonterminals[195]))
    tree.list = False
    if current != None and (current.getId() in []):
      return tree
    if current == None:
      return tree
    if rule == 260:
      tree.astTransform = AstTransformNodeCreator('ParameterList', {'identifiers': 0})
      subtree = self.parse__gen30()
      tree.add( subtree )
      return tree
    elif rule == 276:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_parameter_type_list()
      tree.add( subtree )
      return tree
    return tree
  def parse_trailing_comma_opt(self):
    current = self.tokens.current()
    rule = self.table[80][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(196, self.nonterminals[196]))
    tree.list = False
    if current != None and (current.getId() in [49]):
      return tree
    if current == None:
      return tree
    if rule == 262:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(112) # trailing_comma
      tree.add(t)
      return tree
    return tree
  def parse_parameter_declaration(self):
    current = self.tokens.current()
    rule = self.table[81][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(197, self.nonterminals[197]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 1:
      tree.astTransform = AstTransformNodeCreator('ParameterDeclaration', {'sub': 1, 'declaration_specifiers': 0})
      subtree = self.parse__gen1()
      tree.add( subtree )
      subtree = self.parse__gen32()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen27(self):
    current = self.tokens.current()
    rule = self.table[82][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(198, self.nonterminals[198]))
    tree.list = 'slist'
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 58:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_parameter_declaration()
      tree.add( subtree )
      subtree = self.parse__gen28()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen28(self):
    current = self.tokens.current()
    rule = self.table[83][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(199, self.nonterminals[199]))
    tree.list = 'slist'
    if current != None and (current.getId() in [104]):
      return tree
    if current == None:
      return tree
    if rule == 155:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(3) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse_parameter_declaration()
      tree.add( subtree )
      subtree = self.parse__gen28()
      tree.add( subtree )
      return tree
    return tree
  def parse_designation(self):
    current = self.tokens.current()
    rule = self.table[84][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(200, self.nonterminals[200]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 117:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen15()
      tree.add( subtree )
      t = self.expect(103) # assign
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_sizeof_body(self):
    current = self.tokens.current()
    rule = self.table[85][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(201, self.nonterminals[201]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 38:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(71) # lparen
      tree.add(t)
      subtree = self.parse_type_name()
      tree.add( subtree )
      t = self.expect(43) # rparen
      tree.add(t)
      return tree
    elif rule == 129:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(80) # identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_struct_specifier(self):
    current = self.tokens.current()
    rule = self.table[86][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(202, self.nonterminals[202]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 191:
      tree.astTransform = AstTransformNodeCreator('Struct', {'definition': 1})
      t = self.expect(19) # struct
      tree.add(t)
      subtree = self.parse_struct_or_union_sub()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen25(self):
    current = self.tokens.current()
    rule = self.table[87][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(203, self.nonterminals[203]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [80, 85, 3, 111, 106, 102, 71, 104]):
      return tree
    if current == None:
      return tree
    if rule == 343:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_type_qualifier()
      tree.add( subtree )
      subtree = self.parse__gen25()
      tree.add( subtree )
      return tree
    return tree
  def parse_abstract_declarator(self):
    current = self.tokens.current()
    rule = self.table[88][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(204, self.nonterminals[204]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 204:
      tree.astTransform = AstTransformNodeCreator('AbstractDeclarator', {'direct_abstract_declarator': 1, 'pointer': 1})
      subtree = self.parse_pointer_opt()
      tree.add( subtree )
      subtree = self.parse__direct_abstract_declarator()
      tree.add( subtree )
      return tree
    elif current.getId() in [111, 71]:
      tree.astTransform = AstTransformNodeCreator('AbstractDeclarator', {'direct_abstract_declarator': 1, 'pointer': 1})
      subtree = self.parse_pointer_opt()
      tree.add( subtree )
      subtree = self.parse__direct_abstract_declarator()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_else_if_statement_list(self):
    current = self.tokens.current()
    rule = self.table[89][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(205, self.nonterminals[205]))
    tree.list = False
    if current == None:
      return tree
    if rule == 359:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen39()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen37(self):
    current = self.tokens.current()
    rule = self.table[90][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(206, self.nonterminals[206]))
    tree.list = False
    if current != None and (current.getId() in [0, 44, 1, 91, 8, 9, 12, 70, 113, 40, 18, 109, 19, 71, 16, 23, 26, 102, 28, 59, 36, 37, 39, 20, 69, 42, 79, 49, 7, 55, 80, 58, 62, 52, 66, 94, 81, 107, 25, 65, 75, 77, 48, 50, 51, 84, 86, 89, 47, 27, 93, 97, 99, 98, 60, 106, 108, 6]):
      return tree
    if current == None:
      return tree
    if rule == 137:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_else_if_statement_list()
      tree.add( subtree )
      return tree
    return tree
  def parse_va_args(self):
    current = self.tokens.current()
    rule = self.table[91][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(207, self.nonterminals[207]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 118:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(104) # comma_va_args
      tree.add(t)
      t = self.expect(32) # elipsis
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_expression_statement(self):
    current = self.tokens.current()
    rule = self.table[92][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(208, self.nonterminals[208]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 298:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_expression_opt()
      tree.add( subtree )
      t = self.expect(113) # semi
      tree.add(t)
      return tree
    elif current.getId() in [62, 48, 70, 80, 86, 107, 8, 71, 84, 93, 44, 60, 27, 77, 6, 102]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_expression_opt()
      tree.add( subtree )
      tree.add( self.expect(113) ) # semi
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_external_prototype(self):
    current = self.tokens.current()
    rule = self.table[93][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(209, self.nonterminals[209]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 185:
      tree.astTransform = AstTransformNodeCreator('FunctionPrototype', {'declaration_list': 2, 'declarator': 1})
      t = self.expect(101) # function_prototype_hint
      tree.add(t)
      subtree = self.parse_declarator()
      tree.add( subtree )
      subtree = self.parse__gen5()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_designator(self):
    current = self.tokens.current()
    rule = self.table[94][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(210, self.nonterminals[210]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 143:
      tree.astTransform = AstTransformNodeCreator('ArrayAccess', {'index': 1})
      t = self.expect(96) # lsquare
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      t = self.expect(105) # rsquare
      tree.add(t)
      return tree
    elif rule == 408:
      tree.astTransform = AstTransformNodeCreator('MemberAccess', {'name': 1})
      t = self.expect(35) # dot
      tree.add(t)
      t = self.expect(80) # identifier
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_iteration_statement(self):
    current = self.tokens.current()
    rule = self.table[95][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(211, self.nonterminals[211]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 158:
      tree.astTransform = AstTransformNodeCreator('While', {'expr': 2, 'statement': 4})
      t = self.expect(1) # while
      tree.add(t)
      t = self.expect(71) # lparen
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      t = self.expect(43) # rparen
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      return tree
    elif rule == 205:
      tree.astTransform = AstTransformNodeCreator('For', {'init': 2, 'cond': 3, 'incr': 4, 'statement': 6})
      t = self.expect(109) # for
      tree.add(t)
      t = self.expect(71) # lparen
      tree.add(t)
      subtree = self.parse_for_init()
      tree.add( subtree )
      subtree = self.parse_for_cond()
      tree.add( subtree )
      subtree = self.parse_for_incr()
      tree.add( subtree )
      t = self.expect(43) # rparen
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      return tree
    elif rule == 274:
      tree.astTransform = AstTransformNodeCreator('DoWhile', {'expr': 4, 'statement': 1})
      t = self.expect(25) # do
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      t = self.expect(1) # while
      tree.add(t)
      t = self.expect(71) # lparen
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      t = self.expect(43) # rparen
      tree.add(t)
      t = self.expect(113) # semi
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen15(self):
    current = self.tokens.current()
    rule = self.table[96][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(212, self.nonterminals[212]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [103]):
      return tree
    if current == None:
      return tree
    if rule == 245:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_designator()
      tree.add( subtree )
      subtree = self.parse__gen15()
      tree.add( subtree )
      return tree
    return tree
  def parse_selection_statement(self):
    current = self.tokens.current()
    rule = self.table[97][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(213, self.nonterminals[213]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 111:
      tree.astTransform = AstTransformNodeCreator('If', {'elseif': 6, 'statement': 4, 'condition': 2, 'else': 7})
      t = self.expect(39) # if
      tree.add(t)
      t = self.expect(71) # lparen
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      t = self.expect(43) # rparen
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      t = self.expect(69) # endif
      tree.add(t)
      subtree = self.parse__gen37()
      tree.add( subtree )
      subtree = self.parse__gen38()
      tree.add( subtree )
      return tree
    elif rule == 142:
      tree.astTransform = AstTransformNodeCreator('Switch', {'expr': 2, 'statment': 4})
      t = self.expect(108) # switch
      tree.add(t)
      t = self.expect(71) # lparen
      tree.add(t)
      subtree = self.parse__expr()
      tree.add( subtree )
      t = self.expect(43) # rparen
      tree.add(t)
      subtree = self.parse_statement()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen38(self):
    current = self.tokens.current()
    rule = self.table[98][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(214, self.nonterminals[214]))
    tree.list = False
    if current != None and (current.getId() in [0, 44, 1, 91, 8, 9, 12, 70, 113, 40, 18, 109, 19, 71, 16, 23, 26, 102, 28, 59, 36, 37, 39, 20, 69, 42, 79, 49, 7, 55, 80, 58, 62, 52, 66, 94, 81, 107, 25, 65, 75, 77, 48, 50, 51, 84, 86, 89, 47, 27, 93, 97, 98, 60, 106, 108, 6]):
      return tree
    if current == None:
      return tree
    if rule == 401:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_else_statement()
      tree.add( subtree )
      return tree
    return tree
  def parse_declarator(self):
    current = self.tokens.current()
    rule = self.table[99][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(215, self.nonterminals[215]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 374:
      tree.astTransform = AstTransformNodeCreator('Declarator', {'direct_declarator': 1, 'pointer': 0})
      subtree = self.parse_pointer_opt()
      tree.add( subtree )
      subtree = self.parse__direct_declarator()
      tree.add( subtree )
      return tree
    elif current.getId() in [85, 71, 80]:
      tree.astTransform = AstTransformNodeCreator('Declarator', {'direct_declarator': 1, 'pointer': 0})
      subtree = self.parse_pointer_opt()
      tree.add( subtree )
      subtree = self.parse__direct_declarator()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_declaration_list(self):
    current = self.tokens.current()
    rule = self.table[100][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(216, self.nonterminals[216]))
    tree.list = False
    if current == None:
      return tree
    if rule == 351:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen7()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen5(self):
    current = self.tokens.current()
    rule = self.table[101][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(217, self.nonterminals[217]))
    tree.list = False
    if current != None and (current.getId() in [113, 91, 3]):
      return tree
    if current == None:
      return tree
    if rule == 377:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declaration_list()
      tree.add( subtree )
      return tree
    return tree
  def parse_jump_statement(self):
    current = self.tokens.current()
    rule = self.table[102][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(218, self.nonterminals[218]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 55:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(66) # continue
      tree.add(t)
      return tree
    elif rule == 61:
      tree.astTransform = AstTransformNodeCreator('Goto', {'name': 1})
      t = self.expect(58) # goto
      tree.add(t)
      t = self.expect(80) # identifier
      tree.add(t)
      t = self.expect(113) # semi
      tree.add(t)
      return tree
    elif rule == 133:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(65) # break
      tree.add(t)
      t = self.expect(113) # semi
      tree.add(t)
      return tree
    elif rule == 248:
      tree.astTransform = AstTransformNodeCreator('Return', {'expr': 1})
      t = self.expect(50) # return
      tree.add(t)
      subtree = self.parse_expression_opt()
      tree.add( subtree )
      t = self.expect(113) # semi
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen32(self):
    current = self.tokens.current()
    rule = self.table[103][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(219, self.nonterminals[219]))
    tree.list = False
    if current != None and (current.getId() in [3, 104]):
      return tree
    if current == None:
      return tree
    if rule == 69:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_parameter_declaration_sub()
      tree.add( subtree )
      return tree
    elif current.getId() in [85, 71, 80]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_parameter_declaration_sub()
      tree.add( subtree )
    elif current.getId() in [111, 71]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_parameter_declaration_sub()
      tree.add( subtree )
    return tree
  def parse_pointer_opt(self):
    current = self.tokens.current()
    rule = self.table[104][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(220, self.nonterminals[220]))
    tree.list = False
    if current != None and (current.getId() in [80, 3, 85, 111, 71, 104]):
      return tree
    if current == None:
      return tree
    if rule == 42:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_pointer()
      tree.add( subtree )
      return tree
    return tree
  def parse_specifier_qualifier(self):
    current = self.tokens.current()
    rule = self.table[106][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(222, self.nonterminals[222]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 145:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_type_specifier()
      tree.add( subtree )
      return tree
    elif rule == 177:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_type_qualifier()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen39(self):
    current = self.tokens.current()
    rule = self.table[107][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(223, self.nonterminals[223]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [0, 44, 1, 91, 8, 9, 12, 70, 113, 40, 18, 109, 19, 71, 16, 23, 26, 102, 28, 59, 36, 37, 39, 20, 69, 42, 79, 49, 7, 55, 80, 58, 62, 52, 66, 94, 81, 107, 25, 65, 75, 77, 48, 50, 51, 84, 86, 89, 47, 27, 93, 97, 99, 98, 60, 106, 108, 6]):
      return tree
    if current == None:
      return tree
    if rule == 168:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_else_if_statement()
      tree.add( subtree )
      subtree = self.parse__gen39()
      tree.add( subtree )
      return tree
    return tree
  def parse_pp(self):
    current = self.tokens.current()
    rule = self.table[108][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(224, self.nonterminals[224]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 227:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(11) # pp_number
      tree.add(t)
      return tree
    elif rule == 289:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(24) # defined_separator
      tree.add(t)
      return tree
    elif rule == 296:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(45) # defined
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_direct_declarator_size(self):
    current = self.tokens.current()
    rule = self.table[109][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(225, self.nonterminals[225]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 14:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(102) # asterisk
      tree.add(t)
      return tree
    elif rule == 348:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr()
      tree.add( subtree )
      return tree
    elif current.getId() in [62, 48, 70, 80, 86, 107, 8, 71, 84, 93, 44, 60, 27, 77, 6, 102]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__expr()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_init_declarator(self):
    current = self.tokens.current()
    rule = self.table[110][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(226, self.nonterminals[226]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 284:
      tree.astTransform = AstTransformNodeCreator('InitDeclarator', {'initializer': 1, 'declarator': 0})
      subtree = self.parse_declarator()
      tree.add( subtree )
      subtree = self.parse__gen11()
      tree.add( subtree )
      return tree
    elif current.getId() in [85, 71, 80]:
      tree.astTransform = AstTransformNodeCreator('InitDeclarator', {'initializer': 1, 'declarator': 0})
      subtree = self.parse_declarator()
      tree.add( subtree )
      subtree = self.parse__gen11()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen6(self):
    current = self.tokens.current()
    rule = self.table[111][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(227, self.nonterminals[227]))
    tree.list = False
    if current != None and (current.getId() in [113, 3]):
      return tree
    if current == None:
      return tree
    if rule == 399:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_init_declarator()
      tree.add( subtree )
      return tree
    elif current.getId() in [85, 71, 80]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_init_declarator()
      tree.add( subtree )
    return tree
  def parse_external_declaration(self):
    current = self.tokens.current()
    rule = self.table[112][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(228, self.nonterminals[228]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 78:
      tree.astTransform = AstTransformNodeCreator('ExternalDeclaration', {'declarations': 2, 'declaration_specifiers': 1})
      t = self.expect(100) # external_declaration_hint
      tree.add(t)
      subtree = self.parse__gen1()
      tree.add( subtree )
      subtree = self.parse_external_declaration_sub()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_struct_declarator(self):
    current = self.tokens.current()
    rule = self.table[113][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(229, self.nonterminals[229]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 225:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declarator()
      tree.add( subtree )
      subtree = self.parse__gen21()
      tree.add( subtree )
      return tree
    elif rule == 382:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_struct_declarator_body()
      tree.add( subtree )
      return tree
    elif current.getId() in [85, 71, 80]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declarator()
      tree.add( subtree )
      subtree = self.parse__gen21()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen19(self):
    current = self.tokens.current()
    rule = self.table[114][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(230, self.nonterminals[230]))
    tree.list = 'slist'
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 416:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_struct_declarator()
      tree.add( subtree )
      subtree = self.parse__gen20()
      tree.add( subtree )
      return tree
    elif current.getId() in [85, 71, 80]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_struct_declarator()
      tree.add( subtree )
      subtree = self.parse__gen20()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen20(self):
    current = self.tokens.current()
    rule = self.table[115][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(231, self.nonterminals[231]))
    tree.list = 'slist'
    if current != None and (current.getId() in [113]):
      return tree
    if current == None:
      return tree
    if rule == 79:
      tree.astTransform = AstTransformSubstitution(0)
      t = self.expect(3) # comma
      tree.add(t)
      tree.listSeparator = t
      subtree = self.parse_struct_declarator()
      tree.add( subtree )
      subtree = self.parse__gen20()
      tree.add( subtree )
      return tree
    return tree
  def parse_struct_or_union_sub(self):
    current = self.tokens.current()
    rule = self.table[116][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(232, self.nonterminals[232]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 28:
      tree.astTransform = AstTransformNodeCreator('StructOrUnion', {'body': 1, 'name': 0})
      t = self.expect(80) # identifier
      tree.add(t)
      subtree = self.parse__gen16()
      tree.add( subtree )
      return tree
    elif rule == 255:
      tree.astTransform = AstTransformNodeCreator('StructOrUnion', {'body': 0})
      subtree = self.parse_struct_or_union_body()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_type_qualifier_list_opt(self):
    current = self.tokens.current()
    rule = self.table[117][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(233, self.nonterminals[233]))
    tree.list = False
    if current != None and (current.getId() in [80, 85, 3, 111, 106, 102, 71, 104]):
      return tree
    if current == None:
      return tree
    if rule == 84:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen25()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen1(self):
    current = self.tokens.current()
    rule = self.table[118][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(234, self.nonterminals[234]))
    tree.list = 'mlist'
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 63:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declaration_specifier()
      tree.add( subtree )
      subtree = self.parse__gen2()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen2(self):
    current = self.tokens.current()
    rule = self.table[119][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(235, self.nonterminals[235]))
    tree.list = 'mlist'
    if current != None and (current.getId() in [80, 57, 111, 71, 113, 101, 3, 104, 102, 85, 78]):
      return tree
    if current == None:
      return tree
    if rule == 161:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declaration_specifier()
      tree.add( subtree )
      subtree = self.parse__gen2()
      tree.add( subtree )
      return tree
    return tree
  def parse__gen0(self):
    current = self.tokens.current()
    rule = self.table[120][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(236, self.nonterminals[236]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [-1]):
      return tree
    if current == None:
      return tree
    if rule == 89:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_external_declaration()
      tree.add( subtree )
      subtree = self.parse__gen0()
      tree.add( subtree )
      return tree
    return tree
  def parse_block_item_list(self):
    current = self.tokens.current()
    rule = self.table[121][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(237, self.nonterminals[237]))
    tree.list = False
    if current == None:
      return tree
    if rule == 246:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen36()
      tree.add( subtree )
      return tree
    elif current.getId() in [62, 48, 70, 80, 86, 107, 8, 71, 84, 93, 44, 60, 27, 77, 6, 102]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen36()
      tree.add( subtree )
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__gen35(self):
    current = self.tokens.current()
    rule = self.table[122][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(238, self.nonterminals[238]))
    tree.list = False
    if current != None and (current.getId() in [49]):
      return tree
    if current == None:
      return tree
    if rule == 257:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_block_item_list()
      tree.add( subtree )
      return tree
    elif current.getId() in [62, 48, 70, 80, 86, 107, 8, 71, 84, 93, 44, 60, 27, 77, 6, 102]:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_block_item_list()
      tree.add( subtree )
    return tree
  def parse__gen7(self):
    current = self.tokens.current()
    rule = self.table[123][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(239, self.nonterminals[239]))
    tree.list = 'nlist'
    if current != None and (current.getId() in [113, 91, 3]):
      return tree
    if current == None:
      return tree
    if rule == 2:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_declaration()
      tree.add( subtree )
      subtree = self.parse__gen7()
      tree.add( subtree )
      return tree
    return tree
  def parse_declaration(self):
    current = self.tokens.current()
    rule = self.table[125][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(241, self.nonterminals[241]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 98:
      tree.astTransform = AstTransformNodeCreator('Declaration', {'init_declarators': 1, 'declaration_specifiers': 0})
      subtree = self.parse__gen1()
      tree.add( subtree )
      subtree = self.parse__gen8()
      tree.add( subtree )
      t = self.expect(113) # semi
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_external_declaration_sub(self):
    current = self.tokens.current()
    rule = self.table[126][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(242, self.nonterminals[242]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 116:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse__gen3()
      tree.add( subtree )
      t = self.expect(113) # semi
      tree.add(t)
      return tree
    elif rule == 135:
      tree.astTransform = AstTransformSubstitution(0)
      subtree = self.parse_external_function()
      tree.add( subtree )
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse_struct_or_union_body(self):
    current = self.tokens.current()
    rule = self.table[127][current.getId()] if current else -1
    tree = ParseTree( NonTerminal(243, self.nonterminals[243]))
    tree.list = False
    if current == None:
      raise SyntaxError('Error: unexpected end of file')
    if rule == 65:
      tree.astTransform = AstTransformSubstitution(1)
      t = self.expect(91) # lbrace
      tree.add(t)
      subtree = self.parse__gen17()
      tree.add( subtree )
      t = self.expect(49) # rbrace
      tree.add(t)
      return tree
    raise SyntaxError('Error: Unexpected symbol (%s) when parsing %s' % (current, whoami()))
  def parse__expr( self, rbp = 0):
    name = '_expr'
    if name not in self.expressionParsers:
      self.expressionParsers[name] = ExpressionParser__expr(self)
    return self.expressionParsers[name].parse(rbp)
  def parse__expr_sans_comma( self, rbp = 0):
    name = '_expr_sans_comma'
    if name not in self.expressionParsers:
      self.expressionParsers[name] = ExpressionParser__expr_sans_comma(self)
    return self.expressionParsers[name].parse(rbp)
  def parse__direct_declarator( self, rbp = 0):
    name = '_direct_declarator'
    if name not in self.expressionParsers:
      self.expressionParsers[name] = ExpressionParser__direct_declarator(self)
    return self.expressionParsers[name].parse(rbp)
  def parse__direct_abstract_declarator( self, rbp = 0):
    name = '_direct_abstract_declarator'
    if name not in self.expressionParsers:
      self.expressionParsers[name] = ExpressionParser__direct_abstract_declarator(self)
    return self.expressionParsers[name].parse(rbp)
