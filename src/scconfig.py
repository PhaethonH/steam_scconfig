#!/usr/bin/env python3
# encoding=utf-8

# Configurator module for Steam Valve Controller

# Uses SCVDF for reading and writing VDF files.

import scvdf



####################
# Helper functions #
####################


# Helper function for iterating SCVDFDict values -- helps simplify iteration as: for x in get_all(dictMultivalueInstance)
def get_all (container, key, default_value):
  if key in container:
    val = container[key]
    if not isinstance(val, list):
      return [ val ]
    else:
      return iter(val)
  else:
    return default_value


# Convert dict type to list-of-pairs (list of 2-tuples).
def dict2lop (kv_dict):
  lop = []
  for k,v in kv_dict.items():
    lop.append( (k,str(v)) )
  return lop


# Helper class for commonly recurring 'settings' field, which is all-scalar.
class EncodableDict (object):
  def __init__ (self, index=None, copyfrom=None):
    if index is None:
      index = VSC_SETTINGS
    elif isinstance(index,dict):
      # and would imply copyfrom is missing.
      copyfrom = index
      index = None
    self.index = index
    self.valid_keys = []  # also maintain order.
    self.store = {}
    if isinstance(copyfrom,dict):
      for k,v in copyfrom.items():
        self[k] = v
  def __setitem__ (self, k, v):
    self.valid_keys.append(k)
    self.store[k] = v
  def __getitem__ (self, k):
    return self.store[k]
  def __delitem__ (self, k):
    del self.store[k]
    self.valid_keys.remove(k)
  def keys (self):
    return self.valid_keys
  def items (self):
    for k in self.valid_keys:
      v = self.store[k]
      yield (k,v)
    return
  def values (self):
    for k in self.valid_keys:
      v = self.store[k]
      yield v
    return
  def update (self, d):
    for (k,v) in d.items():
      self[k] = v
  def encode_pair (self):
    lop = []
    for k in self.valid_keys:
      v = self.store[k]
      try:
        lop.append(v.encode_pair())
      except AttributeError as e:
        lop.append( (k,str(v)) )
    whole = (self.index, lop)
    return whole
  def encode_kv (self):
    kv = scvdf.SCVDFDict()
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


def filter_enum (enum_mapping, initval):
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


def mangle_vdfliteral (s):
  """mangle binding, to embed warning messages in vdf/Steam Client."""
  retval = s.replace('"', "'").replace("//", "/").replace(",", ";")
  return retval


def _stringlike (x):
  try: return callable(x.isalpha)
  except AttributeError: return False


# VSC config keywords.
VSC_KEYPRESS = "key_press"
VSC_MOUSEBUTTON = "mouse_button"
VSC_MOUSEWHEEL = "mouse_wheel"
VSC_SETLED = "set_led"
VSC_CONTROLLERACTION = "controller_action"
VSC_GAMEPADBUTTON = "xinput_button"
VSC_EMPTYBINDING = "empty_binding"
VSC_MODE_SHIFT = "mode_shift"   # with underscore, in bindings{}
VSC_MODESHIFT = "modeshift"     # without underscore, in preset{}
VSC_ACTIVE = "active"
VSC_INACTIVE = "inactive"

VSC_SETTINGS = "settings"
VSC_INPUTS = "inputs"




##########################
# Substantiative objects #
##########################


class IconInfo (object):
  """Icon info, third portion of "binding" command, for radial menus."""
  def __init__ (self, path=None, bg=None, fg=None, *args):
    if path and len(path)>0 and ' ' in path:
      # split in place.
      # TODO: parse quoted, escaped, space-in-path?
      words = path.split(None,3)
      path = words[0]
      bg = words[1]
      fg = words[2]
      # ignore fourth space and after.
    self.path = path
    self.bg = bg
    self.fg = fg
  def __str__ (self):
    return ' '.join([self.path, self.bg, self.fg])
  def __repr__ (self):
    return "{}(path={!r},bg={!r},fg={!r})".format(
            self.__class__.__name__,
            self.path, self.bg, self.fg)


# Evgen = Event Generator (Synthesis)

class EvgenBase (object):
  """One binding instance in a list of many, as part of Activate"""
  ALIASES = []
  def __init__ (self, evtype, *details):
    """
'details' for simplified static storage case.

'details' are used for printing, concatenated with the base command.

More complex details should implement/override _get_details(), which should return a list of strings to be concatenated after the base command.
"""
    self._evtype = evtype
    self._evdetails = details  # default [].
  def _get_evdetails (self):
    return self._evdetails
  def __str__ (self):
    if not self._evtype:
      return ""
    words = [self._evtype]
    evdetails = self._get_evdetails()
    if evdetails:
      words.extend(self._evdetails)
    retval = " ".join(words)
    return retval
  def __repr__ (self):
    details = self._get_evdetails()
    if details:
      if len(details) == 1:
        return "{}({!r})".format(self.__class__.__name__, details[0])
      else:
        return "{}{!r}".format(self.__class__.__name__, tuple(details))
    else:
      return "{}()".format(self.__class__.__name__)


class Evgen_Invalid (EvgenBase):
  """Placeholder for unknown event generators to preserve across edits."""
  def __init__ (self, *args):
    EvgenBase.__init__(self, *args)


class Evgen_Empty (EvgenBase):
  """alias for Evgen_Host('empty_binding')"""
  ALIASES = [ VSC_CONTROLLERACTION ]
  def __init__ (self, strict_match=None, *args):
    if strict_match is not None:
      if strict_match != 'empty_binding':
        raise ValueError("Invalid argument to initializer: {!r}".format(strict_match))
    EvgenBase.__init__(self, VSC_CONTROLLERACTION, VSC_EMPTYBINDING)

  def __repr__ (self):
    return "{}()".format(self.__class__.__name__)


class Evgen_Keystroke (EvgenBase):
  ALIASES = [ VSC_KEYPRESS ]
  def __init__ (self, evcode):
    EvgenBase.__init__(self, VSC_KEYPRESS, evcode)


class Evgen_MouseSwitch (EvgenBase):
  ALIASES = [ VSC_MOUSEBUTTON, VSC_MOUSEWHEEL ]
  TRANSLATE_BUTTON = {
    "1": "LEFT", "2": "MIDDLE", "3": "RIGHT",
    "4": "BACK", "5": "FORWARD"
    }
  TRANSLATE_WHEEL = {
    "u": "SCROLL_UP", "d": "SCROLL_DOWN",
    }
  def __init__ (self, evcode):
    major, vdfliteral = None, None
    if vdfliteral is None:
      vdfliteral = filter_enum(self.TRANSLATE_BUTTON, evcode)
      major = VSC_MOUSEBUTTON if vdfliteral else None
    if vdfliteral is None:
      vdfliteral = filter_enum(self.TRANSLATE_WHEEL, evcode)
      major = VSC_MOUSEWHEEL if vdfliteral else None
    if major and vdfliteral:
      EvgenBase.__init__(self, major, vdfliteral)
    else:
      raise ValueError("Unknown mouse evcode '{}'".format(evcode))


