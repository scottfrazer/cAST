from collections import OrderedDict
from itertools import zip_longest

class Theme:
  pass

class VT100ColorMapper:
  primary = [
    0x000000, 0x800000, 0x008000, 0x808000, 0x000080, 0x800080, 0x008080, 0xc0c0c0
  ]

  bright = [
    0x808080, 0xff0000, 0x00ff00, 0xffff00, 0x0000ff, 0xff00ff, 0x00ffff, 0xffffff
  ]

class XTermColorMapper(VT100ColorMapper):
  grayscale_start = 0x08;
  grayscale_end = 0xf8;
  grayscale_step = 10;
  intensities = [
    0x00, 0x5F, 0x87, 0xAF, 0xD7, 0xFF
  ];

  def __init__(self):
    self.colors = list()
    self.colors_ordered_by_rgb = None

  def _map(self):
    for index, color in enumerate(self.primary + self.bright):
      self.colors.append( (color, index) )

    c = 16
    for i in self.intensities: 
      color = i << 16;
      for j in self.intensities: 
        color &= ~(0xff << 8);
        color |= j << 8;
        for k in self.intensities: 
          color &= ~0xff;
          color |= k;
          self.colors.append( (color, c) );
          c += 1

    c = 232    
    for hex in list(range(self.grayscale_start, self.grayscale_end, self.grayscale_step)):
      color = (hex << 16) | (hex << 8) | hex;
      self.colors.append( (color, c) )
      c += 1

    self.colors_ordered_by_rgb = [(rgb, xterm) for rgb, xterm in sorted(self.colors, key=lambda x: x[0])]

    for hexcolor, xterm in self.colors_ordered_by_rgb:
      string = "\033[38;5;{xterm:d}m{xterm:d} :: #{hexcolor:06x} :: \"\\033[38;5;{xterm:d}m\"\033[0m"
      print(string.format(xterm=xterm, hexcolor=hexcolor));

  def convert(self, hexcolor):
    if not len(self.colors):
      self._map()

    colors = self.colors_ordered_by_rgb
    for cthis, cnext in zip_longest(colors, colors[1:]):
      (this_rgb, this_xterm) = cthis
      (next_rgb, next_xterm) = (0, 0)
      if cnext:
        (next_rgb, next_xterm) = cnext
      this_diff = this_rgb - hexcolor
      next_diff = next_rgb - hexcolor
      if abs(next_diff) > abs(this_diff):
        return this_xterm


class VT100Theme(Theme):
  pass

class XTermTheme(Theme):
  pass

class HTML5Theme(Theme):
  pass

class PlainTextTheme(Theme):
  pass
