from cast.ppParser import Ast as ppAst
from cast.cParser import Ast as cAst
from cast.ppParser import ParseTree as ppParseTree
from cast.cParser import ParseTree as cParseTree
from cast.Token import Token
import termcolor

def noColor(string, color):
  return string

class AstPrettyPrintable:
  def __init__(self, ast, tokenFormat='type', color=False):
    self.__dict__.update(locals())
  def getAttr(self, attr):
    return self.ast.getAttr(attr)
  def __str__(self):
    return self._prettyPrint(self.ast, 0)
  def _prettyPrint(self, ast, indent = 0):
    indentStr = ''.join([' ' for x in range(indent)])
    colored = noColor
    if self.color:
      colored = termcolor.colored
    if isinstance(ast, ppAst) or isinstance(ast, cAst):
      string = '%s(%s:\n' % (indentStr, colored(ast.name, 'blue'))
      string += ',\n'.join([ \
        '%s  %s=%s' % (indentStr, colored(name, 'green'), self._prettyPrint(value, indent + 2).lstrip()) for name, value in ast.attributes.items() \
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
    elif isinstance(ast, Token):
      return '%s%s' % (indentStr, colored(ast.toString(self.tokenFormat), 'red'))
    else:
      return '%s%s' % (indentStr, colored(ast, 'red'))

class ParseTreePrettyPrintable:
  def __init__(self, ast, tokenFormat='type'):
    self.__dict__.update(locals())
  def __str__(self):
    return self._prettyPrint(self.ast, 0)
  def _prettyPrint(self, parsetree, indent = 0):
    indentStr = ''.join([' ' for x in range(indent)])
    if isinstance(parsetree, ppParseTree) or isinstance(parsetree, cParseTree):
      if len(parsetree.children) == 0:
        return '(%s: )' % (parsetree.nonterminal)
      string = '%s(%s:\n' % (indentStr, parsetree.nonterminal)
      string += ',\n'.join([ \
        '%s  %s' % (indentStr, self._prettyPrint(value, indent + 2).lstrip()) for value in parsetree.children \
      ])
      string += '\n%s)' % (indentStr)
      return string
    elif isinstance(parsetree, Token):
      return '%s%s' % (indentStr, parsetree.toString(self.tokenFormat))
    else:
      return '%s%s' % (indentStr, parsetree)
