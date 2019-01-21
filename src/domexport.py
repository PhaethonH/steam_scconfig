#!/usr/bin/env python3
# vim: ts=2 sw=2 expandtab

# Convert from a DOM-like structure to Scconfig.

import scconfig, scvdf
import re
import pprint
import sys, yaml
from collections import OrderedDict

def _stringlike (x):
  try: return x.isalpha
  except AttributeError: return False


# Helper classes
def dict_alias (propname, elideable=False):
  def getter (self):
    if elideable and (self[propname] is None):
      raise KeyError(propname)
    return self[propname]
  def setter (self, val):
    self[propname] = val
  def deleter (self):
    self[propname] = None
  return property(getter, setter, deleter)

def intOrNegOne(z):
  try:
    return int(z)
  except ValueError:
    return -1

def auto_style (x, strictness=0):
  """Determine a suitable input style for the specified srcsym(s).
strictness=0 implies a advisory/speculative first pass detemrination.
strictness=1 implies a mandatory/definitive second pass for exporting.
"""
#    print("* AUTOMODE {},{}".format(x,strictness))
  if any(['u' in x, 'd' in x, 'l' in x, 'r' in x]):
    return 'dpad'
  if any(['a' in x, 'b' in x, 'x' in x, 'y' in x]):
    return 'four_buttons'
  if any(['s' in x, 'e' in x, 'w' in x, 'n' in x]):
    return 'four_buttons'
  if strictness and any (['c' in x, 'o' in x]):
    # ambiguous, multiple styles.
    return 'joystick_move'
  if x in ('BK', 'ST', 'LB', 'RB', 'LG', 'RG', 'INF'):
    return 'switches'

  nums = [ intOrNegOne(z) for z in x ] if len(x) > 0 else [-1]
  m = max(nums)

  if 0 in nums:
    return 'radial'  # '00' - radial center/unselect
  elif any([2 in nums, 4 in nums, 7 in nums, 9 in nums, 12 in nums, 13 in nums, 16 in nums]):
    if not strictness: # ambiguously touch or radial.
      return 'touch_menu'
  elif m > 0:
    return 'radial_menu'

  if not strictness:
    return 'dpad'
  else:
    return None

class PoleDict (OrderedDict):
  def __init__ (self, pole_sym, syntheses=None):
    super(PoleDict,self).__init__()
    self["sym"] = pole_sym
    if syntheses is None:
      syntheses = []
    self["synthesis"] = syntheses     # List of EventDict
  sym = dict_alias("sym")
  synthesis = dict_alias("synthesis")

  def merge_syntheses (self, syntheses):
    r"""merge_syntheses(syntheses:list)
"""
    try:
      syntheses.keys()
    except (AttributeError,):
      # assume list-like.
      self["synthesis"].extend(syntheses)
    else:
      # assume single instance.
      one_synthesis = syntheses
      self["syntheses"].append(one_synthesis)

class ClusterDict (OrderedDict):
  def __init__ (self, cluster_sym=None, init_style=None, poles=None):
    super(ClusterDict,self).__init__()
    self["sym"] = cluster_sym
    self["modeshift"] = None
    self["style"] = init_style
    if poles is None:
      poles = PolesProxy()
    self["pole"] = poles      # List of PoleDict
#    self["settings"] = None   # Group.settings
  sym = dict_alias("sym")
  style = dict_alias("style")
  pole = dict_alias("pole")
  modeshift = dict_alias("modeshift")
  settings = dict_alias("settings", True)

  def merge_pole (self, pole, syntheses=None):
    r"""merge_pole(pole:PoleDict)
merge_pole(pole_sym:str, syntheses:list)
"""
    pole_sym = None
    try:
      pole_sym = pole["sym"]
    except (TypeError,):
      pole_sym = pole
    extant = None
    for x in self["pole"]:
      if x["sym"] == pole_sym:
        extant = x
    if extant is None:
      self["pole"].append(pole)
    else:
      for k,v in pole.items():
        if k == "synthesis":
          extant.merge_syntheses(v)
        elif k == "settings":
          extant[k].update(v)
        else:
          extant[k] = v

class SymmablesProxy (list):
  LIST_PROPERTIES = []
  DICT_PROPERTIES = []
  def __init__ (self):
    super(SymmablesProxy,self).__init__()
  def __getitem__ (self, sym):
    for x in self:
      if x.get("sym",None) == sym:
        return x
    try:
      return super(SymmablesProxy,self).__getitem__(sym)
    except (IndexError,TypeError):
      return None
  def __setitem__ (self, sym, val):
    for x in self:
      if x.get("sym",None) == sym:
        for k,v in val.items():
          if k in self.LIST_PROPERTIES:
            self[k].append(v)
          elif k in self.DICT_PROPERTIES:
            self[k].update(v)
          else:
            self[k] = v
        return
    self.append(val)

class PolesProxy (SymmablesProxy):
  LIST_PROPERTIES = [ "synthesis" ]
  DICT_PROPERTIES = [ "settings" ]
  def make (self, pole_sym, syntheses=None):
    retval = PoleDict(pole_sym, syntheses)
    self.append(retval)
    return retval

class ClustersProxy (SymmablesProxy):
  LIST_PROPERTIES = [ "pole" ]
  def make (self, cluster_sym, cluster_style=None):
    if cluster_style is None:
      cluster_style = auto_style(cluster_sym, 0)
    retval = ClusterDict(cluster_sym, cluster_style, None)
    self.append(retval)
    return retval

class LayerDict (OrderedDict):
  """Working-copy of layer dict.
"""
  def __init__ (self, name=None, clusters=None):
    super(LayerDict,self).__init__()
    self["name"] = name
    if clusters is None:
      clusters = ClustersProxy()
    self["cluster"] = clusters
    self["settings"] = None
  name = dict_alias("name")
  settings = dict_alias("settings")
  cluster = dict_alias("cluster")

  def merge_cluster (self, cluster, cluster_style=None):
    r"""merge_cluster(cluster:ClusterDict)
merge_cluster(cluster:dict)
merge_cluster(cluster_sym:str, cluster_style:str)
"""
    extant = None
    try:
      cluster.keys()
    except (AttributeError,):
      # resolve to cluster obj.
      cluster_sym = cluster
      extant = self.cluster[cluster_sym]
      if extant is None:
        extant = self.cluster.make(cluster_sym, None)
    else:
      for x in self.cluster:
        if (x.sym == cluster.sym) and (x.modeshift == cluster.modeshift):
          extant = x
          break
    if extant is None:
      self.cluster.append(cluster)
    else:
      for k,v in cluster.items():
        if k == "pole":
          for one_pole in v:
            extant.merge_pole(one_pole)
        elif k == "settings":
          extant[k].update(v)
        else:
          extant[k] = v

  def merge_cluster_pole (self, cluster_sym, cluster_style, pole):
    cluster = self.cluster[cluster_sym]
    if cluster is None:
      if cluster_style is None and pole.get("sym", None):
        cluster_style = auto_style(pole["sym"], 0)
      cluster = self.cluster.make(cluster_sym, cluster_style)
    cluster.merge_pole(pole)

  def merge_settings (self, settingsdict):
    if self.settings is None:
      self.settings = dict()
    self.settings.update(settingsdict)