class Evgen_Gamepad (EvgenBase):
  ALIASES = [ VSC_GAMEPADBUTTON ]
  TRANSLATION = {
    "A": "A", "B": "B", "X": "X", "Y": "Y",
    "LB": "SHOULDER_LEFT", "RB": "SHOULDER_RIGHT",
    "LT": "TRIGGER_LEFT", "RT": "TRIGGER_RIGHT",
    "DUP": "DPAD_UP", "DDN": "DPAD_DOWN", "DLT": "DPAD_LEFT", "DRT": "DPAD_RIGHT",
    "BK": "SELECT", "ST": "START", "LS": "JOYSTICK_LEFT", "RS": "JOYSTICK_RIGHT",
    "LJx": "LSTICK_LEFT", "LJX": "LSTICK_RIGHT", "LJy": "LSTICK_UP", "LJY": "LSTICK_DOWN",
    "RJx": "RSTICK_LEFT", "LJX": "RSTICK_RIGHT", "LJy": "RSTICK_UP", "LJY": "RSTICK_DOWN",
    }
  def __init__ (self, evcode):
    vdfliteral = filter_enum(self.TRANSLATION, evcode)
    if vdfliteral is not None:
      EvgenBase.__init__(self, VSC_GAMEPADBUTTON, vdfliteral)
    else:
      raise KeyError("Unknown xpad evcode '{}'.".format(evcode))


