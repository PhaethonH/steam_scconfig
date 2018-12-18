#!/usr/bin/env python3

# Configurator module for Steam Valve Controller

import scvdf

class BindingBase (object):
  """One binding instance in a list of many, as part of Activate"""
  def __init__ (self, evtype, evdetails, label=None):
    self.evtype = evtype
    self.evdetails = evdetails
    self.label = label
  def __str__ (self):
    if not self.evtype:
      return ""
    tail = ""
    if self.evdetails:
      tail = " " + " ".join(self.evdetails)
    front = self.evtype
    label = ""
    if self.label:
      label = ", {}".format(self.label)
    retval = "{}{}{}".format(front, tail, label)
    return retval
  @staticmethod
  def _filter_enum (enum_mapping, initval):
    """Helper function to handle filtering acceptable values based on internal dialect or VDF-acceptable value."""
    if enum_mapping is None:
      return None
    lower_check = initval.lower()
    upper_check = initval.upper()
    try:
      vl = enum_mapping.values()
    except AttributeError as e:
      vl = enum_mapping
    if (initval in vl) or (lower_check in vl) or (upper_check in vl):
      # Already in final form.
      return initval
    # Subject to mapping.
    if initval in enum_mapping:
      return enum_mapping[initval]
    if lower_check in enum_mapping:
      return enum_mapping[lower_check]
    if upper_check in enum_mapping:
      return enum_mapping[upper_check]
    # Not accepted.
    return None
  @staticmethod
  def _mangle_vdfliteral (s):
    """mangle binding, to embed warning messages in vdf/Steam Client."""
    retval = s.replace('"', "'").replace("//", "/").replace(",", ";")
    return retval
  @staticmethod
  def _parse (binding):
    """Parse 'binding' string into a parsed tuple form:
( cmd:list, label:str )

Tuple elements are delimited by comma+space.
cmd elements are delimited by space.
"""
    if not binding:
      return None
    # Not clear if more than one comma is allowed; if so, which is label?
    comma_parts = binding.split(', ', 1)
    phrase0 = comma_parts[0]
    # TODO: is label supposed to be second phrase [1] or final phrase [-1] ?
    label = comma_parts[-1] if len(comma_parts) > 1 else None
    args = phrase0.split(' ')
    retval = ( args , label )
    return retval


class Binding_Empty (BindingBase):
  """alias for Binding_Host('empty_binding')"""
  def __init__ (self, label=None):
    BindingBase.__init__(self, 'controller_action', ['empty_binding'], label)

  @staticmethod
  def make (parsed_tuple):
    """Instantiate from a parsed tuple."""
    ( (cmd, *args), label) = parsed_tuple
    if cmd == 'controller_action' and args[0] == 'empty_binding':
      return Binding_Empty(label=label)
    return None


class Binding_Keystroke (BindingBase):
  def __init__ (self, keycode, label=None):
    BindingBase.__init__(self, "key_press", [keycode], label)

  @staticmethod
  def make (parsed_tuple):
    """Instantiate from a parsed tuple."""
    ( (cmd, *args), label) = parsed_tuple
    if cmd in ('key_press',):
      try:
        return Binding_Keystroke(args[0], label=label)
      except:
        pass
    return None


class Binding_MouseSwitch (BindingBase):
  TRANSLATE_BUTTON = {
    "1": "LEFT", "2": "MIDDLE", "3": "RIGHT",
    "4": "BACK", "5": "FORWARD"
    }
  TRANSLATE_WHEEL = {
    "u": "SCROLL_UP", "d": "SCROLL_DOWN",
    }
  def __init__ (self, evdetails, label=None):
    major, vdfliteral = None, None
    if vdfliteral is None:
      vdfliteral = self._filter_enum(self.TRANSLATE_BUTTON, evdetails)
      major = 'mouse_button' if vdfliteral else None
    if vdfliteral is None:
      vdfliteral = self._filter_enum(self.TRANSLATE_WHEEL, evdetails)
      major = 'mouse_wheel' if vdfliteral else None
    if major and vdfliteral:
      BindingBase.__init__(self, major, vdfliteral, self.label)
    else:
      raise("Unknown mouse keysym '{}'".format(evdetails))

  @staticmethod
  def make (parsed_tuple):
    """Instantiate from a parsed tuple."""
    ( (cmd, *args), label) = parsed_tuple
    if cmd in ('mouse_button', 'mouse_wheel'):
      try:
        return Binding_MouseSwitch(cmd, args[0], label=label)
      except:
        pass
    return None


