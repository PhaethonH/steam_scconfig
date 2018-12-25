#!/usr/bin/env python3

# Given a dict describing a controller configuration,
# generate Scconfig and VDF.

import re

r"""
	cfg:
  .name
  actions[]:
    layers[]:
      "srcsym": [ "evsym" ]
    modifiers[]:
      "srcsym": "shiftdesc"

srcsym:
  LT, RT : Left/Right trigger (full pull); c.f. LT.e, RT.e for soft pull
  LB, RB : Left/Right Bumper (shoulder)
  LP, RP : Left/Right Pad
  LG, RG : Left/Right Grip (bottom/behind pad)
  BK, ST : Back (aka Select), Start (aka Options, View)
  LS : Left Stick click
  LJ : Left Joystick whole
  BQ : Button Quad - face buttons
  GY : gyro(scope); pad tilt
 (PS3, XB360, PS4)
  RS : Right Stick click
  RJ : Right Joystick whole
 (PS4)
  TP : Touchpad whole (LP, RP for implicit split-pad).

  cluster accessor, suffix:
  .c = click
  .o = edge (threshold, soft pull)
  .t = touch
  .u .d .l .r = Direction Pad up, down, left, right
  .n .e .s .w = Button Quad north, east, south, west
  .a .b .x .y = Button Quad south, east, west, north
  .02 .04 .07 .09 .13 .15. 16 = TouchMenu or RadialMenu, menu item #
  .01  .03 .05.  06  .08  .10 .11 .12  .14  .17 .18 .19 .20 = Radial Menu

  Activator signal prefix
  / : Full Press (explicit)
       .toggle : bool
       .delay_start : int [ms]
       .delay_end: int [ms]
       .haptic [enum: 0, 1, 2, 3 ]
       .cycle : bool
       .repeat : int (0..9999)
  + : Start Press
      .toggle, .delay_start, .delay_end, .haptic, .cycle
  - : Release
      .delay_start, .delay_end, .haptic, .cycle
  _ : Long Press
      .long_press_time, .delay_start, .delay_end, .haptic, .cycle, .repeat
  : : Double Press
      .doubetap_max_duration, .delay_start, .delay_end, .haptic, .cycle, .repeat
  = : Double Press
  & : Chord?
      .chord, .toggle, .delay_start, .delay_end, .haptic, .cycle, .repeat


Modifiers:
  shift
  lock
  latch
  bounce



evsym indicators:
  < : keypress
  ( : gamepad
  [ : mouse
  { : verbose descriptor / everything else


activator modifer/options suffices:
  $ : activator-specific tweak (Long=>press time, Double=>duration, Chord=>chord)
  % : toggle on
  | : interruptible
  @ : delay_start '+' delay_end ("@0+10")
  ~ : haptics : 0,1,2,3 (default 2?; "~2")
  ^ : cycle on
  / : repeat on : 0..9999 (default 0; "/0")
"""


r"""
simultaneous presses

LB: <Left_Control><C>

LB:
  Full_Press:
    bindings:
      - Left_Control
      - C
    settings:
      toggle: False


On the edge:

LB: +<Up> -<Down>

+LB: <Up>
-LB: <Down>

LB:
  - +<Up>
    settings: {}
  - -<Down>
    settings: {}

LB:
  Start_Press:
    bindings:
      - Up
    settings: {}
  Release:
    bindings: - Down
    settings: {}
 
"""



r"""
evsym: keypress_evsym evsym |
       mouseswitch_evsym evsym |
       gamepad_evsym evsym |
       generic_evsym evsym |
       None
keypress_evsym: '<' IDENTIFIER '>'
mouseswitch_evsym: '[' IDENTIFIER ']
gamepad_evsym: '(' IDENTIFYER ')'
generic_evsym: '{' identifiers '}'
identifiers: IDENTIFIER identifiers |
             IDENTIFIER

subsrc: '.' dpad_sub |
        '.' buttonquad_sub |
        '.' trigger_sub |
        '.' menuitem_sub
        '.' touchpad_sub |
dpad_sub: 'u' | 'd' | 'l' | 'r' | 'c' | 'o'
button_quad_sub: 'n' | 'w' | 'e' | 's' |
                 'y' | 'x' | 'b' | 'a'
trigger_sub: 'c' | 'e'
menuitem_sub: DIGIT DIGIT
touchpad_sub: dpad_sub | 't'

genmod: specific genmod |
        may_toggle genmod |
        may_interrupt genmod |
        delay_spec genmod |
        haptic_spec genmod |
        may_cycle genmod |
        repeat_spec genmod |
        None
specific: ':' INTEGER |
          's' INTEGER
may_toggle: '%' |
            't'
may_interrupt: '|' |
               'i'
delay_spec: '@' integer_pair |
            'd' integer_pair
integer_pair: INTEGER ',' INTEGER |
              INTEGER '+' INTEGER
haptic_spec: '~' | '~' DIGIT |
             'h' DIGIT
may_cycle: '^' |
           'c'
repeat_spec: '/' INTEGER |
             'r' INTEGER

"""