class ModeshiftIntermediate (object):
  """mode_shift intermediate form."""
  def __init__ (self, grpid=-1, evgen=None):
    self.grpid = -1
    self.evgen = evgen
  def __repr__ (self):
    return "{}(grpid={!r}, evgen={!r})".format(
      self.__class__.__name__,
      self.grpid,
      self.evgen)


class ScconfigExporter (object):
  r"""
Expected format (canonical):

<name/>
<revision/>
<description/>
<author/>
<timestamp/>
<devtype/>
<aliases>
  <name/>
  <value/>
</aliases>
<action>+
  <name/>
  <layer>+
    <name/>
    <cluster>*
      <sym/>
      <modeshift/>
      <style/>
      <pole>*
        <sym/>
        <synthesis>+
          <signal/>
          <event_sym>+
            <evtype/>
            <evcode/>
          </event_sym>
          <settings/>
        </synthesis>
      </pole>
      <settings/>
    </cluster>
  </layer>
  <shiftmap>
    <shifter>
      <source_sym/>
      <style/>
      <bitmask/>
    </shifter>
    <overlay>
      <level/>
      <layer/>+
    </overlay>
  </shiftmap>
</action>


Shorthand
<action>+
  <name/>
  <layer>+
    <name/>
    <ClusterSym>
      <style/>
      <ComponentSym>
        [Evspec]
      </ComponentSym>
    </ClusterSym>
  </layer>
</action>
"""
  def __init__ (self, toplevel):
    self.actionsets = []    # List of action sets in Steam config order.
    self.actionlayers = []  # List of action layers in Steam config order.
    self.actions = []   # list of action sets/layers in Steam config order.
    self.aliases = {}
    self.rewrite_modeshift = []  # pending modeshifter rewrites.


  # Attributes: for machine-readable values.
  # CDATA: for human-presentable values.
  def get_domattr (self, dom_node, attr_name, default_value=None):
    r"""attribute of an element."""
    return dom_node.get(attr_name, default_value)

  def iter_children (self, dom_node, element_name):
    r"""iterate through multiple instances of child element.
element_name of None to iterate through all children as (element_name,element_content) pairs.
"""
    if element_name is None:
      return dom_node.items()
    else:
      probe = dom_node.get(element_name, None)
      if probe:
        if isinstance(probe, list):
          return iter(probe)
        else:
          return [ probe ]
    return []

  def get_domtext (self, dom_node, element_name, default_value=''):
    r"""CDATA of/in a child element."""
    probe = dom_node.get(element_name, default_value)
    return probe

  def get_domchild (self, dom_node, element_name):
    r"""first such named child element."""
    probe = dom_node.get(element_name, None)
    return probe



  # Map Chord symbolic to integer enum value.
  CHORD_MAP = {
    "LB": 1,
    "RB": 2,
    "LG": 3,
    "RG": 4,
    "LT": 5,
    "RT": 6,
    # TODO: LT soft, RT soft
    "LS": 9,
    "A": 10,
    "B": 11,
    "X": 12,
    "Y": 13,
    "BK": 14,
    # TODO: LP touch, RP touch
    "LP": 18,
    "RP": 19,
    }

  def export_frob (self, dom_node, settings_obj):
    r"""Convert/export settings subdict to Frob object.
{
  "specific": ...
  "toggle": ...
  "interrupt": ...
  "start": ...
  "end": ...
  "haptic": ...
  "cycle": ...
  "repeat": ...
}

<... specific=I toggle=B interrupt=B start=N end=N haptic=N cycle=B repeat=N />
"""
    retval = settings_obj

    specific = dom_node.get('specific', None)
    if specific is not None:
      if isinstance(settings_obj, scconfig.ActivatorLongPress.Settings):
        retval.long_press_time = int(specific)
      elif isinstance(settings_obj, scconfig.ActivatorDoublePress.Settings):
        retval.double_tap_time = int(specific)
      elif isinstance(settings_obj, scconfig.ActivatorChord.Settings):
        # TODO: resolve symbolic
        specific = CHORD_MAP.get(specific, specific)
        retval.chord_button = int(specific)

    toggle = None
    if toggle is None: toggle = self.get_domattr(dom_node, 'toggle')
    if toggle is not None:
      retval.toggle = bool(toggle)

    interrupt = None
    if interrupt is None: interrupt = self.get_domattr(dom_node, 'interrupt')
    if interrupt is None: interrupt = self.get_domattr(dom_node, 'interruptible')
    if interrupt is not None:
      retval.interruptible = bool(interrupt)

    start = None
    if start is None: start = self.get_domattr(dom_node, 'start')
    if start is None: start = self.get_domattr(dom_node, 'delay_start')
    if start is not None:
      retval.delay_start = int(start)

    end = None
    if end is None: end = self.get_domattr(dom_node, 'end')
    if end is None: end = self.get_domattr(dom_node, 'delay_end')
    if end is not None:
      retval.delay_end = int(end)

    haptic = None
    if haptic is None: haptic = self.get_domattr(dom_node, "haptic")
    if haptic is None: haptic = self.get_domattr(dom_node, "haptic_intensity")
    if haptic is not None:
      retval.haptic_intensity = int(haptic)

    cycle = None
    if cycle is None: cycle = self.get_domattr(dom_node, 'cycle')
    if cycle is not None:
      retval.cycle = bool(cycle)

    repeat = None
    if repeat is None: repeat = self.get_domattr(dom_node, "repeat")
    if repeat is None: repeat = self.get_domattr(dom_node, "repeat_rate")
    if repeat is not None:
      repeat_value = int(repeat)
      if repeat_value > 0:
        retval.hold_repeats = True
        retval.repeat_rate = int(repeat)
      else:
        retval.hold_repeats = False

    return retval

  def translate_event (self, dom_node):
    r"""Convert/export event subdict to Evgen object.
{
  "evtype": ...
  "evcode": ...
}
"""
#    print("translating event {}".format(dom_node))
    evtype = self.get_domattr(dom_node, 'evtype')
    evcode = self.get_domattr(dom_node, 'evcode')
    if evtype in ('keyboard',):
      return scconfig.EvgenFactory.make_keystroke(evcode)
    elif evtype in ('gamepad',):
      return scconfig.EvgenFactory.make_gamepad(evcode)
    elif evtype in ('mouse',):
      return scconfig.EvgenFactory.make_mouseswitch(evcode)
    elif evtype in ("mode_shift", "modeshift"):
      (cluster_sym, tokenid) = evcode
      tokenid = int(tokenid)
      semimodeshift = self.rewrite_modeshift[tokenid]
      grpid = semimodeshift.grpid   # -1=placeholder (group not yet exported).
      inpsrc = self.GRPSRC_MAP.get(cluster_sym, cluster_sym)
      retval = scconfig.EvgenFactory.make_modeshift(inpsrc, grpid)
      semimodeshift.evgen = retval  # save placeholder for future group export.
      return retval
      #return scconfig.EvgenFactory.make_modeshift("joystick", -1)
    elif evtype in ('host',):
      host_evcode = " ".join(evcode)
      return scconfig.EvgenFactory.make_hostcall(host_evcode)
    elif evtype in ('overlay',):
      # TODO: resolve overlay by name.
      names = [ a.get('name',None) for a in self.actions ]
      (actcmd, actname) = evcode
      try:
        # 1-based indexing.
        actid = names.index(actname) + 1
      except ValueError:
        # Not found.  Incomplete maps.  Do not transit.
        return scconfig.EvgenFactory.make_empty()
      else:
        return scconfig.EvgenFactory.make_overlay(actcmd, str(actid), "0", "0")
      #return scconfig.EvgenFactory.make_overlay("apply", "-1", '0', '0')
    elif evtype in ('empty',):
      return scconfig.EvgenFactory.make_empty()
    return None

  def export_synthesis (self, dom_node, inputobj):
    r"""Convert/export synthesis subdict to Input object.
{
  "actsig": ...
  "label": ...
  "icon": ...
  "event": [
    `event`,
    ...
  ]
  "frob": `frob`
}

"""
    ACTMAP = {
      'full': scconfig.ActivatorFullPress,
      'long': scconfig.ActivatorLongPress,
      'double': scconfig.ActivatorDoublePress,
      'start': scconfig.ActivatorStartPress,
      'release': scconfig.ActivatorRelease,
      'chord': scconfig.ActivatorChord,
      None: scconfig.ActivatorFullPress,
    }
    actsig = self.get_domattr(dom_node, "actsig")
    actclass = ACTMAP[actsig]
    signame = actclass.signal

    bindings = []
    settings = actclass.Settings()
    label = self.get_domtext(dom_node, "label")
    iconinfo = None
    evgenlist = []
    for evdesc in self.iter_children(dom_node, "event"):
      # label and icon copied for each entry in bindings.
      evgen = self.translate_event(evdesc)
      b = scconfig.Binding(evgen, label, iconinfo)
      bindings.append(b)
    for frobdesc in self.iter_children(dom_node, "settings"):
      self.export_frob(frobdesc, settings)
      break
    else:
      for frobdesc in self.iter_children(dom_node, "frob"):
        self.export_frob(frobdesc, settings)
        break
