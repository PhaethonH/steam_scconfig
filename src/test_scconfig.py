#!/usr/bin/env python3
# encoding=utf-8

try:
  unicode
except NameError:
  # py3
  def bytevector (x):
    return bytes(x, "utf-8")
else:
  # py2
  bytevector = bytes


import unittest, hashlib, sys
import scconfig, scvdf
try:
  from StringIO import StringIO
except ImportError:
  from io import StringIO

PRESET_DEFAULTS1 = [('controller_mappings',
  [('version', '3'),
   ('revision', '2'),
   ('title', 'Defaults1'),
   ('description',
    'Evocation of built-in gamepad binds by corrupting save files.'),
   ('creator', '76561198085425470'),
   ('controller_type', 'controller_steamcontroller_gordon'),
   ('Timestamp', '-366082071'),
   ('group',
    [('id', '0'),
     ('mode', 'four_buttons'),
     ('inputs',
      [('button_a',
        [('activators',
          [('Full_Press',
            [('bindings', [('binding', 'xinput_button A')])])])]),
       ('button_b',
        [('activators',
          [('Full_Press',
            [('bindings', [('binding', 'xinput_button B')])])])]),
       ('button_x',
        [('activators',
          [('Full_Press',
            [('bindings', [('binding', 'xinput_button X')])])])]),
       ('button_y',
        [('activators',
          [('Full_Press',
            [('bindings', [('binding', 'xinput_button Y')])])])])])]),
   ('group',
    [('id', '1'),
     ('mode', 'dpad'),
     ('inputs',
      [('dpad_north',
        [('activators',
          [('Full_Press',
            [('bindings', [('binding', 'xinput_button dpad_up')])])])]),
       ('dpad_south',
        [('activators',
          [('Full_Press',
            [('bindings',
              [('binding', 'xinput_button dpad_down')])])])]),
       ('dpad_east',
        [('activators',
          [('Full_Press',
            [('bindings',
              [('binding', 'xinput_button dpad_right')])])])]),
       ('dpad_west',
        [('activators',
          [('Full_Press',
            [('bindings',
                              [('binding', 'xinput_button dpad_left')])])])])]),
     ('settings', [('deadzone', '5000')])]),
   ('group',
    [('id', '2'),
     ('mode', 'joystick_camera'),
     ('inputs',
      [('click',
        [('activators',
          [('Full_Press',
            [('bindings',
              [('binding', 'xinput_button JOYSTICK_RIGHT')]),
             ('settings', [('haptic_intensity', '1')])])])])])]),
   ('group',
    [('id', '3'),
     ('mode', 'joystick_move'),
     ('inputs',
      [('click',
        [('activators',
          [('Full_Press',
            [('bindings',
              [('binding', 'xinput_button JOYSTICK_LEFT')]),
             ('settings', [('haptic_intensity', '2')])])])])])]),
   ('group',
    [('id', '4'),
     ('mode', 'trigger'),
     ('inputs',
      [('click',
        [('activators',
          [('Full_Press',
            [('bindings',
              [('binding', 'xinput_button TRIGGER_LEFT')]),
             ('settings', [('haptic_intensity', '2')])])])])]),
     ('settings', [('output_trigger', '1')])]),
   ('group',
    [('id', '5'),
     ('mode', 'trigger'),
     ('inputs',
      [('click',
        [('activators',
          [('Full_Press',
            [('bindings',
              [('binding', 'xinput_button TRIGGER_RIGHT')]),
             ('settings', [('haptic_intensity', '2')])])])])]),
     ('settings', [('output_trigger', '2')])]),
   ('group',
    [('id', '6'),
     ('mode', 'switches'),
     ('inputs',
      [('button_escape',
        [('activators',
          [('Full_Press',
            [('bindings', [('binding', 'xinput_button start')])])])]),
       ('button_menu',
        [('activators',
          [('Full_Press',
            [('bindings', [('binding', 'xinput_button select')])])])]),
       ('left_bumper',
        [('activators',
          [('Full_Press',
            [('bindings',
              [('binding', 'xinput_button shoulder_left')])])])]),
       ('right_bumper',
        [('activators',
          [('Full_Press',
            [('bindings',
              [('binding', 'xinput_button shoulder_right')])])])]),
       ('button_back_left',
        [('activators',
          [('Full_Press',
            [('bindings', [('binding', 'xinput_button a')])])])]),
       ('button_back_right',
        [('activators',
          [('Full_Press',
            [('bindings', [('binding', 'xinput_button x')])])])])])]),
   ('preset',
    [('id', '0'),
     ('name', 'Default'),
     ('group_source_bindings',
      [('6', 'switch active'),
       ('0', 'button_diamond active'),
       ('1', 'left_trackpad active'),
       ('2', 'right_trackpad active'),
       ('3', 'joystick active'),
       ('4', 'left_trigger active'),
       ('5', 'right_trigger active')])]),
   ('settings', [('left_trackpad_mode', '0'), ('right_trackpad_mode', '0')])])]


