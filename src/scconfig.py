#!/usr/bin/env python3
# encoding=utf-8

# Configurator module for Steam Valve Controller

# Uses SCVDF for reading and writing VDF files.

import scvdf
import types
from collections import OrderedDict

# PseudoNamespace - py2 and py3 compat.  Access list of names with _nsdict.
try:
  types.SimpleNamespace
except AttributeError:
  # py2
  class PseudoNamespace (object):
    def __init__ (me, **k): [me.__dict__.__setitem__(k,v) for k,v in k.items()]
    _nsdict = property(lambda self: self.__dict__)
else:
  # py3
  class PseudoNamespace (types.SimpleNamespace):
    _nsdict = property(lambda self: self.__dict__)


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
class EncodableDict (OrderedDict):
  """Extends SCVDFDict to support .encode_kv()"""
  def __init__ (self, index=None, copyfrom=None):
    if isinstance(index,dict):  # implies copyfrom currently None.
      copyfrom, index = index, None
    if copyfrom:
      OrderedDict.__init__(self, copyfrom)
    else:
      OrderedDict.__init__(self)
    self.index = VSC_SETTINGS if (index is None) else None
  def encode_kv (self):
    kv = scvdf.SCVDFDict()
    for k, v in self.items():
      try:
        kv[k] = v.encode_kv()     # recursively encode.
      except AttributeError as e:
        if isinstance(v, bool): v = int(v)    # cast bool to int.
        kv[k] = str(v)
    return kv


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




##################################


# Settings map scalar to scalar; SCVDF overloads multiple assignments to mean building an array value.
class SettingsBase (OrderedDict):
  # Constraints on settings values.
  # Tuples indicate an integer range, such that tuple[0] <= value <= tuple[1].
  # List specifies the set of acceptable values.
  # class-object contains acceptable values: class.__dict__.values().
  # primitive type to indicate the allowable value type.
  ## setting keys not listed in constraints are unconstrainted.
  _CONSTRAINTS = {}

  def __init__ (self, index=None, **kwargs):
    super(SettingsBase,self).__init__(kwargs)
    if index is not None:
      self.index = index

  def _filtered_assign (self, k, val):
    constraint = self._CONSTRAINTS.get(k, None)
    if isinstance(constraint,tuple):      # integer range constraint.
      lower, upper = constraint
      if (val < lower) or (upper < val):
        raise ValueError("Value {} violates range constraint {}".format(val, constraint))
    elif isinstance(constraint,list):     # any from a list.
      if not (val in constraint):
        raise ValueError("Value {} violates list constraint {}".format(val, constraint))
    elif type(constraint) == PseudoNamespace:   # any from namespace.
      if not (val in constraint._nsdict.values()):
        raise ValueError("Value {} violates namespace constraint {}".format(val, constraint))
        return
    elif constraint is None:  # no constraint.
      pass
    else:       # is of type.
      if type(val) != constraint:
        raise ValueError("Value {} violates type constraint {}".format(val, constraint))
    self[k] = val

  @staticmethod
  def _settings_getter (settings_key):
    def getter (self):
      return self.get(settings_key, None)
    return getter
  @staticmethod
  def _settings_setter (settings_key):
    def setter (self, val):
      self._filtered_assign(settings_key, val)
    return setter
  @staticmethod
  def _settings_deleter (settings_key):
    def deleter (self):
      del self[settings_key]
    return deleter
  @staticmethod
  def _new_setting (settings_key):
    return property(SettingsBase._settings_getter(settings_key),
                    SettingsBase._settings_setter(settings_key),
                    SettingsBase._settings_deleter(settings_key))

  def encode_kv (self):
    kv = scvdf.SCVDFDict()
    for k, v in self.items():
      try:
        kv[k] = v.encode_kv()     # recursively encode.
      except AttributeError as e:
        if isinstance(v, bool): v = int(v)    # cast bool to int.
        kv[k] = str(v)
    return kv



###########################
# Evgen - Event Generator #
###########################
# Empty
# Keystroke
# MouseSwitch
# Gamepad
# Host
# Light
# Overlay
# Modeshift

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



#############
# Activator #
#############
# Full_Press
# Double_Press
# Long_Press
# Start_Press
# Release
# Chord


class ActivatorBase (object):
  """Base class for activators:
* FullPress ("Full_Press"), aka RegularPress
* LongPress ("Long_Press")
* StartPress ("Start_Press")
* DoublePress ("Double_Press")
* Release ("release")
* Chord ("chord")

Nested attributes:
 * bindings: list of `binding` instances, what event to event to synthesize.
 * settings: settings for the activator (e.g. enable repeat while held).
"""
  signal = None     # change for each derived class.

  class Settings (SettingsBase):
    _VSC_KEYS = PseudoNamespace(
      TOGGLE = "toggle",
      INTERRUPTIBLE = "interruptable",    # sic
      DELAY_START = "delay_start",
      DELAY_END = "delay_end",
      HAPTIC_INTENSITY = "haptic_intensity",
      CYCLE = "cycle",
      HOLD_REPEATS = "hold_repeats",
      REPEAT_RATE = "repeat_rate",
      DOUBLE_TAP_TIME = "double_tap_time",
      LONG_PRESS_TIME = "long_press_time",
      CHORD_BUTTON = "chord_button",
      )

    HapticIntensity = PseudoNamespace(
      OFF = 0,
      LOW = 1,
      MEDIUM = 2,
      HIGH = 3,
      )

  def __init__ (self, py_bindings=None, py_settings=None, **kwargs):
    # self.signal  is class-scope per derived class.
    self.bindings = []
    self.settings = self.Settings(py_settings)

    if py_bindings:
      # expect list of pyobject.
      self.bindings.extend(py_bindings)
    elif 'bindings' in kwargs:
      for bind_name, bind_val in kwargs['bindings'].items():
        if bind_name == "binding":
          self.add_binding(bind_val)

    if VSC_SETTINGS in kwargs:
      self.settings.update(kwargs[VSC_SETTINGS])

  def add_binding (self, binding):
    try:
      binding.isalpha
    except AttributeError:
      # treat as not-string - assume instance of Binding.
      pass
    else:
      binding_str = binding
      if binding_str:
        binding = Binding(binding_str)
      else:
        binding = None
    if binding:
      self.bindings.append(binding)

  def encode_kv (self):
    kv = scvdf.SCVDFDict()
    kv_bindings = scvdf.SCVDFDict()
    for binding in self.bindings:
      kv_bindings['binding'] = str(binding)
    kv['bindings'] = kv_bindings
    if self.settings:
      kv[VSC_SETTINGS] = self.settings.encode_kv()
    return kv

class ActivatorFullPress (ActivatorBase):
  signal = 'Full_Press'
  class Settings (ActivatorBase.Settings):
    HapticIntensity = ActivatorBase.Settings.HapticIntensity
    S = ActivatorBase.Settings._VSC_KEYS
    _CONSTRAINTS = {
      S.TOGGLE: bool,
      S.INTERRUPTIBLE: bool,
      S.DELAY_START: int,   # TODO: range
      S.DELAY_END: int,     # TODO: range
      S.HAPTIC_INTENSITY: HapticIntensity,
      S.CYCLE: bool,
      S.HOLD_REPEATS: bool,
      S.REPEAT_RATE: (1, 9999),
    }
    toggle = SettingsBase._new_setting(S.TOGGLE)
    interruptible = SettingsBase._new_setting(S.INTERRUPTIBLE)
    delay_start = SettingsBase._new_setting(S.DELAY_START)
    delay_end = SettingsBase._new_setting(S.DELAY_END)
    haptic_intensity = SettingsBase._new_setting(S.HAPTIC_INTENSITY)
    cycle = SettingsBase._new_setting(S.CYCLE)
    hold_repeats = SettingsBase._new_setting(S.HOLD_REPEATS)
    repeat_rate = SettingsBase._new_setting(S.REPEAT_RATE)
  def __init__ (self, py_bindings=None, py_settings=None, **kwargs):
    ActivatorBase.__init__(self, py_bindings, py_settings, **kwargs)