#    act = scconfig.ActivatorFactory.make(signame, bindings, settings)
    act = inputobj.add_activator(signame, py_bindings=bindings, py_settings=settings)
    return True

  FILTER_SYMS = {
    scconfig.GroupAbsoluteMouse.MODE: {
      'c': scconfig.GroupAbsoluteMouse.Inputs.CLICK,
      '2': scconfig.GroupAbsoluteMouse.Inputs.DOUBLETAP,
      't': scconfig.GroupAbsoluteMouse.Inputs.TOUCH,
    },
    scconfig.GroupDpad.MODE: {
      'u': scconfig.GroupDpad.Inputs.DPAD_NORTH,
      'l': scconfig.GroupDpad.Inputs.DPAD_WEST,
      'r': scconfig.GroupDpad.Inputs.DPAD_EAST,
      'd': scconfig.GroupDpad.Inputs.DPAD_SOUTH,
      'c': scconfig.GroupDpad.Inputs.CLICK,
      'o': scconfig.GroupDpad.Inputs.EDGE,
    },
    scconfig.GroupFourButtons.MODE: {
      'n': scconfig.GroupFourButtons.Inputs.BUTTON_Y,
      'e': scconfig.GroupFourButtons.Inputs.BUTTON_B,
      'w': scconfig.GroupFourButtons.Inputs.BUTTON_X,
      's': scconfig.GroupFourButtons.Inputs.BUTTON_A,
      'y': scconfig.GroupFourButtons.Inputs.BUTTON_Y,
      'x': scconfig.GroupFourButtons.Inputs.BUTTON_X,
      'b': scconfig.GroupFourButtons.Inputs.BUTTON_B,
      'a': scconfig.GroupFourButtons.Inputs.BUTTON_A,
      'Y': scconfig.GroupFourButtons.Inputs.BUTTON_Y,
      'X': scconfig.GroupFourButtons.Inputs.BUTTON_X,
      'B': scconfig.GroupFourButtons.Inputs.BUTTON_B,
      'A': scconfig.GroupFourButtons.Inputs.BUTTON_A,
    },
    scconfig.GroupJoystickCamera.MODE: {
      'c': scconfig.GroupJoystickCamera.Inputs.CLICK,
    },
    scconfig.GroupJoystickMove.MODE: {
      'c': scconfig.GroupJoystickMove.Inputs.CLICK,
      'o': scconfig.GroupJoystickMove.Inputs.EDGE,
    },
    scconfig.GroupJoystickMouse.MODE: {
      'c': scconfig.GroupJoystickMouse.Inputs.CLICK,
      'o': scconfig.GroupJoystickMouse.Inputs.EDGE,
    },
    scconfig.GroupMouseJoystick.MODE: {
      'c': scconfig.GroupMouseJoystick.Inputs.CLICK,
    },
    scconfig.GroupMouseRegion.MODE: {
      'c': scconfig.GroupMouseRegion.Inputs.CLICK,
      'o': scconfig.GroupMouseRegion.Inputs.EDGE,
      't': scconfig.GroupMouseRegion.Inputs.EDGE,
    },
    scconfig.GroupRadialMenu.MODE: dict([
      ('c', scconfig.GroupRadialMenu.Inputs.CLICK),
      ] +
      # touch_menu_button_%02d
      [ ("{:02d}".format(x), "touch_menu_button_{:d}".format(x))  for x in range(0, 21) ]
    ),
    scconfig.GroupScrollwheel.MODE: {
      'c': scconfig.GroupScrollwheel.Inputs.CLICK,
      'u': scconfig.GroupScrollwheel.Inputs.SCROLL_CLOCKWISE,
      'd': scconfig.GroupScrollwheel.Inputs.SCROLL_COUNTERCLOCKWISE,
    },
    scconfig.GroupSingleButton.MODE: {
      'c': scconfig.GroupSingleButton.Inputs.CLICK,
      't': scconfig.GroupSingleButton.Inputs.TOUCH,
    },
    scconfig.GroupSwitches.MODE: {
      'BK': scconfig.GroupSwitches.Inputs.BUTTON_MENU,
      'ST': scconfig.GroupSwitches.Inputs.BUTTON_ESCAPE,
      'LB': scconfig.GroupSwitches.Inputs.LEFT_BUMPER,
      'RB': scconfig.GroupSwitches.Inputs.RIGHT_BUMPER,
      'LG': scconfig.GroupSwitches.Inputs.BUTTON_BACK_LEFT,
      'RG': scconfig.GroupSwitches.Inputs.BUTTON_BACK_RIGHT,
      'INF': scconfig.GroupSwitches.Inputs.ALWAYS_ON,

      '1': scconfig.GroupSwitches.Inputs.BUTTON_MENU,
      '2': scconfig.GroupSwitches.Inputs.LEFT_BUMPER,
      '3': scconfig.GroupSwitches.Inputs.BUTTON_BACK_LEFT,
      '4': scconfig.GroupSwitches.Inputs.BUTTON_ESCAPE,
      '5': scconfig.GroupSwitches.Inputs.RIGHT_BUMPER,
      '6': scconfig.GroupSwitches.Inputs.BUTTON_BACK_RIGHT,
    },
    scconfig.GroupTouchMenu.MODE: dict(
      # touch_menu_button_%02d
      [ ("{:02d}".format(x), "touch_menu_button_{:d}".format(x))  for x in range(1, 17) ]
    ),
    scconfig.GroupTrigger.MODE: {
      'c': scconfig.GroupTrigger.Inputs.CLICK,
      'o': scconfig.GroupTrigger.Inputs.EDGE,
    },
  }


  RE_ACTSIG = r"([:=_&+-])"
  RE_EVENTS = r"(<[A-Za-z0-9_]*>|\[[A-Za-z0-9_]*\]|\([A-Za-z0-9]*\)|{[^}]*})"
  RE_FROBS = r"(\||\%|\^|~[0-9]?|:[0-9]+|/[0-9]+|@[0-9]+,[0-9]+)"
  RE_LABEL = r"(#[^#]*)"
  RE_SYM = r"{}?({}+)({}*)({}*)".format(RE_ACTSIG, RE_EVENTS, RE_FROBS, RE_LABEL)
  RE_ALIAS = r"\$(\{[^}]*\}|[A-Za-z_][A-Za-z0-9_]*)"

  def expand_synthesis (self, evspec):
    r"""Expand shorthand synthesis into canonical synthesis subdict.

Keypresses indicated by angle brackets: <A>, <Up_Arrow>, <Left_Shift>, <Escape>
Gamepad buttons indicaed by parenthess: (A), (DUP), (LB), (ST)
Mouse buttons are indicated by brackets: [1], [u]
Host calls and other specials use braces, arguments separated with commas:
  {overlay,apply,Default}, {mouse_position,16384,16384,0}

Trailing characters specify behavior modifiers that map to Settings:
  %   Toggle on
  ^   Interruptible on
  |   Cycle on
  /N  Repeat on, with interval set to N [milliseconds] (0 to force off)
  ~H  Haptic intensity, 0=off, 1=low, 2=medium, 3=high
  @S,E  Delay start to S, Delay end by E [milliseconds]
  :X  activator-specific setting:
        Long_Press: affects Long Press Time [milliseconds]
        Double_Press: affect Double Press Time [milliseconds]
        chord: specifies the chorded button [enumeration]

A '#' starts label segment.  Additional instances of '#' turn into spaces.
e.g. "#FirstButton" => label="FirstButton",
     "#First#Button" => label="First Button",
     "#First###Button" => label="First   Button",
"""
    # TODO: rename variables to more reasonable ones.

    if evspec is None:
      return None

    # resolve aliases.
    re_alias = re.compile(self.RE_ALIAS)
    autolabel = False
    while '$' in evspec:
      subst = re_alias.search(evspec).group(1)
      if subst[0] == '{':
        k = subst[1:-1]
        autolabel = False
      else:
        k = subst
        autolabel = k
      v = self.aliases.get(k, '')
      evspec = re_alias.sub(v, evspec)
    if autolabel:  # Outermost evaluation is final label (may be False).
      evspec = "{}#{}".format(evspec, autolabel)

    re_actsig = re.compile(self.RE_ACTSIG)
    re_events = re.compile(self.RE_EVENTS)
    re_frobs = re.compile(self.RE_FROBS)
    re_label = re.compile(self.RE_LABEL)
    re_sym = re.compile(self.RE_SYM)

    matches = re_sym.findall(evspec)[0]
    sigspec = matches[0]
    evspecs = matches[1]
    frobspec = matches[3]
    labelspec = matches[5]

    # Extract signal fragment.
    SIGMAP = {
      '': 'full',
      '_': 'long',
      ':': 'double',
      '=': 'double',
      '+': 'start',
      '-': 'release',
      '&': 'chord',
      }
    actsig = SIGMAP.get(sigspec, 'Full_Press')

    # Extract event fragment.
    matches = re_events.findall(evspecs)
    evgenlist = []
    for evspec in matches:
      if evspec[0] == '<' and evspec[-1] == '>':
        evtype = 'keyboard'
        evcode = evspec[1:-1]
      elif evspec[0] == '(' and evspec[-1] == ')':
        evtype = 'gamepad'
        evcode = evspec[1:-1]
      elif evspec[0] == '[' and evspec[-1] == ']':
        evtype = 'mouse'
        evcode = evspec[1:-1]
      elif evspec[0] == '{' and evspec[-1] == '}':
        evcode = evspec[1:-1]
        if ',' in evcode:
          evcode = evcode.split(',')
        if evcode[0] == 'overlay':
          evtype = 'overlay'
          evcode = evcode[1:]
        elif evcode[0] in ("modeshift", "mode_shift"):
          evtype = 'mode_shift'
          evcode = evcode[1:]
        else:
          evtype = 'host'
      else:
        evcode = evspec[:]
      if (evcode is None) or (evcode == ''):
        evtype = 'empty'
        evcode = ''
      d = {
        "evtype": evtype,
        "evcode": evcode,
        }
      ev = d
      evgenlist.append(ev)

    # Extract frob fragment.
    frobdef = {}
    matches = re_frobs.findall(frobspec)
    for frobmark in matches:
      frobtype = frobmark[0]
      if frobtype in ('%','t'):
        frobdef['toggle'] = True
      elif frobtype in ('^', 'i'):
        frobdef['interrupt'] = True
      elif frobtype in ('|', 'c'):
        frobdef['cycle'] = True
      elif frobtype in ('@', 'd'):
        start,end = frobmark[1:].split(',')
        frobdef['delay_start'] = int(start)
        frobdef['delay_end'] = int(end)
      elif frobtype in ('~', 'h'):
        frobdef['haptic'] = int(frobmark[1:])
      elif frobtype in (':', 's'):
        frobdef['specific'] = int(frobmark[1:])
      elif frobtype in ('/', 'r'):
        frobdef['repeat'] = int(frobmark[1:])
      else:
        pass
    if not frobdef:
      frobdef = None

    # Extract label fragment.
    labelparts = None
    matches = re_label.findall(labelspec)
    for labelfragment in matches:
      if labelparts is None:
        labelparts = []
      labelparts.append(labelfragment[1:])
    if labelparts is not None:
      label = " ".join(labelparts)
    else:
      label = None

    # Normalize to synthesis dict.
    d = {
      "actsig": actsig,
      "event": evgenlist,
      "settings": frobdef,
      "label": label,
      "iconinfo": None,
      }
    return d


  def expand_shorthand_syntheses (self, evlistspec):
    r"""Convert space-separated shorthand syntheses into list of synthesis subdict.

e.g. "<A> <B>" =>
[ { "evtype": "keystroke", "evcode": "A" },
  { "evtype": "keystroke", "evcode": 'B" }
  ]
"""
    if ' ' in evlistspec:
      evspecs = evlistspec.split()
    else:
      evspecs = [ evlistspec ]
    retval = []
    for evspec in evspecs:
      evsynth = self.expand_synthesis(evspec)
      retval.append(evsynth)
    return retval


  def export_pole (self, dom_node, groupobj):
    # Maps to scconfig.ControllerInput
    r"""Convert/export pole subdict to Input object attached to Group.
{
  "sym": ...
  "synthesis": [
    `synthesis`,
    ...
  ]
}
"""
    partsym = self.get_domattr(dom_node, "sym")

