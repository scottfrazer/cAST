class SourceCode:
  def __init__(self, resource, fp, line = 1, column = 1):
    self.__dict__.update(locals())
    self.sourceCode = fp.read()
    fp.close()

  def getResource(self):
    return self.resource

  def getString(self):
    return self.sourceCode

  def getColumn(self):
    return self.column

  def getLine(self):
    return self.line

  def __str__(self):
    return '<SourceCode file=%s>' % (self.resource)

class SourceCodeString:
  def __init__(self, resource, string, line=1, column=1):
    self.__dict__.update(locals())

  def getResource(self):
    return self.resource

  def getString(self):
    return self.string

  def getColumn(self):
    return self.column

  def getLine(self):
    return self.line

class SourceCodeEmpty:
  def __init__(self, resource):
    self.resource = resource

  def getResource(self):
    return self.resource

  def getString(self):
    return ''

  def getColumn(self):
    return 0

  def getLine(self):
    return 0