class Binding_Gamepad (BindingBase):
  TRANSLATION = {
    "A": "A", "B": "B", "X": "X", "Y": "Y",
    "LB": "SHOULDER_LEFT", "RB": "SHOULDER_RIGHT",
    "LT": "TRIGGER_LEFT", "RT": "TRIGGER_RIGHT",
    "DUP": "DPAD_UP", "DDN": "DPAD_DOWN", "DLT": "DPAD_LEFT", "DRT": "DPAD_RIGHT",
    "BK": "SELECT", "ST": "START", "LS": "JOYSTICK_LEFT", "RS": "JOYSTICK_RIGHT",
    "LJx": "LSTICK_LEFT", "LJX": "LSTICK_RIGHT", "LJy": "LSTICK_UP", "LJY": "LSTICK_DOWN",
    "RJx": "RSTICK_LEFT", "LJX": "RSTICK_RIGHT", "LJy": "RSTICK_UP", "LJY": "RSTICK_DOWN",
    }
  def __init__ (self, keycode, label=None):
    vdfliteral = self._filter_enum(self.TRANSLATION, keycode)
    if vdfliteral is not None:
      BindingBase.__init__(self, "xinput_button", [vdfliteral], label)
    else:
      raise KeyError("Unknown xpad keysym '{}'.".format(keycode))

  @staticmethod
  def make (parsed_tuple):
    """Instantiate from a parsed tuple."""
    ( (cmd, *args), label) = parsed_tuple
    if cmd == 'xinput_button':
      try:
        return Binding_Gamepad(args[0], label=label)
      except:
        pass
    return None

class Binding_Host (BindingBase):
  """Host operations."""
  TRANSLATION = {
    'empty': "empty_binding",
    'keyboard': "show_keyboard",
    'screenshot': "screenshot",
    'magnifier': "toggle_magnifier",
    'magnify': "toggle_magnifier",
    'music': "steammusic_playpause",
    'music_play/pause': "steammusic_playpause",
    'music_play': "steammusic_playpause",
    'music_pause': "steammusic_playpause",
    'music_next': "steammusic_next",
    'music_prev': "steammusic_prev",
    'music_previous': "steammusic_previous",
    'volume_up': "steammusic_volup",
    'volume_down': "steammusic_voldown",
    'volume_mute': "steammusic_volmute",
    'steam_hangup': "controller_poweroff",
    'steam_kill': "quit_application",
    'steam_terminate': "quit_application",
    'steam_forcequit': "quit_application",
    'steam_open': "bigpicture_open",
    'steam_hide': "bigpicture_minimize",
    'steam_exit': "bigpicture_quit",
    'host_suspend': "host_suspend",
    'host_restart': "host_restart",
    'host_poweroff': "host_poweroff",
  }
  def __init__ (self, details, label=None):
    vdfliteral = self._filter_enum(self.TRANSLATION, details)
    if vdfliteral is None:
      mangle = self._mangle_vdfliteral(details)
      raise ValueError("Unknown host action '{}'".format(mangled))
    BindingBase.__init__(self, vdfliteral, [], label)

  @staticmethod
  def make (parsed_tuple):
    """Instantiate from a parsed tuple."""
    ( (cmd, *args), label) = parsed_tuple
    try:
      return Binding_Host(cmd, label=label)
    except:
      return None


