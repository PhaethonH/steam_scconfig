#!/usr/bin/env python3

# Given a dict describing a controller configuration,
# generate Scconfig and VDF.

import re
import scconfig, scvdf

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
? SW : switches as a cluster
 (PS3, XB360, PS4)
  RS : Right Stick click
  RJ : Right Joystick whole
 (PS4)
  TP : Touchpad whole (LP, RP for implicit split-pad).

  cluster accessor, suffix:
  .c = click
  .o = edge (threshold, soft pull)
  .t = touch
  .2 = double-tap
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

def _stringlike (x):
  try: x.isalpha
  except AttributeError: return False
  else: return True

def _dictlike (x):
  try: x.items
  except AttributeError: return False
  else: return True

class Srcspec (object):
  REGEX = r"([/+-_=:&])?([LR][TBGPSJ]|GY|BQ|BK|ST)(\.([neswabxyudlrcet]|[0-9][0-9]))?"
  def __init__ (self):
    pass

  @staticmethod
  def _parse (s):
    srcsymre = re.compile(Srcspec.REGEX)
    matches = srcsymre.match(s)
    if matches:
      actsig = matches.group(1)
      srcsym = matches.group(2)
      subpart = matches.group(4)
      return (actsig, srcsym, subpart)
    else:
      return None

  @staticmethod
  def parse (s):
    actsig, srcsym, subpart = Srcspec._parse(s)
    return Srcspec(actsig, srcsym, subpart)


class Evsym (object):
  """'bindings' fork in 'activator'."""
  REGEX_SYM = """(<[A-Za-z0-9_]+>|\[[A-Za-z0-9_]+\]|\([A-Za-z0-9_]+\)|{[^}]*})"""

  def __init__ (self, evtype=None, evcode=None):
    self.evtype = evtype  # EventSym physical device
    self.evcode = evcode  # EventSym code

  def __str__ (self):
    parts = []
    if self.evtype == "keyboard":
      parts.append("<{}>".format(self.evcode))
    elif self.evtype == "mouse":
      parts.append("[{}]".format(self.evcode))
    elif self.evtype == "gamepad":
      parts.append("({})".format(self.evcode))
    elif self.evtype == "host":
      parts.append("{}{}{}".format("{", self.evcode, "}"))
    else:
      parts.append("{}".format(self.evcode))
    return "".join(parts)

  def __repr__ (self):
    return "{}(evtype='{!s}', evcode='{!s}')".format(
      self.__class__.__name__,
      self.evtype,
      self.evcode,
      )

  @staticmethod
  def _parse (s):
    specs = re.compile(Evsym.REGEX_SYM)
    matches = specs.findall(s)
    evsymspec = matches[0]
    evcode = None
    if evsymspec[0] == '<':
      evtype = "keyboard"
      evcode = evsymspec[1:]
      if evcode[-1] == '>':
        evcode = evcode[:-1]
    elif evsymspec[0] == '[':
      evtype = "mouse"
      evcode = evsymspec[1:]
      if evcode[-1] == ']':
        evcode = evcode[:-1]
    elif evsymspec[0] == '(':
      evtype = "gamepad"
      evcode = evsymspec[1:]
      if evcode[-1] == ')':
        evcode = evcode[:-1]
    elif evsymspec[0] == '{':
      evtype = "host"
      evcode = evsymspec[1:]
      if evcode[-1] == '}':
        evcode = evcode[:-1]
    return (evtype, evcode)

  @staticmethod
  def parse (s):
    evtype, evcode = Evsym._parse(s)
    return Evsym(evtype, evcode)


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
      self.specific,
      self.toggle,
      self.interrupt,
      self.delay_start, self.delay_end,
      self.haptic,
      self.cycle,
      self.repeat)

  def export_scconfig (self, activator_type=None):
    """Convert Evfrob to Scconfig fragment (settings)."""
    retval = {}
    VSC_KEYS = scconfig.ActivatorBase.Settings._VSC_KEYS

    SPECIFIC_MAP = {
      scconfig.ActivatorLongPress.signal: (VSC_KEYS.LONG_PRESS_TIME, int),
      scconfig.ActivatorDoublePress.signal: (VSC_KEYS.DOUBLE_TAP_TIME, int),
      # TODO: map keysym:str to chord_button:int
      scconfig.ActivatorChord.signal: (VSC_KEYS.CHORD_BUTTON, lambda x:x),
      }
    specific_key, converter = SPECIFIC_MAP.get(activator_type, (None,None))
    if specific_key:
      retval[specific_key] = converter(self.specific)

    if activator_type == scconfig.ActivatorLongPress.signal:
      retval[VSC_KEYS.LONG_PRESS_TIME] = int(self.specific)
    elif activator_type == scconfig.ActivatorDoublePress.signal:
      retval[VSC_KEYS.DOUBLE_TAP_TIME] = int(self.specific)
    elif activator_type == scconfig.ActivatorChord.signal:
      # TODO: map keysym:str to chord_button:int
      retval[VSC_KEYS.CHORD_BUTTON] = self.specific

    if self.toggle:
      retval[VSC_KEYS.TOGGLE] = bool(self.toggle)
    if self.interrupt:
      retval[VSC_KEYS.INTERRUPTIBLE] = bool(self.interrupt)
    if self.delay_start is not None or self.delay_end is not None:
      retval[VSC_KEYS.DELAY_START] = int(self.delay_start)
      retval[VSC_KEYS.DELAY_END] = int(self.delay_end)
    if self.haptic is not None:
      retval[VSC_KEYS.HAPTIC_INTENSITY] = self.haptic
    if self.cycle is not None:
      retval[VSC_KEYS.CYCLE] = bool(self.cycle)
    if self.repeat:
      retval[VSC_KEYS.HOLD_REPEATS] = True
      retval[VSC_KEYS.REPEAT_RATE] = self.repeat
    return retval

  @staticmethod
  def _parse (s):
    re_frobs = re.compile(Evfrob.REGEX_FROB)
    matches = re_frobs.findall(s)
    specific, toggle, interrupt, delay_start, delay_end, haptic, cycle, repeat = (None,)*8
    for s in matches:
      if s[0] in "t%":
        toggle = True
      if s[0] in "i^":
        interrupt = True
      if s[0] in "c|":
        cycle = True
      if s[0] in "s:":
        specific = int(s[1:])
      if s[0] in "d@":
        parts = s[1:].split(",")
        delay_start = int(parts[0])
        delay_end = int(parts[1])
      if s[0] in "h~":
        haptic = int(s[1:])
      if s[0] in "r/":
        repeat = int(s[1:])
    return (specific, toggle, interrupt, delay_start, delay_end, haptic, cycle, repeat)

  @staticmethod
  def parse (s):
    parsed = Evfrob._parse(s)
    return Evfrob(*parsed)


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
    self.actsig = actsig    # one character of REGEX_SIGNAL
    self.evsyms = evsyms    # list of Evsym instances.
    self.evfrob = evfrob    # Evfrob instance.

  def __str__ (self):
    evsymspec = "".join(map(str, self.evsyms))
    retval = """{}{}{}""".format(
      self.actsig if self.actsig else "",
      evsymspec,
      str(self.evfrob),
      )
    return retval

  def __repr__ (self):
    evsymspec = "".join(map(str, self.evsyms))
