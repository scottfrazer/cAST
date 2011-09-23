#!/usr/bin/env python3

import sys

try:
  from hermes.GrammarFileParser import GrammarFileParser, HermesParserFactory
  from hermes.GrammarCodeGenerator import PythonTemplate, Resources
except:
  sys.stderr.write('Hermes is not installed.  Cannot bootstrap.')
  sys.exit(-1)

grammarFileParser = GrammarFileParser(HermesParserFactory().create())

grammars = [
  ('cast/ppParser.py', 'grammars/pp.zgr', 'pp_file'),
  ('cast/cParser.py', 'grammars/c.zgr', 'translation_unit')
]

for outFile, grammarFile, start in grammars:
  print('generating grammar %s -> %s' % (grammarFile, outFile))
  grammar = grammarFileParser.parse( open(grammarFile), start )
  template = PythonTemplate(Resources(grammar))
  code = template.render()
  fp = open(outFile, 'w')
  fp.write(code)
  fp.close()

import setup