class ActivatorDoublePress (ActivatorBase):
  signal = 'Double_Press'
  class Settings (ActivatorBase.Settings):
    HapticIntensity = ActivatorBase.Settings.HapticIntensity
    S = ActivatorBase.Settings._VSC_KEYS
    _CONSTRAINTS = {
      S.DOUBLE_TAP_TIME: int,  # TODO: range
      S.TOGGLE: bool,
      S.INTERRUPTIBLE: bool,
      S.DELAY_START: int,   # TODO: range
      S.DELAY_END: int,     # TODO: range
      S.HAPTIC_INTENSITY: HapticIntensity,
      S.CYCLE: bool,
      S.HOLD_REPEATS: bool,
      S.REPEAT_RATE: (1, 9999),
    }
    double_tap_time = SettingsBase._new_setting(S.DOUBLE_TAP_TIME)
    toggle = SettingsBase._new_setting(S.TOGGLE)
    interruptible = SettingsBase._new_setting(S.INTERRUPTIBLE)
    delay_start = SettingsBase._new_setting(S.DELAY_START)
    delay_end = SettingsBase._new_setting(S.DELAY_END)
    haptic_intensity = SettingsBase._new_setting(S.HAPTIC_INTENSITY)
    cycle = SettingsBase._new_setting(S.CYCLE)
    hold_repeats = SettingsBase._new_setting(S.HOLD_REPEATS)
    repeat_rate = SettingsBase._new_setting(S.REPEAT_RATE)
  def __init__ (self, py_bindings=None, py_settings=None, **kwargs):
    ActivatorBase.__init__(self, py_bindings, py_settings, **kwargs)

class ActivatorLongPress (ActivatorBase):
  signal = 'Long_Press'
  class Settings (ActivatorBase.Settings):
    HapticIntensity = ActivatorBase.Settings.HapticIntensity
    S = ActivatorBase.Settings._VSC_KEYS
    _CONSTRAINTS = {
      S.LONG_PRESS_TIME: int,  # TODO: range
      S.TOGGLE: bool,
      S.INTERRUPTIBLE: bool,
      S.DELAY_START: int,   # TODO: range
      S.DELAY_END: int,     # TODO: range
      S.HAPTIC_INTENSITY: HapticIntensity,
      S.CYCLE: bool,
      S.HOLD_REPEATS: bool,
      S.REPEAT_RATE: (1, 9999),
    }
    long_press_time = SettingsBase._new_setting(S.LONG_PRESS_TIME)
    toggle = SettingsBase._new_setting(S.TOGGLE)
    interruptible = SettingsBase._new_setting(S.INTERRUPTIBLE)
    delay_start = SettingsBase._new_setting(S.DELAY_START)
    delay_end = SettingsBase._new_setting(S.DELAY_END)
    haptic_intensity = SettingsBase._new_setting(S.HAPTIC_INTENSITY)
    cycle = SettingsBase._new_setting(S.CYCLE)
    hold_repeats = SettingsBase._new_setting(S.HOLD_REPEATS)
    repeat_rate = SettingsBase._new_setting(S.REPEAT_RATE)
  def __init__ (self, py_bindings=None, py_settings=None, **kwargs):
    ActivatorBase.__init__(self, py_bindings, py_settings, **kwargs)

class ActivatorStartPress (ActivatorBase):
  signal = 'Start_Press'
  class Settings (ActivatorBase.Settings):
    HapticIntensity = ActivatorBase.Settings.HapticIntensity
    S = ActivatorBase.Settings._VSC_KEYS
    _CONSTRAINTS = {
      S.TOGGLE: bool,
      S.DELAY_START: int,   # TODO: range
      S.DELAY_END: int,     # TODO: range
      S.HAPTIC_INTENSITY: HapticIntensity,
      S.CYCLE: bool,
    }
    toggle = SettingsBase._new_setting(S.TOGGLE)
    delay_start = SettingsBase._new_setting(S.DELAY_START)
    delay_end = SettingsBase._new_setting(S.DELAY_END)
    haptic_intensity = SettingsBase._new_setting(S.HAPTIC_INTENSITY)
    cycle = SettingsBase._new_setting(S.CYCLE)
  def __init__ (self, py_bindings=None, py_settings=None, **kwargs):
    ActivatorBase.__init__(self, py_bindings, py_settings, **kwargs)

class ActivatorRelease (ActivatorBase):
  signal = 'release'
  class Settings (ActivatorBase.Settings):
    HapticIntensity = ActivatorBase.Settings.HapticIntensity
    S = ActivatorBase.Settings._VSC_KEYS
    _CONSTRAINTS = {
      S.TOGGLE: bool,
      S.INTERRUPTIBLE: bool,
      S.DELAY_START: int,   # TODO: range
      S.DELAY_END: int,     # TODO: range
      S.HAPTIC_INTENSITY: HapticIntensity,
    }
    toggle = SettingsBase._new_setting(S.TOGGLE)
    interruptible = SettingsBase._new_setting(S.INTERRUPTIBLE)
    delay_start = SettingsBase._new_setting(S.DELAY_START)
    delay_end = SettingsBase._new_setting(S.DELAY_END)
    haptic_intensity = SettingsBase._new_setting(S.HAPTIC_INTENSITY)
    cycle = SettingsBase._new_setting(S.CYCLE)
  def __init__ (self, py_bindings=None, py_settings=None, **kwargs):
    ActivatorBase.__init__(self, py_bindings, py_settings, **kwargs)

class ActivatorChord (ActivatorBase):
  signal = 'chord'
  class Settings (ActivatorBase.Settings):
    ChordButton = PseudoNamespace(
      NONE = 0,
      LEFT_BUMPER = 1,
      RIGHT_BUMPER= 2,
      LEFT_GRIP = 3,
      RIGHT_GRIP = 4,
      LEFT_TRIGGER_FULL = 5,
      RIGHT_TRIGGER_FULL = 6,
      LEFT_TRIGGER_SOFT = 7,
      RIGHT_TRIGGER_SOFT = 8,
      JOYSTICK_CLICK = 9,
      BUTTON_A = 10,
      BUTTON_B = 11,
      BUTTON_X = 12,
      BUTTON_Y = 13,
      SELECT = 14,
      START = 15,
      LEFT_PAD_TOUCH = 16,
      RIGHT_PAD_TOUCH = 17,
      LEFT_PAD_CLICK = 18,
      RIGHT_PAD_CLICK = 19,
      )
    HapticIntensity = ActivatorBase.Settings.HapticIntensity
    S = ActivatorBase.Settings._VSC_KEYS
    _CONSTRAINTS = {
      S.CHORD_BUTTON: ChordButton,
      S.TOGGLE: bool,
      S.INTERRUPTIBLE: bool,
      S.DELAY_START: int,   # TODO: range
      S.DELAY_END: int,     # TODO: range
      S.HAPTIC_INTENSITY: HapticIntensity,
      S.HOLD_REPEATS: bool,
      S.REPEAT_RATE: (1, 9999),
    }
    chord_button = SettingsBase._new_setting(S.CHORD_BUTTON)
    toggle = SettingsBase._new_setting(S.TOGGLE)
    interruptible = SettingsBase._new_setting(S.INTERRUPTIBLE)
    delay_start = SettingsBase._new_setting(S.DELAY_START)
    delay_end = SettingsBase._new_setting(S.DELAY_END)
    haptic_intensity = SettingsBase._new_setting(S.HAPTIC_INTENSITY)
    cycle = SettingsBase._new_setting(S.CYCLE)
    hold_repeats = SettingsBase._new_setting(S.HOLD_REPEATS)
    repeat_rate = SettingsBase._new_setting(S.REPEAT_RATE)
  def __init__ (self, py_bindings=None, py_settings=None, **kwargs):
    ActivatorBase.__init__(self, py_bindings, py_settings, **kwargs)