try:
  unittest.TestCase.assertRaisesRegex
except AttributeError:
  # py2
  unittest.TestCase.assertRaisesRegex = unittest.TestCase.assertRaisesRegexp


class TestSupportClasses (unittest.TestCase):
  def test_restrictive_dict (self):
    TargetDict = scconfig.RestrictiveDict
    src = { "alpha": 1 }
    d = TargetDict(src)
    self.assertEqual(d, { "alpha": 1 })

    d = TargetDict()
    d._ALLOW = True
    d['alpha'] = 1
    d['echo'] = { "e":0, "c":1, "h":2, "o":3 }
    self.assertEqual(d['alpha'], 1)
    self.assertEqual(d['echo'], { "e":0, "c":1, "h":2, "o":3 })

    d = TargetDict()
    d._ALLOW = { "alpha", "bravo", "charlie" }
    d['alpha'] = 1
    d['bravo'] = "b"
    d['charlie'] = [10,20,30]
    with self.assertRaisesRegex(KeyError, "not allowed"):
      d['delta'] = True

    p = dict(list(d.items()))
    self.assertEqual(p, { "alpha": 1, "bravo": "b", "charlie": [10,20,30] })

    d['charlie'] = 30
    p = dict(list(d.items()))
    self.assertEqual(p, { "alpha": 1, "bravo": "b", "charlie": 30 })

    class Restrict1 (TargetDict):
      _ALLOW = {}
      ALPHA = "alpha"
      BRAVO = "bravo"
      CHARLIE = "charlie"
    Restrict1._create_alias(Restrict1.ALPHA)
    Restrict1._create_alias(Restrict1.BRAVO)
    Restrict1._create_alias(Restrict1.CHARLIE)

    class Restrict2 (TargetDict):
      _ALLOW = {}
      ABLE = "able"
      BAKER = "baker"
      CHARLIE = "charlie"
    Restrict2._create_alias(Restrict2.ABLE)
    Restrict2._create_alias(Restrict2.BAKER)
    Restrict2._create_alias(Restrict2.CHARLIE)

    self.assertEqual(Restrict1._ALLOW, { "alpha", "bravo", "charlie" })
    self.assertEqual(Restrict2._ALLOW, { "able", "baker", "charlie" })

    r1 = Restrict1()
    r2 = Restrict2()

    r1['alpha'] = True
    r1['bravo'] = True
    r1['charlie'] = True
    with self.assertRaisesRegex(KeyError, "not allowed"):
      r1["able"] = True
    with self.assertRaisesRegex(KeyError, "not allowed"):
      r1["baker"] = True

    r2['able'] = True
    r2['baker'] = True
    r2['charlie'] = True
    with self.assertRaisesRegex(KeyError, "not allowed"):
      r2["alpha"] = True
    with self.assertRaisesRegex(KeyError, "not allowed"):
      r2["bravo"] = True


