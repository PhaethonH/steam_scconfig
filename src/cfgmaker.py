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

  REGEX_SYM = """(<[A-Za-z0-9_]+>|\[[A-Za-z_][A-Za-z0-9_]*\]|\([A-Za-z_][A-Za-z0-9_]*\)|{[^}]*})"""

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
  SUBPARTS = set()
  SUBPARTS = dict()
  def __init__ (self, mode=None, py_dict=None):
    self.mode = mode
    self.subparts = {}  # key <- subpart name; value <- CfgEvspec
    if py_dict:
      self.load(py_dict)

  def load (self, py_dict):
    self.mode = py_dict.get("mode", None)
    for k,v in py_dict.items():
      if k in self.SUBPARTS:
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

  def export_group (self, grp, ordering):
    for k in ordering:
      if k in self.subparts:
        realfield = self.SUBPARTS[k]
        grp.inputs[realfield] = self.export_input(k)

  def export_group_dpad (self, grp):
#    for k in [ 'u', 'd', 'l', 'r', 'c', 'o' ]:
#      if k in self.subparts:
#        realfield = self.SUBPARTS[k]
#        grp.inputs[realfield] = self.export_input(k)
    self.export_group(grp, [ 'u', 'd', 'l', 'r', 'c', 'o' ])

  def export_group_face (self, grp):
#    grp.inputs.s = self.subparts["s"].export_scconfig()
#    grp.inputs.e = self.subparts["e"].export_scconfig()
#    grp.inputs.w = self.subparts["w"].export_scconfig()
#    grp.inputs.n = self.subparts["n"].export_scconfig()
#    for k in [ 's', 'e', 'w', 'n' ]:
#      if k in self.subparts:
#        realfield = self.SUBPARTS[k]
#        grp.inputs[realfield] = self.export_input(k)
    self.export_group(grp, [ 's', 'e', 'w', 'n' ])

  def export_scconfig (self, py_dict):
    """Generate Scconfig fragment."""
    MODE_MAP = {
      "face": scconfig.GroupFourButtons.MODE,
      }

    # Effective mode.
    effmode = MODE_MAP.get(self.mode, self.mode)
    grp = scconfig.GroupFactory.make(mode=effmode)

    if self.mode == 'dpad':
      self.export_group_dpad(grp)
    elif self.mode == 'face':
      self.export_group_face(grp)

    return scconfig.toVDF(grp)

class CfgClusterPen (CfgClusterBase):
  SUBPARTS = set([
    "c", "2", "t",
    ])
  SUBPARTS = {
    "c": scconfig.GroupAbsoluteMouse.Inputs.CLICK,
    "2": scconfig.GroupAbsoluteMouse.Inputs.DOUBLETAP,
    "t": scconfig.GroupAbsoluteMouse.Inputs.TOUCH,
    }
  def __init__ (self, py_dict=None):
    super(CfgClusterPen,self).__init__('pen', py_dict)

class CfgClusterDpad (CfgClusterBase):
  SUBPARTS = set([
    "u", "d", "l", "r", "c", "o"
    ])
  SUBPARTS = {
    "u": scconfig.GroupDpad.Inputs.DPAD_NORTH,
    "d": scconfig.GroupDpad.Inputs.DPAD_SOUTH,
    "l": scconfig.GroupDpad.Inputs.DPAD_WEST,
    "r": scconfig.GroupDpad.Inputs.DPAD_EAST,
    "c": scconfig.GroupDpad.Inputs.CLICK,
    "o": scconfig.GroupDpad.Inputs.EDGE,
  }
  def __init__ (self, py_dict=None):
    super(CfgClusterDpad,self).__init__('dpad', py_dict)

class CfgClusterFace (CfgClusterBase):
  SUBPARTS = set([
    "s", "e", "w", "n",
    "a", "b", "x", "y"
    ])
  SUBPARTS = {
    "s": scconfig.GroupFourButtons.Inputs.BUTTON_A,
    "e": scconfig.GroupFourButtons.Inputs.BUTTON_B,
    "w": scconfig.GroupFourButtons.Inputs.BUTTON_X,
    "n": scconfig.GroupFourButtons.Inputs.BUTTON_Y,
  }
  def __init__ (self, py_dict=None):
    super(CfgClusterFace,self).__init__('face', py_dict)

class CfgClusterJoystick (CfgClusterBase):
  SUBPARTS = set([
    "u", "d", "l", "r", "c", "o"
    ])
  SUBPARTS = {
    "c": "click",
    "o": "edge",
  }
  def __init__ (self, py_dict=None):
    super(CfgClusterJoystick,self).__init__('js-generic', py_dict)


class CfgClusterFactory (object):
  @staticmethod
  def make_pen (py_dict): return CfgClusterPen(py_dict)
  @staticmethod
  def make_dpad (py_dict): return CfgClusterDpad(py_dict)
  @staticmethod
  def make_face (py_dict): return CfgClusterFace(py_dict)
  @staticmethod
  def make_js (py_dict): return CfgClusterJoystick(py_dict)
  @staticmethod
  def make_cluster (py_dict):
    DELEGATE = {
      "pen": CfgClusterFactory.make_pen,
      "dpad": CfgClusterFactory.make_dpad,
      "face": CfgClusterFactory.make_face,
      "js-move": CfgClusterFactory.make_js,
      "js-cam": CfgClusterFactory.make_js,
      "js-mouse": CfgClusterFactory.make_js,
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
    self.specs = {}

  CLUSTER_SYMS = set([
    "LP", "RP", "LJ", "BQ", "LT", "RT", "GY", "SW",
    "RJ"
    ])

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
    for k,v in py_dict:
      if k in self.CLUSTER_SYMS:
        # TODO: filter bind
        v2 = self.filter_bind(v)
        self.spec[k] = v2

  def export_scconfig (self, sccfg):
    pass


class CfgAction (object):
  def __init__ (self):
    self.name = None
    self.layers = []

  def load (self, py_dict):
    pass

  def export_scconfig (self, sccfg=None):
    pass


class CfgMaker (object):
  r"""
actions:
  layers:
    <SrcSpec>: <Evsym>+
"""
  def __init__ (self):
    self.name = None
    self.actions = []

  def load (self, py_dict):
    self.name = py_dict.get("name", self.name)
    actions_list = py_dict.get("actions", None)
    for action_dict in actions_list:
      action = CfgAction()
      action.load(action_dict)
      self.actions.append(action)

  def export_scconfig (self, sccfg=None):
    if sccfg is None:
      sccfg = scconfig.Scconfig()
    return