#    evsymspec = self.evsyms
    evfrobspec = str(self.evfrob) if self.evfrob is not None else None
    retval = """{}(actsig={!r}, evsyms='{!s}', evfrob={!r})""".format(
      self.__class__.__name__,
      self.actsig,
      evsymspec,    # list of Evsym
      evfrobspec,   # list of Evfrob
      )
    return retval

  @staticmethod
  def _parse (s):
    evsymre = re.compile(Evspec.REGEX_MAIN)
    evsyms = evsymre.match(s)

    if evsyms:
      signal = evsyms.group(1)
      evsymspec = evsyms.group(2)
      evfrobspec = evsyms.group(4)
    else:
      signal, evsymspec, evfrobspec = None, None, None

    return (signal, evsymspec, evfrobspec)

  @staticmethod
  def parse (s):
    signal, evsymspec, evfrobspec = Evspec._parse(s)

    re_signal = re.compile(Evspec.REGEX_SIGNAL)
    re_evsym = re.compile(Evsym.REGEX_SYM)
    re_evfrob = re.compile(Evfrob.REGEX_FROB)

    matches_evsym = re_evsym.findall(evsymspec) if evsymspec else None
    evsyms = [ Evsym.parse(s) for s in matches_evsym ] if matches_evsym else None
    evfrobs = Evfrob.parse(evfrobspec) if evfrobspec else None

    return Evspec(signal, evsyms, evfrobs)




class CfgEvgen (object):
  def __init__ (self):
    pass
  pass


class CfgBind (object):
  r"""
<SrcSym>: <Evgen>+

"""
  def __init__ (self):
    # List of event generators.
    self.evgen = []
  pass


class CfgEvspec (object):
  r"""

- signal: { full, start, long, ... }
  label: ...
  icon: ...
  bindings:
    - <Evsym>
    - <Evsym>
  settings:
    toggle: ...
    repeat: ...
"""
  def __init__ (self, evspec=None):
    self.evspec = evspec

  def export_scbind (self, evsym):
    retval = None
    if evsym.evtype == "keyboard":
      retval = scconfig.EvgenFactory.make_keystroke(evsym.evcode)
    elif evsym.evtype == "mouse":
      retval = scconfig.EvgenFactory.make_mouseswitch(evsym.evcode)
    elif evsym.evtype == "gamepad":
      retval = scconfig.EvgenFactory.make_gamepad(evsym.evcode)
    elif evsym.evtype == "host":
      retval = scconfig.EvgenFactory.make_hostcall(evsym.evcode)
    elif evsym.evtype == "overlay":
      retval = scconfig.EvgenFactory.make_overlay(*evsym.evcode)
    else:
      retval = scconfig.EvgenFactory.make__literal(evsym.evcode[1:-1])
    return retval

  def export_signal (self):
    SIGNAL_MAP = {
      "+": scconfig.ActivatorStartPress.signal,
      "_": scconfig.ActivatorLongPress.signal,
      ":": scconfig.ActivatorDoublePress.signal,
      "=": scconfig.ActivatorDoublePress.signal,
      "-": scconfig.ActivatorRelease.signal,
      "&": scconfig.ActivatorChord.signal,
      "/": scconfig.ActivatorFullPress.signal,
      None: scconfig.ActivatorFullPress.signal,
      }
    evspec = self.evspec
    actsig = SIGNAL_MAP.get(evspec.actsig, scconfig.ActivatorFullPress.signal)
    return actsig

  def export_scconfig (self):
    """Convert Evspec to Scconfig.Activator*"""
    evspec = self.evspec
    actsig = self.export_signal()
    if evspec.evsyms:
      bindings = [ self.export_scbind(evsym) for evsym in evspec.evsyms ]
      settings = evspec.evfrob.export_scconfig() if evspec.evfrob else None
      retval = scconfig.ActivatorFactory.make(actsig, bindings, settings)
    else:
      retval = None
    return retval