class TestScvdfComponents (unittest.TestCase):
  def test_binding (self):
    b = scconfig.Binding("key_press ESCAPE, Open Menu")
    self.assertEqual(b.geninfo.__class__, scconfig.Evgen_Keystroke)
    self.assertEqual(b.label, "Open Menu")

    b = scconfig.Binding("mouse_button 1")
    self.assertEqual(b.geninfo.__class__, scconfig.Evgen_MouseSwitch)

    b = scconfig.Binding("xinput_button a")
    self.assertEqual(b.geninfo.__class__, scconfig.Evgen_Gamepad)

    b = scconfig.Binding("controller_action steammusic_playpause")
    self.assertEqual(b.geninfo.__class__, scconfig.Evgen_Host)

    b = scconfig.Binding("controller_action set_led 0 0 0 0 0 0")
    self.assertEqual(b.geninfo.__class__, scconfig.Evgen_Light)

    b = scconfig.Binding("controller_action add_layer 2 0 0")
    self.assertEqual(b.geninfo.__class__, scconfig.Evgen_Overlay)

    b = scconfig.Binding("mode_shift joystick 12")
    self.assertEqual(b.geninfo.__class__, scconfig.Evgen_Modeshift)

    b = scconfig.Binding("controller_action empty_binding")
    self.assertEqual(b.geninfo.__class__, scconfig.Evgen_Empty)

    b = scconfig.Binding("controller_action change_preset 2 0 0")
    self.assertEqual(b.geninfo.__class__, scconfig.Evgen_Overlay)

    b = scconfig.Binding("controller_action sed_led 255 0 255 100 192 2, manually set led, ghost_045_move_0413.png #232323 #E4E4E4")
    self.assertEqual(b.geninfo.__class__, scconfig.Evgen_Light)
    self.assertEqual(b.label, "manually set led")
    self.assertEqual(b.iconinfo.__class__, scconfig.IconInfo)
    self.assertEqual(b.iconinfo.path, "ghost_045_move_0413.png")
    self.assertEqual(b.iconinfo.bg, "#232323")
    self.assertEqual(b.iconinfo.fg, "#E4E4E4")

  def test_group (self):
    g = scconfig.GroupDpad()

    # Test boolean property.
    g.settings.requires_click
    g.settings.requires_click = True
    self.assertEqual(g.settings.requires_click, True)
    g.settings.requires_click = False
    self.assertEqual(g.settings.requires_click, False)
    with self.assertRaisesRegex(ValueError, 'Value 42.*constraint.*bool'):
      g.settings.requires_click = 42
    self.assertEqual(g.settings.requires_click, False)

    # Test enumerated/namespaced property.
    g.settings.layout
    g.settings.layout = g.settings.Layout.CROSS_GATE
    self.assertEqual(g.settings.layout, 3)
    g.settings.layout = g.settings.Layout.EIGHT_WAY
    self.assertEqual(g.settings.layout, 1)
    with self.assertRaisesRegex(ValueError, 'Value 42.*namespace constraint'):
      g.settings.layout = 42
    self.assertEqual(g.settings.layout, 1)

    # Test range-constraint integer.
    g.settings.deadzone
    g.settings.deadzone = 0
    self.assertEqual(g.settings.deadzone, 0)
    g.settings.deadzone = 10000
    self.assertEqual(g.settings.deadzone, 10000)
    g.settings.deadzone = 32000
    self.assertEqual(g.settings.deadzone, 32000)
    with self.assertRaisesRegex(ValueError, "Value.*constraint.*0, 32767"):
      g.settings.deadzone = 99999
    self.assertEqual(g.settings.deadzone, 32000)

    kv = scconfig.toVDF(g.settings)
    self.assertEqual(kv, { "requires_click": "0", "layout": "1", "deadzone": "32000" })

    s = g.settings
    s.__class__.check_of_list = s._alias("check_of_list")
    s._CONSTRAINTS['check_of_list'] = [ 'foo', 'bar', 'quux' ]
    self.assertEqual(s.check_of_list, None)
    with self.assertRaisesRegex(ValueError, 'Value.*constraint.*\['):
      s.check_of_list = 42
    s.check_of_list ='bar'
    self.assertEqual(s.check_of_list, 'bar')

  def test_inputs (self):
    # Test accessing and mutating input elements of a group.
    g = scconfig.GroupDpad()
    self.assertEqual(g.inputs.__class__, scconfig.GroupDpad.Inputs)
    i = g.inputs.dpad_up
    self.assertEqual(i, None)
    # Test assigning invalid key => error.
    with self.assertRaises(KeyError):
      g.inputs['dpad_nope'] = None
    # Test making with almost-but-still-invalid key => error.
    with self.assertRaises(KeyError):
      g.add_input("dpad_up")
    g.add_input("dpad_north")
    i = g.inputs.dpad_up
    self.assertEqual(type(i), scconfig.ControllerInput)

  def test_activator (self):
    a = scconfig.ActivatorFullPress()
    a.settings.toggle = True
    a.settings.haptic_intensity = a.settings.HapticIntensity.OFF
    a.settings.interruptible = True
    a.settings.delay_start = 0
    a.settings.delay_end = 0
    a.settings.cycle = False
    a.settings.hold_repeats = False
    a.settings.repeat_rate = 1
    with self.assertRaisesRegex(ValueError, 'Value.*constraint.*bool'):
      a.settings.cycle = 42
    with self.assertRaisesRegex(ValueError, 'Value.*constraint.*[0-9]'):
      a.settings.repeat_rate = False

    d = scconfig.toVDF(a)
    self.assertEqual(d, {
      "bindings": {},
      "settings": {
        "interruptable": "1", # sic
        "haptic_intensity": "0",
        "toggle": "1", "delay_start": "0", "delay_end": "0",
        "cycle": "0", "hold_repeats": "0", "repeat_rate": "1" }})