class ActivatorFactory:
  @staticmethod
  def make_full_press (py_bindings=None, py_settings=None, **kwargs):
    return ActivatorFullPress(py_bindings, py_settings, **kwargs)
  @staticmethod
  def make_double_press (py_bindings=None, py_settings=None, **kwargs):
    return ActivatorDoublePress(py_bindings, py_settings, **kwargs)
  @staticmethod
  def make_long_press (py_bindings=None, py_settings=None, **kwargs):
    return ActivatorLongPress(py_bindings, py_settings, **kwargs)
  @staticmethod
  def make_start_press (py_bindings=None, py_settings=None, **kwargs):
    return ActivatorStartPress(py_bindings, py_settings, **kwargs)
  @staticmethod
  def make_release (py_bindings=None, py_settings=None, **kwargs):
    return ActivatorRelease(py_bindings, py_settings, **kwargs)
  @staticmethod
  def make_chord (py_bindings=None, py_settings=None, **kwargs):
    return ActivatorChord(py_bindings, py_settings, **kwargs)

  DELEGATES = [
    ActivatorFullPress,
    ActivatorDoublePress,
    ActivatorLongPress,
    ActivatorStartPress,
    ActivatorRelease,
    ActivatorChord,
  ]
  @staticmethod
  def make (signal_name=None, py_bindings=None, py_settings=None, **kwargs):
    retval = None
    for delegate in ActivatorFactory.DELEGATES:
      if signal_name == delegate.signal:
        try:
          retval = delegate(py_bindings, py_settings, **kwargs)
        except Exception as e:
          raise
    return retval


def Activator (activator_signal, **kwargs):
  return ActivatorFactory.make(activator_signal, **kwargs)

###### end of Activator ######



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



#################
# (Input) Group #
#################
# AbsoluteMouse
# Dpad
# FourButtons
# JoystickCamera
# JoystickMove
# JoystickMouse
# MouseJoystick
# MouseRegion
# RadialMenu
# Scrollwheel
# SingleButton
# Switches
# TouchMenu

class GroupBase (object):
  """Base class for input groups: joystick, dpad, triggers, etc."""

  class Settings (SettingsBase):
    # VSC VDF settings keys at 'group' level.
    _VSC_KEYS = PseudoNamespace(
  # starting with dpad
      REQUIRES_CLICK = "requires_click",
      LAYOUT = "layout",
      DEADZONE = "deadzone",
      EDGE_BINDING_RADIUS = "edge_binding_radius",
      EDGE_BINDING_INVERT = "edge_binding_invert",
      ANALOG_EMULATION_PERIOD = "analog_emulation_period",
      ANALOG_EMULATION_DUTY_CYCLE = "analog_emulation_duty_cycle",
      OVERLAP_REGION = "overlap_region",
      GYRO_BUTTON_INVERT = "gyro_button_invert",
      HAPTIC_INTENSITY_OVERRIDE = "haptic_intensity_override",
      GYRO_NEUTRAL = "gyro_neutral",
      GYRO_BUTTON = "gyro_button",

  # four-buttons
      BUTTON_SIZE = "button_size",
      BUTTON_DIST = "button_dist",

  # joystick-camera
      CURVE_EXPONENT = "curve_exponent",
      SWIPE_DURATION = "swipe_duration",
      HAPTIC_INTENSITY = "haptic_intensity",
      OUTPUT_JOYSTICK = "output_joystick",
      SENSITIVITY_VERT_SCALE = "sensitivity_vert_scale",
      ANTI_DEADZONE = "anti_deadzone",
      ANTI_DEADZONE_BUFFER = "anti_deadzone_buffer",
      INVERT_X = "invert_x",
      INVERT_Y = "invert_y",
      JOYSTICK_SMOOTHING = "joystick_smoothing",
      GYRO_AXIS = "gyro_axis",

  # joystick-mouse
      CUSTOM_CURVE_EXPONENT = "custom_curve_exponent",
      DEADZONE_INNER_RADIUS = "deadzone_inner_radius",
      DEADZONE_OUTER_RADIUS = "deadzone_outer_radius",
      DEADZONE_SHAPE = "deadzone_shape",
      SENSITIVITY = "sensitivity",
      SENSITIVITY_HORIZ_SCALE = "sensitivity_horiz_scale",

  # joystick-move
      GYRO_LOCK_EXTENTS = "gyro_lock_extents",
      OUTPUT_AXIS = "output_axis",

  # mouse-joystick
      DOUBLETAP_BEEP = "doubletap_beep",
      TRACKBALL = "trackball",
      ROTATION = "rotation",
      FRICTION = "friction",
      FRICTION_VERT_SCALE = "friction_vert_scale",
      MOUSE_MOVE_THRESHOLD = "mouse_move_threshold",
      EDGE_SPIN_VELOCITY = "edge_spin_velocity",
      EDGE_SPIN_RADIUS = "edge_spin_radius",
      DOUBLETAP_MAX_DURATION = "doubetap_max_duration",  # [sic]
      MOUSE_DAMPENING_TRIGGER = "mouse_dampening_trigger",
      MOUSE_TRIGGER_CLAMP_AMOUNT = "mouse_trigger_clamp_amount",
      MOUSEJOYSTICK_DEADZONE_X = "mousejoystick_deadzone_x",
      MOUSEJOYSTICK_DEADZONE_Y = "mousejoystick_deadzone_y",
      MOUSEJOYSTICK_PRECISION = "mousejoystick_precision",
      GYRO_SENSITIVITY_SCALE = "gyro_sensitivity_scale",

  # mouse-region
      SCALE = "scale",
      POSITION_X = "position_x",
      POSITION_Y = "position_y",
      TELEPORT_STOP = "teleport_stop",

  # radial-menu
      TOUCHMENU_BUTTON_FIRE_TYPE = "touchmenu_button_fire_type",
      TOUCH_MENU_OPACITY = "touch_menu_opacity",
      TOUCH_MENU_POSITION_X = "touch_menu_position_x",
      TOUCH_MENU_POSITION_Y = "touch_menu_position_y",
      TOUCH_MENU_SCALE = "touch_menu_scale",
      TOUCH_MENU_SHOW_LABELS = "touch_menu_show_labels",

  # scrollwheel
      SCROLL_ANGLE = "scroll_angle",
      SCROLL_TYPE = "scroll_type",
      SCROLL_INVERT = "scroll_invert",
      SCROLL_WRAP = "scroll_wrap",
      SCROLL_FRICTION = "scroll_friction",

  # touch-menu
      TOUCH_MENU_BUTTON_COUNT = "touch_menu_button_count",

  # trigger
      ADAPTIVE_THRESHOLD = "adaptive_threshold",
      OUTPUT_TRIGGER = "output_trigger",

  # absolute-mouse
      ACCELERATION = "acceleration",
      MOUSE_SMOOTHING = "mouse_smoothing",
      )
    _VSC_KEYS.DOUBETAP_MAX_DURATION = _VSC_KEYS.DOUBLETAP_MAX_DURATION  # maintain misspelling.

    # Values for 'acceleration'.
    Acceleration = PseudoNamespace(
      OFF = 0,
      LOW = 1,
      MEDIUM = 2,
      HIGH = 3,
      )

    # Values for 'curve_exponent'.
    CurveExponent = PseudoNamespace(
      LINEAR = 0,
      AGGRESIVE = 1,
      RELAXED = 2,
      WIDE = 3,
      EXTRA_WIDE = 4,
      CUSTOM = 5,
      )

    # Values for 'deadzone_shape'.
    DeadzoneShape = PseudoNamespace(
      CROSS = 0,
      CIRCLE = 1,
      SQUARE = 2,
      )

    # Values for 'friction'.
    Friction = PseudoNamespace(
      OFF = 0,
      LOW = 1,
      MEDIUM = 2,
      HIGH = 3,
      )
    # aliases
    Friction.DEFAULT = Friction.MEDIUM

    # values for 'gyro_button'.
    GyroButton = PseudoNamespace(
      ALWAYS = None,   # actually, key itself should be missing.
      RIGHT_PAD_TOUCH = 1,
      LEFT_PAD_TOUCH = 2,
      RIGHT_PAD_CLICK = 3,
      LEFT_PAD_CLICK = 4,
      RIGHT_BUMPER = 5,
      LEFT_BUMPER = 6,
      RIGHT_GRIP = 7,
      LEFT_GRIP = 8,
      RIGHT_TRIGGER_FULL = 9,
      LEFT_TRIGGER_FULL = 10,
      RIGHT_TRIGGER_SOFT = 11,
      LEFT_TRIGGER_SOFT = 12,
      A = 13,
      B = 14,
      X = 15,
      Y = 16,
      LEFT_STICK_CLICK = 17,
      )

    # Values for 'haptic_intensity'.
    HapticIntensity = PseudoNamespace(
      OFF = 0,
      LOW = 1,
      MEDIUM = 2,
      HIGH = 3,
      )

    # Values for 'mouse_dampening_trigger'.
    MouseDampeningTrigger = PseudoNamespace(
      NO = 0,
      RIGHT_TRIGGER_SOFT_PULL = 1,
      LEFT_TRIGGER_SOFT_PULL = 2,
      BOTH_TRIGGER_SOFT_PULL = 3,
      RIGHT_TRIGGER_FULL_PULL = 4,
      LEFT_TRIGGER_FULL_PULL = 5,
      BOTH_TRIGGER_FULL_PULL = 6,
      )

    # Values for 'swipe_duration'.
    SwipeDuration = PseudoNamespace(
      OFF = 0,
      LOW = 1,
      MEDIUM = 2,
      HIGH =3,
      )

    # Values for 'output_joystick'.
    OutputAxis = PseudoNamespace(
      HORIZONTAL = 0,
      VERTICAL = 1,
      BOTH = 2,
      )

    # Values for 'output_trigger'.
    OutputTrigger = PseudoNamespace(
      NO_ANALOG = 0,
      LEFT_TRIGGER = 1,
      RIGHT_TRIGGER = 2,
      )

    # Values for 'touchmenu_button_fire_type'.
    TouchmenuButtonFireType = PseudoNamespace(
      BUTTON_CLICK = 0,
      BUTTON_RELEASE = 1,
      TOUCH_RELEASE_MODESHIFT_END = 2,
      ALWAYS = 3,
      )
    # aliases
    TouchmenuButtonFireType.TOUCH_RELEASE = TouchmenuButtonFireType.TOUCH_RELEASE_MODESHIFT_END,
    TouchmenuButtonFireType.MODESHIFT_END = TouchmenuButtonFireType.TOUCH_RELEASE_MODESHIFT_END,

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
    self.settings = self.Settings(py_settings)

    if py_inputs:
      # Expect dictionary of key to pyobjects.
      self.inputs.update(inputs)
    elif VSC_INPUTS in kwargs:
      # expect dict within ControllerConfig
      for (inp_name, inp_kv) in kwargs[VSC_INPUTS].items():
        self.make_input(inp_name, **inp_kv)

    if VSC_SETTINGS in kwargs:
      # Expect dictionary of pure scalars.  This might break in future?
      self.settings.update(kwargs[VSC_SETTINGS])

  def make_input (self, input_element, py_activators=None, **kwargs):
    '''Factory for 'input' node.'''
    inp = ControllerInput(input_element, py_activators=py_activators, **kwargs)
    self.inputs[input_element] = inp
    return inp

  def encode_kv (self):
    kv = scvdf.SCVDFDict()
    kv['id'] = str(self.index)
    kv['mode'] = str(self.mode)
    # Always generate ['inputs']
    kv[VSC_INPUTS] = self.inputs.encode_kv()
    if self.settings:
      kv[VSC_SETTINGS] = self.settings.encode_kv()
    return kv