# Filter sym based on groupobj type.
    partsym = self.FILTER_SYMS.get(groupobj.MODE, {}).get(partsym, partsym)

    inputobj = scconfig.ControllerInput(partsym)
    for syndesc in self.iter_children(dom_node, "synthesis"):
      self.export_synthesis(syndesc, inputobj)
    groupobj.add_input(inputobj)
    return True

  def export_settings (self, dom_node, settingsobj):
    """Generalized Settings export."""
    for k in sorted(settingsobj._CONSTRAINTS.keys()):
      v = self.get_domattr(dom_node, k)
      if v is not None:
        setattr(settingsobj, k, v)
    return settingsobj


  UNIQUE_POLE_SYMS = {
    "BK": ("SW", "BK"),
    "ST": ("SW", "ST"),
    "LB": ("SW", "LB"),
    "RB": ("SW", "RB"),
    "LG": ("SW", "LG"),
    "RG": ("SW", "RG"),
    "INF": ("SW", "INF"),
    "LS": ("LJ", "c"),
    "RS": ("RJ", "c"),
    }

  def normalize_cluster (self, dom_node):
    """Resolve shorthand notations for poles.

Returns a cluster DOM which is a copy of the original but with shorthand notation expanded/resolved.
"""
#    print("normalizing cluster {}".format(dom_node))
    extcluster = ClusterDict()

    # Shorthand entire joystick.
    if dom_node in ("LJ", "(LJ)"):
      extcluster.style = "jsmove"
      return extcluster
    if dom_node in ("RJ", "(RJ)"):
      extcluster.style = "jscam"
      return extcluster

    scanned_syms = []
    style = None
    # First pass, definite style.
    for k,v in self.iter_children(dom_node, None):
      if k == 'style':
        style = self.GRPSTYLE_MAP.get(v, v)
        extcluster.style = style
    # Second pass, collect.
    for k,v in self.iter_children(dom_node, None):
      pole_sym = None
      if k in self.UNIQUE_POLE_SYMS:
        cluster_sym, pole_sym = self.UNIQUE_POLE_SYMS[k]
      elif len(k) == 1:
        pole_sym = k
      elif k in self.FILTER_SYMS.get(style, []):
        pole_sym = self.FILTER_SYMS[style][k]
      elif intOrNegOne(k) >= 0:
        # unique to radial/touchmenu.
        pole_sym = k
      if pole_sym:
        if _stringlike(v):    # Parse from string.
          syntheses = self.expand_shorthand_syntheses(v)
        elif v:       # presume list of Synthesis
          syntheses = v
        # Merge or create poles with the syntheses.
        if syntheses is not None:
          pole = extcluster.pole[pole_sym] or extcluster.pole.make(pole_sym)
          pole.merge_syntheses(syntheses)
          scanned_syms.append(pole_sym)
      else:
        if k == 'pole':
          for pole in v:
            extcluster.merge_pole(pole)
        else:
          extcluster[k] = v
    # Determine style.
    if not 'style' in extcluster:
      style = auto_style(scanned_syms)
      extcluster.style = style