class CfgClusterBase (object):
  r"""
<ClusterSrcSym>:
  mode: ...
  <SubpartSrcSym>:
    - [[CfgEvspec]]

    - signal: { full, start, long, ... }
      label: ...
      icon: ...
      bindings:
        - <Evsym>
        - <Evsym>
      settings:
        toggle: ...
        repeat: ...
    - signal: ...
"""
  MODES = set([
    "pen",
    "dpad",
    "face",
    "js-move"
    "js-cam",
    "js-mouse",
    "mouse-js",
    "region",
    "pie",
    "scroll",
    "single",
    "switches",
    "menu",
    "trigger",
    ])
  MODE = mode = None
  SUBPARTS = dict()
  def __init__ (self, py_dict=None):
    self.index = 0
    self.subparts = {}  # key <- subpart name; value <- list of CfgEvspec
    if py_dict:
      self.load(py_dict)

  def bind_subpart (self, subpartname, bindspec):
    if _stringlike(bindspec):
      # generate list of CfgEvspec
      collate = []
      evspecs = bindspec.split()
      for evspec in evspecs:
        cfgevspec = CfgEvspec(Evspec.parse(evspec))
        if cfgevspec:
          collate.append(cfgevspec)
      self.subparts[subpartname] = collate
    elif isinstance(bindspec, CfgEvspec):
      if not subpartname in self.subparts:
        self.subparts[subpartname] = []
      self.subparts[subpartname].append(bindspec)
    else:
      # assume py literals (list of CfgEvspec).
      self.subparts[subpartname] = bindspec
    return True

  def load (self, py_dict):
    for k,v in py_dict.items():
      if k in self.SUBPARTS:
        self.bind_subpart(k, v)
    return

  def export_input (self, subpart_name):
    inputobj = None
    if self.subparts.get(subpart_name, None):
      inputobj = scconfig.ControllerInput(subpart_name)
      for evspec in self.subparts[subpart_name]:
        d = evspec.export_scconfig()
        a = scconfig.toVDF(d)
        signal = evspec.export_signal()
        #signal = d.signal
        inputobj.add_activator(signal, **a)
    return inputobj

  def export_scconfig (self, index=None):
    """Convert CfgCluster to scconfig.Group*"""
    if index is None:
      index = self.index
    grp = scconfig.GroupFactory.make(index, mode=self.COUNTERPART.MODE)
    for k in self.ORDERING:
      if k in self.subparts:
        realfield = self.SUBPARTS[k]
        grp.inputs[realfield] = self.export_input(k)
    #return scconfig.toVDF(grp)
    return grp

class CfgClusterPen (CfgClusterBase):
  MODE = mode = "pen"
  COUNTERPART = scconfig.GroupAbsoluteMouse
  ORDERING = "c2t"
  SUBPARTS = {
    "c": COUNTERPART.Inputs.CLICK,
    "2": COUNTERPART.Inputs.DOUBLETAP,
    "t": COUNTERPART.Inputs.TOUCH,
    }

class CfgClusterDpad (CfgClusterBase):
  MODE = mode = "dpad"
  COUNTERPART = scconfig.GroupDpad
  ORDERING = "udlrco"
  SUBPARTS = {
    "u": COUNTERPART.Inputs.DPAD_NORTH,
    "d": COUNTERPART.Inputs.DPAD_SOUTH,
    "l": COUNTERPART.Inputs.DPAD_WEST,
    "r": COUNTERPART.Inputs.DPAD_EAST,
    "c": COUNTERPART.Inputs.CLICK,
    "o": COUNTERPART.Inputs.EDGE,
  }

class CfgClusterFace (CfgClusterBase):
  MODE = mode = "face"
  COUNTERPART = scconfig.GroupFourButtons
  ORDERING = "sewn"
  SUBPARTS = {
    "s": COUNTERPART.Inputs.BUTTON_A,
    "e": COUNTERPART.Inputs.BUTTON_B,
    "w": COUNTERPART.Inputs.BUTTON_X,
    "n": COUNTERPART.Inputs.BUTTON_Y,
  }

class CfgClusterJoystick (CfgClusterBase):
  MODE = mode = "js-generic"
  COUNTERPART = scconfig.GroupJoystickMove
  ORDERING = "co"
  SUBPARTS = {
    "c": COUNTERPART.Inputs.CLICK,
    "o": COUNTERPART.Inputs.EDGE,
    '>': "output_joystick",
  }

  def export_scconfig (self, index=None):
    grp = super(CfgClusterJoystick,self).export_scconfig(index)
    if '>' in self.subparts:
      val = int(self.subparts['>'])
      grp.settings.output_joystick = val
    return grp

class CfgClusterJoystickMove (CfgClusterJoystick):
  MODE = mode = "jsmove"
  COUNTERPART = scconfig.GroupJoystickMove

class CfgClusterJoystickCamera (CfgClusterJoystick):
  MODE = mode = "jscam"
  COUNTERPART = scconfig.GroupJoystickCamera

class CfgClusterJoystickMouse (CfgClusterJoystick):
  MODE = mode = "jsmouse"
  COUNTERPART = scconfig.GroupJoystickMouse
  ORDERING = "co"
  SUBPARTS = {
    "c": COUNTERPART.Inputs.CLICK,
    "o": COUNTERPART.Inputs.EDGE,
    }

class CfgClusterMouseJoystick (CfgClusterBase):
  MODE = mode = "mousejs"
  COUNTERPART = scconfig.GroupMouseJoystick
  ORDERING = "c2"
  SUBPARTS = {
    "c": COUNTERPART.Inputs.CLICK,
    "2": COUNTERPART.Inputs.DOUBLETAP,
    }

class CfgClusterRegion (CfgClusterBase):
  MODE = mode = "region"
  COUNTERPART  = scconfig.GroupMouseRegion
  ORDERING = "cet"
  SUBPARTS = {
    "c": COUNTERPART.Inputs.CLICK,
    "e": COUNTERPART.Inputs.EDGE,
    "t": COUNTERPART.Inputs.TOUCH,
    }

class CfgClusterPie (CfgClusterBase):
  MODE = mode = "pie"
  COUNTERPART = scconfig.GroupRadialMenu
  MAX_BUTTONS = COUNTERPART.Inputs.N_BUTTONS+1
  ORDERING = [ "{:02d}".format(x) for x in range(0,MAX_BUTTONS) ] + [ 'c' ]
  SUBPARTS = dict( [
    ("{:02d}".format(x),"touch_menu_button_{}".format(x))
      for x in range(0, MAX_BUTTONS) ] + \
    [ ('c', COUNTERPART.Inputs.CLICK) ] )