class TestScconfigEncoding (unittest.TestCase):
  WRITE_FILES = False

  def hash_and_dump (self, configobj, cksum, f=None):
    kvs = scconfig.toVDF(configobj)
    fulldump_kvs = scvdf.dumps(kvs)
    #print(fulldump_kvs)
    fulldump_hashable = bytevector(fulldump_kvs)
    hasher = hashlib.new("md5")
    hasher.update(fulldump_hashable)
    if self.WRITE_FILES and f:
      do_close = False
      try:
        f.write
      except AttributeError as e:
        f = open(f, "wt")
        do_close = True
      f.write(fulldump_kvs)
      if do_close:
        f.close()
    self.assertEqual(hasher.hexdigest(), cksum)

  def test_dumping0 (self):
    self.buffer = True
    config = scconfig.ControllerConfig()

    mapping = config.add_mapping()
    mapping.version = '3'
    mapping.revision = '2'
    mapping.title = 'Defaults1'
    mapping.description = 'Evocation of built-in gamepad binds by corrupting save files.'
    mapping.creator = '76561198085425470'
    mapping.controller_type = 'controller_steamcontroller_gordon'
    mapping.timestamp = '-366082071'

    mapping.settings['left_trackpad_mode'] = 0
    mapping.settings['right_trackpad_mode'] = 0

    group0 = mapping.add_group(0, "four_buttons")
    inp = group0.add_input("button_a")
    activator = inp.add_activator("Full_Press")
    activator.add_binding("xinput_button A")
    inp = group0.add_input("button_b")
    activator = inp.add_activator("Full_Press")
    activator.add_binding("xinput_button B")
    inp = group0.add_input("button_x")
    activator = inp.add_activator("Full_Press")
    activator.add_binding("xinput_button X")
    inp = group0.add_input("button_y")
    activator = inp.add_activator("Full_Press")
    activator.add_binding("xinput_button Y")

    group1 = mapping.add_group(1, "dpad")
    inp = group1.add_input("dpad_north")
    activator = inp.add_activator("Full_Press")
    activator.add_binding('xinput_button dpad_up')
    inp = group1.add_input("dpad_south")
    activator = inp.add_activator("Full_Press")
    activator.add_binding('xinput_button dpad_down')
    inp = group1.add_input("dpad_east")
    activator = inp.add_activator("Full_Press")
    activator.add_binding('xinput_button dpad_right')
    inp = group1.add_input("dpad_west")
    activator = inp.add_activator("Full_Press")
    activator.add_binding('xinput_button dpad_left')
    group1.settings['deadzone'] = 5000

    group2 = mapping.add_group(2, "joystick_camera")
    inp = group2.add_input("click")
    activator = inp.add_activator("Full_Press")
    activator.add_binding("xinput_button JOYSTICK_RIGHT")
    activator.settings['haptic_intensity'] = 1

    group3 = mapping.add_group(3, "joystick_move")
    inp = group3.add_input("click")
    activator = inp.add_activator("Full_Press")
    activator.add_binding("xinput_button JOYSTICK_LEFT")
    activator.settings['haptic_intensity'] = 2

    group4 = mapping.add_group(4, "trigger")
    inp = group4.add_input("click")
    activator = inp.add_activator("Full_Press")
    activator.add_binding("xinput_button TRIGGER_LEFT")
    activator.settings['haptic_intensity'] = 2
    group4.settings['output_trigger'] = 1

    group5 = mapping.add_group(5, "trigger")
    inp = group5.add_input("click")
    activator = inp.add_activator("Full_Press")
    activator.add_binding("xinput_button TRIGGER_RIGHT")
    activator.settings['haptic_intensity'] = 2
    group5.settings['output_trigger'] = 2

    group6 = mapping.add_group(6, "switches")
    inp = group6.add_input('button_escape')
    activator = inp.add_activator("Full_Press")
    activator.add_binding("xinput_button start")
    inp = group6.add_input('button_menu')
    activator = inp.add_activator("Full_Press")
    activator.add_binding("xinput_button select")
    inp = group6.add_input('left_bumper')
    activator = inp.add_activator("Full_Press")
    activator.add_binding("xinput_button shoulder_left")
    inp = group6.add_input('right_bumper')
    activator = inp.add_activator("Full_Press")
    activator.add_binding("xinput_button shoulder_right")
    inp = group6.add_input('button_back_left')
    activator = inp.add_activator("Full_Press")
    activator.add_binding("xinput_button a")
    inp = group6.add_input('button_back_right')
    activator = inp.add_activator("Full_Press")
    activator.add_binding("xinput_button x")

    preset0 = mapping.add_preset(0, "Default")
    preset0.add_gsb(6, 'switch', True, False)
    preset0.add_gsb(0, 'button_diamond', True, False)
    preset0.add_gsb(1, 'left_trackpad', True, False)
    preset0.add_gsb(2, 'right_trackpad', True, False)
    preset0.add_gsb(3, 'joystick', True, False)
    preset0.add_gsb(4, 'left_trigger', True, False)
    preset0.add_gsb(5, 'right_trigger', True, False)