#    print("normalized cluster ="); pprint.pprint(extcluster)
    return extcluster

  def export_cluster (self, dom_node, groupobj):
    # Maps to scconfig.Group
    r"""Convert/export cluster subdict as Group.
{
  "style": ...
  "pole": [
    `pole`,
    ...
  ]
}


shorthand
{
  "style": ...
  <ComponentSym>: [
    `synthesis`,
    ]
  <ComponentSym>: <EvgenSpec>
"""
#    print("exporting cluster"); pprint.pprint(dom_node)
    clusterstyle = self.get_domattr(dom_node, "style")
    for polespec in self.iter_children(dom_node, "pole"):
#      print("export pole {}/{} to groupobj {}".format(clusterstyle, polespec, groupobj))
      self.export_pole(polespec, groupobj)
    for ss in self.iter_children(dom_node, "settings"):
      self.export_settings(ss, groupobj.settings)
      break  # only handle the first.
#    for pole in self.iter_children(dom_node, "pole"):
#      self.export_pole(pole, groupobj)
    return True

  # map cluster name to groupsrc name.
  GRPSRC_MAP = {
    "SW": "switch",
    "BQ": "button_diamond",
    "LP": "left_trackpad",
    "RP": "right_trackpad",
    "LJ": "joystick",
    "LT": "left_trigger",
    "RT": "right_trigger",
    "GY": "gyro",
    "DP": "dpad",
    "RJ": "right_joystick",
  }
  GRPSTYLE_MAP = {
    'pen': 'absolute_mouse',
    'face': 'four_buttons',
    'jsmove': 'joystick_move',
    'jscam': 'joystick_camera',
    'jsmouse': 'joystick_mouse',
    'mousejs': 'mouse_joystick',
    'radial': 'radial_menu',
    'region': 'mouse_region',
    'scroll': 'scrollwheel',
    'single': 'single_button',
    'menu': 'touch_menu',
    'switch': 'switches',
    'trigger': 'trigger',
    }
  MODESHIFT_MAP = {
    'BK': "button_escape",
    'ST': "button_menu",
    'LB': "left_bumper",
    'RB': "right_bumper",
    'LG': "button_back_left",
    'RG': "button_back_right",
    'LT': "left_trigger",   'LTf': "left_trigger",   'LT.c': "left_trigger",
    'RT': "right_trigger",  'RTf': "right_trigger",  'RT.c': "right_trigger",
    'LT.o': "left_trigger_threshold",   'LTs': "left_trigger_threshold",
    'RT.o': "right_trigger_threshold",  'RTs': "right_trigger_threshold",
    'LP': "left_click",
    'RP': "right_click",
    'LS': "left_stick_click",
    'A': "button_a",  'a': "button_a",
    'B': "button_b",  'b': "button_b",
    'X': "button_x",  'x': "button_x",
    'Y': "button_y",  'y': "button_y",
    }

  def normalize_layer (self, dom_node, conmap, layeridx=0):
    r"""Resolve shorthands in a layer subdict.
Returns a substitute layer which is copy of the original (dom_node), but with shorthand notations for/in clusters resolved.
"""
    paralayer = LayerDict(self.get_domtext(dom_node, "name"))

    # Scan shorthands.
    for k,v in self.iter_children(dom_node, None):
      base_sym, modeshift_sym = k, None
      cluster_sym = pole_sym = None
      if '&' in k:
        # modeshifted.
        base_sym, modeshift_sym = k.split('&')
      if base_sym in self.GRPSRC_MAP:
        # short-hand for cluster.
        cluster_sym = base_sym
        normcluster = self.normalize_cluster(v)
        normcluster.sym = base_sym
        if base_sym in ("RT", "LT"):
          normcluster.style = "trigger"
        modeshift_sym = self.MODESHIFT_MAP.get(modeshift_sym, modeshift_sym)
        normcluster.modeshift = modeshift_sym
        paralayer.merge_cluster(normcluster, normcluster.get("style",None))

        # Hook mode_shift command.
        if modeshift_sym:
          tokenid = len(self.rewrite_modeshift)
          semimodeshift = ModeshiftIntermediate()
          self.rewrite_modeshift.append(semimodeshift)
          normcluster["will_modeshift"] = semimodeshift

          shorthand = "{{mode_shift,{},{}}}".format(cluster_sym, tokenid)
          syntheses = self.expand_shorthand_syntheses(shorthand)
          modeshift_pole = PoleDict(normcluster.modeshift, syntheses)
          paralayer.merge_cluster_pole("SW", "switches", modeshift_pole)
        continue  # bypass cluster.pole case.

      (cluster_sym, pole_sym) = self.normalize_srcsym(base_sym)

      if cluster_sym and pole_sym:  # key in the form "cluster.pole".
        if _stringlike(v):
          syntheses = self.expand_shorthand_syntheses(v)
        else: syntheses = v
        pole = PoleDict(pole_sym, syntheses)
        paralayer.merge_cluster_pole(cluster_sym, None, pole)
      else:   # Not recognized as shorthand; assume longhand.
        # copy verbatim.
        if base_sym == 'cluster':
          vv = [ self.normalize_cluster(cl) for cl in v ]
          for cluster in vv:
            paralayer.merge_cluster(cluster)
        else:
          paralayer[base_sym] = v
    # auto-style from all poles.
    for cluster in paralayer.cluster:
      if not cluster.style:
        polelist = [ x.sym for x in cluster.pole ]
        autostyle = auto_style(polelist)
        cluster.style = autostyle