class CfgClusterScroll (CfgClusterBase):
  MODE = mode = "scroll"
  COUNTERPART = scconfig.GroupScrollwheel
  ORDERING = "ioc0123456789"
  SUBPARTS = {
    "i": COUNTERPART.Inputs.SCROLL_CLOCKWISE,
    "o": COUNTERPART.Inputs.SCROLL_COUNTERCLOCKWISE,
    "c": COUNTERPART.Inputs.CLICK,
    "0": "scroll_wheel_list_0",
    "1": "scroll_wheel_list_1",
    "2": "scroll_wheel_list_2",
    "3": "scroll_wheel_list_3",
    "4": "scroll_wheel_list_4",
    "5": "scroll_wheel_list_5",
    "6": "scroll_wheel_list_6",
    "7": "scroll_wheel_list_7",
    "8": "scroll_wheel_list_8",
    "9": "scroll_wheel_list_9",
    }

class CfgClusterSingle (CfgClusterBase):
  MODE = mode = "single"
  COUNTERPART = scconfig.GroupSingleButton
  ORDERING = "ct"
  SUBPARTS = {
    'c': COUNTERPART.Inputs.CLICK,
    't': COUNTERPART.Inputs.TOUCH,
    }

class CfgClusterSwitches (CfgClusterBase):
  MODE = mode = "switches"
  COUNTERPART = scconfig.GroupSwitches
  ORDERING = [ 'BK', 'ST', 'LB', 'RB', 'LG', 'RG' ]
  SUBPARTS = {
    'BK': COUNTERPART.Inputs.BUTTON_ESCAPE,
    'ST': COUNTERPART.Inputs.BUTTON_MENU,
    'LB': COUNTERPART.Inputs.LEFT_BUMPER,
    'RB': COUNTERPART.Inputs.RIGHT_BUMPER,
    'LG': COUNTERPART.Inputs.LEFT_GRIP,
    'RG': COUNTERPART.Inputs.RIGHT_GRIP,
    }

class CfgClusterMenu (CfgClusterBase):
  MODE = mode = "menu"
  COUNTERPART = scconfig.GroupRadialMenu
  MAX_BUTTONS = COUNTERPART.Inputs.N_BUTTONS+1
  ORDERING = [ "{:02d}".format(x) for x in range(0,MAX_BUTTONS) ] + [ 'c' ]
  SUBPARTS = dict( [
    ("{:02d}".format(x),"touch_menu_button_{}".format(x))
      for x in range(0, MAX_BUTTONS) ] + \
    [ ('c', COUNTERPART.Inputs.CLICK) ] )

class CfgClusterTrigger (CfgClusterBase):
  MODE = mode = "trigger"
  COUNTERPART = scconfig.GroupTrigger
  ORDERING = "co"
  SUBPARTS = {
    'c': COUNTERPART.Inputs.CLICK,
    'o': COUNTERPART.Inputs.EDGE,
    '>': "output_trigger",
    }

  def export_scconfig (self, index=None):
    grp = super(CfgClusterTrigger,self).export_scconfig(index)
    if '>' in self.subparts:
      val = int(self.subparts['>'])
      grp.settings.output_trigger = val
    return grp


class CfgClusterFactory (object):
  @staticmethod
  def make_pen (py_dict): return CfgClusterPen(py_dict)
  @staticmethod
  def make_dpad (py_dict): return CfgClusterDpad(py_dict)
  @staticmethod
  def make_face (py_dict): return CfgClusterFace(py_dict)
  @staticmethod
  def make_jsmove (py_dict): return CfgClusterJoystickMove(py_dict)
  @staticmethod
  def make_jscam (py_dict): return CfgClusterJoystickCamera(py_dict)
  @staticmethod
  def make_jsmouse (py_dict): return CfgClusterJoystickMouse(py_dict)
  @staticmethod
  def make_mousejs (py_dict): return CfgClusterMouseJoystick(py_dict)
  @staticmethod
  def make_pie (py_dict): return CfgClusterPie(py_dict)
  @staticmethod
  def make_region (py_dict): return CfgClusterRegion(py_dict)
  @staticmethod
  def make_scroll (py_dict): return CfgClusterScroll(py_dict)
  @staticmethod
  def make_single (py_dict): return CfgClusterSingle(py_dict)
  @staticmethod
  def make_switches (py_dict): return CfgClusterSwitches(py_dict)
  @staticmethod
  def make_menu (py_dict): return CfgClusterMenu(py_dict)
  @staticmethod
  def make_trigger (py_dict): return CfgClusterTrigger(py_dict)
  @staticmethod
  def make_cluster (py_dict):
    DELEGATE = {
      CfgClusterPen.MODE: CfgClusterFactory.make_pen,
      CfgClusterDpad.MODE: CfgClusterFactory.make_dpad,
      CfgClusterFace.MODE: CfgClusterFactory.make_face,
      CfgClusterJoystickMove.MODE: CfgClusterFactory.make_jsmove,
      CfgClusterJoystickCamera.MODE: CfgClusterFactory.make_jscam,
      CfgClusterJoystickMouse.MODE: CfgClusterFactory.make_jsmouse,
      CfgClusterMouseJoystick.MODE: CfgClusterFactory.make_mousejs,
      CfgClusterRegion.MODE: CfgClusterFactory.make_region,
      CfgClusterPie.MODE: CfgClusterFactory.make_pie,
      CfgClusterScroll.MODE: CfgClusterFactory.make_scroll,
      CfgClusterSingle.MODE: CfgClusterFactory.make_single,
      CfgClusterSwitches.MODE: CfgClusterFactory.make_switches,
      CfgClusterMenu.MODE: CfgClusterFactory.make_menu,
      CfgClusterTrigger.MODE: CfgClusterFactory.make_trigger,
      }
    delegate = DELEGATE[py_dict["mode"]]
    if delegate:
      retval = delegate(py_dict)
      return retval
    return None


