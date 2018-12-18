#!/usr/bin/env python3
# coding=utf-8

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


class TestScconfigEncoding (unittest.TestCase):
  def hash_and_dump (self, configobj, cksum, f=None):
    kvs = configobj.encode_kv()
    fulldump_kvs = scvdf.dumps(kvs)
    #print(fulldump_kvs)
    fulldump_hashable = fulldump_kvs.encode("utf-8")
    hasher = hashlib.new("md5")
    hasher.update(fulldump_hashable)
    if f:
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

    mapping = config.make_mapping()
    mapping.version = '3'
    mapping.revision = '2'
    mapping.title = 'Defaults1'
    mapping.description = 'Evocation of built-in gamepad binds by corrupting save files.'
    mapping.creator = '76561198085425470'
    mapping.controller_type = 'controller_steamcontroller_gordon'
    mapping.timestamp = '-366082071'

    mapping.settings['left_trackpad_mode'] = 0
    mapping.settings['right_trackpad_mode'] = 0

    group0 = mapping.make_group("four_buttons", 0)
    inp = group0.make_input("button_a")
    activator = inp.make_activator("Full_Press")
    activator.add_binding_str("xinput_button A")
    inp = group0.make_input("button_b")
    activator = inp.make_activator("Full_Press")
    activator.add_binding_str("xinput_button B")
    inp = group0.make_input("button_x")
    activator = inp.make_activator("Full_Press")
    activator.add_binding_str("xinput_button X")
    inp = group0.make_input("button_y")
    activator = inp.make_activator("Full_Press")
    activator.add_binding_str("xinput_button Y")

    group1 = mapping.make_group("dpad", 1)
    inp = group1.make_input("dpad_north")
    activator = inp.make_activator("Full_Press")
    activator.add_binding_str('xinput_button dpad_up')
    inp = group1.make_input("dpad_south")
    activator = inp.make_activator("Full_Press")
    activator.add_binding_str('xinput_button dpad_down')
    inp = group1.make_input("dpad_east")
    activator = inp.make_activator("Full_Press")
    activator.add_binding_str('xinput_button dpad_right')
    inp = group1.make_input("dpad_west")
    activator = inp.make_activator("Full_Press")
    activator.add_binding_str('xinput_button dpad_left')
    group1.settings['deadzone'] = 5000

    group2 = mapping.make_group("joystick_camera", 2)
    inp = group2.make_input("click")
    activator = inp.make_activator("Full_Press")
    activator.add_binding_str("xinput_button JOYSTICK_RIGHT")
    activator.settings['haptic_intensity'] = 1

    group3 = mapping.make_group("joystick_move", 3)
    inp = group3.make_input("click")
    activator = inp.make_activator("Full_Press")
    activator.add_binding_str("xinput_button JOYSTICK_LEFT")
    activator.settings['haptic_intensity'] = 2

    group4 = mapping.make_group("trigger", 4)
    inp = group4.make_input("click")
    activator = inp.make_activator("Full_Press")
    activator.add_binding_str("xinput_button TRIGGER_LEFT")
    activator.settings['haptic_intensity'] = 2
    group4.settings['output_trigger'] = 1

    group5 = mapping.make_group("trigger", 5)
    inp = group5.make_input("click")
    activator = inp.make_activator("Full_Press")
    activator.add_binding_str("xinput_button TRIGGER_RIGHT")
    activator.settings['haptic_intensity'] = 2
    group5.settings['output_trigger'] = 2

    group6 = mapping.make_group("switches", 6)
    inp = group6.make_input('button_escape')
    activator = inp.make_activator("Full_Press")
    activator.add_binding_str("xinput_button start")
    inp = group6.make_input('button_menu')
    activator = inp.make_activator("Full_Press")
    activator.add_binding_str("xinput_button select")
    inp = group6.make_input('left_bumper')
    activator = inp.make_activator("Full_Press")
    activator.add_binding_str("xinput_button shoulder_left")
    inp = group6.make_input('right_bumper')
    activator = inp.make_activator("Full_Press")
    activator.add_binding_str("xinput_button shoulder_right")
    inp = group6.make_input('button_back_left')
    activator = inp.make_activator("Full_Press")
    activator.add_binding_str("xinput_button a")
    inp = group6.make_input('button_back_right')
    activator = inp.make_activator("Full_Press")
    activator.add_binding_str("xinput_button x")

    preset0 = mapping.make_preset("Default", 0)
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
    self.hash_and_dump(config, "99d8c4ded89ec867519792db86d3bffc", None)

  def test_loading0 (self):
    kv = scvdf.DictMultivalue()
    kv.update_pairs(PRESET_DEFAULTS1)
    config = scconfig.ControllerConfig.restore(kv)

    self.hash_and_dump(config, "99d8c4ded89ec867519792db86d3bffc")

  def test_loading1 (self):
    f = open("../examples/com³-wip3_0.vdf", "rt")
    pydict = scvdf.load(f, scvdf.DictMultivalue)
    f.close()
    config = scconfig.ControllerConfig.restore(pydict)

    self.hash_and_dump(config, "01dc2f4e9b6c8f86e2d1678c2763540d")


if __name__ == "__main__":
  #unittest.main(defaultTest=['TestScconfigEncoding.test_dumping0'])
  unittest.main()

