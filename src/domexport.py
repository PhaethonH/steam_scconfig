#!/usr/bin/env python3
# vim: ts=2 sw=2 expandtab

# Convert from a DOM-like structure to Scconfig.

import scconfig, scvdf
import re
import pprint
import sys, yaml

def _stringlike (x):
  try: return x.isalpha
  except AttributeError: return False

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
      <mode/>
      <component>*
        <sym/>
        <generator>+
          <signal/>
          <event_sym>+
            <evtype/>
            <evcode/>
          </event_sym>
        </generator>
      </component>
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
      <mode/>
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



  def export_frob (self, dom_node, settings_obj):
    r"""
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
      if isinstance(settings, scconfig.ActivatorLongPress.Settings):
        retval.long_press_time = int(specific)
      elif isinstance(settings, scconfig.ActivatorDoublePress.Settings):
        retval.double_tap_time = int(specific)
      elif isinstance(settings, scconfig.ActivatorChord.Settings):
        # TODO: resolve symbolic
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
    r"""
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
    elif evtype in ('host',):
      pass
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
    return None

  def export_synthesis (self, dom_node, inputobj):
    r"""
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
    for frobdesc in self.iter_children(dom_node, "frob"):
      self.export_frob(dom_node, settings)
      break
#    act = scconfig.ActivatorFactory.make(signame, bindings, settings)
    inputobj.add_activator(signame, py_bindings=bindings, py_settings=settings)
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
    },
    scconfig.GroupFourButtons.MODE: {
      'n': scconfig.GroupFourButtons.Inputs.BUTTON_Y,
      'e': scconfig.GroupFourButtons.Inputs.BUTTON_X,
      'w': scconfig.GroupFourButtons.Inputs.BUTTON_B,
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
    scconfig.GroupRadialMenu.MODE: {
      'c': scconfig.GroupRadialMenu.Inputs.CLICK,
      # TODO: touch_menu_button_%02d
    },
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
      'BK': scconfig.GroupSwitches.Inputs.BUTTON_ESCAPE,
      'ST': scconfig.GroupSwitches.Inputs.BUTTON_MENU,
      'LB': scconfig.GroupSwitches.Inputs.LEFT_BUMPER,
      'RB': scconfig.GroupSwitches.Inputs.RIGHT_BUMPER,
      'LG': scconfig.GroupSwitches.Inputs.BUTTON_BACK_LEFT,
      'RG': scconfig.GroupSwitches.Inputs.BUTTON_BACK_RIGHT,
      'INF': scconfig.GroupSwitches.Inputs.ALWAYS_ON,

      '1': scconfig.GroupSwitches.Inputs.BUTTON_ESCAPE,
      '2': scconfig.GroupSwitches.Inputs.LEFT_BUMPER,
      '3': scconfig.GroupSwitches.Inputs.BUTTON_BACK_LEFT,
      '4': scconfig.GroupSwitches.Inputs.BUTTON_MENU,
      '5': scconfig.GroupSwitches.Inputs.RIGHT_BUMPER,
      '6': scconfig.GroupSwitches.Inputs.BUTTON_BACK_RIGHT,
    },
    scconfig.GroupTouchMenu.MODE: {
      # TODO: touch_menu_button_%02d
    },
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
  def expand_synthesis (self, evspec):
    # TODO: rename variables to more reasonable ones.

    if evspec is None:
      return None

    # resolve aliases.
    while evspec[0] == '$':
      evspec = self.aliases.get(evspec[1:], None)

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

    d = {
      "actsig": actsig,
      "event": evgenlist,
      "settings": frobdef,
      "label": label,
      "iconinfo": None,
      }
    return d


  def expand_shorthand_syntheses (self, evlistspec):
    if ' ' in evlistspec:
      evspecs = evlistspec.split()
    else:
      evspecs = [ evlistspec ]
    retval = []
    for evspec in evspecs:
      evsynth = self.expand_synthesis(evspec)
      retval.append(evsynth)
    return retval


  def export_component (self, dom_node, groupobj):
    # Maps to scconfig.ControllerInput
    r"""
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

    inode = scconfig.ControllerInput(partsym)
    for syndesc in self.iter_children(dom_node, "synthesis"):
      self.export_synthesis(syndesc, inode)
    groupobj.add_input(inode)
    return True

  def export_settings (self, dom_node, settingsobj):
    """Generalized Settings export."""
    for k in sorted(settingsobj._CONSTRAINTS.keys()):
      v = settingsobj[k]
      settingsobj.__dict__[k] = v
    return settingsobj


  def normalize_cluster (self, dom_node):
    """Resolve shorthand notations for components.

Returns a cluster DOM which is a copy of the original but with shorthand notation resolved.
"""
#    print("normalizing cluster {}".format(dom_node))
    extcluster = {'component':[]}

    if dom_node in ("LJ", "(LJ)"):
      extcluster["mode"] = "jsmove"
      return extcluster
    if dom_node in ("RJ", "(RJ)"):
      extcluster["mode"] = "jscam"
      return extcluster

    scanned_syms = []
    for k,v in self.iter_children(dom_node, None):
      cluster_sym, component_sym = None, None
      if k in self.UNIQUE_COMPONENT_SYMS:
        cluster_sym, component_sym = self.UNIQUE_COMPONENT_SYMS[k]
      elif len(k) == 1:
        component_sym = k
      if component_sym:
        syntheses = None

        if _stringlike(v):
          # parse
          syntheses = self.expand_shorthand_syntheses(v)
        elif v:
          # presume list of Synthesis
          syntheses = v

        if syntheses is not None:
          compspec = {
              "sym": component_sym,
              "synthesis": syntheses
            }
          scanned_syms.append(component_sym)
          extcluster['component'].append(compspec)
      else:
        if k == 'component':
          extcluster[k].extend(v)
        else:
          extcluster[k] = v
    if not 'mode' in extcluster:
      mode = self.auto_mode(scanned_syms)
      extcluster['mode'] = mode

    return extcluster

  UNIQUE_COMPONENT_SYMS = {
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
  def export_cluster (self, dom_node, groupobj):
    # Maps to scconfig.Group
    r"""
{
  "mode": ...
  "component": [
    `component`,
    ...
  ]
}


shorthand
{
  "mode": ...
  <ComponentSym>: [
    `synthesis`,
    ]
  <ComponentSym>: <EvgenSpec>
"""
    clustermode = self.get_domattr(dom_node, "mode")
    for compspec in self.iter_children(dom_node, "component"):
      self.export_component(compspec, groupobj)
    for ss in self.iter_children(dom_node, "settings"):
      self.export_settings(ss, groupobj.settings)
      break
    for k,v in self.iter_children(dom_node, None):
      cluster_sym, component_sym = None, None
      if k in self.UNIQUE_COMPONENT_SYMS:
        cluster_sym, component_sym = self.UNIQUE_COMPONENT_SYMS[k]
      elif len(k) == 1:
        component_sym = k
      if component_sym:
        syntheses = None

        if _stringlike(v):
          # parse
          syntheses = self.expand_shorthand_syntheses(v)
        elif v:
          # presume list of Synthesis
          syntheses = v

        if syntheses is not None:
          compspec = {
              "sym": component_sym,
              "synthesis": syntheses
            }
          self.export_component(compspec, groupobj)
    return True

  @staticmethod
  def auto_mode (x):
    if any(['u' in x, 'd' in x, 'l' in x, 'r' in x]):
      return 'dpad'
    if any(['a' in x, 'b' in x, 'x' in x, 'y' in x]):
      return 'four_buttons'
    if any(['s' in x, 'e' in x, 'w' in x, 'n' in x]):
      return 'four_buttons'
    if any(['c' in x, 'o' in x]):
      return 'joystick_move'
    if x in ('BK', 'ST', 'LB', 'RB', 'LG', 'RG', 'INF'):
      return 'switches'

    def intOrNegOne(z):
      try:
        return int(z)
      except ValueError:
        return -1

    nums = [ intOrNegOne(z) for z in x ]
    m = max(nums)

    if 0 in nums:
      return 'radial'  # '00' - radial center/unselect
    elif any([2 in nums, 4 in nums, 7 in nums, 9 in nums, 12 in nums, 13 in nums, 16 in nums]):
      return 'touch_menu'
    elif m > 0:
      return 'radial_menu'

    return 'dpad'

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
  GRPMODE_MAP = {
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

  def normalize_layer (self, dom_node, conmap, layeridx=0):
    r"""resolve shorthands.
Returns a substitute layer which is copy of the original (dom_node), but with shorthand notations for/in clusters resolved.
"""
#    print("normalizing layer: {}".format(dom_node))
    paralayer = {'cluster': []}

    # Scan shorthands.
    paraclusters = {}   # Map cluster_sym to cluster contents.
    for k,v in self.iter_children(dom_node, None):
#      print("scanning shorthand {!r}".format(k))
      cluster_sym = component_sym = None
      if '.' in k:    # "CLUSTER.POLE"
        cluster_sym, component_sym = k.split('.')
#        print("DOTTED PAIR: {} . {}".format(cluster_sym, component_sym))
      elif k in self.UNIQUE_COMPONENT_SYMS:   # "POLE(UNIQUE)"
        cluster_sym, component_sym = self.UNIQUE_COMPONENT_SYMS[k]
#        print(" UNIQUEIFIED {} => {} . {}".format(k, cluster_sym, component_sym))
      elif k in self.GRPSRC_MAP:
#        print(" SHORTHAND CLUSTERSYM {} => {}".format(k, cluster_sym))
        component_sym = None
#        print("using v = {!r}".format(v))
#        v['sym'] = k
#        v['mode'] = 'dpad'  # TODO: automode
        vv = self.normalize_cluster(v)
        vv['sym'] = k
#        print("  normalized as {}".format(vv))

        if cluster_sym in paraclusters: # reuse cluster.
          cluster = paraclusters[cluster_sym]
          cluster['component'].extend(vv['component'])
        else: # create cluster.
          cluster = vv
          paraclusters[cluster_sym] = vv
          # TODO update paralayer?
#          print("* CREATE CLUSTER {}".format(cluster_sym))
          paralayer['cluster'].append(cluster)

#        paralayer['cluster'].append(vv)

        continue

      # TODO: expand on a parallel struct.
      if cluster_sym and component_sym:
        # Find cluster.
#        print("paraclusters = {} (@ {})".format(paraclusters.keys(), cluster_sym))
        if cluster_sym in paraclusters: # reuse cluster.
          cluster = paraclusters[cluster_sym]
        else: # create cluster.
          automode = self.auto_mode(component_sym)
          cluster = {
            "mode": automode,
            "sym": cluster_sym,
            "component": []
            }
#          print("CREATE CLUSTER {}".format(cluster_sym))
          paraclusters[cluster_sym] = cluster
          # TODO update paralayer?
          paralayer['cluster'].append(cluster)
        # Find component.
        component = None
        for comp in cluster['component']: # reuse component
          if cluster.get('sym', None) == component_sym:
            component = comp
            break
        else: # create component.
          component = {
            'sym': component_sym,
            'synthesis': []
            }
          # TODO: auto-mode here?
          cluster['component'].append(component)
        # Update cluster.
        if _stringlike(v):
          syntheses = self.expand_shorthand_syntheses(v)
        else: syntheses = v
        component['synthesis'].extend(syntheses)
        # TODO: auto-mode from all components.
        if cluster.get('mode', None) is None:
          complist = [ x.get("sym") for x in cluster['component'] ]
          automode = self.auto_mode(complist)
          cluster['mode'] = automode
      else:   # Not recognized as shorthand; assume longhand.
        # copy verbatim.
#        print("COPY VERBATIM {} = {}".format(k, v))
        if k == 'cluster':
          vv = [ self.normalize_cluster(cl) for cl in v ]
          paralayer[k].extend(vv)
        else:
          paralayer[k] = v
#      print("cluster list = {}".format(paralayer['cluster']))
#      pprint.pprint(paralayer['cluster'])
#      print("now paralayer <- {}".format([x['sym'] for x in paralayer['cluster']]))

#    for clustersym, clusterspec in paraclusters.items():
#      grpmode = self.get_domattr(clusterspec, "mode")  # TODO: auto-mode
#      #export_group(clusterspec, grpmode, clustersym, active, modeshift)
#      paralayer['cluster'].append(clusterspec)

#    print("in dom node {}".format(dom_node))
#    for clusterspec in self.iter_children(dom_node, "cluster"):
#      print("normalize: examine {}".format(clusterspec))
#      grpmode = self.get_domattr(clusterspec, "mode")
#      clustersym = self.get_domattr(clusterspec, "sym")
#      active = True
#      modeshift = False
#      paralayer['cluster'].append(clusterspec)

#    print("paralayer = {}".format([x['sym'] for x in paralayer['cluster']]))
    #print("  = {}".format(paralayer))
#    print("  = ")
#    pprint.pprint(paralayer, width=180)
#    print()
    return paralayer

  def export_layer (self, dom_node, conmap, layeridx=0, parent_name=None):
    r"""
{
  "name": ...
  "cluster": [
    `cluster`,
    ...
  ]
}
"""
#    print("export_layer {}".format(dom_node))
    layer_name = self.get_domattr(dom_node, "name")
    presetid = len(conmap.presets)
    grpid = len(conmap.groups)
    # build Preset
    if presetid == 0:
      presetkey = 'Default'
    else:
      presetkey = "Preset_{:07d}".format(presetid)
    presetobj = conmap.add_preset(presetid, presetkey)

    def export_group (clusterspec, grpmode, clustersym, active, modeshift):
#      print("export_group({!r},{!r},{!r},{!r},{!r})".format(clusterspec, grpmode, clustersym, active, modeshift))
      grpsrc = self.GRPSRC_MAP.get(clustersym, clustersym)
#      print(" grpsrc = {}".format(grpsrc))
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
        # map shorthand mode name to full group mode.
        grpmode = self.GRPMODE_MAP.get(grpmode, grpmode)
        grp = conmap.add_group(grpid, grpmode) 
        presetobj.add_gsb(grpid, grpsrc, active, modeshift)
      self.export_cluster(clusterspec, grp)

#    # Scan shorthands.
#    paraclusters = {}   # Map cluster_sym to cluster contents.
#    for k,v in self.iter_children(dom_node, None):
#      cluster_sym = component_sym = None
#      if '.' in k:
#        cluster_sym, component_sym = k.split('.')
#      elif k in self.UNIQUE_COMPONENT_SYMS:
#        cluster_sym, component_sym = self.UNIQUE_COMPONENT_SYMS[k]
#      # TODO: expand on a parallel struct.
#      if cluster_sym and component_sym:
#        # Find cluster.
#        if cluster_sym in paraclusters:
#          cluster = paraclusters[cluster_sym]
#        else:
#          automode = self.auto_mode(component_sym)
#          cluster = paraclusters[cluster_sym] = { "mode": automode, "component": [] }  # TODO: auto-mode
#        # Find component.
#        component = None
#        for comp in cluster['component']:
#          if cluster.get('sym', None) == component_sym:
#            component = comp
#        else: # create component.
#          component = {
#            'sym': component_sym,
#            'synthesis': []
#            }
#          # TODO: auto-mode here?
#          cluster['component'].append(component)
#        # Update cluster.
#        if _stringlike(v):
#          syntheses = self.expand_shorthand_syntheses(v)
#        else:
#          syntheses = v
#        component['synthesis'] = syntheses
#        # TODO: auto-mode from all components.
#        if cluster.get('mode', None) is None:
#          complist = [ x.get("sym") for x in cluster['component'] ]
#          automode = self.auto_mode(complist)
#          cluster['mode'] = automode

    for clusterspec in self.iter_children(dom_node, "cluster"):
      grpmode = self.get_domattr(clusterspec, "mode")
      clustersym = self.get_domattr(clusterspec, "sym")
      active = True
      modeshift = False

      export_group(clusterspec, grpmode, clustersym, active, modeshift)

#    for clustersym, clusterspec in paraclusters.items():
#      grpmode = self.get_domattr(clusterspec, "mode")  # TODO: auto-mode
#      active = True
#      modeshift = False
#
#      export_group(clusterspec, grpmode, clustersym, active, modeshift)

    # add to action_layers[] or actions[]
    if layeridx > 0:
      conmap.add_action_layer(presetkey, layer_name, parent_set_name=parent_name)
    else:
      if layer_name is None or len(conmap.actions) == 0:
        layer_name = 'Default'
      conmap.add_action_set(presetkey, layer_name)
    return layer_name

  def prepare_shifters (self, dom_node, conmap):
    r"""
Prepare an alternate list of action layers with shifters incorporated.
Existing layers may have to be modified (e.g. unbinding conflicted keys).
"""
    extlayers = []   # Extended layers.

    # Copy extant layers.
    lyrid = 0
    for lyr in self.iter_children(dom_node, "layer"):
#      print("feeding normalizer {}".format(lyr))
      postlyr = self.normalize_layer(lyr, conmap, lyrid)
#      extlayers.append(postlyr)
#      lyrid += 1
      extlayers.append(postlyr)
#    print("raw layers = ", extlayers)

    maxshift = 0
    overlays = {}   # map int => list of overlay names
    shifters = {}   # map srcsym => bitmask:int
    for shiftmap in self.iter_children(dom_node, "shiftmap"):

#      if self.get_domattr(self.get_domchild(shiftmap, "shifter"), "srcsym"):
#        # long-form.
#        shiftersiter = [ (self.get_domattr(shifter, "srcsym"), 'hold', self.get_domattr(shifter, "bitmask")) for shifter in self.iter_children(shiftmap, "shifter") ]
#      else:
#        # short-form.
#        shiftersiter = [ sh for sh in self.iter_children(shifter, None) ]
#      for srcsym, bitmaskstr in shiftersiter:
#        shifters[srcsym] = bitmaskstr

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
#          print("SRCSYM={}, bitmask={}".format(srcsym, bitmask))
        else:
          for srcsym, shiftaction in self.iter_children(shifter, None):
            parts = shiftaction.split()
            shiftcmd = parts[0]
            bitmaskstr = parts[1] if len(parts) > 1 else 0
            bitmask = int(bitmaskstr)
            maxshift |= bitmask
#            print("SRCSYM={}, bitmask={}".format(srcsym, bitmask))
            shifters[srcsym] = bitmask

      for overlay in self.iter_children(shiftmap, "overlay"):
        level = self.get_domattr(overlay, "level")
        if level is not None:
          level = int(level)
          accum = []
          for layername in self.iter_children(overlay, "layer"):
            accum.append(layername)
          overlays[level] = accum
#          print("OVERLAYS[{}] = {}".format(level, accum))
        else:
          for levelstr, layernames in self.iter_children(overlay, None):
            level = int(levelstr)
            accum = []
            for layername in layernames:
              accum.append(layername)
            overlays[level] = accum
#            print("OVERLAYS[{}] = {}".format(level, accum))
      break
#    print("MAXSHIFT = {}".format(maxshift))

    baselayer = None
    for lyr in self.iter_children(dom_node, "layer"):
      baselayer = lyr
      break
    # TODO: handle no-layers case.

    def make_shifter_bind (from_level, bitmask):
      pending = []
      next_level = from_level ^ bitmask
      # Apply next level.
      if next_level & bitmask:
        # on key press.
        pending.insert(0, "+")
        if next_level != 0:   # can't apply 0 - achieved by removing all layers.
          pending.append("{{overlay,apply,Preshift_{}}}".format(next_level))
#          pending.append("#+Preshift_{}".format(next_level))
      else:
        # on key release.
        pending.insert(0, "-")
        if next_level != 0:   # can't apply 0 - achieved by removing all layers.
          pending.append("{{overlay,apply,Shift_{}}}".format(next_level))
#          pending.append("#+Shift_{}".format(next_level))
      # Remove current level.
      if from_level != 0:   # can't remove 0 (base).
        pending.append("{{overlay,peel,Preshift_{}}}".format(from_level))
#        pending.append("#-Preshift_{}".format(next_level))
        pending.append("{{overlay,peel,Shift_{}}}".format(from_level))
#        pending.append("#-Shift_{}".format(next_level))
      pending.append("#goto#{}".format(next_level))
      return "".join(pending)

    # Set up shift level 0
    for shiftsym,bitmask in shifters.items():
      baselayer[shiftsym] = make_shifter_bind(0, bitmask)

    # Preshift: find all clusters involved with shift.
    for n in range(1, maxshift+1):
      # for shift level n...
      preclusters = set()
      for overlayname in overlays.get(n, []):
        for lyr in self.iter_children(dom_node, "layer"):
          if lyr.get("name", None) == overlayname:
#            print("cluster {}".format(lyr.get("cluster", None)))
            for clusterdef in lyr.get("cluster", []):
              preclusters.add(clusterdef["sym"])
#      print("preclusters {}".format(preclusters))
#      print("CREATE LAYER Preshift_{}".format(n))

      # bind shiftkeys for preshift n; set preclusters to advance to shift n.
      preshiftlayer = {
        "name": "Preshift_{}".format(n),
        "cluster": [],
        }
      for shiftsym,bitmask in shifters.items():
        preshiftlayer[shiftsym] = make_shifter_bind(n, bitmask)
      advbinddef = [ {
        "actsig": 'start',
        "event": [ { "evtype": "overlay", "evcode": ("apply", "Shift_{}".format(n)) } ],
        "label": "advance Shift_{}".format(n),
        } ]
      for clsym in sorted(preclusters):
        cldef = { 
          "sym": clsym,
          "mode": 'dpad',
          'u': advbinddef,
          'd': advbinddef,
          'l': advbinddef,
          'r': advbinddef,
#          'c': advbinddef,
          }
        preshiftlayer['cluster'].append(cldef)
#      print("preshiftlayer = {}".format(preshiftlayer))
      #dom_node['layer'].append(preshiftlayer)
#      print("CREATE LAYER Shift_{}".format(n))

      # bind shiftkeys for shift n.
      shiftlayer = {
        "name": "Shift_{}".format(n),
        "cluster": [],
        }
      for shiftsym,bitmask in shifters.items():
        shiftlayer[shiftsym] = make_shifter_bind(n, bitmask)

#      print("* preshiftlayer = ",end='')
#      pprint.pprint(preshiftlayer)
      normalized_preshiftlayer = self.normalize_layer(preshiftlayer, conmap)
#      print("*  normalized = ",end='')
#      pprint.pprint(normalized_preshiftlayer)
      normalized_shiftlayer = self.normalize_layer(shiftlayer, conmap)
      extlayers.append(normalized_preshiftlayer)
      extlayers.append(normalized_shiftlayer)
#    print("extlayers = {}".format(extlayers))
    return extlayers

  def prepare_action (self, dom_node, conmap):
    # Update layers (self.actionsets, self.actionlayers) with shiftmap.
    normlayer = self.normalize_layer(dom_node, conmap)
#    print("*normalizing {}".format(dom_node))
#    print("* using normalized layer {}", end='')
#    pprint.pprint(normlayer)
    paralayers = self.prepare_shifters(normlayer, conmap)
    lyrid = 0
    for lyrspec in paralayers:
      if lyrid == 0:
        self.actionsets.append(lyrspec)
      else:
        self.actionlayers.append(lyrspec)
      lyrid += 1
    return paralayers

  def export_action (self, dom_node, conmap):
    r"""
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
#    print("exporting action {}".format(dom_node))
    lyrid = 0
    basename = None
    for lyrspec in self.iter_children(dom_node, "layer"):
      lyrname = self.export_layer(lyrspec, conmap, lyrid, parent_name=basename)
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
      self.export_action(actdesc, conmap)

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