class CfgLayer (object):
  r"""
# abbreviated
layer:
  name: 
  <SrcSym>: <Evgen> <Evgen> <Evgen>


# canonical
layer:
  name:
  <SubpartSrcSym>:
    [[CfgCluster*]]
  <SubpartSrcSym>:
  ...

"""
  def __init__ (self):
    self.name = None
    self.clusters = {}    # map to list of CfgCluster*

  ORDERING = [ "SW", "BQ", "LP", "RP", "LJ", "LT", "RT", "RJ", "DP" ]
  CLUSTER_SYMS = set([
    "LP", "RP", "LJ", "BQ", "LT", "RT", "GY", "SW",
    "RJ"
    ])
  CLUSTERS = {
    "SW": "switch",
    "DP": "dpad",
    "BQ": "button_diamond",
    "LJ": "joystick",
    "LT": "left_trigger",
    "RT": "right_trigger",
    "LP": "left_trackpad",
    "RP": "right_trackpad",
    "RJ": "right_joystick",
    }
  SW_SYMS = set([
    "BK", "ST",
    "LB", "RB",
    "LG", "RG"
    ])

  def filter_bind (self, v_dict):
    retval = {}
    if 'mode' in v_dict:
      m = v_dict.get("mode", None)
      if not m in CfgClusterNode.MODES:
        m = None
      retval['mode'] = m
    pass

  def pave_cluster (self, clustername, create_mode=None):
    """Ensure cluster entry exists, with specified mode if create needed."""
    if not clustername in self.clusters:
      cluster = CfgClusterFactory.make_cluster({"mode": create_mode})
      self.clusters[clustername] = cluster
    return True

  def pave_subpart (self, clustername, subpartname):
    """Ensure subpart within cluster exists (is ready for bind()).
For inlined subparts.
"""
    if not clustername in self.clusters:
      mode = self.auto_mode(subpartname)
      print("using mode {} / {}.{}".format(mode, clustername, subpartname))
      self.pave_cluster(clustername, mode)
    return True

  def bind_point (self, clustername, subpartname, bindspec):
    # bindspec: (dict, str, CfgEvspec, [ CfgEvspec ])
    if clustername in ("LT", "RT"):
      self.pave_cluster(clustername, "trigger")
    elif clustername is None:
      if subpartname in CfgClusterSwitches.SUBPARTS:
        # directly inlined switch subpart: BK, ST, LB, RB, LG, RG
        clustername = "SW"
        self.pave_cluster(clustername, "switches")
      elif len(subpartname) > 2 and subpartname[2] == '.' and subpartname[:2] in self.CLUSTERS:
        # inline subpart "XX.y".
        prefix = subpartname[:3]
        clustername = subpartname[:2]
        subpartname = subpartname[3:]
        cluster = self.clusters.get(clustername, None)
        if cluster is None:
          if clustername in ("LT", "RT"):
            self.pave_cluster(clustername, "trigger")
          else:
            subparts = [ x[3] for x in py_dict if x.startswith(prefix) ]
            mode = self.auto_mode(subparts)
            self.pave_cluster(clustername, mode)
    self.pave_subpart(clustername, subpartname)
    self.clusters[clustername].bind_subpart(subpartname, bindspec)

  def auto_mode (self, subparts):
    """Determine cluster mode from available subparts specified."""
    if any([ x in subparts  for x in "udlr" ]):
      return CfgClusterDpad.mode
    if any([x in subparts  for x in "sewn" ]):
      return CfgClusterFace.mode
    if any([x in subparts  for x in "abxy" ]):
      return CfgClusterFace.mode
    def _intlike (x):
      try: int(x)
      except (TypeError, ValueError): return False
      else: return True
    def _intOrNegOne(x):
      try: return int(x)
      except (ValueError, TypeError): return -1
    numerics = [ _intOrNegOne(x) for x in subparts ]
    if any([_intlike(x) for x in subparts ]):
      zero = 0 in numerics
      m = max(numerics)
      if (m > 16) or (zero):
        # definitely pie: more than 16, or exists 0 = center/unselect.
        return CfgClusterPie.mode
      if m in (2, 4, 7, 9, 13, 15, 16):
        # TouchMenu if exactly these many, and 0 does not exist.
        return CfgClusterMenu.mode
      # any other max-numeric.
      return CfgClusterPie.mode
    return None

  def load_trigger (self, trigger_name, trigger_value):
    # analog assignment of triggers.
    k, v = trigger_name, trigger_value
    if v[0] == '(':
      v = v[1:3]
    if v in ("LT", "RT"):
      if k == v:
        # same side
        output_trigger = scconfig.GroupBase.Settings.OutputTrigger.MATCHED_SIDE
      else:
        # opposite side
        output_trigger = scconfig.GroupBase.Settings.OutputTrigger.OPPOSITE_SIDE

      self.pave_cluster(trigger_name, "trigger")
      self.bind_point(trigger_name, '>', output_trigger)
    else:
      # full-press only assignment.
      self.pave_cluster(trigger_name, "trigger")
      self.bind_point(trigger_name, 'c', v)
    return True

  def load_joystick (self, js_name, js_value):
    # analog assignment of joysticks.
    k, v = js_name, js_value
    if v[0] == '(':
      v = v[1:3]
    if v[1] != 'J':
      # not joystick assignment.
      return False
    if k[0] == v[0]:
      # same side
      output_joystick = 0
    else:
      # opposite side
      output_joystick = 1
    if js_name[0] == 'R':
      self.pave_cluster(js_name, "jscam")
    else:
      self.pave_cluster(js_name, "jsmove")
    self.bind_point(js_name, '>', output_joystick)
    return True

  def load_touchpad (self, tp_name, tp_value):
    self.pave_cluster(tp_name, "single")
    self.bind_point(tp_name, 'c', tp_value)
    return True

  def load (self, py_dict):
    if 'name' in py_dict:
      self.name = py_dict['name']
    for k,v in py_dict.items():
      if v == "":
        # No-Op binding: do nothing.
        pass
      elif k in self.CLUSTERS:
        # whole cluster full spec.
        v = py_dict[k]
        if _dictlike(v):
          self.clusters[k] = CfgClusterFactory.make_cluster(v)
        else:
          # whole-cluster single bind.
          if k in ('LT', 'RT'):
            # analog or full-press-only assignment of triggers.
            self.load_trigger(k, v)
          elif k in ('LJ', 'RJ'):
            # analog assignment of joysticks.
            self.load_joystick(k, v)
          elif k in ('LP', 'RP'):
            # analog or single-button assigment of touchpads.
            if not self.load_joystick(k, v):
              self.load_touchpad(k, v)
      elif k in CfgClusterSwitches.SUBPARTS:
        # directly inlined switch subpart: BK, ST, LB, RB, LG, RG
        clustername = "SW"
        subpartname = k
        self.pave_cluster(clustername, "switches")
        self.bind_point(clustername, subpartname, v)
      elif len(k) > 2 and k[2] == '.' and k[:2] in self.CLUSTERS:
        # inline subpart "XX.y".
        clustername = k[:2]
        subpartname = k[3:]
        cluster = self.clusters.get(clustername, None)
        if cluster is None:
          prefix = k[:3]
          if clustername in ("LT", "RT"):
            self.pave_cluster(clustername, "trigger")
          else:
            subparts = [ x[3] for x in py_dict if x.startswith(prefix) ]
            mode = self.auto_mode(subparts)
            self.pave_cluster(clustername, mode)
        self.bind_point(clustername, subpartname, v)

  def export_preset (self, sccfg):
    grpid = len(sccfg.groups)
    presetid = len(sccfg.presets)
    if presetid:
      index = "Preset_{:07d}".format(1000000 + presetid)
    else:
      index = 'Default'

    preset = scconfig.Preset(str(presetid), py_name=index)
    for k in self.ORDERING:
      if k in self.clusters:
        cluster = self.clusters[k]
        realfield = self.CLUSTERS[k]
        # add Group to Sccfg
        grp = cluster.export_scconfig(grpid)
        grpid += 1
        sccfg.add_group(grp)
        # add GSB to Preset
        preset.add_gsb(grp.index, realfield)
    sccfg.add_preset(preset)
    return preset

  def export_scconfig (self, sccfg, parent_set_name='', **overrides):
    # Generate "preset" entry.
    preset = self.export_preset(sccfg)
    presetname = preset.name

    # add ActionLayer to Sccfg
    d = {
      "title": self.name,
      "legacy_set": True,
      }
    if 'index' in overrides:
      index = overrides['index']
    else:
      index = self.name
    if parent_set_name:
      d.update({
        'set_layer': 1,
        'parent_set_name': parent_set_name,
        })
      d.update(overrides)
      if 'index' in d: del d['index']
      if index is None:
        index = presetname
      sccfg.add_action_layer(index, **d)
    else:
      d.update(overrides)
      if 'index' in d: del d['index']
      if index is None:
        index = presetname
      sccfg.add_action_set(index, **d)
    return sccfg


