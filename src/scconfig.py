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

class BindingEmpty (BindingBase):
  """alias for Binding_Host('empty_binding')"""
  def __init__ (self):
    pass

class Binding_Keystroke (BindingBase):
  def __init__ (self, keycode, label=None):
    BindingBase.__init__(self, "key_press", keycode, label)

class Binding_MouseSwitch (BindingBase):
  TRANSLATE_BUTTON = {
    "1": "LEFT", "2": "MIDDLE", "3": "RIGHT",
    "4": "BACK", "5": "FORWARD"
    }
  TRANSLATE_WHEEL = {
    "u": "SCROLL_UP", "d": "SCROLL_DOWN",
    }
  def __init__ (self, evdetails, label=None):
    if evdetails in self.TRANSLATE_BUTTON:
      vdfliteral = self.TRANSLATE_BUTTON[evdetails]
      BindingBase.__init__(self, "mouse_button", vdfliteral, self.label)
    elif evdetails in self.TRANSLATE_WHEEL:
      vdfliteral = self.TRANSLATE_WHEEL[evdetails]
      BindingBase.__init__(self, "mouse_wheel", vdfliteral, self.label)
    else:
      raise("Unknown mouse keysym '{}'".format(evdetails))

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
    caps_keycode = keycode.upper()
    vdfliteral = None

    valuelist = self.TRANSLATION.values()
    if (caps_keycode in valuelist) or (keycode in valuelist):
      vdfliteral = keycode

    # Try mapping.
    if vdfliteral is None:
      vdfliteral = self.TRANSLATION.get(keycode, None)
      if vdfliteral is None:
        vdfliteral = self.TRANSLATION.get(caps_keycode, None)

    if vdfliteral is not None:
      BindingBase.__init__(self, "xinput_button", [vdfliteral], label)
    else:
      raise KeyError("Unknown xpad keysym '{}'.".format(keycode))

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
    pass

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
    self.R = R
    self.G = G
    self.B = B
    self.X = X
    self.L = L
    self.M = M
    BindingBase.__init__(self, "set_led", (R,G,B,X,L,M), label)




def decode_binding (binding):
  retval = None
  #print("BINDING = %r" % (binding,))
  fragments = binding.split(',')
  payload = fragments[0]
  label = fragments[1] if len(fragments) > 1 else None
  cmd, *args = payload.split(' ')
#  print("parts={!r}".format(parts))
  if cmd == 'xinput_button':
    keysym = args[0]
    retval = Binding_Gamepad(keysym, label)
  elif cmd == 'key_press':
    keysym = args[0]
    retval = Binding_Keystroke(keysym)
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
    bindinfo = decode_binding(binding_str)
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

    if self.inputs:
      lop.append( self.inputs.encode_pair() )

    if self.settings:
      lop.append( self.settings.encode_pair() )

    whole = ('group', lop)
    return whole

  def encode_kv (self):
    kv = scvdf.DictMultivalue()
    kv['id'] = str(self.index)
    kv['mode'] = str(self.mode)

    if self.inputs:
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


class ActionLayer (object):
  """tuple_key='action_layer'
Action Layer, consists of one or more  ...
"""
  pass


class ActionSet (object):
  """An 'Action Set', consists of one or more Actions Layers."""
  pass


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

    # TODO: action sets
    # TODO: action layers

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

