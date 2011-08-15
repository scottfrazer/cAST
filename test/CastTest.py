import unittest, os
from cast.ppLexer import Factory as ppLexerFactory
from cast.ppParser import Parser as ppParser
from cast.Ast import AstPrettyPrintable
from cast.PreProcessor import Factory as PreProcessorFactory

def dataProvider(fn_data_provider):
    def test_decorator(fn):
        def repl(self, *args):
            for i in fn_data_provider():
                try:
                    fn(self, *i)
                except AssertionError:
                    print("Assertion error caught with data set ", i)
                    raise
        return repl
    return test_decorator

class CastTest(unittest.TestCase):

  mapFunc = lambda y, x: '%s,%s,%s' % (x.getTerminalStr(), x.getLine(), x.getColumn())

  def get_ppLexer(self, sourceString):
    cPPLFactory = ppLexerFactory()
    cPPL = cPPLFactory.create()
    cPPL.setString(sourceString)
    return cPPL

  def get_ppAst(self, sourceString):
    cPPL = self.get_ppLexer(sourceString)
    parser = ppParser()
    parsetree = parser.parse(cPPL, 'pp_file')
    return parsetree.toAst()

  def get_cLexer(self, filePath, sourceString):
    ppAst = self.get_ppAst( sourceString )
    cPPFactory = PreProcessorFactory()
    cPP = cPPFactory.create([], [os.path.dirname(os.path.abspath(filePath))])
    cT, symbols = cPP.process( sourceString )
    return cT

  def assert_pptok(self, sourceString, expectedTokens):
    cPPL = self.get_ppLexer(sourceString) 
    actualTokens = list(map(self.mapFunc, list(cPPL)))
    self.assertEqual(actualTokens, expectedTokens)
  
  def write_pptok(self, path, sourceString):
    cPPL = self.get_ppLexer(sourceString)
    actualTokens = list(map(self.mapFunc, list(cPPL)))
    fp = open(path, 'w')
    fp.write('\n'.join(actualTokens))
    fp.close()
  
  def assert_ppast(self, sourceString, expectedAst):
    ast = self.get_ppAst(sourceString)
    prettyprint = str(AstPrettyPrintable(ast, 'type'))
    self.assertEqual(prettyprint, expectedAst)
  
  def write_ppast(self, path, sourceString):
    ast = self.get_ppAst(sourceString)
    prettyprint = str(AstPrettyPrintable(ast, 'type'))
    fp = open(path, 'w')
    fp.write(prettyprint)
    fp.close()

  def assert_ctok(self, filePath, expectedTokens):
    fp = open(filePath)
    sourceString = fp.read()
    fp.close()
    cL = self.get_cLexer(filePath, sourceString)
    actualTokens = list(map(self.mapFunc, list(cL)))
    self.assertEqual(actualTokens, expectedTokens)
  
  def write_ctok(self, filePath, outPath):
    fp = open(filePath)
    sourceString = fp.read()
    fp.close()
    cL = self.get_cLexer(filePath, sourceString)
    actualTokens = list(map(self.mapFunc, list(cL)))
    fp = open(outPath, 'w')
    fp.write('\n'.join(actualTokens))
    fp.close()
