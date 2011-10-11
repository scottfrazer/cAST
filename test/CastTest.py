import unittest, os
from cast.ppParser import Parser as ppParser
from cast.ppLexer import ppLexer
from cast.Ast import AstPrettyPrintable
from cast.PreProcessor import Factory as PreProcessorFactory
from cast.SourceCode import SourceCode, SourceCodeString

class CastTest(unittest.TestCase):

  mapFunc = lambda y, x: "%s,%s,%s,%s,%s" % (x.getTerminalStr(), x.getLine(), x.getColumn(), x.getString().replace('\n', '\\n'), x.getResource())

  def get_ppLexer(self, filePath):
    sourceCode = SourceCode( filePath, open(filePath) )
    return ppLexer(sourceCode)

  def get_ppAst(self, filePath):
    cPPL = self.get_ppLexer(filePath)
    parser = ppParser()
    parsetree = parser.parse(cPPL)
    return parsetree.toAst()

  def get_cLexer(self, filePath):
    ppAst = self.get_ppAst( filePath )
    cPPFactory = PreProcessorFactory()
    cPP = cPPFactory.create([], [os.path.dirname(filePath)])
    cSourceCode = SourceCode(filePath, open(filePath))
    cT, symbols = cPP.process( cSourceCode, dict() )
    return cT

  def assert_pptok(self, filePath, expectedTokens):
    cPPL = self.get_ppLexer(filePath) 
    actualTokens = list(map(self.mapFunc, list(cPPL)))
    self.assertEqual(actualTokens, expectedTokens)
  
  def write_pptok(self, path, filePath):
    cPPL = self.get_ppLexer(filePath)
    actualTokens = list(map(self.mapFunc, list(cPPL)))
    fp = open(path, 'w')
    fp.write('\n'.join(actualTokens))
    fp.close()
  
  def assert_ppast(self, filePath, expectedAst):
    ast = self.get_ppAst(filePath)
    prettyprint = str(AstPrettyPrintable(ast, 'type'))
    self.assertEqual(prettyprint, expectedAst)
  
  def write_ppast(self, path, filePath):
    ast = self.get_ppAst(filePath)
    prettyprint = str(AstPrettyPrintable(ast, 'type'))
    fp = open(path, 'w')
    fp.write(prettyprint)
    fp.close()

  def assert_ctok(self, filePath, expectedTokens, file):
    cL = self.get_cLexer(filePath)
    actualTokens = list(map(self.mapFunc, list(cL)))
    self.assertEqual(actualTokens, expectedTokens, "%s C token mismatch" % (file))
  
  def write_ctok(self, filePath, outPath):
    cL = self.get_cLexer(filePath)
    actualTokens = list(map(self.mapFunc, list(cL)))
    fp = open(outPath, 'w')
    fp.write('\n'.join(actualTokens))
    fp.close()

  def assert_pp(self, filePath, expected):
    cL = self.get_cLexer(filePath)
    self.assertEqual(cL.toString(), expected)
  
  def write_pp(self, filePath, outPath):
    cL = self.get_cLexer(filePath)
    fp = open(outPath, 'w')
    fp.write( cL.toString() )
    fp.close()