class Binding_Light (BindingBase):
  """Set controller LED - color and/or brightness.

R : red value, 0..255
G : green value, 0..255
B : blue value, 0..255
X : unknown, 0
L : brightness, 0..255 (off to brightest)
M : 0=UserPrefs (ignore R,G,B,X,L), 1=use R,G,B,L values, 2=set by XInput ID (ignore R,G,B,X,L)
"""
  def __init__ (self, R, G, B, X, L, M, label=None):
    BindingBase.__init__(self, "set_led", (R,G,B,X,L,M), label)
    self.R = R
    self.G = G
    self.B = B
    self.X = X
    self.L = L
    self.M = M

  @staticmethod
  def make (parsed_tuple):
    """Instantiate from a parsed tuple."""
    ( (cmd, *args), label) = parsed_tuple
    return None


class Binding_Overlay (BindingBase):
  """Control overlays."""
  ACTIONS = {
    "apply_layer": "add_layer",
    "apply": "add_layer",
    "peel_layer": "remove_layer",
    "peel": "remove_layer",
    "hold_layer": "hold_layer",
    "hold": "hold_layer",
#    "empty": "empty_binding",
# TODO: change action set
  }
  def __init__ (self, actionspec, layer_id, set_id, unk=0, label=None):
    vdfliteral = self._filter_enum(self.ACTIONS, actionspec)
    if vdfliteral is None:
      raise ValueError("Unknown overlay action '{}'".format(vdfliteral))
    marshal = [ vdfliteral, str(layer_id), str(set_id), str(unk) ]
    BindingBase.__init__(self, 'controller_action', marshal, label)
    self.layer_id = layer_id
    self.set_id = set_id
    self.unk = unk

  @staticmethod
  def make (parsed_tuple):
    ( (cmd, *args), label ) = parsed_tuple
    if (cmd == 'controller_action'):
      try:
        return Binding_Overlay(*args[:4], label=label)
      except:
        pass
      if args[0] in ('empty_binding', 'empty', None):
        return Binding_Empty(label=label)
      else:
        mangled = self._mangle_vdfliteral(str(parsed_tuple))
        return Binding_Empty('UNKNOWN_CONTROLLER_ACTION({})'.format(mangled))
    return None


class Binding_Modeshift (BindingBase):
  # TODO: filter inpsrc
  ACCEPTABLE = [
    "dpad", "button_diamond", "left_trigger", "right_trigger",
    "joystick", "right_joystick"
    ]
  def __init__ (self, input_source, group_id, label=None):
    vdfliteral = self._filter_enum(self.ACCEPTABLE, input_source)
    BindingBase.__init__(self, 'mode_shift', [ vdfliteral, str(group_id) ], label)
    self.inpsrc = vdfliteral
    self.group_id = group_id

  @staticmethod
  def make (parsed_tuple):
    """Instantiate from a parsed tuple."""
    ( (cmd, *args), label) = parsed_tuple
    if (cmd == 'mode_shift'):
      return Binding_Modeshift(args[0], int(args[1]), label=label)



class BindingFactory (object):
  @staticmethod
  def _mangle_vdfliteral (s):
    return BindingBase._mangle_vdfliteral(s)
  @staticmethod
  def make_empty (label=None):
    return Binding_Empty(label=label)
  @staticmethod
  def make_keystroke (synthsym, label=None):
    return Binding_Keystroke(synthsym, label=label)
  @staticmethod
  def make_mouseswitch (synthsym, label=None):
    return Binding_MouseSwitch(synthsym, label=label)
  @staticmethod
  def make_gamepad (synthsym, label=None):
    return Binding_Gamepad(synthsym, label=label)
  @staticmethod
  def make_hostcall (hostreq, label=None):
    return Binding_Host(hostreq, label=label)
  @staticmethod
