import unittest
from cast.ppLexer import Factory as ppLexerFactory

class CastTest(unittest.TestCase):
  def assert_pptok(self, sourceString, expectedTokens):
    cPPLFactory = ppLexerFactory()
    cPPL = cPPLFactory.create()
    cPPL.setString(sourceString)
    mapFunc = lambda x: '%s,%s,%s' % (x.getTerminalStr(), x.getLine(), x.getColumn())
    actualTokens = list(map(mapFunc, list(cPPL)))
    self.assertEqual(actualTokens, expectedTokens)
