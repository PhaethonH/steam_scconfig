#!/usr/bin/env python3

# Configurator module for Steam Valve Controller

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
    if keycode in self.TRANSLATION:
      vdfliteral = self.TRANSLATION[keycode]
      BindingBase.__init__(self, "xinput_button", vdfliteral, label)
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
  def __init__ (self):
    pass
  pass


class Group (object):
  """A group of controls.
Multiple controller elements combine together into groups that act as a unit to form a higher-order input type.
Notable example include the four cardinal points of a d-pad to form not just a d-pad, but also pie menu control.
"""
  pass

class ActionLayer (object):
  """Action Layer, consists of one or more  ..."""
  pass


class ActionSet (object):
  """An 'Action Set', consists of one or more Actions Layers."""
  pass


class Mapping (object):
  """Encapsulates controller mapping (toplevel)"""
  pass
  def __init __(self):
    self.version = 3
    self.revision = 0
    self.title = "Unnamed"
    self.description = "Unnamed configuration"
    self.creator = 0
    self.controller_type = "controller_ps3"
    self.timetsamp = "0"
    # List of Action Sets
    self.actions = []
    # List of Action Layers
    self.layers = []
    # List of Groups
    self.groups = []
    # List of Presets
    self.presets = []
    # Miscellaneous settings
    self.settings = {}

