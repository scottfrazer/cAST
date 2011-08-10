#!/usr/bin/env python

from types import *
from os import path
import sys, os, argparse, subprocess, re
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
              choices = ['pp', 'pptok', 'ppast', 'ctok'],
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

  parser.add_argument('-I', '--include-path',
              required = False,
              default = '',
              help = "A path containing the list of directories separated by colons.")

  result = parser.parse_args()

  if not os.path.isfile( result.source_file[0] ):
    sys.stderr.write("Error: Source file does not exist\n")
    sys.exit(-1)

  try:
    cSourceText = open(result.source_file[0], encoding='utf-8').read()
  except UnicodeDecodeError:
    cSourceText = open(result.source_file[0], encoding='iso-8859-1').read()

  target = subprocess.check_output(["gcc", "-dumpmachine"]).decode('ascii').strip()
  include_path_global = ['/usr/include', '/usr/local/include', 'usr/' + target + '/include']
  include_path_global.extend( list(filter(lambda x: x, result.include_path.split(':'))) )
  include_path_local = [os.path.dirname(os.path.abspath(result.source_file[0]))]

  cPPFactory = PreProcessorFactory()
  cPP = cPPFactory.create( include_path_global, include_path_local )

  if result.action == 'pp':
    try:
      (cT, symbols) = cPP.process( cSourceText )
      print(cT.toString())
    except Exception as e:
      print(e, '\n', e.tracer)
      sys.exit(-1)

  if result.action == 'pptok':
    cPPLFactory = ppLexerFactory()
    cPPL = cPPLFactory.create()
    cPPL.setString(cSourceText)
    for token in cPPL:
      print(token.toString(result.format))

  if result.action == 'ppast':
    from cast.ppParser import Parser as ppParser
    try:
      cPPLFactory = ppLexerFactory()
      cPPL = cPPLFactory.create()
      cPPL.setString(cSourceText)
      parser = ppParser()
      parsetree = parser.parse(cPPL, 'pp_file')
      ast = parsetree.toAst()
      print(ast)
    except Exception as e:
      print(e, '\n', e.tracer)
      sys.exit(-1)

  if result.action == 'ctok':
    try:
      cT, symbols = cPP.process( cSourceText )
      for token in cT:
        print(token.toString(result.format))
    except Exception as e:
      print(e, '\n', e.tracer)
      sys.exit(-1)

if __name__ == '__main__':
    Cli()
