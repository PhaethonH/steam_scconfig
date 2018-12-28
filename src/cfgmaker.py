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
  def __init__ (self, evtype=None, evcode=None):
    self.evtype = evtype  # EventSym physical device
    self.evcode = evcode  # EventSym code

  REGEX_SYM = """(<[A-Za-z0-9_]+>|\[[A-Za-z0-9_]+\]|\([A-Za-z0-9_]+\)|{[^}]*})"""

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
    self.actsig = actsig
    self.evsyms = evsyms
    self.evfrob = evfrob

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
    evfrobspec = str(self.evfrob)
    retval = """{}(actsig='{!s}', evsyms='{!s}', evfrob='{!s}')""".format(
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

    signal = evsyms.group(1)
    evsymspec = evsyms.group(2)
    evfrobspec = evsyms.group(4)

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
      pass
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
    bindings = [ self.export_scbind(evsym) for evsym in evspec.evsyms ]
    settings = evspec.evfrob.export_scconfig() if evspec.evfrob else None
    retval = scconfig.ActivatorFactory.make(actsig, bindings, settings)
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
    self.subparts = {}  # key <- subpart name; value <- CfgEvspec
    if py_dict:
      self.load(py_dict)

  def load (self, py_dict):
    self.mode = py_dict.get("mode", None)
    for k,v in py_dict.items():
      if k in self.SUBPARTS:
        # if string, parse as [CfgEvspec]; otherwise, take directly.
        if _stringlike(v):
          # generate list of CfgEvspec
          collate = []
          evspecs = v.split()
          for evspec in evspecs:
            cfgevspec = CfgEvspec(Evspec.parse(evspec))
            collate.append(cfgevspec)
          self.subparts[k] = collate
        else:
          self.subparts[k] = v
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
  }

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
    }


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
    self.clusters = {}

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

  def filter_bind (self, v_dict):
    retval = {}
    if 'mode' in v_dict:
      m = v_dict.get("mode", None)
      if not m in CfgClusterNode.MODES:
        m = None
      retval['mode'] = m
    pass

  def load (self, py_dict):
    if 'name' in py_dict:
      self.name = py_dict['name']
    for k,v in py_dict.items():
      if k in self.CLUSTERS:
        # TODO: filter bind
        v2 = self.filter_bind(v)
        self.spec[k] = v2

  def load (self, py_dict):
    if 'name' in py_dict:
      self.name = py_dict['name']
    for k,v in py_dict.items():
      if k in self.CLUSTERS:
        v = py_dict[k]
        #self.clusters[k] = v
        self.clusters[k] = CfgClusterFactory.make_cluster(v)

  def export_preset (self, sccfg):
    # TODO: better place to store grpid.
    grpid = 0
    preset = scconfig.Preset(py_name=self.name)
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

  def export_scconfig (self, sccfg, parent_set_name='', **overrides):
    # Generate "preset" entry.
    self.export_preset(sccfg)

    # add ActionLayer to Sccfg
    d = {
      "title": self.name,
      "legacy_set": True,
      "set_layer": 1,
      "parent_set_name": parent_set_name,
      }
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
        index = "{GENSYM_LAYER}"
      sccfg.add_action_layer(index, **d)
    else:
      d.update(overrides)
      if 'index' in d: del d['index']
      if index is None:
        index = "{GENSYM_SET}"
      sccfg.add_action_set(index, **d)
    return sccfg


class CfgAction (object):
  def __init__ (self):
    self.name = None
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
      sccfg = scconfig.Scconfig(py_version=3)

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