class GroupAbsoluteMouse (GroupBase):
  CLICK = "click"
  DOUBLETAP = "doubletap"
  TOUCH = "toucH"
  INPUTS = set([
    CLICK, DOUBLETAP, TOUCH
    ])

  class Settings (GroupBase.Settings):
    # Values for 'friction.
    Friction = PseudoNamespace(
      OFF = 0,    # no inertia -- do not spin at all
      LOW = 1,
      MEDIUM = 2,
      HIGH = 3,
      NONE = 4,   # no-friction -- spin forever
      )

    S = GroupBase.Settings._VSC_KEYS
    _CONSTRAINTS = {
      S.SENSITIVITY: (1, 1000),
      S.TRACKBALL: bool,
      S.DOUBLETAP_BEEP: bool,
      S.INVERT_X: bool,
      S.INVERT_Y: bool,
      S.HAPTIC_INTENSITY: GroupBase.Settings.HapticIntensity,
      S.ROTATION: (-30, 30),
      S.FRICTION: Friction,
      S.FRICTION_VERT_SCALE: (0, 200),
      S.SENSITIVITY_VERT_SCALE: (0, 200),
      S.ACCELERATION: GroupBase.Settings.Acceleration,
      S.MOUSE_MOVE_THRESHOLD: (0, 40),
      S.MOUSE_SMOOTHING: (0, 40),
      S.EDGE_SPIN_VELOCITY: (0, 1000),
      S.EDGE_SPIN_RADIUS: (0, 32767),
      S.DOUBLETAP_MAX_DURATION: (20, 500),
      S.MOUSE_DAMPENING_TRIGGER: GroupBase.Settings.MouseDampeningTrigger,
      S.MOUSE_TRIGGER_CLAMP_AMOUNT: (0, 100),
      S.GYRO_AXIS: [ 0, 1 ],
      S.GYRO_BUTTON: GroupBase.Settings.GyroButton,
      S.GYRO_BUTTON_INVERT: [ 1, 2 ],  # invert, toggle
      S.DEADZONE_OUTER_RADIUS: (0, 32000),
      }