#        print(" fallback autostyle {} => {}".format(polelist, autostyle))
#    print("normalized layer "); pprint.pprint(dom_node); print(" =>"); pprint.pprint(paralayer)
#    print("normalized layer ="); pprint.pprint(paralayer)
    return paralayer

  def export_layer (self, dom_node, conmap, layeridx=0, parent_name=None):
    r"""Convert/export layer subdict to ActionLayer, Preset, Groups.
{
  "name": ...
  "cluster": [
    `cluster`,
    ...
  ]
}
"""
#    print("* EXPORT LAYER"); pprint.pprint(dom_node)
    layer_name = self.get_domattr(dom_node, "name")
    presetid = len(conmap.presets)
    grpid = len(conmap.groups)
    # build Preset
    if presetid == 0:
      presetkey = 'Default'
    else:
      presetkey = "Preset_{:07d}".format(presetid + 1000000)
    presetobj = conmap.add_preset(presetid, presetkey)

    def export_group (clusterspec, grpstyle, clustersym, active, modeshift):
      grpsrc = self.GRPSRC_MAP.get(clustersym, clustersym)
      grp = None
      # Find existing.
      for grpid,gsbval in presetobj.gsb.items():
        if gsbval.groupsrc == grpsrc:
          for grpiter in conmap.groups:
            if grpiter.index == grpid:
              grp = grpiter
              break
      if not grp:  # Create.
        grpsrc = self.GRPSRC_MAP.get(clustersym, clustersym)
        grpid = len(conmap.groups)
        # map shorthand style name to full group style.
        grpstyle = self.GRPSTYLE_MAP.get(grpstyle, grpstyle)
        grp = conmap.add_group(grpid, grpstyle) 
        presetobj.add_gsb(grpid, grpsrc, active, modeshift)

        if 'will_modeshift' in clusterspec:
          semimodeshift = clusterspec["will_modeshift"]
          semimodeshift.grpid = grpid  # for any future mode_shift.
          if semimodeshift.evgen:
            # Already instantiated with placeholder value.
            semimodeshift.evgen.group_id = grpid

#      print("EXPORT GROUP {}".format(clustersym))
      self.export_cluster(clusterspec, grp)

    for clusterspec in self.iter_children(dom_node, "cluster"):
      grpstyle = self.get_domattr(clusterspec, "style")
      clustersym = self.get_domattr(clusterspec, "sym")
      active = True
      modeshifter = self.get_domattr(clusterspec, "modeshift")
      modeshift = (modeshifter != None)

      export_group(clusterspec, grpstyle, clustersym, active, modeshift)

    # add to action_layers[] or actions[]
    if layeridx > 0:
      conmap.add_action_layer(presetkey, layer_name, parent_set_name=parent_name)
    else:
      if (layer_name is None) or (len(conmap.actions) == 0):
        layer_name = 'Default'
      conmap.add_action_set(presetkey, layer_name)
    return layer_name

  def normalize_srcsym (self, srcsymspec, implied_cluser=None):
    if '.' in srcsymspec:
      cluster_sym, pole_sym = srcsymspec.split('.', 1)
    elif srcsymspec in self.UNIQUE_POLE_SYMS:
      cluster_sym, pole_sym = self.UNIQUE_POLE_SYMS[srcsymspec]
    else:
      cluster_sym, pole_sym = None, srcsymspec
    return (cluster_sym, pole_sym)

  # tuple( list-of-fixed-kv, list-of-advbinddef-keys )
  ADVANCING_TEMPLATE = {
    "RT": ( [("style","trigger")], "co" ),
    "LT": ( [("style","trigger")], "co" ),
    "DP": ( [("style","dpad")], "udlr" ),
    "BQ": ( [("style","four_buttons")], "abxy" ),
    "LJ": ( [("style","dpad")], "udlrc" ),
    "RJ": ( [("style","dpad")], "udlrc" ),
    "LP": ( [("style","single_button")], "tc" ),
    "RP": ( [("style","single_button")], "tc" ),
    "SW": ( [("style","switches")], ["BK","ST","LB","RB","LG","RG"] ),
    }

  def prepare_shifters (self, dom_node, conmap):
    r"""
Prepare an alternate list of action layers with shifters incorporated.
Existing layers may have to be modified (e.g. unbinding conflicted keys).
"""
    extlayers = []   # Extended layers.

    # Copy extant layers.
    lyrid = 0
    for lyr in self.iter_children(dom_node, "layer"):
      postlyr = self.normalize_layer(lyr, conmap, lyrid)
      extlayers.append(postlyr)

    maxshift = 0
    overlays = {}   # map int => list of overlay names
    shifters = {}   # map srcsym => bitmask:int
    hermits = {}    # map srcsym => evlist
    extents = {}    # shifter-extenders.
    sanity = None   # Sanity bind.
    sanitizeable = [] # List of layer names involved with sanitization.

    # Collect shifters info.
    for shiftmap in self.iter_children(dom_node, "shiftmap"):

      for shifter in self.iter_children(shiftmap, "shifter"):
        # Expect instances of <shifter srcsym="..." bitmask="..."/>
        srcsym = self.get_domattr(shifter, "srcsym")
        if srcsym is not None:
          shiftcmd = self.get_domattr(shifter, "cmd")
          if shiftcmd is None:
            shiftcmd = "hold"
          bitmask = self.get_domattr(shifter, "bitmask")
          bitmask = int(bitmask)
          maxshift |= bitmask
          shifters[srcsym] = bitmask
        else:
          for srcsym, shiftaction in self.iter_children(shifter, None):
            parts = shiftaction.split()
            shiftcmd = parts[0]
            bitmaskstr = parts[1] if len(parts) > 1 else 0
            bitmask = int(bitmaskstr)
            maxshift |= bitmask
            shifters[srcsym] = bitmask

      for overlay in self.iter_children(shiftmap, "overlay"):
        level = self.get_domattr(overlay, "level")
        if level is not None:
          # "overlay": [ { "level": "N", "layer": [ ..., ... ] } ]
          level = int(level)
          accum = []
          for layername in self.iter_children(overlay, "layer"):
            accum.append(layername)
            sanitizeable.append(layername)
          overlays[level] = accum
        else:
          # "overlay": { "N": [ ... ] }
          for levelstr, layernames in self.iter_children(overlay, None):
            level = int(levelstr)
            accum = []
            for layername in layernames:
              accum.append(layername)
              sanitizeable.append(layername)
            overlays[level] = accum

      for hermit in self.iter_children(shiftmap, "hermit"):
        srcsym = self.get_domattr(hermit, "srcsym")
        if srcsym is not None:
          # "hermit": [ { "srcsym": "Y", "synthesis": [ ...  } ]
          # longhand form.
          pass
        else:
          # "hermit": { "Y": "..." }
          # shorthand form.
          for lvl, evlistspec in self.iter_children(hermit, None):
            hermits[lvl] = evlistspec

      for extend in self.iter_children(shiftmap, "extend"):
        srcsym = self.get_domattr(hermit, "srcsym")
        if srcsym is not None:
          # "extend": [ { "srcsym": "Y", "synthesis": [ ...  } ]
          # longhand form.
          pass
        else:
          # "extend": { "Y": "..." }
          # shorthand form.
          for lvl, evlistspec in self.iter_children(extend, None):
            extents[lvl] = evlistspec

      sanity = self.get_domattr(shiftmap, "sanity")
