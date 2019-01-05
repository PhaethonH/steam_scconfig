#!/usr/bin/env python3

# Convert from a DOM-like structure to Scconfig.

import scconfig, scvdf

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
    pass


  # Attributes: for machine-readable values.
  # CDATA: for human-presentable values.
  def get_domattr (self, dom_node, attr_name, default_value=None):
    r"""attribute of an element."""
    return dom_node.get(attr_name, default_value)

  def iter_children (self, dom_node, element_name):
    r"""List of children nodes."""
    probe = dom_node.get(element_name, None)
    if probe:
      if isinstance(probe, list):
        return iter(probe)
      else:
        return [ probe ]
    return []

  def get_domtext (self, dom_node, element_name):
    r"""CDATA of/in a child element."""
    probe = dom_node.get(element_name, '')
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
      pass
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

  def export_component (self, dom_node, groupobj):
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
    for k in sorted(settingsobj._CONSTRAINTS.keys()):
      v = settingsobj[k]
      settingsobj.__dict__[k] = v
    return settingsobj

  def export_cluster (self, dom_node, groupobj):
    r"""
{
  "mode": ...
  "component": [
    `component`,
    ...
  ]
}
"""
    clustermode = self.get_domattr(dom_node, "mode")
    for compspec in self.iter_children(dom_node, "component"):
      self.export_component(compspec, groupobj)
    for ss in self.iter_children(dom_node, "settings"):
      self.export_settings(ss, groupobj.settings)
      break
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
  def export_layer (self, dom_node, conmap, layeridx=0):
    r"""
{
  "name": ...
  "cluster": [
    `cluster`,
    ...
  ]
}
"""
    layer_name = self.get_domattr(dom_node, "name")
    presetid = len(conmap.presets)
    grpid = len(conmap.groups)
    # build Preset
    if presetid == 0:
      presetkey = 'Default'
    else:
      presetkey = "Preset_{:07d}".format(presetid)
    presetobj = conmap.add_preset(presetid, presetkey)
    for clusterspec in self.iter_children(dom_node, "cluster"):
      grpmode = self.get_domattr(clusterspec, "mode")
      grp = conmap.add_group(grpid, grpmode)
      self.export_cluster(clusterspec, grp)
      clustersym = self.get_domattr(clusterspec, "sym")
      grpsrc = self.GRPSRC_MAP.get(clustersym, clustersym)
      active = True
      modeshift = False
      presetobj.add_gsb(grpid, grpsrc, active, modeshift)
      grpid += 1
    # add to action_layers[] or actions[]
    if layeridx > 0:
      conmap.add_action_layer(presetkey, layer_name)
    else:
      if layer_name is None or len(conmap.actions) == 0:
        layer_name = 'Default'
      conmap.add_action_set(presetkey, layer_name)
    return True

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
    # TODO: update layers with shiftmap.
    for shiftspec in self.iter_children(dom_node, "shiftmap"):
      break

    lyrid = 0
    for lyrspec in self.iter_children(dom_node, "layer"):
      self.export_layer(lyrspec, conmap, lyrid)
      lyrid += 1

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

    title = self.get_domtext(dom_node, 'title')

    revision = self.get_domattr(dom_node, 'rev', 1)
    revision = self.get_domattr(dom_node, 'revision', revision)

    description = None
    if description is None:
      description = self.get_domtext(dom_node, 'desc')
    if description is None:
      description = self.get_domtext(dom_node, 'descr')
    if description is None:
      description = self.get_domtext(dom_node, 'description')

    author = None
    if author is None:
      author = self.get_domtext(dom_node, 'creator')
    if author is None:
      author = self.get_domtext(dom_node, 'author')

    timestamp = self.get_domattr(dom_node, 'Timestamp', -1)
    timestamp = self.get_domattr(dom_node, 'timestamp', timestamp)

    for actdesc in self.iter_children(dom_node, "action"):
      self.export_action(actdesc, conmap)

    return conmap


