import logging

from xtermcolor.ColorMap import XTermColorMap

class Factory:
  def initialize(self, debug):
    logger = logging.getLogger('cast')
    logger.setLevel(logging.DEBUG)
    stdoutLogger = logging.StreamHandler()
    stdoutLogger.setLevel(logging.DEBUG)
    colormap = XTermColorMap()
    debug = '[%10s]' % (colormap.colorize('debug', 0x00ff00))
    formatter = logging.Formatter('%s%(levelname)-10s%s %(message)s')
    stdoutLogger.setFormatter(formatter)
    if debug:
      logger.addHandler(stdoutLogger)
    return logger
  def getProgramLogger(self):
    return logging.getLogger('cast')
  def getModuleLogger(self, module):
    return logging.getLogger('%s' % (module))
  def getClassLogger(self, module, className):
    return logging.getLogger('%s.%s' % (module, className))
