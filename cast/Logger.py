import logging

class Factory:
  def initialize(self, debug):
    logger = logging.getLogger('cast')
    logger.setLevel(logging.DEBUG)
    fileLogger = logging.FileHandler('cast.log')
    fileLogger.setLevel(logging.DEBUG)
    stdoutLogger = logging.StreamHandler()
    stdoutLogger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fileLogger.setFormatter(formatter)
    stdoutLogger.setFormatter(formatter)
    if debug:
      logger.addHandler(fileLogger)
      logger.addHandler(stdoutLogger)
    return logger
  def getProgramLogger(self):
    return logging.getLogger('cast')
  def getModuleLogger(self, module):
    return logging.getLogger('%s' % (module))
  def getClassLogger(self, module, className):
    return logging.getLogger('%s.%s' % (module, className))