# TODO: set_led
  def make_light (label=None):
    pass
  @staticmethod
  def make_overlay (subcmd, layer_id=0, set_id=0, unk=0, label=None):
    return Binding_Overlay(subcmd, layer_id, set_id, unk, label)
  @staticmethod
  def make_modeshift (inpsrc, grpid, label=None):
    return Binding_Modeshift(inpsrc, grpid, label)
  @staticmethod
  def make_controller_action (*args, label=None):
    if len(args) > 4:
      return BindingFactory.make_overlay(*args[:4], label=label)
    elif args[0] in [ 'empty_binding', 'empty', None ]:
      return Binding_Empty()
    else:
      mangled = BindingFactory._mangle_vdfliteral(' '.join(args))
      return Binding_Empty("UNKNOWN_CONTROLLER_ACTION({})".format(mangled))

  @staticmethod
  def parse (binding):
    self = BindingFactory
    parsed_tuple = BindingBase._parse(binding)
    ATTEMPTS = [
      Binding_Overlay,
      Binding_Modeshift,
      Binding_MouseSwitch,
      Binding_Keystroke,
      Binding_Gamepad,
      ]
    retval = None
    for candidate in ATTEMPTS:
      retval = candidate.make(parsed_tuple)
      if retval:
        return retval
    if not retval:
      mangled = self._mangle_vdfliteral(binding)
      retval = self.make_empty("UNKNOWN_BINDING({})".format(mangled))
    return retval




def dict2lop (kv_dict):
  lop = []
  for k,v in kv_dict.items():
    lop.append( (k,str(v)) )
  return lop




class EncodableDict (object):
  def __init__ (self, whole_key=None):
    if whole_key is None:
      self.whole_key = 'settings'
    else:
      self.whole_key = whole_key
    self.valid_keys = []  # also maintain order.
    self.store = {}
  def __setitem__ (self, k, v):
    self.valid_keys.append(k)
    self.store[k] = v
  def __getitem__ (self, k):
    return self.store[k]
  def __delitem__ (self, k):
    del self.store[k]
    self.valid_keys.remove(k)
  def encode_pair (self):
    lop = []
    for k in self.valid_keys:
      v = self.store[k]
      try:
        lop.append(v.encode_pair())
      except AttributeError as e:
        lop.append( (k,str(v)) )
    whole = (self.whole_key, lop)
    return whole
  def encode_kv (self):
    kv = scvdf.DictMultivalue()
    for k in self.valid_keys:
      v = self.store[k]
      try:
        kv[k] = v.encode_kv()
      except AttributeError as e:
        kv[k] = str(v)
    return kv
  def __bool__ (self):
    return bool(self.valid_keys)
  def __nonzero__ (self):
    return len(self.valid_keys) > 0

  @staticmethod
  def decode_kv (kv, parentkey=None):
    retval = EncodableDict()
    for k,v in kv.items():
      retval[k] = v
    return retval



