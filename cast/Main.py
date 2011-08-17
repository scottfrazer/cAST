#!/usr/bin/env python

from types import *
import sys, os, argparse, subprocess, re, logging
from cast.PreProcessor import Factory as PreProcessorFactory
from cast.ppLexer import Factory as ppLexerFactory
from cast.ppParser import Parser as ppParser
from cast.Ast import AstPrettyPrintable
from cast.SourceCode import SourceCode
from cast.Logger import Factory as LoggerFactory

def Cli():

  ver = sys.version_info

  # Version 3.2 required for argparse
  if ver.major < 3 or (ver.major == 3 and ver.minor < 2):
    print("Python 3.2+ required. %d.%d.%d installed" %(ver.major, ver.minor, ver.micro))
    sys.exit(-1)

  parser = argparse.ArgumentParser(
              description = 'cAST: C Preprocessor and Parser',
              epilog = '(c) 2011 Scott Frazer')

  commands = dict()
  subparsers = parser.add_subparsers(help='Available actions', dest='command')
  commands['pp'] = subparsers.add_parser('pp', help='Preprocess.')
  commands['pptok'] = subparsers.add_parser('pptok', help='Tokenize C preprocessor.')
  commands['ppast'] = subparsers.add_parser('ppast', help='Parse C preprocessor.')
  commands['ctok'] = subparsers.add_parser('ctok', help='Preprocess and tokenize C code.')

  parser.add_argument('source_file',
              metavar = 'SOURCE_FILE',
              nargs = 1,
              help = 'C Source File')
  
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

  cli = parser.parse_args()
  logger = LoggerFactory().initialize()
  logger.debug('CLI Parameters: %s' % (cli))

  if not os.path.isfile( cli.source_file[0] ):
    sys.stderr.write("Error: Source file does not exist\n")
    sys.exit(-1)

  try:
    cSourceFp = open(cli.source_file[0], encoding='utf-8')
  except UnicodeDecodeError:
    cSourceFp = open(cli.source_file[0], encoding='iso-8859-1').read()

  cSourceCode = SourceCode(cli.source_file[0], cSourceFp)

  target = subprocess.check_output(["gcc", "-dumpmachine"]).decode('ascii').strip()
  include_path_global = ['/usr/include', '/usr/local/include', 'usr/' + target + '/include']
  include_path_global.extend( list(filter(lambda x: x, cli.include_path.split(':'))) )
  include_path_local = [os.path.dirname(os.path.abspath(cli.source_file[0]))]

  cPPFactory = PreProcessorFactory()
  cPP = cPPFactory.create( include_path_global, include_path_local )

  if cli.command == 'pp':
    try:
      (cT, symbols) = cPP.process( cSourceCode )
      print(cT.toString())
    except Exception as e:
      print(e, '\n', e.tracer)
      sys.exit(-1)

  if cli.command == 'pptok':
    cPPLFactory = ppLexerFactory()
    cPPL = cPPLFactory.create()
    cPPL.setSourceCode(cSourceCode)
    for token in cPPL:
      print(token.toString(cli.format))

  if cli.command == 'ppast':
    from cast.ppParser import Parser as ppParser
    try:
      cPPLFactory = ppLexerFactory()
      cPPL = cPPLFactory.create()
      cPPL.setSourceCode(cSourceCode)
      parser = ppParser()
      parsetree = parser.parse(cPPL, 'pp_file')
      ast = parsetree.toAst()
      print(AstPrettyPrintable(ast))
    except Exception as e:
      print(e, '\n', e.tracer)
      sys.exit(-1)

  if cli.command == 'ctok':
    try:
      cT, symbols = cPP.process( cSourceCode )
      for token in cT:
        print(token.toString(cli.format))
    except Exception as e:
      print(e, '\n', e.tracer)
      sys.exit(-1)

if __name__ == '__main__':
    Cli()