#      print("PEND SANITY {}".format(sanity))

      break

    def make_shifter_bind (from_level, bitmask, overlays, hermits, extents):
      # helper function
      pending = []
      next_level = from_level ^ bitmask

      if from_level in extents:
        extensions = extents[from_level]
        for extspec in extensions:
          pending.append(extspec)
        pending.append(" ")

      # Apply next level.
      if (next_level & bitmask) == bitmask:
        # on key press.
        pending.append("+")

        if next_level != 0:   # can't apply 0 - achieved by removing all layers.
          if next_level in hermits:
#            print("preshift for {}".format(next_level))
            pending.append("{{overlay,apply,Preshift_{}}}".format(next_level))
          else:
#            print("forego to shift for {}".format(next_level))

            overlaying = "".join([ "{{overlay,apply,{}}}".format(ov)  for ov in overlays.get(next_level,[]) ])
            if overlaying:
              pending.append(overlaying)
              pending.append("#+overlays({})".format(next_level))
              pending.append(" +")

            pending.append("{{overlay,apply,Shift_{}}}".format(next_level))
#          pending.append("#+Preshift_{}".format(next_level))
      else:
        # on key release.
        pending.append("-")

        if next_level in overlays:
          overlaying = [ "{{overlay,apply,{}}}".format(ov) for ov in overlays[next_level] ]
          overlaying = "".join(overlaying)
          if overlaying:
            pending.append(overlaying)
            pending.append("#-overlays({})".format(next_level))
            pending.append(" -")

        if next_level != 0:   # can't apply 0 - achieved by removing all layers.
          pending.append("{{overlay,apply,Shift_{}}}".format(next_level))
#          pending.append("#+Shift_{}".format(next_level))
      # Remove current level.
      if from_level != 0:   # can't remove 0 (base).
        if from_level in overlays:
          overlaying = [ "{{overlay,peel,{}}}".format(ov) for ov in overlays[from_level] ]
          overlaying = "".join(overlaying)
          pending.append(overlaying)
        if from_level in hermits:
          pending.append("{{overlay,peel,Preshift_{}}}".format(from_level))
#        pending.append("#-Preshift_{}".format(next_level))
        pending.append("{{overlay,peel,Shift_{}}}".format(from_level))
#        pending.append("#-Shift_{}".format(next_level))
      pending.append("#goto#{}".format(next_level))
      retval = "".join(pending)