#  @property
#  def sensitivity (self):
#    return self.settings.get(self.S.SENSITIVITY, None)
#  @sensitivity.setter
#  def sensitivity (self, val):
#    self.setings[self.S.SENSITIVITY] = val
#  @sensitivity.deleter
#  def sensitivity (self):
#    del self.settings[self.S.SENSITIVITY]
    sensitivity = property(SettingsBase._settings_getter(S.SENSITIVITY),
                            SettingsBase._settings_setter(S.SENSITIVITY),
                            SettingsBase._settings_deleter(S.SENSITIVITY))

    trackball = SettingsBase._new_setting(S.TRACKBALL)
    doubletap_beep = SettingsBase._new_setting(S.DOUBLETAP_BEEP)
    invert_x = SettingsBase._new_setting(S.INVERT_X)
    invert_y = SettingsBase._new_setting(S.INVERT_Y)
    haptic_intensity = SettingsBase._new_setting(S.HAPTIC_INTENSITY)
    rotation = SettingsBase._new_setting(S.ROTATION)
    friction = SettingsBase._new_setting(S.FRICTION)
    friction_vert_scale = SettingsBase._new_setting(S.FRICTION_VERT_SCALE)
    sensitivity_vert_scale = SettingsBase._new_setting(S.SENSITIVITY_VERT_SCALE)
    acceleration = SettingsBase._new_setting(S.ACCELERATION)
    mouse_move_threshold = SettingsBase._new_setting(S.MOUSE_MOVE_THRESHOLD)
    mouse_smoothing = SettingsBase._new_setting(S.MOUSE_SMOOTHING)
    edge_spin_velocity = SettingsBase._new_setting(S.EDGE_SPIN_VELOCITY)
    edge_spin_radius = SettingsBase._new_setting(S.EDGE_SPIN_RADIUS)
    doubletap_max_duration = SettingsBase._new_setting(S.DOUBLETAP_MAX_DURATION)
    mouse_dampening_trigger = SettingsBase._new_setting(S.MOUSE_DAMPENING_TRIGGER)
    mouse_trigger_clamp_amount = SettingsBase._new_setting(S.MOUSE_TRIGGER_CLAMP_AMOUNT)
    gyro_axis = SettingsBase._new_setting(S.GYRO_AXIS)
    gyro_button = SettingsBase._new_setting(S.GYRO_BUTTON)
    gyro_button_invert = SettingsBase._new_setting(S.GYRO_BUTTON_INVERT)
    deadzone_outer_radius = SettingsBase._new_setting(S.DEADZONE_OUTER_RADIUS)
    # alias
    doubetape_max_duraction = doubletap_max_duration

  def __init__ (self, index=None, py_inputs=None, py_settings=None, **kwargs):
    GroupBase.__init__(self, 'absolute_mouse', index, py_inputs, py_settings, **kwargs)


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

  class Settings (GroupBase.Settings):
    Layout = PseudoNamespace(
      FOUR_WAY = 0,
      EIGHT_WAY = 1,
      ANALOG_EMULATION = 2,
      CROSS_GATE = 3,
      )

    S = GroupBase.Settings._VSC_KEYS
    GyroButton = GroupBase.Settings.GyroButton
    HapticIntensityOverride = GroupBase.Settings.HapticIntensity
    _CONSTRAINTS = {
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

    requires_click = SettingsBase._new_setting(S.REQUIRES_CLICK)
    layout = SettingsBase._new_setting(S.LAYOUT)
    deadzone = SettingsBase._new_setting(S.DEADZONE)
    edge_binding_radius = SettingsBase._new_setting(S.EDGE_BINDING_RADIUS)
    edge_binding_invert = SettingsBase._new_setting(S.EDGE_BINDING_INVERT)
    analog_emulation_period = SettingsBase._new_setting(S.ANALOG_EMULATION_PERIOD)
    overlap_region = SettingsBase._new_setting(S.OVERLAP_REGION)
    gyro_button_invert = SettingsBase._new_setting(S.GYRO_BUTTON_INVERT)
    gyro_button = SettingsBase._new_setting(S.GYRO_BUTTON)
    gyro_neutral = SettingsBase._new_setting(S.GYRO_NEUTRAL)
    haptic_intensity_override = SettingsBase._new_setting(S.HAPTIC_INTENSITY_OVERRIDE)

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

  class Settings (GroupBase.Settings):
    S = GroupBase.Settings._VSC_KEYS
    _CONSTRAINTS = {
      S.REQUIRES_CLICK: bool,
      S.BUTTON_SIZE: (1, 32767),
      S.BUTTON_DIST: (1, 32767),
      }
    requires_click = SettingsBase._new_setting(S.REQUIRES_CLICK)
    button_size = SettingsBase._new_setting(S.BUTTON_SIZE)
    button_dist = SettingsBase._new_setting(S.BUTTON_DIST)
    # alias
    button_distance = button_dist

  def __init__ (self, index=None, py_inputs=None, py_settings=None, **kwargs):
    GroupBase.__init__(self, 'four_buttons', index, py_inputs, py_settings, **kwargs)


class GroupJoystickCamera (GroupBase):
  class Settings (GroupBase.Settings):
    CurveExponent = GroupBase.Settings.CurveExponent
    SwipeDuration = GroupBase.Settings.SwipeDuration
    HapticIntensity = GroupBase.Settings. HapticIntensity
    GyroButton = GroupBase.Settings.GyroButton
    OutputJoystick = PseudoNamespace(
      MATCHED_SIDE = 0,
      OPPOSITE_SITE = 1,
      RELATIVE_MOUSE = 2,
      )

    S = GroupBase.Settings._VSC_KEYS
    _CONSTRAINTS = {
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
    curve_exponent = SettingsBase._new_setting(S.CURVE_EXPONENT)
    swipe_duration = SettingsBase._new_setting(S.SWIPE_DURATION)
    haptic_intensity = SettingsBase._new_setting(S.HAPTIC_INTENSITY)
    output_joystick = SettingsBase._new_setting(S.OUTPUT_JOYSTICK)
    sensitivity_vert_scale = SettingsBase._new_setting(S.SENSITIVITY_VERT_SCALE)
    anti_deadzone = SettingsBase._new_setting(S.ANTI_DEADZONE)
    anti_deadzone_buffer = SettingsBase._new_setting(S.ANTI_DEADZONE_BUFFER)
    invert_x = SettingsBase._new_setting(S.INVERT_X)
    invert_y = SettingsBase._new_setting(S.INVERT_Y)
    joystick_smoothing = SettingsBase._new_setting(S.JOYSTICK_SMOOTHING)
    sensitivity = SettingsBase._new_setting(S.SENSITIVITY)
    gyro_button = SettingsBase._new_setting(S.GYRO_BUTTON)
    gyro_neutral = SettingsBase._new_setting(S.GYRO_NEUTRAL)

  def __init__ (self, index=None, py_inputs=None, py_settings=None, **kwargs):
    GroupBase.__init__(self, 'joystick_camera', index, py_inputs, py_settings, **kwargs)


class GroupJoystickMouse (GroupBase):
  CLICK = "click"
  EDGE = "edge"
  INPUTS = set([ CLICK, EDGE ])

  class Settings (GroupBase.Settings):
    CurveExponent = GroupBase.Settings.CurveExponent
    OutputJoystick = PseudoNamespace(
      MATCHED_SIDE = 0,
      OPPOSITE_SIDE = 1,
      )
    S = GroupBase.Settings._VSC_KEYS
    _CONSTRAINTS = {
      S.CURVE_EXPONENT: CurveExponent,
      S.CUSTOM_CURVE_EXPONENT: int,   # TODO: research range
      S.EDGE_BINDING_RADIUS: (0, 32767),
      S.EDGE_BINDING_INVERT: bool,
      S.ANTI_DEADZONE: (0, 32767),
      S.ANTI_DEADZONE_BUFFER: (0, 32767),
      S.OUTPUT_JOYSTICK: OutputJoystick,
    }
    curve_exponent = SettingsBase._new_setting(S.CURVE_EXPONENT)
    custom_curve_exponent = SettingsBase._new_setting(S.CUSTOM_CURVE_EXPONENT)
    edge_binding_radius = SettingsBase._new_setting(S.EDGE_BINDING_RADIUS)
    edge_binding_invert = SettingsBase._new_setting(S.EDGE_BINDING_INVERT)
    anti_deadzone = SettingsBase._new_setting(S.ANTI_DEADZONE)
    anti_deadzone_buffer = SettingsBase._new_setting(S.ANTI_DEADZONE_BUFFER)
    output_joystick = SettingsBase._new_setting(S.OUTPUT_JOYSTICK)

  def __init__ (self, index=None, py_inputs=None, py_settings=None, **kwargs):
    GroupBase.__init__(self, 'joystick_mouse', index, py_inputs, py_settings, **kwargs)


class GroupJoystickMove (GroupBase):
  class Settings (GroupBase.Settings):
    CurveExponent = GroupBase.Settings.CurveExponent
    DeadzoneShape = GroupBase.Settings.DeadzoneShape
    GyroButton = GroupBase.Settings.GyroButton
    HapticIntensity = GroupBase.Settings.HapticIntensity
    OutputAxis = GroupBase.Settings.OutputAxis
    OutputJoystick = PseudoNamespace(
      LEFT_JOYSTICK = 0,
      RIGHT_JOYSTICK = 1,
      RELATIVE_JOYSTICK = 2,
      )
    S = GroupBase.Settings._VSC_KEYS
    _CONSTRAINTS = {
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
    curve_exponent = SettingsBase._new_setting(S.CURVE_EXPONENT)
    custom_curve_exponent = SettingsBase._new_setting(S.CUSTOM_CURVE_EXPONENT)
    edge_binding_radius = SettingsBase._new_setting(S.EDGE_BINDING_RADIUS)
    edge_binding_invert = SettingsBase._new_setting(S.EDGE_BINDING_INVERT)
    output_joystick = SettingsBase._new_setting(S.OUTPUT_JOYSTICK)
    anti_deadzone = SettingsBase._new_setting(S.ANTI_DEADZONE)
    anti_deadzone_buffer = SettingsBase._new_setting(S.ANTI_DEADZONE_BUFFER)
    haptic_intensity = SettingsBase._new_setting(S.HAPTIC_INTENSITY)
    deadzone_inner_radius = SettingsBase._new_setting(S.DEADZONE_INNER_RADIUS)
    deadzone_outer_radius = SettingsBase._new_setting(S.DEADZONE_OUTER_RADIUS)
    output_axis = SettingsBase._new_setting(S.OUTPUT_AXIS)
    gyro_lock_extents = SettingsBase._new_setting(S.GYRO_LOCK_EXTENTS)
    invert_x = SettingsBase._new_setting(S.INVERT_X)
    invert_y = SettingsBase._new_setting(S.INVERT_Y)
    sensitivity = SettingsBase._new_setting(S.SENSITIVITY)
    sensitivity_vert_scale = SettingsBase._new_setting(S.SENSITIVITY_VERT_SCALE)
    sensitivity_horiz_scale = SettingsBase._new_setting(S.SENSITIVITY_HORIZ_SCALE)
    gyro_neutral = SettingsBase._new_setting(S.GYRO_NEUTRAL)
    gyro_button = SettingsBase._new_setting(S.GYRO_BUTTON)
    gyro_button_invert = SettingsBase._new_setting(S.GYRO_BUTTON_INVERT)
    gyro_lock_extents = SettingsBase._new_setting(S.GYRO_LOCK_EXTENTS)

  def __init__ (self, index=None, py_inputs=None, py_settings=None, **kwargs):
    GroupBase.__init__(self, 'joystick_move', index, py_inputs, py_settings, **kwargs)


class GroupMouseJoystick (GroupBase):
  class Settings (GroupBase.Settings):
    Friction = GroupBase.Settings.Friction
    GyroButton = GroupBase.Settings.GyroButton
    MouseDampeningTrigger = GroupBase.Settings.MouseDampeningTrigger
    S = GroupBase.Settings._VSC_KEYS
    _CONSTRAINTS = {
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
    trackball = SettingsBase._new_setting(S.TRACKBALL)
    doubletap_beep = SettingsBase._new_setting(S.DOUBLETAP_BEEP)
    invert_x = SettingsBase._new_setting(S.INVERT_X)
    invert_y = SettingsBase._new_setting(S.INVERT_Y)
    haptic_intensity = SettingsBase._new_setting(S.HAPTIC_INTENSITY)
    rotation = SettingsBase._new_setting(S.ROTATION)
    friction = SettingsBase._new_setting(S.FRICTION)
    sensitivity_vert_scale = SettingsBase._new_setting(S.SENSITIVITY_VERT_SCALE)
    mouse_move_threshold = SettingsBase._new_setting(S.MOUSE_MOVE_THRESHOLD)
    edge_spin_velocity = SettingsBase._new_setting(S.EDGE_SPIN_VELOCITY)
    edge_spin_radius = SettingsBase._new_setting(S.EDGE_SPIN_RADIUS)
    doubletap_max_duration = SettingsBase._new_setting(S.DOUBLETAP_MAX_DURATION)
    mouse_dampening_trigger = SettingsBase._new_setting(S.MOUSE_DAMPENING_TRIGGER)
    mouse_trigger_clamp_amount = SettingsBase._new_setting(S.MOUSE_TRIGGER_CLAMP_AMOUNT)
    mousejoystick_deadzone_x = SettingsBase._new_setting(S.MOUSEJOYSTICK_DEADZONE_X)
    mousejoystick_deadzone_y = SettingsBase._new_setting(S.MOUSEJOYSTICK_DEADZONE_Y)
    mousejoystick_precision = SettingsBase._new_setting(S.MOUSEJOYSTICK_PRECISION)
    custom_curve_exponent = SettingsBase._new_setting(S.CUSTOM_CURVE_EXPONENT)
    gyro_button = SettingsBase._new_setting(S.GYRO_BUTTON)
    gyro_button_invert = SettingsBase._new_setting(S.GYRO_BUTTON_INVERT)
    gyro_axis = SettingsBase._new_setting(S.GYRO_AXIS)
    gyro_sensitivity_scale = SettingsBase._new_setting(S.GYRO_SENSITIVITY_SCALE)

  def __init__ (self, index=None, py_inputs=None, py_settings=None, **kwargs):
    GroupBase.__init__(self, 'mouse_joystick', index, py_inputs, py_settings, **kwargs)


class GroupMouseRegion (GroupBase):
  CLICK = "click"
  EDGE = "edge"
  TOUCH = "touch"
  INPUTS = set([ CLICK, EDGE, TOUCH ])

  class Settings (GroupBase.Settings):
    HapticIntensity = GroupBase.Settings.HapticIntensity
    MouseDampeningTrigger = GroupBase.Settings.MouseDampeningTrigger
    OutputJoystick = PseudoNamespace(
      LEFT = 0,
      RIGHT = 1,
      MOUSE = 2,
      )
    S = GroupBase.Settings._VSC_KEYS
    _CONSTRAINTS = {
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
    edge_binding_radius = SettingsBase._new_setting(S.EDGE_BINDING_RADIUS)
    edge_binding_invert = SettingsBase._new_setting(S.EDGE_BINDING_INVERT)
    haptic_intensity = SettingsBase._new_setting(S.HAPTIC_INTENSITY)
    output_joystick = SettingsBase._new_setting(S.OUTPUT_JOYSTICK)
    scale = SettingsBase._new_setting(S.SCALE)
    position_x = SettingsBase._new_setting(S.POSITION_X)
    position_y = SettingsBase._new_setting(S.POSITION_Y)
    sensitivity_vert_scale = SettingsBase._new_setting(S.SENSITIVITY_VERT_SCALE)
    sensitivity_horiz_scale = SettingsBase._new_setting(S.SENSITIVITY_HORIZ_SCALE)
    teleport_stop = SettingsBase._new_setting(S.TELEPORT_STOP)
    mouse_dampening_trigger = SettingsBase._new_setting(S.MOUSE_DAMPENING_TRIGGER)
    mouse_trigger_clamp_amount = SettingsBase._new_setting(S.MOUSE_TRIGGER_CLAMP_AMOUNT)

  def __init__ (self, index=None, py_inputs=None, py_settings=None, **kwargs):
    GroupBase.__init__(self, 'mouse_region', index, py_inputs, py_settings, **kwargs)


class GroupRadialMenu (GroupBase):
  CLICK = "click"
  # touch_menu_button_%d  0..15
  INPUTS = set([ CLICK, ])

  class Settings (GroupBase.Settings):
    TouchmenuButtonFireType = GroupBase.Settings.TouchmenuButtonFireType
    S = GroupBase.Settings._VSC_KEYS
    _CONSTRAINTS = {
      S.TOUCHMENU_BUTTON_FIRE_TYPE: TouchmenuButtonFireType,
      S.TOUCH_MENU_OPACITY: (40, 100),
      S.TOUCH_MENU_POSITION_X: (0, 100),
      S.TOUCH_MENU_POSITION_Y: (0, 100),
      S.TOUCH_MENU_SCALE: (50, 150),
      S.TOUCH_MENU_SHOW_LABELS: bool,
    }
    touchmenu_button_fire_type = SettingsBase._new_setting(S.TOUCHMENU_BUTTON_FIRE_TYPE)
    touch_menu_opacity = SettingsBase._new_setting(S.TOUCH_MENU_OPACITY)
    touch_menu_position_x = SettingsBase._new_setting(S.TOUCH_MENU_POSITION_X)
    touch_menu_position_y = SettingsBase._new_setting(S.TOUCH_MENU_POSITION_Y)
    touch_menu_scale = SettingsBase._new_setting(S.TOUCH_MENU_SCALE)
    touch_menu_show_labels = SettingsBase._new_setting(S.TOUCH_MENU_SHOW_LABELS)

  def __init__ (self, index=None, py_inputs=None, py_settings=None, **kwargs):
    GroupBase.__init__(self, 'radial_menu', index, py_inputs, py_settings, **kwargs)


class GroupScrollwheel (GroupBase):
  CLICK = "click"
  SCROLL_CLOCKWISE = "scroll_clockwise"
  SCROLL_COUNTERCLOCKWISE = "scroll_counterclockwise"
  # scroll_wheel_list_%d  0..9
  INPUTS = set([ CLICK, SCROLL_CLOCKWISE, SCROLL_COUNTERCLOCKWISE ])

  class Settings (GroupBase.Settings):
    Friction = GroupBase.Settings.Friction
    HapticIntensity = GroupBase.Settings.HapticIntensity
    ScrollType = PseudoNamespace(
      CIRCULAR = 0,
      HORIZONTAL = 1,
      VERTICAL = 2,
      )
    S = GroupBase.Settings._VSC_KEYS
    _CONSTRAINTS = {
      S.SCROLL_ANGLE: (1, 180),
      S.HAPTIC_INTENSITY: HapticIntensity,
      S.SCROLL_TYPE: ScrollType,
      S.SCROLL_INVERT: bool,
      S.SCROLL_WRAP: bool,
      S.SCROLL_FRICTION: Friction,
    }
    scroll_angle = SettingsBase._new_setting(S.SCROLL_ANGLE)
    haptic_intensity = SettingsBase._new_setting(S.HAPTIC_INTENSITY)
    scroll_type = SettingsBase._new_setting(S.SCROLL_TYPE)
    scroll_invert = SettingsBase._new_setting(S.SCROLL_INVERT)
    scroll_wrap = SettingsBase._new_setting(S.SCROLL_WRAP)
    scroll_friction = SettingsBase._new_setting(S.SCROLL_FRICTION)

  def __init__ (self, index=None, py_inputs=None, py_settings=None, **kwargs):
    GroupBase.__init__(self, 'scrollwheel', index, py_inputs, py_settings, **kwargs)


class GroupSingleButton (GroupBase):
  CLICK = "click"
  TOUCH = "touch"
  INPUTS = set([ CLICK, TOUCH ])

  def __init__ (self, index=None, py_inputs=None, py_settings=None, **kwargs):
    GroupBase.__init__(self, 'single_button', index, py_inputs, py_settings, **kwargs)

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

  def __init__ (self, index=None, py_inputs=None, py_settings=None, **kwargs):
    GroupBase.__init__(self, 'switches', index, py_inputs, py_settings, **kwargs)

class GroupTouchMenu (GroupBase):
  # touch_menu_button_%d  0..15
  class Settings (GroupBase.Settings):
    TouchmenuButtonFireType = GroupBase.Settings.TouchmenuButtonFireType
    S = GroupBase.Settings._VSC_KEYS
    _CONSTRAINTS = {
      S.TOUCH_MENU_BUTTON_COUNT: [ 2, 4, 7, 9, 12, 13, 16 ], 
      S.TOUCH_MENU_OPACITY: bool,
      S.TOUCH_MENU_POSITION_X: (0, 100),
      S.TOUCH_MENU_POSITION_Y: (0, 100),
      S.TOUCH_MENU_SCALE: (50, 150),
      S.TOUCH_MENU_SHOW_LABELS: bool,
      S.TOUCHMENU_BUTTON_FIRE_TYPE: TouchmenuButtonFireType,
      }
    touch_menu_button_count = SettingsBase._new_setting(S.TOUCH_MENU_BUTTON_COUNT)
    touch_menu_opacity = SettingsBase._new_setting(S.TOUCH_MENU_OPACITY)
    touch_menu_position_x = SettingsBase._new_setting(S.TOUCH_MENU_POSITION_X)
    touch_menu_position_y = SettingsBase._new_setting(S.TOUCH_MENU_POSITION_Y)
    touch_menu_scale = SettingsBase._new_setting(S.TOUCH_MENU_SCALE)
    touch_menu_show_labels = SettingsBase._new_setting(S.TOUCH_MENU_SHOW_LABELS)
    touchmenu_button_fire_type = SettingsBase._new_setting(S.TOUCHMENU_BUTTON_FIRE_TYPE)

  def __init__ (self, index=None, py_inputs=None, py_settings=None, **kwargs):
    GroupBase.__init__(self, 'touch_menu', index, py_inputs, py_settings, **kwargs)


class GroupTrigger (GroupBase):
  CLICK = "click"
  EDGE = "edge"
  INPUTS = set([ CLICK, EDGE ])

  class Settings (GroupBase.Settings):
    AdaptiveThreshold = PseudoNamespace(
      SIMPLE_THRESHOLD = 0,
      HAIR_TRIGGER = 1,
      HIP_FIRE_AGGRESSIVE = 2,
      HIP_FIRE_NORMAL = 3,
      HIP_FIRE_RELAXED = 4,
      HIP_FIRE_EXCLUSIVE = 5,
      )
    CurveExponent = GroupBase.Settings.CurveExponent
    OutputTrigger = GroupBase.Settings.OutputTrigger
    S = GroupBase.Settings._VSC_KEYS
    _CONSTRAINTS = {
      S.OUTPUT_TRIGGER: OutputTrigger,
      S.DEADZONE_OUTER_RADIUS: (0, 32767),
      S.DEADZONE_INNER_RADIUS: (0, 32767),
      S.EDGE_BINDING_RADIUS: (0, 32767),
      S.ADAPTIVE_THRESHOLD: AdaptiveThreshold,
      S.CURVE_EXPONENT: CurveExponent,
      S.CUSTOM_CURVE_EXPONENT: (25, 4000),
    }
    output_trigger = SettingsBase._new_setting(S.OUTPUT_TRIGGER)
    deadzone_outer_radius = SettingsBase._new_setting(S.DEADZONE_OUTER_RADIUS)
    deadzone_inner_radius = SettingsBase._new_setting(S.DEADZONE_INNER_RADIUS)
    edge_binding_radius = SettingsBase._new_setting(S.EDGE_BINDING_RADIUS)
    adaptive_threshold = SettingsBase._new_setting(S.ADAPTIVE_THRESHOLD)
    curve_exponent = SettingsBase._new_setting(S.CURVE_EXPONENT)
    custom_curve_exponent = SettingsBase._new_setting(S.CUSTOM_CURVE_EXPONENT)

  def __init__ (self, index=None, py_inputs=None, py_settings=None, **kwargs):
    GroupBase.__init__(self, 'trigger', index, py_inputs, py_settings, **kwargs)


class GroupFactory (object):
  @staticmethod
  def make_absolute_mouse (index, py_inputs=None, py_settings=None, **kwargs):
    return GroupAbsoluteMouse(index, py_inputs, py_settings=None, **kwargs)
  @staticmethod
  def make_dpad (index, py_inputs=None, py_settings=None, **kwargs):
    return GroupDpad(index, py_inputs, py_settings=None, **kwargs)
  @staticmethod
  def make_four_buttons (index, py_inputs=None, py_settings=None, **kwargs):
    return GroupFourButtons(index, py_inputs, py_settings=None, **kwargs)
  @staticmethod
  def make_joystick_camera (index, py_inputs=None, py_settings=None, **kwargs):
    return GroupJoystickCamera(index, py_inputs, py_settings=None, **kwargs)
  @staticmethod
  def make_joystick_move (index, py_inputs=None, py_settings=None, **kwargs):
    return GroupJoystickMove(index, py_inputs, py_settings=None, **kwargs)
  @staticmethod
  def make_joystick_mouse (index, py_inputs=None, py_settings=None, **kwargs):
    return GroupJoystickMouse(index, py_inputs, py_settings=None, **kwargs)
  @staticmethod
  def make_mouse_joystick (index, py_inputs=None, py_settings=None, **kwargs):
    return GroupJoystickMove(index, py_inputs, py_settings=None, **kwargs)
  @staticmethod
  def make_mouse_region (index, py_inputs=None, py_settings=None, **kwargs):
    return GroupMouseRegion(index, py_inputs, py_settings=None, **kwargs)
  @staticmethod
  def make_radial_menu (index, py_inputs=None, py_settings=None, **kwargs):
    return GroupRadialMenu(index, py_inputs, py_settings=None, **kwargs)
  @staticmethod
  def make_scrollwheel (index, py_inputs=None, py_settings=None, **kwargs):
    return GroupScrollwheel(index, py_inputs, py_settings=None, **kwargs)
  @staticmethod
  def make_single_button (index, py_inputs=None, py_settings=None, **kwargs):
    return GroupSingleButton(index, py_inputs, py_settings=None, **kwargs)
  @staticmethod
  def make_switches (index, py_inputs=None, py_settings=None, **kwargs):
    return GroupSwitches(index, py_inputs, py_settings=None, **kwargs)
  @staticmethod
  def make_touch_menu (index, py_inputs=None, py_settings=None, **kwargs):
    return GroupTouchMenu(index, py_inputs, py_settings=None, **kwargs)
  @staticmethod
  def make_trigger (index, py_inputs=None, py_settings=None, **kwargs):
    return GroupTrigger(index, py_inputs, py_settings=None, **kwargs)

  # GroupFactory.make
  @staticmethod
  def make (py_index=None, py_mode=None, py_inputs=None, py_settings=None, **kwargs):
    DISPATCH = {
      'absolute_mouse': GroupFactory.make_absolute_mouse,
      'dpad': GroupFactory.make_dpad,
      'four_buttons': GroupFactory.make_four_buttons,
      'joystick_camera': GroupFactory.make_joystick_camera,
      'joystick_mouse': GroupFactory.make_joystick_mouse,
      'joystick_move': GroupFactory.make_joystick_move,
      'mouse_joystick': GroupFactory.make_mouse_joystick,
      'mouse_region': GroupFactory.make_mouse_region,
      'radial_menu': GroupFactory.make_radial_menu,
      'scrollwheel': GroupFactory.make_scrollwheel,
      'single_button': GroupFactory.make_single_button,
      'switches': GroupFactory.make_switches,
      'touch_menu': GroupFactory.make_touch_menu,
      'trigger': GroupFactory.make_trigger,

      'pen': GroupFactory.make_absolute_mouse,
      'absolute': GroupFactory.make_absolute_mouse,
      '4buttons': GroupFactory.make_four_buttons,
      'face_buttons': GroupFactory.make_four_buttons,
      'camera': GroupFactory.make_joystick_camera,
      'joystick': GroupFactory.make_joystick_move,
      'mousejs': GroupFactory.make_mouse_joystick,
      'scroll_wheel': GroupFactory.make_scrollwheel,
      'radial': GroupFactory.make_radial_menu,
      'piemenu': GroupFactory.make_radial_menu,
      'pie_menu': GroupFactory.make_radial_menu,
      'region': GroupFactory.make_mouse_region,
      'singlebutton': GroupFactory.make_single_button,
      'one_button': GroupFactory.make_single_button,
      'onebutton': GroupFactory.make_single_button,
      'touchmenu': GroupFactory.make_touch_menu,
      }
    if py_mode is None:
      if 'mode' in kwargs:
        py_mode = kwargs['mode']
    if py_index is None:
      py_index = int(kwargs['id']) if 'id' in kwargs else None
    maker = DISPATCH.get(py_mode, None)
    if maker:
      return maker(py_index, py_inputs, py_settings, **kwargs)
    else:
      return None


def Group (*args, **kwargs):
  return GroupFactory.make(*args, **kwargs)

##### end Group #####


###########
# Overlay #
###########
# ActionSet
# ActionLayer

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

##### end of Overly #####


class GroupSourceBindingValue (object):
  ValidSources = PseudoNamespace(
    SWITCH = 'switch',
    DPAD = 'dpad',
    BUTTON_DIAMOND = 'button_diamond',
    LEFT_TRACKPAD = 'left_trackpad',
    RIGHT_TRACKPAD = 'right_trackpad',
    LEFT_TRIGGER = 'left_trigger',
    RIGHT_TRIGGER = 'right_trigger',
    JOYSTICK = 'joystick',
    RIGHT_JOYSTICK = 'right_joystick',
    )
  VALID_SOURCES = list(ValidSources.__dict__.values())

  def __init__ (self, groupsrc, active=True, modeshift=False):
    if ' ' in groupsrc:
      groupsrc, active, modeshift = self._parse(groupsrc)
    self.active = active
    self.modeshift = modeshift
    self._groupsrc = None
    # self.groupsrc is a property
    self.groupsrc = groupsrc

  @property
  def groupsrc (self):
    return self._groupsrc
  @groupsrc.setter
  def groupsrc (self, v):
    if v is not None:
      if v in GroupSourceBindingValue.VALID_SOURCES:
        self._groupsrc = v
        return
    raise ValueError("Bad group source '{}'".format(v))

  @staticmethod
  def _parse (s):
    words = s.split()
    inpsrc = words[0]
    active = (words[1] == VSC_ACTIVE) if len(words) > 1 else False
    modeshift = (words[2] == VSC_MODESHIFT) if len(words) > 2 else False
    return (inpsrc, active, modeshift)

  def encode_kv (self):
    words = [ self.groupsrc ]
    words.append(VSC_ACTIVE if self.active else VSC_INACTIVE)
    words.append(VSC_MODESHIFT) if self.modeshift else None
    return " ".join(words)


class Preset (object):
  def __init__ (self, index=None, py_name=None, py_gsb=None, **kwargs):
    if index is None:
      index = int(kwargs.get('id', 0))
    if py_name is None:
      py_name = kwargs.get('name', "")

    self.index = index
    self.name = py_name
    self.gsb = scvdf.SCVDFDict()  # map group-id:int to GroupSourceBindingValue

    if py_gsb:
      # expect compatible with dict.update()
      self.gsb.update(py_gsb)
    elif 'group_source_bindings' in kwargs:
      d = kwargs['group_source_bindings']
      for (gsb_key, gsb_value) in d.items():
        self.add_gsb(gsb_key, gsb_value)

  def add_gsb (self, groupid, groupsrc, active=True, modeshift=False):
    gsbv = GroupSourceBindingValue(groupsrc, active, modeshift)
    self.gsb[int(groupid)] = gsbv

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
    for k,v in self.gsb.items():
      kv_gsb[str(k)] = v.encode_kv()
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

  class Settings (SettingsBase):
    _VSC_KEYS = PseudoNamespace(
      LEFT_TRACKPAD_MODE = "left_trackpad_mode",
      RIGHT_TRACKPAD_MODE = "right_trackpad_mode",
      ACTION_SET_TRIGGER_CURSOR_SHOW = "action_set_trigger_cursor_show",
      ACTION_SET_TRIGGER_CURSOR_HIDE = "action_set_trigger_cursor_hide",
      )
    _CONSTRAINTS = {
    }
    left_trackpad_mode = SettingsBase._new_setting(_VSC_KEYS.LEFT_TRACKPAD_MODE)
    right_trackpad_mode = SettingsBase._new_setting(_VSC_KEYS.RIGHT_TRACKPAD_MODE)
    action_set_trigger_cursor_show = SettingsBase._new_setting(_VSC_KEYS.ACTION_SET_TRIGGER_CURSOR_SHOW)
    action_set_trigger_cursor_hide = SettingsBase._new_setting(_VSC_KEYS.ACTION_SET_TRIGGER_CURSOR_HIDE)

  def __init__ (self, py_version=None, py_revision=None, py_title=None, py_description=None, py_creator=None, py_controller_type=None, py_timestamp=None, py_settings=None, **kwargs):
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
    self.settings = self.Settings(py_settings)

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