#    lop = config.encode_pair()
#    kv = config.encode_kv()
#
#    fulldump_pair = scvdf.dumps(lop)
#    fulldump_kv = scvdf.dumps(kv)
#    self.assertEqual(fulldump_pair, fulldump_kv)
#    fulldump = fulldump_kv.encode("utf-8")
#    #print(fulldump_kv)
#    hasher = hashlib.new("md5")
#    hasher.update(fulldump)
#    self.assertEqual(hasher.hexdigest(), "99d8c4ded89ec867519792db86d3bffc")
    self.hash_and_dump(config, "99d8c4ded89ec867519792db86d3bffc", "out1.txt")

  def test_loading0 (self):
    kv = scvdf.SCVDFDict()
    kv.update(PRESET_DEFAULTS1)
    config = scconfig.ControllerConfigFactory.make_from_dict(kv)

    self.hash_and_dump(config, "99d8c4ded89ec867519792db86d3bffc", "out2.txt")

  def test_loading1 (self):
    f = open("../examples/com³-wip3_0.vdf", "rt")
    pydict = scvdf.load(f, scvdf.SCVDFDict)
    f.close()
    config = scconfig.ControllerConfigFactory.make_from_dict(pydict)

    self.hash_and_dump(config, "01dc2f4e9b6c8f86e2d1678c2763540d", "out3.txt")

  def test_loading2 (self):
    f = open("../examples/led_sets1_0.vdf", "rt")
    pydict = scvdf.load(f, scvdf.SCVDFDict)
    f.close()
    config = scconfig.ControllerConfigFactory.make_from_dict(pydict)

    self.hash_and_dump(config, "1bd70090976c6d218cf6273ba3e26a12", "out4.txt")

  def test_loading3 (self):
    f = open("../examples/team fortress 2 defaults_0.vdf", "rt")
    pydict = scvdf.load(f, scvdf.SCVDFDict)
    f.close()
    config = scconfig.ControllerConfigFactory.make_from_dict(pydict)

    self.hash_and_dump(config, "a324245c4ef0629027646297cf4f93a7", "out5.txt")


if __name__ == "__main__":
  unittest.main()