#      print("made shifter bind #{} {!r}".format(from_level, retval))
      return retval

    baselayer = extlayers[0]
    # TODO: handle no-layers case.
    # Set up shift level 0
    for shiftsym,bitmask in shifters.items():
      shiftspec = make_shifter_bind(0, bitmask, overlays, hermits, extents)
      cl,po = self.normalize_srcsym(shiftsym)
      autostyle = auto_style(po)
      syntheses = self.expand_shorthand_syntheses(shiftspec)
      pole = PoleDict(po, syntheses)
      baselayer.merge_cluster_pole(cl, autostyle, pole)

    # Preshift: find all clusters involved with shift.
    for n in range(1, maxshift+1):
      # for shift level n...
      preclusters = set()   # Set of clusters involved with this preshifter.
      for overlayname in overlays.get(n, []):
        for lyr in extlayers:
          if lyr.get("name", None) == overlayname:
            for clusterdef in lyr.get("cluster", []):
              preclusters.add(clusterdef["sym"])

      # bind shiftkeys for preshift n; set preclusters to advance to shift n.
      preshiftlayer = LayerDict("Preshift_{}".format(n))
      for shiftsym,bitmask in shifters.items():
        cl,po = self.normalize_srcsym(shiftsym,None)
        autostyle = auto_style(po)
        shifterspec = make_shifter_bind(n, bitmask, overlays, hermits, extents)
        syntheses = self.expand_shorthand_syntheses(shifterspec)
        if (n in hermits) and (n & bitmask) == bitmask:
          hermitspec = "{}#hermit({})".format(hermits[n], n)
          syntheses.extend(self.expand_shorthand_syntheses(hermitspec))
        pole = PoleDict(po, syntheses)
        preshiftlayer.merge_cluster_pole(cl, autostyle, pole)

      # Generate Preshift's advancer binds for involve clusters.
      advbinddef = [
        {
          "actsig": 'start',
          # apply the new shift state.
          "event": [ {
                      "evtype": "overlay",
                      "evcode": ("apply", "Shift_{}".format(n)),
                     } ],
          "label": "advance Shift_{}".format(n),
        },
        {
          "actsig": 'start',
          # apply all the new overlays
          "event": [ {
                      "evtype":"overlay",
                      "evcode": ("apply", ov)
                     } for ov in overlays.get(n,[])
                     ],
            "label": "+overlays({})".format(n),
        }
      ]
      # Bind all poles in involved clusters to 'advbinddef'.
      for clsym in sorted(preclusters):
        cldef = ClusterDict()
        if clsym in self.ADVANCING_TEMPLATE:
          templ = self.ADVANCING_TEMPLATE[clsym]
          cldef.sym = clsym
          for fixed_kv in templ[0]:
            k,v = fixed_kv
            cldef[k] = v
          for advbindkey in templ[1]:
            shorthand = "{}.{}".format(clsym, advbindkey)
            if (advbindkey in shifters) or (shorthand in shifters):
              continue    # Skip if already serving as shifter key.
            # Skip if already serving as sanity key.
            if (advbindkey == sanity) or (shorthand == sanity):  # TODO: compare normalized syms.
              continue
            cldef[advbindkey] = advbinddef
        else:
          cldef = None
          #raise ValueError("no advancing bind possible for {!r}".format(clsym))
        if cldef:
          preshiftlayer.merge_cluster(cldef)

      # bind shiftkeys for shift n.
      shiftlayer = LayerDict("Shift_{}".format(n))
      for shiftsym,bitmask in shifters.items():
        shiftlayer[shiftsym] = make_shifter_bind(n, bitmask, overlays, hermits, extents)

      if n in hermits:
        # Conditionally generate Preshift layer.
        normalized_preshiftlayer = self.normalize_layer(preshiftlayer, conmap)
        extlayers.append(normalized_preshiftlayer)
        sanitizeable.append(preshiftlayer['name'])
      # Generate Shift layer.
      normalized_shiftlayer = self.normalize_layer(shiftlayer, conmap)
      extlayers.append(normalized_shiftlayer)
      sanitizeable.append(shiftlayer['name'])

    # Establish sanity bind.
    if sanity:
      sanitizeable = [ "{{overlay,peel,{}}}".format(x) for x in sanitizeable ]
      sanitizeable.append("#sanity")
      if sanitizeable:
        cl,po = self.normalize_srcsym(sanity)
        sanitize_shorthand = "".join(sanitizeable)
        sanitizer = self.expand_shorthand_syntheses(sanitize_shorthand)
        autostyle = auto_style(po)
        pole = PoleDict(po, sanitizer)
        extlayers[0].merge_cluster_pole(cl, autostyle, pole)
    return extlayers

  def prepare_action (self, dom_node, conmap):
    # Update layers (self.actionsets, self.actionlayers) with shiftmap.
    paralayers = self.prepare_shifters(dom_node, conmap)
#    print("paralayers = "); pprint.pprint(paralayers)
    lyrid = 0
    for lyrspec in paralayers:
      if lyrid == 0:
        self.actionsets.append(lyrspec)
      else:
        self.actionlayers.append(lyrspec)
      lyrid += 1
    return paralayers

  def export_action (self, dom_node, conmap, phase=0):
    r"""Convert/export action subdict to ActionSet, ActionLayer, Preset, Group.
{
  "name":
  "layer": [
    `layer`,
    ...
  ],
  "shiftmap": {
    "shifter": [
      { "srcsym": ...,
        "bitmask": ... },
      ...
    ],
    "overlay": [
      { "level": ...
        "layers": [
          layer_name:str,
          ...
        ]
      }
    ]
  }
}
"""
    lyrid = 0
    basename = None
    for lyrspec in self.iter_children(dom_node, "layer"):
      if phase == 0:
        if lyrid == 0:
          # Export only base layer.
          lyrname = self.export_layer(lyrspec, conmap, lyrid, parent_name=basename)
      elif phase == 1:
        if lyrid == 0:
          lyrname = None
          for exported_action in conmap.actions:
            if exported_action.title == lyrspec["name"]:
              lyrname = exported_action.index
        elif lyrid != 0:
          # Export non-base layers.
          lyrname = self.export_layer(lyrspec, conmap, lyrid, parent_name=basename)
      if phase == 0:  # Phase 1: only base layer.
        break
      if lyrid == 0:
        basename = lyrname
      lyrid += 1

  def load_aliases (self, dom_node):
    if dom_node:
      for aliasname,aliasdesc in self.iter_children(dom_node, None):
        v = aliasdesc
        self.aliases[aliasname] = v
    return True

  def export_conmap (self, dom_node, conmap):
    """Generate Mapping"""
    r"""
{
  "title": ...
  "revision": ...
  "description": ...
  "author": ...
  "action": [
    `action`,
    ...
  ]
}
"""
    if conmap is None:  
      conmap = scconfig.Mapping()

    self.load_aliases(self.get_domchild(dom_node, "aliases"))

    title = "(Unnamed)"
    title = self.get_domtext(dom_node, "name", title)
    title = self.get_domtext(dom_node, "title", title)

    # Key order from least-preferred to most-preferred.
    revision = self.get_domattr(dom_node, "rev", 1)
    revision = self.get_domattr(dom_node, "revision", revision)

    description = "(no description)"
    description = self.get_domtext(dom_node, "desc", description)
    description = self.get_domtext(dom_node, "descr", description)
    description = self.get_domtext(dom_node, "description", description)

    author = "(Unknown)"
    author = self.get_domtext(dom_node, "creator", author)
    author = self.get_domtext(dom_node, "author", author)

    devtype = None
    devtype = self.get_domattr(dom_node, "devtype", devtype)
    devtype = self.get_domattr(dom_node, "controller_type", devtype)

    timestamp = -1
    timestamp = self.get_domattr(dom_node, "Timestamp", timestamp)
    timestamp = self.get_domattr(dom_node, "timestamp", timestamp)

#    for actdesc in self.iter_children(dom_node, "action"):
#      self.export_action(actdesc, conmap)
    self.actions = []   # Action Sets and Layers in VDF order.
    paractions = []
    for actdesc in self.iter_children(dom_node, "action"):
      extlayers = self.prepare_action(actdesc, conmap)
#      print("processed exlayers = {}".format(extlayers))
#      print("processed exlayers = ", end='')
#      pprint.pprint(extlayers)
      paractions.append(extlayers)
    self.actions.extend(self.actionsets)
    self.actions.extend(self.actionlayers)
    extactions = [ {"layer":x} for x in paractions ]    # Convert to dom-like.
    for actdesc in extactions:
      self.export_action(actdesc, conmap, phase=0)
    for actdesc in extactions:
      self.export_action(actdesc, conmap, phase=1)

    conmap.revision = revision
    conmap.title = title
    conmap.description = description
    conmap.creator = author
    conmap.controller_type = devtype
    conmap.timestamp = timestamp

    return conmap

  def export_config (self, dom_node, cfg=None):
    if cfg is None:
      cfg = scconfig.ControllerConfigFactory.make_from_dict({})

    conmap = cfg.add_mapping()
    self.export_conmap(dom_node, conmap)

    return cfg



if __name__ == "__main__":
  with sys.stdin as f:
    d_yaml = yaml.load(f)
  exporter = ScconfigExporter(None)
  cfg = exporter.export_config(d_yaml)
  vdf = scconfig.toVDF(cfg)
  with sys.stdout as f:
    scvdf.dump(vdf, f)