class Evgen_Host (EvgenBase):
  ALIASES = [ VSC_CONTROLLERACTION ]
  """Host operations."""
  TRANSLATION = {
#    'empty': "empty_binding",
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
  def __init__ (self, details):
    vdfliteral = filter_enum(self.TRANSLATION, details)
    if vdfliteral is None:
      mangle = mangle_vdfliteral(details)
      raise ValueError("Unknown host action '{}'".format(mangled))
    EvgenBase.__init__(self, VSC_CONTROLLERACTION, vdfliteral)


class Evgen_Light (EvgenBase):
  ALIASES = [ VSC_CONTROLLERACTION ]
  """Set controller LED - color and/or brightness.

R : red value, 0..255
G : green value, 0..255
B : blue value, 0..255
X : unknown, 100
L : brightness, 0..255 (off to brightest)
M : 0=UserPrefs (ignore R,G,B,X,L), 1=use R,G,B,L values, 2=set by XInput ID (ignore R,G,B,X,L)
"""
  def __init__ (self, major, R, G, B, X, L, M):
    EvgenBase.__init__(self, VSC_CONTROLLERACTION, VSC_SETLED, R, G, B, X, L, M)
    self.R = R
    self.G = G
    self.B = B
    self.X = X
    self.L = L
    self.M = M


class Evgen_Overlay (EvgenBase):
  ALIASES = [ VSC_CONTROLLERACTION ]
  """Control overlays."""
  ACTIONS = {
    "apply_layer": "add_layer",
    "apply": "add_layer",
    "peel_layer": "remove_layer",
    "peel": "remove_layer",
    "hold_layer": "hold_layer",
    "hold": "hold_layer",
    "change": "change_preset",
  }
  def __init__ (self, actionspec, target_id, frob0, frob1):
    vdfliteral = filter_enum(self.ACTIONS, actionspec)
    if vdfliteral is None:
      raise ValueError("Unknown overlay action '{}'".format(vdfliteral))
    marshal = [ vdfliteral, str(target_id), str(frob0), str(frob1) ]
    EvgenBase.__init__(self, VSC_CONTROLLERACTION, *marshal)
    self.target_id = target_id
    self.frob0 = frob0
    self.frob1 = frob1


class Evgen_Modeshift (EvgenBase):
  ALIASES = [ VSC_MODE_SHIFT ]
  ACCEPTABLE = [
    "left_trackpad", "right_trackpad",
    "left_trigger", "right_trigger",
    "dpad", "button_diamond",
    "joystick", "right_joystick",
    "gyro"
    ]
  def __init__ (self, input_source, group_id):
    vdfliteral = filter_enum(self.ACCEPTABLE, input_source)
    EvgenBase.__init__(self, VSC_MODE_SHIFT, vdfliteral, str(group_id))
    self.inpsrc = vdfliteral
    self.group_id = group_id



class EvgenFactory (object):
  @staticmethod
  def make_empty ():
    return Evgen_Empty()
  @staticmethod
  def make_keystroke (synthsym):
    return Evgen_Keystroke(synthsym)
  @staticmethod
  def make_mouseswitch (synthsym):
    return Evgen_MouseSwitch(synthsym)
  @staticmethod
  def make_gamepad (synthsym):
    return Evgen_Gamepad(synthsym)
  @staticmethod
  def make_hostcall (hostreq):
    return Evgen_Host(hostreq)
  @staticmethod
  def make_light (led_mode, red, green, blue, unk, brightness):
    return Evgen_Light(red, green, blue, unk, brightness, mode)
  @staticmethod
  def make_overlay (subcmd, layer_id=0, set_id=0, unk=0):
    return Evgen_Overlay(subcmd, layer_id, set_id, unk)
  @staticmethod
  def make_modeshift (inpsrc, grpid):
    return Evgen_Modeshift(inpsrc, grpid)
  @staticmethod
  def make_controller_action (*args):
    if len(args) > 4:
      return EvgenFactory.make_overlay(*args[:4])
    elif args[0] in [ 'empty_binding', 'empty', None ]:
      return Evgen_Empty()
    else:
      mangled = mangle_vdfliteral(' '.join(args))
      return Evgen_Empty("UNKNOWN_CONTROLLER_ACTION({})".format(mangled))

  @staticmethod
  def _parse (bindstr):
    words = bindstr.split()
    return words

  @staticmethod
  def make (*args):
    if len(args) == 1 and ' ' in args[0]:
      # parse in place.
      in_str = args[0]
      args = EvgenFactory._parse(in_str)
    ATTEMPTS = [
      # Roughly in order of most initializer arguments to least.
      Evgen_Light,
      Evgen_Overlay,
      Evgen_Modeshift,
      Evgen_MouseSwitch,
      Evgen_Keystroke,
      Evgen_Gamepad,
      Evgen_Host,
      Evgen_Empty,
      ]
    retval = None
    for gencls in ATTEMPTS:
      if args[0] in gencls.ALIASES:
        try:
          retval = gencls(*args[1:])
          break
        except:
          retval = None
    if args[0] in Evgen_Empty.ALIASES and args[1] == 'empty_binding':
      retval = Evgen_Empty()
    if retval is None:
      retval = Evgen_Invalid(*args)
    return retval


class Binding (object):
  """Binding object connects:
  1. Evgen object
  2. a label
  3. Icon info
"""
  def __init__ (self, geninfo, label=None, iconinfo=None):
    if _stringlike(geninfo):
      # parse in place.
      geninfo, label, iconinfo = self._parse(geninfo)
    self.geninfo = geninfo
    self.label = label
    self.iconinfo = iconinfo

  def __str__ (self):
    """Generate string suited for VDF output."""
    phrases = []
    phrases.append(self.geninfo.__str__())
    if self.label:
      while len(phrases) < 1: phrases.append('')
      phrases.append(self.label)
    if self.iconinfo:
      while len(phrases) < 2: phrases.append('')
      phrases.append(self.iconinfo.__str__())
    retval = ', '.join(phrases)
    return retval

  def __repr__ (self):
    return "{}(geninfo={!r}, label={!r}, iconinfo={!r})".format(
              self.__class__.__name__,
              self.geninfo,
              self.label,
              self.iconinfo)

  @staticmethod
  def _parse (s):
    phrases = s.split(', ')
    geninfo = EvgenFactory.make(phrases[0])
    label = phrases[1] if len(phrases) > 1 else None
    # TODO: better parse/convert.
    iconinfo = IconInfo(*(phrases[2].split())) if len(phrases) > 2 else None
    retval = (geninfo, label, iconinfo)
    return retval




### end of Binding and Bindings related classes ###



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
  def __init__ (self, signal, py_bindings=None, **kwargs):
    self.signal = signal
    self.bindings = []
    self.settings = EncodableDict(VSC_SETTINGS)

    if py_bindings:
      # expect list of pyobject.
      self.bindings.extend(py_bindings)
    elif 'bindings' in kwargs:
      for bind_name, bind_val in kwargs['bindings'].items():
        if bind_name == "binding":
          self.add_binding_str(bind_val)

    if VSC_SETTINGS in kwargs:
      self.settings.update(kwargs[VSC_SETTINGS])

  def add_binding_obj (self, binding_obj):
    self.bindings.append(binding_obj)
    return binding_obj
  def add_binding_str (self, binding_str):
    #bindinfo = EvgenFactory.parse(binding_str)
    bindinfo = Binding(binding_str)
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
    kv = scvdf.SCVDFDict()
    kv_bindings = scvdf.SCVDFDict()
    for binding in self.bindings:
      kv_bindings['binding'] = str(binding)
    kv['bindings'] = kv_bindings
    if self.settings:
      kv[VSC_SETTINGS] = self.settings.encode_kv()
    return kv


class ControllerInput (object):
  """An input description within a group."""
  def __init__ (self, input_element, py_activators=None, **kwargs):
    self.ideal_input = input_element
    self.activators = []
    if py_activators:
      # expect list of pyobject
      self.activators.extend(py_activators)
    elif 'activators' in kwargs:
      for (act_signal, act_kv) in kwargs['activators'].items():
        self.make_activator(act_signal, **act_kv)
  def make_activator (self, activator_signal, **kwargs):
    activator = Activator(activator_signal, **kwargs)
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
    kv = scvdf.SCVDFDict()
    kv_activators = scvdf.SCVDFDict()
    if self.activators:
      for activator in self.activators:
        #kv_activators.append( activator.encode_pair() )
        signal = activator.signal
        kv_activators[signal] = activator.encode_kv()
    kv['activators'] = kv_activators
    return kv


# TODO: base class GroupBase.
# TODO: derived class for each Mode variant.
# TODO: change Group into factory class/namespace.

class GroupBase (object):
  """Base class for input groups: joystick, dpad, triggers, etc."""

  class SETTINGS:
    """namespace for settings keys."""
# starting with dpad
    REQUIRES_CLICK = "requires_click"
    LAYOUT = "layout"
    DEADZONE = "deadzone"
    EDGE_BINDING_RADIUS = "edge_binding_radius"
    EDGE_BINDING_INVERT = "edge_binding_invert"
    ANALOG_EMULATION_PERIOD = "analog_emulation_period"
    ANALOG_EMULATION_DUTY_CYCLE = "analog_emulation_duty_cycle"
    OVERLAP_REGION = "overlap_region"
    GYRO_BUTTON_INVERT = "gyro_button_invert"
    HAPTIC_INTENSITY_OVERRIDE = "haptic_intensity_override"
    GYRO_NEUTRAL = "gyro_neutral"
    GYRO_BUTTON = "gyro_button"

# four-buttons
    BUTTON_SIZE = "button_size"
    BUTTON_DIST = "button_dist"

# joystick-camera
    CURVE_EXPONENT = "curve_exponent"
    SWIPE_DURATION = "swipe_duration"
    HAPTIC_INTENSITY = "haptic_intensity"
    OUTPUT_JOYSTICK = "output_joystick"
    SENSITIVITY_VERT_SCALE = "sensitivity_vert_scale"
    ANTI_DEADZONE = "anti_deadzone"
    ANTI_DEADZONE_BUFFER = "anti_deadzone_buffer"
    INVERT_X = "invert_x"
    INVERT_Y = "invert_y"
    JOYSTICK_SMOOTHING = "joystick_smoothing"
    GYRO_AXIS = "gyro_axis"

# joystick-mouse
    CUSTOM_CURVE_EXPONENT = "custom_curve_exponent"
    DEADZONE_INNER_RADIUS = "deadzone_inner_radius"
    DEADZONE_OUTER_RADIUS = "deadzone_outer_radius"
    DEADZONE_SHAPE = "deadzone_shape"
    SENSITIVITY = "sensitivity"
    SENSITIVITY_HORIZ_SCALE = "sensitivity_horiz_scale"

# joystick-move
    GYRO_LOCK_EXTENTS = "gyro_lock_extents"
    GYRO_BUTTON_INVERT = "gyro_button_invert"
    OUTPUT_AXIS = "output_axis"

# mouse-joystick
    DOUBLETAP_BEEP = "doubletap_beep"
    TRACKBALL = "trackball"
    ROTATION = "rotation"
    FRICTION = "friction"
    FRICTION_VERT_SCALE = "friction_vert_scale"
    SENSITIVITY_VERT_SCALE = "sensitivity_vert_scale"
    MOUSE_MOVE_THRESHOLD = "mouse_move_threshold"
    EDGE_SPIN_VELOCITY = "edge_spin_velocity"
    EDGE_SPIN_RADIUS = "edge_spin_radius"
    DOUBLETAP_MAX_DURATION = "doubetap_max_duration"  # [sic]
    DOUBETAP_MAX_DURATION = DOUBLETAP_MAX_DURATION
    MOUSE_DAMPENING_TRIGGER = "mouse_dampening_trigger"
    MOUSE_TRIGGER_CLAMP_AMOUNT = "mouse_trigger_clamp_amount"
    MOUSEJOYSTICK_DEADZONE_X = "mousejoystick_deadzone_x"
    MOUSEJOYSTICK_DEADZONE_Y = "mousejoystick_deadzone_y"
    MOUSEJOYSTICK_PRECISION = "mousejoystick_precision"
    GYRO_SENSITIVITY_SCALE = "gyro_sensitivity_scale"

# mouse-region
    SCALE = "scale"
    POSITION_X = "position_x"
    POSITION_Y = "position_y"
    TELEPORT_STOP = "teleport_stop"

# radial-menu
    TOUCHMENU_BUTTON_FIRE_TYPE = "touchmenu_button_fire_type"
    TOUCH_MENU_OPACITY = "touch_menu_opacity"
    TOUCH_MENU_POSITION_X = "touch_menu_position_x"
    TOUCH_MENU_POSITION_Y = "touch_menu_position_y"
    TOUCH_MENU_SCALE = "touch_menu_scale"
    TOUCH_MENU_SHOW_LABELS = "touch_menu_show_labels"

# scrollwheel
    SCROLL_ANGLE = "scroll_angle"
    SCROLL_TYPE = "scroll_type"
    SCROLL_INVERT = "scroll_invert"
    SCROLL_WRAP = "scroll_wrap"
    SCROLL_FRICTION = "scroll_friction"

# touch-menu
    TOUCH_MENU_BUTTON_COUNT = "touch_menu_button_count"

# trigger
    ADAPTIVE_THRESHOLD = "adaptive_threshold"
    OUTPUT_TRIGGER = "output_trigger"

# absolute-mouse
    ACCELERATION = "acceleration"
    MOUSE_SMOOTHING = "mouse_smoothing"

  class Acceleration:
    """Values for 'acceleration'."""
    OFF = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3

  class CurveExponent:
    """Values for 'curve_exponent'."""
    LINEAR = 0
    AGGRESIVE = 1
    RELAXED = 2
    WIDE = 3
    EXTRA_WIDE = 4
    CUSTOM = 5

  class DeadzoneShape:
    CROSS = 0
    CIRCLE = 1
    SQUARE = 2

  class Friction:
    """Values for 'friction'."""
    OFF = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    DEFAULT = MEDIUM

  class GyroButton:
    """Values for 'gyro_button'."""
    ALWAYS = None   # actually, key itself should be missing.
    RIGHT_PAD_TOUCH = 1
    LEFT_PAD_TOUCH = 2
    RIGHT_PAD_CLICK = 3
    LEFT_PAD_CLICK = 4
    RIGHT_BUMPER = 5
    LEFT_BUMPER = 6
    RIGHT_GRIP = 7
    LEFT_GRIP = 8
    RIGHT_TRIGGER_FULL = 9
    LEFT_TRIGGER_FULL = 10
    RIGHT_TRIGGER_SOFT = 11
    LEFT_TRIGGER_SOFT = 12
    A = 13
    B = 14
    X = 15
    Y = 16
    LEFT_STICK_CLICK = 17

  class HapticIntensity:
    """Values for 'haptic_intensity'."""
    OFF = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3

  class MouseDampeningTrigger:
    """Values for 'mouse_dampening_trigger'."""
    NO = 0
    RIGHT_TRIGGER_SOFT_PULL = 1
    LEFT_TRIGGER_SOFT_PULL = 2
    BOTH_TRIGGER_SOFT_PULL = 3
    RIGHT_TRIGGER_FULL_PULL = 4
    LEFT_TRIGGER_FULL_PULL = 5
    BOTH_TRIGGER_FULL_PULL = 6

  class SwipeDuration:
    """Values for 'swipe_duration'."""
    OFF = 0
    LOW = 1
    MEDIUM = 2
    HIGH =3

  class OutputAxis:
    """Values for 'output_joystick'."""
    HORIZONTAL = 0
    VERTICAL = 1
    BOTH = 2

  class OutputTrigger:
    """Values for 'output_trigger'."""
    NO_ANALOG = 0
    LEFT_TRIGGER = 1
    RIGHT_TRIGGER = 2

  class TouchmenuButtonFireType:
    """Values for 'touchmenu_button_fire_type'."""
    BUTTON_CLICK = 0
    BUTTON_RELEASE = 1
    TOUCH_RELEASE_MODESHIFT_END = 2
    TOUCH_RELEASE = TOUCH_RELEASE_MODESHIFT_END
    MODESHIFT_END = TOUCH_RELEASE_MODESHIFT_END
    ALWAYS = 3

  # Constraints on settings values.
  # Tuples indicate an integer range, such that tuple[0] <= value <= tuple[1]
  # List specifies the set of acceptable values
  # class-object contains acceptable values: class.__dict__.values()
  # primitive type to indicate the allowable value type
  _Settings = {}

  def __init__ (self, py_mode=None, index=None, py_inputs=None, py_settings=None, **kwargs):
    if index is None:
      if 'id' in kwargs:
        index = int(kwargs['id'])
    if index is None:
      index = 0

#    if py_mode is None:
#      if 'mode' in kwargs:
#        py_mode = kwargs['mode']
#    py_mode = filter_enum(self.MODES, py_mode)

    self.index = index
    self.mode = py_mode
    self.inputs = EncodableDict(VSC_INPUTS)
    self.settings = EncodableDict(VSC_SETTINGS)

    if py_inputs:
      # Expect dictionary of key to pyobjects.
      self.inputs.update(inputs)
    elif VSC_INPUTS in kwargs:
      # expect dict within ControllerConfig
      for (inp_name, inp_kv) in kwargs[VSC_INPUTS].items():
        self.make_input(inp_name, **inp_kv)

    if py_settings:
      # Expect dictionary of pure scalars.  This might break in future?
      self.settings.update(settings)
    elif VSC_SETTINGS in kwargs:
      self.settings.update(kwargs[VSC_SETTINGS])

  def make_input (self, input_element, py_activators=None, **kwargs):
    '''Factory for 'input' node.'''
    inp = ControllerInput(input_element, py_activators=py_activators, **kwargs)
    self.inputs[input_element] = inp
    return inp


class AbsoluteMouse (GroupBase):
  CLICK = "click"
  DOUBLETAP = "doubletap"
  TOUCH = "toucH"
  INPUTS = set([
    CLICK, DOUBLETAP, TOUCH
    ])

  class Friction:
    """Values for 'friction."""
    OFF = 0    # no inertia -- do not spin at all
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    NONE = 4   # no-friction -- spin forever

  S = GroupBase.SETTINGS
  _Settings = {
    S.SENSITIVITY: (1, 1000),
    S.TRACKBALL: bool,
    S.DOUBLETAP_BEEP: bool,
    S.INVERT_X: bool,
    S.INVERT_Y: bool,
    S.HAPTIC_INTENSITY: GroupBase.HapticIntensity,
    S.ROTATION: (-30, 30),
    S.FRICTION: Friction,
    S.FRICTION_VERT_SCALE: (0, 200),
    S.SENSITIVITY_VERT_SCALE: (0, 200),
    S.ACCELERATION: GroupBase.Acceleration,
    S.MOUSE_MOVE_THRESHOLD: (0, 40),
    S.MOUSE_SMOOTHING: (0, 40),
    S.EDGE_SPIN_VELOCITY: (0, 1000),
    S.EDGE_SPIN_RADIUS: (0, 32767),
    S.DOUBLETAP_MAX_DURATION: (20, 500),
    S.MOUSE_DAMPENING_TRIGGER: GroupBase.MouseDampeningTrigger,
    S.MOUSE_TRIGGER_CLAMP_AMOUNT: (0, 100),
    S.GYRO_AXIS: [ 0, 1 ],
    S.GYRO_BUTTON: GroupBase.GyroButton,
    S.GYRO_BUTTON_INVERT: [ 1, 2 ],  # invert, toggle
    S.DEADZONE_OUTER_RADIUS: (0, 32000),
    }


class GroupDpad (GroupBase):
  DPAD_NORTH = 'dpad_north'
  DPAD_WEST = 'dpad_west'
  DPAD_EAST = 'dpad_east'
  DPAD_SOUTH = 'dpad_south'
  DPAD_CLICK = 'dpad_click'
  DPAD_EDGE = 'dpad_edge'
  INPUTS = set([
    DPAD_NORTH, DPAD_WEST, DPAD_EAST, DPAD_SOUTH, DPAD_CLICK, DPAD_EDGE
    ])

  class Layout:
    FOUR_WAY = 0,
    EIGHT_WAY = 1,
    ANALOG_EMULATION = 2,
    CROSS_GATE = 3

  S = GroupBase.SETTINGS
  GyroButton = GroupBase.GyroButton
  HapticIntensityOverride = GroupBase.HapticIntensity
  _Settings = {
    S.REQUIRES_CLICK: bool,
    S.LAYOUT: Layout,
    S.DEADZONE: (0, 32767),
    S.EDGE_BINDING_RADIUS: (10000, 32000),
    S.EDGE_BINDING_INVERT: bool,
    S.ANALOG_EMULATION_PERIOD: (1, 500),
    S.OVERLAP_REGION: (2000, 16000),
    S.GYRO_BUTTON_INVERT: bool,
    S.GYRO_BUTTON: GyroButton,
    S.HAPTIC_INTENSITY_OVERRIDE: HapticIntensityOverride,
    S.GYRO_NEUTRAL: (0, 32767),
    }

  def __init__ (self, index=None, py_inputs=None, py_settings=None, **kwargs):
    GroupBase.__init__(self, 'dpad', index, py_inputs, py_settings, **kwargs)

class GroupFourButtons (GroupBase):
  BUTTON_A = 'down'
  BUTTON_B = 'right'
  BUTTON_X = 'left'
  BUTTON_Y = 'right'
  INPUTS = set([
    BUTTON_A, BUTTON_B, BUTTON_X, BUTTON_Y
    ])

  S = GroupBase.SETTINGS
  _Settings = {
    S.REQUIRES_CLICK: bool,
    S.BUTTON_SIZE: (1, 32767),
    S.BUTTON_DIST: (1, 32767),
    }

class GroupJoystickCamera (GroupBase):
  CurveExponent = GroupBase.CurveExponent
  SwipeDuration = GroupBase.SwipeDuration
  HapticIntensity = GroupBase.HapticIntensity
  GyroButton = GroupBase.GyroButton
  class OutputJoystick:
    MATCHED_SIDE = 0
    OPPOSITE_SITE = 1
    RELATIVE_MOUSE = 2

  S = GroupBase.SETTINGS
  _Settings = {
    S.CURVE_EXPONENT: CurveExponent,
    S.SWIPE_DURATION: SwipeDuration,
    S.HAPTIC_INTENSITY: HapticIntensity,
    S.OUTPUT_JOYSTICK: OutputJoystick,
    S.SENSITIVITY_VERT_SCALE: (25, 175),
    S.ANTI_DEADZONE: (0, 32767),
    S.ANTI_DEADZONE_BUFFER: (0, 32767),
    S.INVERT_X: bool,
    S.INVERT_Y: bool,
    S.JOYSTICK_SMOOTHING: bool,
    S.SENSITIVITY: (10, 1000),
    S.GYRO_BUTTON: GyroButton,
    S.GYRO_NEUTRAL: (0, 32767),
  }

class GroupJoystickMouse (GroupBase):
  CLICK = "click"
  EDGE = "edge"
  INPUTS = set([ CLICK, EDGE ])

  CurveExponent = GroupBase.CurveExponent
  class OutputJoystick:
    MATCHED_SIDE = 0
    OPPOSITE_SIDE = 1
  S = GroupBase.SETTINGS
  _Settings = {
    S.CURVE_EXPONENT: CurveExponent,
    S.CUSTOM_CURVE_EXPONENT: int,   # TODO: research range
    S.EDGE_BINDING_RADIUS: (0, 32767),
    S.EDGE_BINDING_INVERT: bool,
    S.ANTI_DEADZONE: (0, 32767),
    S.ANTI_DEADZONE_BUFFER: (0, 32767),
    S.OUTPUT_JOYSTICK: OutputJoystick,
  }

class GroupJoystickMove (GroupBase):
  CurveExponent = GroupBase.CurveExponent
  DeadzoneShape = GroupBase.DeadzoneShape
  GyroButton = GroupBase.GyroButton
  HapticIntensity = GroupBase.HapticIntensity
  OutputAxis = GroupBase.OutputAxis
  class OutputJoystick:
    LEFT_JOYSTICK = 0
    RIGHT_JOYSTICK = 1
    RELATIVE_JOYSTICK = 2
  S = GroupBase.SETTINGS
  _Settings = {
    S.CURVE_EXPONENT: CurveExponent,
    S.CUSTOM_CURVE_EXPONENT: (25, 375),
    S.EDGE_BINDING_RADIUS: (0, 32767),
    S.EDGE_BINDING_INVERT: bool,
    S.OUTPUT_JOYSTICK: OutputJoystick,
    S.ANTI_DEADZONE: (0, 32767),
    S.ANTI_DEADZONE_BUFFER: (0, 32767),
    S.HAPTIC_INTENSITY: HapticIntensity,
    S.DEADZONE_INNER_RADIUS: (0, 32000),
    S.DEADZONE_OUTER_RADIUS: (0, 32000),
    S.OUTPUT_AXIS: OutputAxis,
    S.GYRO_LOCK_EXTENTS: bool,
    S.INVERT_X: bool,
    S.INVERT_Y: bool,
    S.SENSITIVITY: (1, 100),
    S.SENSITIVITY_VERT_SCALE: (1,100),
    S.SENSITIVITY_HORIZ_SCALE: (1,100),
    S.GYRO_NEUTRAL: (0, 32767),
    S.GYRO_BUTTON: GyroButton,
    S.GYRO_BUTTON_INVERT: bool,
    S.GYRO_LOCK_EXTENTS: bool,
  }

class GroupMouseJoystick (GroupBase):
  Friction = GroupBase.Friction
  GyroButton = GroupBase.GyroButton
  MouseDampeningTrigger = GroupBase.MouseDampeningTrigger
  S = GroupBase.SETTINGS
  _Settings = {
    S.TRACKBALL: bool,
    S.DOUBLETAP_BEEP: bool,
    S.INVERT_X: bool,
    S.INVERT_Y: bool,
    S.HAPTIC_INTENSITY: bool,
    S.ROTATION: (-30, 30),
    S.FRICTION: Friction,
    S.SENSITIVITY_VERT_SCALE: (0, 200),
    S.MOUSE_MOVE_THRESHOLD: (0, 40),
    S.EDGE_SPIN_VELOCITY: (0, 1000),
    S.EDGE_SPIN_RADIUS: (0, 32767),
    S.DOUBLETAP_MAX_DURATION: (20, 500),
    S.MOUSE_DAMPENING_TRIGGER: MouseDampeningTrigger,
    S.MOUSE_TRIGGER_CLAMP_AMOUNT: int,  # TODO: research limits
    S.MOUSEJOYSTICK_DEADZONE_X: (0, 32767),
    S.MOUSEJOYSTICK_DEADZONE_Y: (0, 32767),
    S.MOUSEJOYSTICK_PRECISION: (1, 100),
    S.CUSTOM_CURVE_EXPONENT: (100, 300),
    S.GYRO_BUTTON: GyroButton,
    S.GYRO_BUTTON_INVERT: [ 1, 2 ],
    S.GYRO_AXIS: [ 0, 1],  # TODO: research enum
    S.GYRO_SENSITIVITY_SCALE: int, # TODO: research limits
  }

class GroupMouseRegion (GroupBase):
  CLICK = "click"
  EDGE = "edge"
  TOUCH = "touch"
  INPUTS = set([ CLICK, EDGE, TOUCH ])

  HapticIntensity = GroupBase.HapticIntensity
  MouseDampeningTrigger = GroupBase.MouseDampeningTrigger
  class OutputJoystick: # TODO: clarify later.
    LEFT = 0
    RIGHT = 1
    MOUSE = 2
  S = GroupBase.SETTINGS
  _Settings = {
    S.EDGE_BINDING_RADIUS: (1, 32767),
    S.EDGE_BINDING_INVERT: bool,
    S.HAPTIC_INTENSITY: HapticIntensity,
    S.OUTPUT_JOYSTICK: OutputJoystick,
    S.SCALE: (1, 100),
    S.POSITION_X: (0, 100),
    S.POSITION_Y: (0, 100),
    S.SENSITIVITY_VERT_SCALE: (0, 200),
    S.SENSITIVITY_HORIZ_SCALE: (0, 200),
    S.TELEPORT_STOP: bool,
    S.MOUSE_DAMPENING_TRIGGER: MouseDampeningTrigger,
    S.MOUSE_TRIGGER_CLAMP_AMOUNT: (100, 8000),
  }

class GroupRadialMenu (GroupBase):
  CLICK = "click"
  # touch_menu_button_%d  0..15
  INPUTS = set([ CLICK, ])

  TouchmenuButtonFireType = GroupBase.TouchmenuButtonFireType
  S = GroupBase.SETTINGS
  _Settings = {
    S.TOUCHMENU_BUTTON_FIRE_TYPE: TouchmenuButtonFireType,
    S.TOUCH_MENU_OPACITY: (40, 100),
    S.TOUCH_MENU_POSITION_X: (0, 100),
    S.TOUCH_MENU_POSITION_Y: (0, 100),
    S.TOUCH_MENU_SCALE: (50, 150),
    S.TOUCH_MENU_SHOW_LABELS: bool,
  }

class GroupScrollwheel (GroupBase):
  CLICK = "click"
  SCROLL_CLOCKWISE = "scroll_clockwise"
  SCROLL_COUNTERCLOCKWISE = "scroll_counterclockwise"
  # scroll_wheel_list_%d  0..9
  INPUTS = set([ CLICK, SCROLL_CLOCKWISE, SCROLL_COUNTERCLOCKWISE ])

  Friction = GroupBase.Friction
  HapticIntensity = GroupBase.HapticIntensity
  class ScrollType:
    CIRCULAR = 0
    HORIZONTAL = 1
    VERTICAL = 1
  S = GroupBase.SETTINGS
  _Settings = {
    S.SCROLL_ANGLE: (1, 180),
    S.HAPTIC_INTENSITY: HapticIntensity,
    S.SCROLL_TYPE: ScrollType,
    S.SCROLL_INVERT: bool,
    S.SCROLL_WRAP: bool,
    S.SCROLL_FRICTION: Friction,
  }

class GroupSingleButton (GroupBase):
  CLICK = "click"
  TOUCH = "touch"
  INPUTS = set([ CLICK, TOUCH ])

class GroupSwitches (GroupBase):
  BUTTON_ESCAPE = "button_escape"
  BUTTON_MENU = "button_menu"
  LEFT_BUMPER = "left_bumper"
  RIGHT_BUMPER = "right_bumper"
  BUTTON_BACK_LEFT = "button_back_left"
  BUTTON_BACK_RIGHT = "button_back_right"
  RIGHT_TRIGGER_MODESHIFT = "right_trigger_modeshift"
  RIGHT_TRIGGER_THRESHOLD_MODESHIFT = "right_trigger_threshold_modeshift"
  LEFT_TRIGGER_MODESHIFT = "left_trigger_modeshift"
  LEFT_TRIGGER_THRESHOLD_MODESHIFT = "left_trigger_threshold_modeshift"
  LEFT_CLICK_MODESHIFT = "left_click_modeshift"
  RIGHT_CLICK_MODESHIFT = "right_click_modeshift"
  LEFT_STICK_CLICK_MODESHIFT = "left_stick_click_modeshift"
  BUTTON_A_MODESHIFT = "button_a_modeshift"
  BUTTON_B_MODESHIFT = "button_b_modeshift"
  BUTTON_X_MODESHIFT = "button_x_modeshift"
  BUTTON_Y_MODESHIFT = "button_y_modeshift"

class GroupTouchMenu (GroupBase):
  # touch_menu_button_%d  0..15
  TouchmenuButtonFireType = GroupBase.TouchmenuButtonFireType
  S = GroupBase.SETTINGS
  _Settings = {
    S.TOUCH_MENU_BUTTON_COUNT: [ 2, 4, 7, 9, 12, 13, 16 ], 
    S.TOUCH_MENU_OPACITY: bool,
    S.TOUCH_MENU_POSITION_X: (0, 100),
    S.TOUCH_MENU_POSITION_Y: (0, 100),
    S.TOUCH_MENU_SCALE: (50, 150),
    S.TOUCH_MENU_SHOW_LABELS: bool,
    S.TOUCHMENU_BUTTON_FIRE_TYPE: TouchmenuButtonFireType,
    }

class GroupTrigger (GroupBase):
  CLICK = "click"
  EDGE = "edge"
  INPUTS = set([ CLICK, EDGE ])

  class AdaptiveThreshold:
    SIMPLE_THRESHOLD = 0
    HAIR_TRIGGER = 1
    HIP_FIRE_AGGRESSIVE = 2
    HIP_FIRE_NORMAL = 3
    HIP_FIRE_RELAXED = 4
    HIP_FIRE_EXCLUSIVE = 5
  CurveExponent = GroupBase.CurveExponent
  OutputTrigger = GroupBase.OutputTrigger
  S = GroupBase.SETTINGS
  _Settings = {
    S.OUTPUT_TRIGGER: OutputTrigger,
    S.DEADZONE_OUTER_RADIUS: (0, 32767),
    S.DEADZONE_INNER_RADIUS: (0, 32767),
    S.EDGE_BINDING_RADIUS: (0, 32767),
    S.ADAPTIVE_THRESHOLD: AdaptiveThreshold,
    S.CURVE_EXPONENT: CurveExponent,
    S.CUSTOM_CURVE_EXPONENT: (25, 4000),
  }




class Group (object):
  """A group of controls.
Multiple controller elements combine together into groups that act as a unit to form a higher-order input type.
Notable example include the four cardinal points of a d-pad to form not just a d-pad, but also pie menu control.
"""
  MODES = {
    "pen": "absolute_mouse",
    "touchpad": "absolute_mouse",
    "absolute": "absolute_mouse",
    "dpad": "dpad",
    "4buttons": "four_buttons",
    "button_quad": "four_buttons",
    "button_diamond": "four_buttons",
    "diamond": "four_buttons",
    "face_buttons": "four_buttons",
    "camera": "joystick_camera",
    "mousejs": "joystick_mouse",
    "joystick": "joystick_move",
    "force_joystick": "mouse_joystick",
    "fake_joystick": "mouse_joystick",
    "region": "mouse_region",
    "radial": "radial_menu",
    "scroll_wheel": "scrollwheel",
    "one_button": "single_button",
    "switches": "switches",
    "menu": "touch_menu",
    "touchmenu": "touch_menu",
    "trigger": "trigger",
  }
  def __init__ (self, index=None, py_mode=None, py_inputs=None, py_settings=None, **kwargs):
    if index is None:
      if 'id' in kwargs:
        index = int(kwargs['id'])
    if index is None:
      index = 0

    if py_mode is None:
      if 'mode' in kwargs:
        py_mode = kwargs['mode']
    py_mode = filter_enum(self.MODES, py_mode)

    self.index = index
    # TODO: py_mode == None  =>  remove Group.
    self.mode = py_mode
    self.inputs = EncodableDict(VSC_INPUTS)
    self.settings = EncodableDict(VSC_SETTINGS)

    if py_inputs:
      # Expect dictionary of key to pyobjects.
      self.inputs.update(inputs)
    elif VSC_INPUTS in kwargs:
      # expect dict within ControllerConfig
      for (inp_name, inp_kv) in kwargs[VSC_INPUTS].items():
        self.make_input(inp_name, **inp_kv)

    if py_settings:
      # Expect dictionary of pure scalars.  This might break in future?
      self.settings.update(settings)
    elif VSC_SETTINGS in kwargs:
      self.settings.update(kwargs[VSC_SETTINGS])

  def make_input (self, input_element, py_activators=None, **kwargs):
    inp = ControllerInput(input_element, py_activators=py_activators, **kwargs)
    self.inputs[input_element] = inp
    return inp

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
    kv = scvdf.SCVDFDict()
    kv['id'] = str(self.index)
    kv['mode'] = str(self.mode)

    # Always generate ['inputs']
    kv[VSC_INPUTS] = self.inputs.encode_kv()

    if self.settings:
      kv[VSC_SETTINGS] = self.settings.encode_kv()

    return kv


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

The term "legacy" refers to emulating events of keyboard, mouse, or gamepad.
The contrast is "native" or "In-Game Actions" (IGA), as per Steam Controller API documentation.
The native actions bypass the entire notion of physical devices (keyboard, mouse, etc.), but require deliberate support by the application/game developer.
"""
  DEFAULT_LEGACY = True
  def __init__ (self, tier, index, py_title=None, py_legacy=None, py_parent=None, **kwargs):
    if py_title is None:
      py_title = kwargs.get("title", "")
    if py_legacy is None:
      if 'legacy_set' in kwargs:
        py_legacy = bool(int(kwargs["legacy_set"]))
      else:
        py_legacy = self.DEFAULT_LEGACY
    if py_parent is None:
      py_parent = kwargs.get("parent_set_name", None)

    self.index = index
    self.title = py_title
    self.tier = tier
    self.legacy = py_legacy
    self.parent_set_name = py_parent

  def encode_kv (self):
    kv = scvdf.SCVDFDict()
    kv['title'] = str(self.title)
    kv['legacy_set'] = str(int(bool(self.legacy)))
    if self.tier == 1:
      kv['set_layer'] = "1"
    if self.parent_set_name:
      kv['parent_set_name'] = self.parent_set_name
    return kv


class ActionLayer (Overlay):
  """tuple_key='action_layer'
Action Layer, consists of one or more  ...
"""
  # Change legacy default to False when native (non-legacy) binds become more prevalent.
  def __init__ (self, index=None, py_title=None, py_legacy=None, py_parent=None, **kwargs):
    Overlay.__init__(self, 1, index, py_title, py_legacy, py_parent, **kwargs)


class ActionSet (Overlay):
  """An 'Action Set', consists of one or more Actions Layers."""
  def __init__ (self, index=None, py_title=None, py_legacy=None, **kwargs):
    Overlay.__init__(self, 0, index, py_title, py_legacy, py_parent=None, **kwargs)


class GroupSourceBinding (object):
  VALID_SOURCES = [
    "switch", "dpad", "button_diamond", "left_trigger", "right_trigger",
    "joystick", "right_joystick"
    ]
  def __init__ (self, groupid, groupsrc, active=True, modeshift=False):
    if groupid is None:
      groupid = 0
    self.groupid = groupid
    self.grpsrc = groupsrc
    self.active = active
    self.modeshift = modeshift

  def _encode (self):
    rhs = []
    rhs.append(self.grpsrc)
    if self.active:
      rhs.append(VSC_ACTIVE)
    else:
      rhs.append(VSC_INACTIVE)
    if self.modeshift:
      rhs.append(VSC_MODESHIFT)
    retval = ' '.join(rhs)
    return retval

  def encode_pair (self):
    encoding = self._encode()
    whole = ( str(self.groupid), encoding )
    return whole

  def encode_kv (self):
    return self._encode()


class Preset (object):
  def __init__ (self, index=None, py_name=None, py_gsb=None, **kwargs):
    if index is None:
      index = int(kwargs.get('id', 0))
    if py_name is None:
      py_name = kwargs.get('name', "")

    self.index = index
    self.name = py_name
    self.gsb = []

    if py_gsb:
      # expect list of pyobject.
      self.gsb.extend(py_gsb)
    elif 'group_source_bindings' in kwargs:
      d = kwargs['group_source_bindings']
      for (gsb_key, gsb_value) in d.items():
        self.add_gsb(gsb_key, gsb_value)

  def add_gsb (self, groupid, groupsrc, active=True, modeshift=False):
    if ' ' in groupsrc:
      # assume not parsed.
      phrases = groupsrc.split()
      groupsrc = phrases[0]
      active = (phrases[1] == VSC_ACTIVE)
      modeshift = (phrases[2] == VSC_MODESHIFT) if len(phrases)>2 else False
    gsb = GroupSourceBinding(groupid, groupsrc, active, modeshift)
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
    kv = scvdf.SCVDFDict()
    kv['id'] = str(self.index)
    kv['name'] = str(self.name)

    kv_gsb = scvdf.SCVDFDict()
    for elt in self.gsb:
      gid = str(elt.groupid)
      kv_gsb[gid] = elt.encode_kv()
    kv['group_source_bindings'] = kv_gsb

    return kv


class Mapping (object):
  """Encapsulates controller mapping (toplevel)"""
  def __init__ (self, index=None, version=None, revision=None, title=None, description=None, creator=None, controller_type=None, Timestamp=None):
    self.index = index
    if version is None: version = 3
    if revision is None: revision = 1
    if title is None: title = "Unnamed"
    if description is None: description = "Unnamed configuration"
    if creator is None: creator = "Anonymous"
    if controller_type is None: controller_type = "controller_steamcontroller_gordon"
    if Timestamp is None:
      # TODO: determine timestamp
      Timestamp = 0
    self.version = version
    self.revision = revision
    self.title = title
    self.description = description
    self.creator = creator
    self.controller_type = controller_type
    self.timestamp = Timestamp

  def __init__ (self, py_version=None, py_revision=None, py_title=None, py_description=None, py_creator=None, py_controller_type=None, py_timestamp=None, **kwargs):
    if py_version is None:
      py_version = int(kwargs.get("version", 3))
    if py_revision is None:
      py_revision = int(kwargs.get("revision", 1))
    if py_title is None:
      py_title = kwargs.get("title", "Unnamed")
    if py_description is None:
      py_description = kwargs.get("description", "Unnamed configuration")
    if py_creator is None:
      py_creator = kwargs.get("creator", "(Auto-Generator)")
    if py_controller_type is None:
      py_controller_type = kwargs.get("controller_type", "controller_steamcontroller_gordon")
    if py_timestamp is None:
      py_timestamp = kwargs.get("Timestamp", None)
      if py_timestamp is None:
        # TODO: determine current timestamp
        py_timestamp = -1
      else:
        py_timestamp = int(py_timestamp)

    self.version = py_version
    self.revision = py_revision
    self.title = py_title
    self.description = py_description
    self.creator = py_creator
    self.controller_type = py_controller_type
    self.timestamp = py_timestamp
    # List of Action Sets
    self.actions = []
    # List of Action Layers
    self.layers = []
    # List of Groups
    self.groups = []
    # List of Presets
    self.presets = []
    # Miscellaneous settings
    self.settings = EncodableDict(VSC_SETTINGS)

    if 'actions' in kwargs:
      for obj_name, obj_kv in kwargs['actions'].items():
        self.make_action_set(obj_name, **obj_kv)

    if 'action_layers' in kwargs:
      for obj_name, obj_kv in kwargs['action_layers'].items():
        self.make_action_layer(obj_name, **obj_kv)

    if 'group' in kwargs:
      for grp_kv in get_all(kwargs, 'group', []):
        self.make_group(**grp_kv)

    if 'preset' in kwargs:
      for preset_kv in get_all(kwargs, 'preset', []):
        self.make_preset(**preset_kv)

    if VSC_SETTINGS in kwargs:
      self.settings.update(kwargs[VSC_SETTINGS])

  def make_group (self, index=None, py_mode=None, **kwargs):
    groupid = index
    if 'id' in kwargs:
      groupid = int(kwargs['id'])
    if groupid is None:
      # TODO: auto-index
      groupid = -1
    group = Group(groupid, py_mode, **kwargs)
    self.groups.append(group)
    return group

  def make_preset (self, index=None, py_name=None, **kwargs):
    # TODO: determine unique presetid by scanning.
    presetid = index
    if presetid is None:
      if 'id' in kwargs:
        presetid = int(kwargs['id'])
      else:
        # TODO: determine unique preset's id by scanning.
        pass
    if py_name is None:
      if not 'name' in kwargs:
        # TODO: derive from autosequence.
        py_name = py_name
    preset = Preset(presetid, py_name, **kwargs)
    self.presets.append(preset)
    return preset


  def make_action_set (self, index=None, py_title=None, py_legacy=None, **kwargs):
    actset = ActionSet(index, py_title, py_legacy, **kwargs)
    self.actions.append(actset)
    return actset

  def make_action_layer (self, index=None, py_title=None, py_legacy=None, py_parent=None, **kwargs):
    layer = ActionLayer(index, py_title, py_legacy, py_parent, **kwargs)
    self.layers.append(layer)
    return layer

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

  def _encode_overlays (self, overlay_store, gensym=0):
    """Helper function to encode the overlays: Action Set, Action Layer."""
    kv = scvdf.SCVDFDict()
    for obj in overlay_store:
      pair_name = obj.index
      pair_val = obj.encode_kv()
      kv[pair_name] = pair_val
    return kv

  def encode_kv (self):
    """Encode object to list of pairs (scvdf)."""
    kv = scvdf.SCVDFDict()
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
# Contrast to 'group':
# The instances of Group ('group') are written to the VDF separately for each instance, and differentiated by a nested "id" key/value, thereby leading to multiple instances of the "groups" key but with different associated values.
# The instances of Action set/layers are each given unique names and made the value of that name in 'actions' or 'action_layers'.
#
# Consequeces to iteration:
# * 'group': either keep sorted by nested "id" key, or brute-force finding instance with the desired "id" key.
#  * 'actions', 'action_layers': The overlays are in no particular order (as per nature of mapping type), but may be iterated in the proper sequence by sorting their names.

    if self.actions:
      kv['actions'] = self._encode_overlays(self.actions)

    if self.layers:
      kv['action_layers'] = self._encode_overlays(self.layers)

    for grp in self.groups:
      kv['group'] = grp.encode_kv()

    for preset in self.presets:
      kv['preset'] = preset.encode_kv()

    if self.settings:
      kv[VSC_SETTINGS] = self.settings.encode_kv()
    else:
      kv[VSC_SETTINGS] = {}

    return kv


class ControllerConfig (object):
  """Toplevel object represeting a controller configuration.
See ControllerConfigFactory for instantiating from a dict or SCVDFDict.
"""
  def __init__ (self, index=None, py_mappings=None, **kwargs):
    self.index = index
    self.mappings = []
    if py_mappings:
      # List of pyobjects.
      self.mappings.extend(py_mappings)
    elif 'controller_mappings' in kwargs:
      conmaps = kwargs['controller_mappings']
      if not isinstance(conmaps, list):
        conmaps = [ conmaps ]
      for cm_kv in conmaps:
        self.make_mapping(**cm_kv)

  def make_mapping (self, py_version=3, **kwargs):
    mapping = Mapping(py_version, **kwargs)
    self.mappings.append(mapping)
    return mapping

  def encode_pair  (self):
    lop = []
    for m in self.mappings:
      lop.append( m.encode_pair() )
    return lop
  def encode_kv (self):
    kv = scvdf.SCVDFDict()
    for m in self.mappings:
      kv['controller_mappings'] = m.encode_kv()
    return kv




##############################################
# Factory class                              #
# Instantiate ControllerConfig from a dict.  #
##############################################

class ControllerConfigFactory (object):
  """Factory class to create instances of ControllerConfig."""
  @staticmethod
  def make_from_dict (pydict, parentkey=None):
    return ControllerConfig(parentkey, **pydict)

