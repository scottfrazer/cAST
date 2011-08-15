import unittest, os
from CastTest import CastTest
from cast.Token import cToken

class cTokenTest(CastTest):

  def __init__(self, filename):
    super(cTokenTest, self).__init__('test_cTokens')
    self.__dict__.update(locals())

  def test_cTokens(self):
    csource = os.path.join('c', self.filename)
    ctokens = os.path.join('c', self.filename + '.ctok')

    if not os.path.isfile(ctokens):
      self.write_ctok(csource, ctokens)

    if os.path.isfile(csource) and os.path.isfile(ctokens):

      fp = open( ctokens )
      expected = list(filter(lambda x: len(x), fp.read().split('\n')))
      fp.close()

      self.assert_ctok( csource, expected )

def load_tests(loader, tests, pattern):
    files = list(filter(lambda x: x.endswith('.c'), os.listdir('c')))
    suite = unittest.TestSuite()
    for filename in files:
      suite.addTest( cTokenTest(filename) )
    return suite

if __name__ == '__main__':
  unittest.main()