class Activator (object):
  """Activator element within a list of activators.
Each activator specifies what button-activation signal to respond to, and how to respond to it (usually with a controller, keyboard, or mouse key/button press).

Activation signals include:
  Regular (reacts to both press and release)
  Long (source button was held)
  Start (source button started to be pressed)
  Release (source button being released)
  Double (previous press detected within some time interval of current press)
  Chord (source button detected as being pressed with another is held)

Responses include:
  key_press : generate a keyboard event
  xinput_button : generate a XInput/XBox360 event
  add layers
  remove layers
  change action sets
  set controller lights
"""
  def __init__ (self, signal):
    self.signal = signal
    self.bindings = []
    self.settings = EncodableDict()
  def add_binding_obj (self, binding_obj):
    self.bindings.append(binding_obj)
    return binding_obj
  def add_binding_str (self, binding_str):
    bindinfo = BindingFactory.parse(binding_str)
    return self.add_binding_obj(bindinfo)
  def encode_pair (self):
    lop = []

    kv_bindings = []
    for binding in self.bindings:
      entry = ('binding', str(binding))
      kv_bindings.append(entry)
    lop.append( ('bindings', kv_bindings) )

    if self.settings:
      lop.append( self.settings.encode_pair() )

    whole = ( (str(self.signal),lop) )
    return whole
  def encode_kv (self):
    kv = scvdf.DictMultivalue()
    kv_bindings = scvdf.DictMultivalue()
    for binding in self.bindings:
      kv_bindings['binding'] = str(binding)
    kv['bindings'] = kv_bindings
    if self.settings:
      kv['settings'] = self.settings.encode_kv()
    return kv
  @staticmethod
  def decode_kv (kv, parentkey=None):
    retval = Activator(parentkey)
    for (bind_name, bind_val) in kv['bindings'].items():
      if bind_name == 'binding':
        retval.add_binding_str(bind_val)
    if 'settings' in kv:
      retval.settings = EncodableDict.decode_kv(kv['settings'], 'settings')
    return retval


class ControllerInput (object):
  """An input description within a group."""
  def __init__ (self, input_element):
    self.ideal_input = input_element
    self.activators = []
  def make_activator (self, activator_signal):
    activator = Activator(activator_signal)
    self.activators.append(activator)
    return activator
  def encode_pair (self):
    lop = []
    kv_activators = []
    if self.activators:
      for activator in self.activators:
        kv_activators.append( activator.encode_pair() )
    lop.append( ('activators', kv_activators) )

    whole = ( self.ideal_input, lop )
    return whole
  def encode_kv (self):
    kv = scvdf.DictMultivalue()
    kv_activators = scvdf.DictMultivalue()
    if self.activators:
      for activator in self.activators:
        #kv_activators.append( activator.encode_pair() )
        signal = activator.signal
        kv_activators[signal] = activator.encode_kv()
    kv['activators'] = kv_activators
    return kv
  @staticmethod
  def decode_kv (kv, parentkey=None):
    retval = ControllerInput(parentkey)
    for (act_signal,act_kv) in kv['activators'].items():
      act = Activator.decode_kv(act_kv, act_signal)
      #act.signal = act_signal
      retval.activators.append(act)
    return retval


class Group (object):
  """A group of controls.
Multiple controller elements combine together into groups that act as a unit to form a higher-order input type.
Notable example include the four cardinal points of a d-pad to form not just a d-pad, but also pie menu control.
"""
  def __init__ (self):
    self.index = 0
    self.mode = ""
    self.inputs = EncodableDict('inputs')
    self.settings = EncodableDict()

  def make_input (self, cluster):
    cipt = ControllerInput(cluster)
    self.inputs[cluster] = cipt
    return cipt

  def encode_pair (self):
    lop = []
    lop.append( ('id', str(self.index)) )
    lop.append( ('mode', str(self.mode)) )

    # Always generate ['inputs']
    lop.append( self.inputs.encode_pair() )

    if self.settings:
      lop.append( self.settings.encode_pair() )

    whole = ('group', lop)
    return whole

  def encode_kv (self):
    kv = scvdf.DictMultivalue()
    kv['id'] = str(self.index)
    kv['mode'] = str(self.mode)

    # Always generate ['inputs']
    kv['inputs'] = self.inputs.encode_kv()

    if self.settings:
      kv['settings'] = self.settings.encode_kv()

    return kv

  @staticmethod
  def decode_kv (kv, parentkey=None):
    retval = Group()
    retval.index = int(kv['id'])
    retval.mode = kv['mode']
    for (inp_name,inp_kv) in kv['inputs'].items():
      inp = ControllerInput.decode_kv(inp_kv, inp_name)
      #inp.ideal_input = inp_name
      retval.inputs[inp_name] = inp
    if 'settings' in kv:
      retval.settings = EncodableDict.decode_kv(kv['settings'], 'settings')
    return retval