class CfgAction (object):
  def __init__ (self):
    self.name = 'Default'
    self.layers = []

  def load (self, py_dict):
    if 'name' in py_dict:
      self.name = py_dict['name']
    for k,v in py_dict.items():
      if k == 'layers':
        for v in py_dict[k]:
          lyr = CfgLayer()
          lyr.load(v)
          self.layers.append(lyr)
    return

  def export_scconfig (self, sccfg=None):
    # Add first layer as Action Set, other layers as Action Layers.
    for lyr in self.layers:
      if lyr == self.layers[0]:
        lyr.export_scconfig(sccfg, title=self.name, index='Default')
      else:
        lyr.export_scconfig(sccfg, parent_set_name=self.name, index=None)
    return sccfg


class CfgShiftState (object):
  def __init__ (self, py_dict=None):
    self.overlays = []  # list of overlaid action layers involved in state.
    self.transits = {}  # map srcsym to next state by name.

    self.load(py_dict)

  def load (self, py_dict):
    for k,v in py_dict.items():
      if k == 'overlays':
        for stname in v:
          self.overlays.append(stname)
      elif k[0] in "+-":
        self.transits[k] = v
    return True

class CfgShifting (object):
  r"""
shifting:
  sanity: <srcsym>
  <layer_name>:
    <edge><srcsym>: <destination_state>
    overlays: [ <layer_name>, ... ]
"""
  # TODO: transition graphs, to validate all states are enterable and exitable.
  # TODO: compilation of involved layers for bind to sanity.
  # TODO: unbind sanity in non-default layers.
  def __init__ (self):
    self.states = {}    # map of state name to state object.
    self.graph = {}     # map of state name to list of next-states.
    self.involved = []  # list of layers involved in any state (for sanity key).

  def load (self, py_dict):
    # Load state transitions.
    for k,v in py_dict.items():
      self.states[k] = CfgShiftState(v)
      if not k in self.graph:
        self.graph[k] = []

    # Build transition graph.
    for srck,stateobj in self.states.items():
      for transitsym,nextstate in stateobj.transits.items():
        self.graph[srck].append(nextstate)

    # Compile sanity de-layering.
    self.involved = []
    for stname,stobj in self.states.items():
      for ov in stobj.overlays:
        self.involved.append(ov)

    # Check transition graph for inconsistencies.
    all_states = []
    all_states.extend([k for k in self.states.keys()])
    for stname,stobj in self.states.items():
      for nextstate in stobj.transits.values():
        all_states.append(nextstate)
    all_states = set(all_states)

    reachable = set()
    leaveable = set()
    for stname,stobj in self.states.items():
      if stobj.transits:
        leaveable.add(stname)
      for nextstate in stobj.transits.values():
        reachable.add(nextstate)

    unreachable = all_states - reachable
    unleaveable = all_states - leaveable
    retval = True
    if unreachable:
      print("Unreachable states: {}".format(unreachable))
      retval = False
    if unleaveable:
      print("Dead-end states: {}".format(unleaveable))
      retval = False
    return retval

  def export_scconfig (self, conmap):
    pass


