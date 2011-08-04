#!/usr/bin/env python

from types import *
from os import path
import sys, os, argparse
from cast.PreProcessor import Factory as PreProcessorFactory
from cast.ppLexer import Factory as ppLexerFactory
from cast.ppParser import Parser as ppParser

def Cli():

  ver = sys.version_info

  # Version 3.2 required for argparse
  if ver.major < 3 or (ver.major == 3 and ver.minor < 2):
    print("Python 3.2+ required. %d.%d.%d installed" %(ver.major, ver.minor, ver.micro))
    sys.exit(-1)

  parser = argparse.ArgumentParser(
              description = 'cAST: C Preprocessor and Parser',
              epilog = '(c) 2011 Scott Frazer')

  parser.add_argument('action',
              choices = ['pp', 'pptok', 'ctok'],
              help = 'Parser Generator Actions')

  parser.add_argument('source_file',
              metavar = 'SOURCE_FILE',
              nargs = 1,
              help = 'C Source File(s)')
  
  parser.add_argument('-d', '--debug',
              required = False,
              help = 'Writes debug information')
  
  parser.add_argument('-e', '--encoding',
              required = False,
              help = 'File encoding')

  parser.add_argument('-f', '--format',
              required = False,
              default = 'long',
              help = "'tiny', 'short', 'long' for outputting tokens.")

  result = parser.parse_args()

  if not os.path.isfile( result.source_file[0] ):
    sys.stderr.write("Error: Source file does not exist\n")
    sys.exit(-1)

  try:
    cSourceText = open(result.source_file[0], encoding='utf-8').read()
  except UnicodeDecodeError:
    cSourceText = open(result.source_file[0], encoding='iso-8859-1').read()

  cPPFactory = PreProcessorFactory()
  cPP = cPPFactory.create()

  if result.action == 'pp':
    try:
      cT = cPP.process( cSourceText )
      print(cT.toString())
    except Exception as e:
      print(e, '\n', e.tracer)
      sys.exit(-1)

  if result.action == 'pptok':
    cPPLFactory = ppLexerFactory()
    cPPP = ppParser()
    cPPL_TokenMap = { terminalString.upper(): cPPP.terminal(terminalString) for terminalString in cPPP.terminalNames() }
    cPPL = cPPLFactory.create(cPPL_TokenMap)
    cPPL.setString(cSourceText)
    for token in cPPL:
      print(token.toString(result.format))

  if result.action == 'ctok':
    try:
      cT = cPP.process( cSourceText )
      for token in cT:
        print(token.toString(result.format))
    except Exception as e:
      print(e, '\n', e.tracer)
      sys.exit(-1)

if __name__ == '__main__':
    Cli()