class Overlay (object):
  """base for ActionSet and ActionLayer.
tier=0 => ActionSet (set_layer=0)
tier=1 => ActionLayer (set_layer=1)

N.B. tier / set_layer
Apparently, 'set' and 'layer' in 'set_layer' are both nouns are referring to
"(Is) Action Set" and "(Is) Action Layer", and not verb/noun to mean assigning
a layer value.
That is, 'set_layer' can be read as "is this a Set or a Layer?"
The name "tier" is used to (a) avoid the multiple meanings available for these words, and (b) avoid presuming there will only ever be two values.
The idea is that "tier 0" establishes the maximum coverage of actions (i.e. the foundation), and "tier 1" extends or overlays tier 0 (stacks on top of).
"""
  def __init__ (self, title, tier=0, legacy=True, index=None, parent=None):
    self.index = index
    self.title = title
    self.tier = tier
    self.legacy = legacy
    self.parent_name = parent

  def encode_kv (self):
    kv = scvdf.DictMultivalue()
    kv['title'] = str(self.title)
    kv['legacy_set'] = str(int(bool(self.legacy)))
    if self.tier == 1:
      kv['set_layer'] = "1"
    if self.parent_name:
      kv['parent_set_name'] = self.parent_name
    return kv


class ActionLayer (Overlay):
  """tuple_key='action_layer'
Action Layer, consists of one or more  ...
"""
  # Change legacy default to False when native (non-legacy) binds become more prevalent.
  def __init__ (self, title, legacy=True, parent_name=None, index=None):
    Overlay.__init__(self, title, 1, legacy, index=index, parent=parent_name)

  @staticmethod
  def decode_kv (kv, parentkey=None):
    retval = ActionLayer(kv['title'], bool(kv.get('legacy_set',None)), kv.get("parent_set_name", None), index=parentkey)
    return retval


class ActionSet (Overlay):
  """An 'Action Set', consists of one or more Actions Layers."""
  def __init__ (self, title, legacy=True, parent_name=None, index=None):
    Overlay.__init__(self, title, 0, legacy, index=index, parent=parent_name)

  @staticmethod
  def decode_kv (kv, parentkey=None):
    retval = ActionSet(kv['title'], bool(kv.get('legacy_set',None)), index=parentkey)
    return retval


class GroupSourceBinding (object):
  VALID_GROUPS = [
    "switch", "dpad", "button_diamond", "left_trigger", "right_trigger",
    "joystick", "right_joystick"
    ]
  def __init__ (self, groupsrc, active=True, modeshift=False):
    self.groupid = 0
    self.grpsrc = groupsrc
    self.active = active
    self.modeshift = modeshift

  def _encode (self):
    rhs = []
    rhs.append(self.grpsrc)
    if self.active:
      rhs.append("active")
    else:
      rhs.append("inactive")
    if self.modeshift:
      rhs.append("modeshift")
    retval = ' '.join(rhs)
    return retval

  def encode_pair (self):
    encoding = self._encode()
    whole = ( str(self.groupid), encoding )
    return whole

  def encode_kv (self):
    return self._encode()