class Srcspec (object):
  REGEX = r"([/+-_=:&])?([LR][TBGPSJ]|GY|BQ|BK|ST)(\.([neswabxyudlrcet]|[0-9][0-9]))?"
  def __init__ (self):
    pass

  @staticmethod
  def parse (s):
    srcsymre = re.compile(Srcspec.REGEX)
    matches = srcsymre.match(s)
    actsig = matches.group(1)
    srcsym = matches.group(2)
    subpart = matches.group(4)
    return (actsig, srcsym, subpart)



class Evsym (object):
  """'bindings' fork in 'activator'."""
  def __init__ (self, evtype=None, evcode=None, actsig=None):
    self.actsig = actsig  # explicit Activator owner.
    self.evtype = evtype  # EventSym physical device
    self.evcode = evcode  # EventSym code

  REGEX_SYM = """(<[A-Za-z_][A-Za-z0-9_]*>|\[[A-Za-z_][A-Za-z0-9_]*\]|\([A-Za-z_][A-Za-z0-9_]*\)|{[^}]*})"""

  @staticmethod
  def parse (s):
    specs = re.compile(REGEX_EVENT)
    matches = specs.findall(s)

class Evfrob (object):
  """'setting' fork in 'activator'."""
  REGEX_FROB = """([t%]|[i^]|[c|]|[s:][0-9]+|[d@][0-9]+[+,][0-9]+|[h~][0-9]*|[r/][0-9]+)"""
  def __init__ (self, specific=None, toggle=None, interrupt=None, delay_start=None, delay_end=None, haptic=None, cycle=None, repeat=None):
    self.specific = specific
    self.toggle = toggle
    self.interrupt = interrupt
    self.delay_start = delay_start
    self.delay_end = delay_end
    self.haptic = haptic
    self.cycle = cycle
    self.repeat = repeat

  def __str__ (self):
    parts = []
    if self.specific:
      parts.append(":{}".format(self.specific))
    if self.toggle:
      parts.append("%")
    if self.interrupt:
      parts.append("^")
    if self.delay_start or self.delay_end:
      parts.append("@{},{}".format(self.delay_start, self.delay_end))
    if self.haptic:
      parts.append("~{}".format(self.haptic))
    if self.cycle:
      parts.append("|")
    if self.repeat:
      parts.append("/{}".format(self.repeat))
    return "".join(parts)

  def __repr__ (self):
    return "{}(specific={!r}, toggle={!r}, interrupt={!r}, delay_start={!r}, delay_end={!r}, haptic={!r}, cycle={!r}, repeat={!r}".format(
      self.__class__.__name__,
      self.toggle,
      self.interrupt,
      self.delay_start, self.delay_end,
      self.haptic,
      self.cycle,
      self.repeat)

  @staticmethod
  def parse (s):
    pass

class Evspec (object):
  """Event specification: combine Evsym and Evfrob."""
  REGEX_SIGNAL = """([-/+_=:\&])"""
  REGEX_SYM = Evsym.REGEX_SYM
  REGEX_FROB = Evfrob.REGEX_FROB

#  REGEX_MAIN = REGEX_SIGNAL + "?" + \
#               "(" + REGEX_SYM + "+)" + \
#               "(" + REGEX_FROBS + "+)?"
  REGEX_MAIN = "{}?({}+)({}+)?".format(REGEX_SIGNAL, REGEX_SYM, REGEX_FROB)

  def __init__ (self, actsig=None, evsyms=None, evfrob=None):
    self.actsig = actsig
    self.evsyms = evsyms
    self.evfrob = evfrob

  def __repr__ (self):
    evsymspec = "".join(self.evsyms)
    evfrobspec = "".join(self.evfrob)
    retval = """{}(actsig={!s}, evsyms='{!s}', evfrob='{!s}')""".format(
      self.__class__.__name__,
      self.actsig,
      self.evsyms,  # list of Evsym
      self.evfrob,  # list of Evfrob
      )
    return retval

  @staticmethod
  def _parse (s):
    evsymre = re.compile(Evspec.REGEX_MAIN)
    evsyms = evsymre.match(s)

    signal = evsyms.group(1)
    evsymspec = evsyms.group(2)
    evfrobspec = evsyms.group(4)

    #evsym = Evsym(evsymspec)
    #evfrob = Evfrob(evfrobspec)
    return (signal, evsymspec, evfrobspec)

  @staticmethod
  def parse (s):
    signal, evsymspec, evfrobspec = Evspec._parse(s)

    re_signal = re.compile(Evspec.REGEX_SIGNAL)
    re_evsym = re.compile(Evsym.REGEX_SYM)
    re_evfrob = re.compile(Evfrob.REGEX_FROB)

    matches_evsym = re_evsym.findall(evsymspec) if evsymspec else None
    matches_evfrob = re_evfrob.findall(evfrobspec) if evfrobspec else None
    evsyms = [ Evsym(s) for s in matches_evsym[1:] ] if matches_evsym else None
    evfrobs = [ Evfrob(s) for s in matches_evfrob[1:] ] if matches_evfrob else None

    return Evspec(signal, evsyms, evfrobs)


class CfgMaker (object):
  pass

