def noColor(string, color):
  return string
def termColor(string, intcolor):
  return "\033[38;5;%dm%s\033[0m" % (intcolor, string)