class Preset (object):
  def __init__ (self):
    self.index = 0
    self.name = ""
    self.gsb = []

  def add_gsb (self, groupid, groupsrc, active=True, modeshift=False):
    gsb = GroupSourceBinding(groupsrc, active, modeshift)
    gsb.groupid = groupid
    self.gsb.append(gsb)
    return gsb

  def encode_pair (self):
    lop = []
    lop.append( ('id', str(self.index)) )
    lop.append( ('name', str(self.name)) )

    kv_gsb = []
    for elt in self.gsb:
      kv_gsb.append(elt.encode_pair())
    lop.append( ('group_source_bindings', kv_gsb) )

    whole = ('preset', lop)
    return whole

  def encode_kv (self):
    kv = scvdf.DictMultivalue()
    kv['id'] = str(self.index)
    kv['name'] = str(self.name)

    kv_gsb = scvdf.DictMultivalue()
    for elt in self.gsb:
      gid = str(elt.groupid)
      kv_gsb[gid] = elt.encode_kv()
    kv['group_source_bindings'] = kv_gsb

    return kv

  @staticmethod
  def decode_kv (kv, parentkey=None):
    retval = Preset()
    retval.index = int(kv['id'])
    retval.name = kv['name']
    for gid in kv['group_source_bindings']:
      binding = kv['group_source_bindings'][gid]
      parts = binding.split(' ',2)
      groupsrc = parts[0]
      active = (parts[1] == 'active')
      modeshift = (parts[2] == 'modeshift' if len(parts) > 2 else False)
      gsb = GroupSourceBinding(groupsrc, active, modeshift)
      gsb.groupid = int(gid)
      retval.gsb.append(gsb)
    return retval


class Mapping (object):
  """Encapsulates controller mapping (toplevel)"""
  def __init__ (self, version=3):
    self.version = version
    self.revision = 0
    self.title = "Unnamed"
    self.description = "Unnamed configuration"
    self.creator = 0
    self.controller_type = "controller_ps3"
    self.timestamp = "0"
    # List of Action Sets
    self.actions = []
    # List of Action Layers
    self.layers = []
    # List of Groups
    self.groups = []
    # List of Presets
    self.presets = []
    # Miscellaneous settings
    self.settings = EncodableDict()

  def make_group (self, mode, index=None):
    groupid = index
    if groupid is None:
      # TODO: auto-index
      groupid = -1
    group = Group()
    group.index = groupid
    group.mode = mode
    self.groups.append(group)
    return group

  def make_preset (self, name, index=None):
    # TODO: determine unique presetid by scanning.
    presetid = 0
    preset = Preset()
    preset.index = presetid
    preset.name = name
    self.presets.append(preset)
    return preset

  def encode_pair (self):
    lop = []
    lop.append( ('version', str(self.version)) )
    lop.append( ('revision', str(self.revision)) )
    lop.append( ('title', str(self.title)) )
    lop.append( ('description', str(self.description)) )
    lop.append( ('creator', str(self.creator)) )
    lop.append( ('controller_type', str(self.controller_type)) )
    lop.append( ('Timestamp', str(self.timestamp)) )

    for grp in self.groups:
      lop.append( grp.encode_pair() )
    for preset in self.presets:
      lop.append( preset.encode_pair() )
    if self.settings:
      lop.append( self.settings.encode_pair() )

    whole = ('controller_mappings', lop)
    return whole

  def encode_overlays (self, overlay_store, gensym=0):
    """Helper function to encode the overlays: Action Set, Action Layer."""
    kv = scvdf.DictMultivalue()
    for obj in overlay_store:
      pair_name = obj.index
      pair_val = obj.encode_kv()
      kv[pair_name] = pair_val
    return kv

  def encode_kv (self):
    """Encode object to list of pairs (scvdf)."""
    kv = scvdf.DictMultivalue()
    kv['version'] = str(self.version)
    kv['revision'] = str(self.revision)
    kv['title'] = str(self.title)
    kv['description'] = str(self.description)
    kv['creator'] = str(self.creator)
    kv['controller_type'] = str(self.controller_type)
    kv['Timestamp'] = str(self.timestamp)

    # Alright, this gets weird.