class CfgShifters (object):
  # Alternative to CfgShifting
  r"""
shifters:
  <srcsym>: <style> <bitmask>
shiftlayers:
  <shiftnum>: [ <layer>, ... ]
 
style:
  hold
  lock
  latch
  bounce

  sanity


shift: chord while holding induce shifted behavior
lock: after release, all keys induce shifted behavior until next lock event.
latch: chord while holding induce shifted behavior;
       empty release causes next key to be shifted, unshift afterwards.
       (similar to keyboard accessibility, "sticky" shift)
bounce: chord while holding induce shifted behavior;
        empty release (release without any chorded presses) generates keystroke.
sanity: revoke all shift state and shift-state overlays.
"""
  STYLE_HOLD = "hold"
  STYLE_LOCK = "toggle"
  STYLE_LATCH = "latch"
  STYLE_BOUNCE = "bounce"
  STYLE_SANITY = "sanity"
  def __init__ (self):
    self.shifters = {}    # map srcsym to shift behavior (style, bitmask)
    self.overlays = {}    # map of shift level (int) to list of layers in level.
    self.involved = []    # all layers involved in shifts, for sanity.
    self.maxshift = 0     # Highest shift level to expect.

  def load (self, py_dict):
    self.maxshift = 0
    for k,v in py_dict.items():
      if k == "shifters":
        for srcsym,shiftspec in v.items():
          parts = shiftspec.split()
          style = parts[0]
          bitmask = int(parts[1]) if len(parts) > 1 else 0
          if not style in (self.STYLE_HOLD, self.STYLE_LOCK, self.STYLE_LATCH, self.STYLE_BOUNCE, self.STYLE_SANITY):
            print("Unknown shift style: {}".format(style))
          self.shifters[srcsym] = (style, bitmask)
          if bitmask:
            self.maxshift |= bitmask
      elif k == "shiftlayers":
        for shiftlevel,layerlist in v.items():
          shiftnum = int(shiftlevel)
          # TODO: all layer names in one string, space-delimited.
          shiftlayers = layerlist
          for layername in shiftlayers:
            self.involved.append(layername)
          self.overlays[shiftnum] = shiftlayers

  def shifter_bind (self, from_level, shiftsym, shiftstyle, shiftbits):
    # TODO: map shift level to action serialid.
    shift_base = 0
    evspec = None
    if shiftstyle == "hold":
      if from_level & shiftbits:
        # release is shift-out.
        nextlevel = from_level & ~shiftbits
        nextlevel += shift_base
      else:
        # press is shift-in.
        nextlevel = from_level | shiftbits
        nextlevel += shift_base

      evsyms = []

      # Apply overlays for next state.
      if nextlevel != 0:  # Can't apply layer 0 (is ActionSet with no layers).
        ovparms = ("apply", "$Shift_{}".format(nextlevel), 0, 0)
        evsym = Evsym('overlay', ovparms)
        evsyms.append(evsym)
        # apply overlays of next level.
        if nextlevel in self.overlays:
          for ov in self.overlays[nextlevel]:
            ovparms = ("apply", "${}".format(ov), 0, 0)
            evsym = Evsym('overlay', ovparms)
            evsyms.append(evsym)

      # Remove overlays from state.
      if from_level != 0:  # Can't remove 0.
        # remove overlays of currnet level.
        if from_level in self.overlays:
          for ov in self.overlays[from_level]:
            ovparms = ("peel", "${}".format(ov), 0, 0)
            evsym = Evsym('overlay', ovparms)
            evsyms.append(evsym)
        # last: remove shift state 'from_level'.
        ovparms = ("peel", "$Shift_{}".format(from_level), 0, 0)
        evsym = Evsym('overlay', ovparms)
        evsyms.append(evsym)

      evspec = Evspec('-', evsyms, None)
    elif shiftstyle == "bounce":
      # Create two groups: one for the Preshift, one for the actual Shift.
      if from_level & shiftbits:
        # release is shift-out.
        nextlevel = from_level & ~shiftbits
        nextlevel += shift_base
      else:
        # press is shift-in.
        nextlevel = from_level | shiftbits
        nextlevel += shift_base

      evsyms = []

      # Apply overlays for next state.
      if nextlevel != 0:  # Can't apply layer 0 (is ActionSet with no layers).
        if from_level & shiftbits:
          # leave on negative edge: skip to stable shift.
          ovparms = ("apply", "$Shift_{}".format(nextlevel), 0, 0)
        else:
          # enter on positive edge: preshift.
          ovparms = ("apply", "$Preshift_{}".format(nextlevel), 0, 0)
        evsym = Evsym('overlay', ovparms)
        evsyms.append(evsym)
        # apply overlays of next level.
        if nextlevel in self.overlays:
          for ov in self.overlays[nextlevel]:
            ovparms = ("apply", "${}".format(ov), 0, 0)
            evsym = Evsym('overlay', ovparms)
            evsyms.append(evsym)

      # Remove overlays from state.
      if from_level != 0:  # Can't remove 0.
        # remove overlays of currnet level.
        if from_level in self.overlays:
          for ov in self.overlays[from_level]:
            ovparms = ("peel", "${}".format(ov), 0, 0)
            evsym = Evsym('overlay', ovparms)
            evsyms.append(evsym)
        # last: remove shift state 'from_level'.
        ovparms = ("peel", "$Preshift_{}".format(from_level), 0, 0)
        evsym = Evsym('overlay', ovparms)
        evsyms.append(evsym)
        # also remove stable shift.
        ovparms = ("peel", "$Shift_{}".format(from_level), 0, 0)
        evsym = Evsym('overlay', ovparms)
        evsyms.append(evsym)

      # TODO: examine all clusters involved in debounced state Shift_{from_level}
      #  set all involved clusters to dpad/trigger/switches to shift to Shift_{from_level}
      proxies = []

      evspec = Evspec('-', evsyms, None)

    if evspec:
      cfgevspec = CfgEvspec(evspec)
      return cfgevspec
    return None

  @staticmethod
  def get_layer_by_name (cfgaction, layer_name):
    for lyr in cfgaction.layers:
      if lyr.name == layer_name:
        return lyr
    else:
      return None

  def preshift_binds (self, cfgaction, lyr, from_level, shiftsym, shiftstyle, bitmask):
    # Examine all clusters involved in current debounced state Shift_{from_level}
    # Set all involved clusters to dpad/trigger/switches to shift from Preshift_{from_level} to Shift_{from_level}
    proxies = []   # clusters that need to proxy into Shift_{from_level}
    for debounced_layernames in self.overlays.get(from_level, []):
      debounced_layer = self.get_layer_by_name(cfgaction, debounced_layernames)
      if debounced_layer:
        for k,v in debounced_layer.clusters.items():
          if k == "SW":
            # Switches special-case.
            for srcsym,evspec in v.items():
              if srcsym in CfgLayer.SW_SYMS:
                proxies.append(srcsym)
          elif k in CfgLayer.CLUSTERS:
            # is a cluster.
            proxies.append(k)

    for shiftsym,shiftspec in self.shifters.items():
      (style, bitmask) = shiftspec
      cfgevspec = self.shifter_bind(from_level, shiftsym, style, bitmask)
      lyr.bind_point(None, shiftsym, cfgevspec)

    proxyevspec = CfgEvspec(Evspec('+', [ Evsym('overlay', ('apply', '$Shift_{}'.format(from_level), 0, 0)) ], None))
    for proxied_clustername in proxies:
      if proxied_clustername in ('LT', 'RT'):
        lyr.bind_point(proxied_clustername, 'c', proxyevspec)
        lyr.bind_point(proxied_clustername, 'o', proxyevspec)
      elif proxied_clustername in CfgLayer.SW_SYMS:
        lyr.bind_point("SW", proxied_clustername, proxyevspec)
      else:
        lyr.bind_point(proxied_clustername, 'u', proxyevspec)
        lyr.bind_point(proxied_clustername, 'd', proxyevspec)
        lyr.bind_point(proxied_clustername, 'l', proxyevspec)
        lyr.bind_point(proxied_clustername, 'r', proxyevspec)

  def update_cfgaction (self, cfgaction):
    # Can only operate on extant layers and binds.
    # Generate the shift FSM layers.
    cfgaction.name = 'Default'
    parent_set_name = cfgaction.name
    layers = cfgaction.layers
    # Generate shifter binds for each layer in action.
    for sl in range(0, self.maxshift+1):
      # Prepare preshifts (bounce keys).
      prelayer = None
      for shiftsym,shiftspec in self.shifters.items():
        (style, bitmask) = shiftspec
        if (style == "bounce") and (sl & bitmask):
          # Prepare preshift.
          d = {
            "name": "Preshift_{}".format(sl),
            }
          prelayer = CfgLayer()
          prelayer.load(d)
          layers.append(prelayer)

      if ((sl == 0) and len(layers) < 1) or (sl > 0):
        d = {
          "name": "Shift_{}".format(sl),
          }
        # Create a new layer representing state exit transitions.
        cfglayer = CfgLayer()
        cfglayer.load(d)
        layers.append(cfglayer)
      else:
        cfglayer = layers[0]
      # Set shifter binds.
      for shiftsym,shiftspec in self.shifters.items():
        (style, bitmask) = shiftspec
        cfgevspec = self.shifter_bind(sl, shiftsym, style, bitmask)
        cfglayer.bind_point(None, shiftsym, cfgevspec)

      if prelayer:
        self.preshift_binds(cfgaction, prelayer, sl, shiftsym, style, bitmask)


