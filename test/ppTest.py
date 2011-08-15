import unittest, os
from CastTest import CastTest
from cast.Token import cToken

class ppTest(CastTest):

  def __init__(self, filename):
    super(ppTest, self).__init__('test_pp')
    self.__dict__.update(locals())

  def test_pp(self):
    csource = os.path.join('c', self.filename)
    pp = os.path.join('c', self.filename + '.pp')

    if not os.path.isfile(pp):
      self.write_pp(csource, pp)

    if os.path.isfile(csource) and os.path.isfile(pp):

      fp = open( pp )
      expected = fp.read()
      fp.close()

      self.assert_pp( csource, expected )

def load_tests(loader, tests, pattern):
    files = list(filter(lambda x: x.endswith('.c'), os.listdir('c')))
    suite = unittest.TestSuite()
    for filename in files:
      suite.addTest( ppTest(filename) )
    return suite

if __name__ == '__main__':
  unittest.main()