## 'internal' refers to internal to Steam Client and therefore not available for direct inspection;
## 'name' refers to the VDF keys of the form "Preset_*" underneath the 'actions' and 'action_layers' keys, associated with an action set/layer;
## 'title' is differentiated as the user-supplied and/or shown text in the Steam Client associated with the Action Set or Action Layer;
## 'set' and 'ActionSet' are shorthand for Action Set (members of 'actions' field);
## 'layer' and 'ActionLayer' are shorthand for Action Layer (members of 'action_layers' field);
## 'overlay' is an umbrella term referring to Action Set and Action Layer.
#
# ActionSet and ActionLayer appear to be the same internal object, and differ by the 'set_layer' field.
# All overlays appear to be internally stored in a shared/common list or pool, since "Preset_*" names increment monotonically from one section into the other.
# The "Preset_*" names also have a suspiciously precise string length, and are not saved across revisions (changes to config from within Steam Client).
# The action layer commands refer to action layers by id number (2) instead of name ("Preset_*") nor title ("New Action Layer").
# The above behavior led to a bug where creating Action Layer binds, then adding a new Action Set, causes all the Action Layer binds to refer to the wrong layer -- off by one (and more for each additional Action Set created).
# Thus, it appears the "Preset_*" names are acting like a very-large-base number correlating to the (internal) id of the action/layer.
# Order seems to enforced by lexicographical sort of the names.
#
# Contrast to 'groups':
# The instances of Group ('groups') are written to the VDF separately for each instance, and differentiated by a nested "id" key/value, thereby leading to multiple instances of the "groups" key but with different associated values.
# The instances of Action set/layers are each given unique names and made the value of that name in 'actions' or 'action_layers'.
#
# Consequeces to iteration:
# * 'groups': either keep sorted by nested "id" key, or brute-force finding instance with the desired "id" key.
#  * 'actions', 'action_layers': The overlays are in no particular order (as per nature of mapping type), but may be iterated in the proper sequence by sorting their names.

    if self.actions:
      kv['actions'] = self.encode_overlays(self.actions)

    if self.layers:
      kv['action_layers'] = self.encode_overlays(self.layers)

    for grp in self.groups:
      kv['group'] = grp.encode_kv()

    for preset in self.presets:
      kv['preset'] = preset.encode_kv()

    if self.settings:
      kv['settings'] = self.settings.encode_kv()

    return kv

  @staticmethod
  def decode_kv (kv, parentkey=None):
    retval = Mapping(int(kv['version']))
    retval.revision = int(kv['revision'])
    retval.title = kv['title']
    retval.description = kv['description']
    retval.creator = kv['creator']
    retval.controller_type = kv['controller_type']
    retval.timestamp = kv['Timestamp']
    if 'actions' in kv:
      for act_name in kv['actions']:
        act_kv = kv['actions'][act_name]
        actset = ActionSet.decode_kv(act_kv, act_name)
        retval.actions.append(actset)
    if 'action_layers' in kv:
      for lyr_name in kv['action_layers']:
        lyr_kv = kv['action_layers'][lyr_name]
        layer = ActionLayer.decode_kv(lyr_kv, lyr_name)
        retval.layers.append(layer)
    for grp_kv in kv.get_all('group', []):
      grp = Group.decode_kv(grp_kv, 'group')
      retval.groups.append(grp)
    for preset_kv in kv.get_all('preset',[]):
      preset = Preset.decode_kv(preset_kv, 'preset')
      retval.presets.append(preset)
    if 'settings' in kv:
      retval.settings = EncodableDict.decode_kv(kv['settings'], 'settings')
    return retval


class ControllerConfig (object):
  def __init__ (self):
    self.mappings = []

  def make_mapping (self, version=3):
    mapping = Mapping(version)
    self.mappings.append(mapping)
    return mapping

  def encode_pair  (self):
    lop = []
    for m in self.mappings:
      lop.append( m.encode_pair() )
    return lop
  def encode_kv (self):
    kv = scvdf.DictMultivalue()
    for m in self.mappings:
      kv['controller_mappings'] = m.encode_kv()
    return kv

  @staticmethod
  def decode_kv (kv, parentkey=None):
    retval = ControllerConfig()
    for valmap in kv.get_all('controller_mappings', []):
      mapping = Mapping.decode_kv(valmap, 'controller_mappings')
      retval.mappings.append(mapping)
    return retval