class CfgMaker (object):
  r"""
name:
title:
revision:
...
settings:
...
actions:
  name:
  layers:
    name:
    <SrcSpec>: <Evsym>+
"""
  COUNTERPART = scconfig.Mapping

  def __init__ (self):
    self.name = None
    self.revision = 1
    self.desc = None
    self.author = None
    self.devtype = None
    self.timestamp = None
    self.actions = []

  def load (self, py_dict):
    for k,v in py_dict.items():
      if k == "actions":
        actions_list = py_dict["actions"]
        for action_dict in actions_list:
          action = CfgAction()
          action.load(action_dict)
          self.actions.append(action)
      elif k in ('name', 'title'):
        self.name = v
      elif k == 'revision':
        self.revision = int(v)
      elif k in ('desc', 'description'):
        self.desc = v
      elif k in ('author', 'creator'):
        self.author = v
      elif k == 'devtype':
        self.devtype = v
      elif k in ('timestamp', 'Timestamp'):
        self.timestamp = int(v)

  def export_scconfig (self, sccfg=None):
    if sccfg is None:
      sccfg = scconfig.Mapping(py_version=3)

    if self.revision is not None:
      sccfg.revision = self.revision
    if self.name is not None:
      sccfg.title = self.name
    if self.desc is not None:
      sccfg.description = self.desc
    if self.author is not None:
      sccfg.creator = self.author
    if self.devtype is not None:
      sccfg.controller_type = self.devtype
    if self.timestamp is not None:
      sccfg.timestamp = self.timestamp

    for action in list(self.actions):
      action.export_scconfig(sccfg)

    return sccfg

  def export_controller_config (self, sccfg=None):
    if sccfg is None:
      sccfg = scconfig.ControllerConfig()
    conmap = self.export_scconfig()
    sccfg.add_mapping(conmap)
    return sccfg

