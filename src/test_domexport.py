#!/usr/bin/env python3

import domexport, scconfig, scvdf
import unittest
import pprint


class TestDomExporter (unittest.TestCase):
  def test_export_frob (self):
    exporter = domexport.ScconfigExporter(None)
    d = {
      "toggle": True,
    }
    ss = scconfig.ActivatorFullPress.Settings()
    exporter.export_frob(d, ss)
    expect = "Settings([('toggle', True)])"
    self.assertEqual(repr(ss), expect)

    d = {
      "toggle": True,
      "interrupt": True,
      "repeat": 150,
    }
    ss = scconfig.ActivatorFullPress.Settings()
    exporter.export_frob(d, ss)
    expect = "Settings([('toggle', True), ('interruptable', True), ('hold_repeats', True), ('repeat_rate', 150)])"
    self.assertEqual(repr(ss), expect)

  def test_gen_ev (self):
    exporter = domexport.ScconfigExporter(None)
    d = {
      "evtype": "keyboard",
      "evcode": "Return",
    }
    ev = exporter.translate_event(d)
    self.assertEqual(repr(ev), "Evgen_Keystroke('Return')")

  d_synthesis1 = {
    "actsig": "full",
    "event": [
      { "evtype": "keyboard", "evcode": "3" },
      { "evtype": "keyboard", "evcode": "Left_Shift" },
    ],
  }
  def test_export_synthesis (self):
    exporter = domexport.ScconfigExporter(None)
    d = self.d_synthesis1
    inode = scconfig.ControllerInput('dpad')
    exporter.export_synthesis(d, inode)
    self.assertEqual(len(inode.activators), 1)
    self.assertEqual(inode.activators[0].bindings[0].geninfo._evtype, "key_press")
    self.assertEqual(inode.activators[0].bindings[1].geninfo._evtype, "key_press")

  d_component1 = {
    "sym": "u",
    "synthesis": [
      d_synthesis1,
      ],
  }
  def test_export_component (self):
    exporter = domexport.ScconfigExporter(None)
    d = self.d_component1
    grpid = None
    grp = scconfig.GroupDpad(grpid)
    exporter.export_component(d, grp)
    self.assertEqual(grp.MODE, 'dpad')
    self.assertEqual(len(grp.inputs), 1)
    self.assertEqual(len(grp.inputs['dpad_north'].activators), 1)
    self.assertEqual(len(grp.inputs['dpad_north'].activators[0].bindings), 2)

  d_cluster1 = {
    "sym": "DP",
    "mode": "dpad",
    "component": [
      d_component1,
      {
        "sym": "d",
        "synthesis": [
          {
            "actsig": "full",
            "event": [
              { "evtype": "keyboard", "evcode": "4" },
            ],
          },
        ],
      }
      ],
  }
  def test_export_cluster (self):
    exporter = domexport.ScconfigExporter(None)
    d = self.d_cluster1
    grpmode = d['mode']
    grpid = 0
    grp = scconfig.GroupFactory.make(grpid, grpmode)
    self.assertIsNot(grp, None)
    exporter.export_cluster(d, grp)
    self.assertEqual(grp.MODE, 'dpad')
    self.assertEqual(len(grp.inputs), 2)
    self.assertEqual(len(grp.inputs['dpad_north'].activators), 1)
    self.assertEqual(len(grp.inputs['dpad_north'].activators[0].bindings), 2)
    self.assertEqual(len(grp.inputs['dpad_south'].activators), 1)

  d_layer1 = {
    "name": "Default Layer",
    "cluster": d_cluster1,
  }
  d_layer2 = {
    "name": "Level2",
    "cluster": [
      { "sym": "BQ",
        "mode": "four_buttons",
        "component": [
          { "sym": "a",
            "synthesis": [
              { "actsig": 'full',
                "event": [
                { "evtype": "keyboard", "evcode": "a" },
                ],
              },
              ],
          },
          ],
      },
      ],
  }
  def test_export_layer (self):
    exporter = domexport.ScconfigExporter(None)
    d = self.d_layer1
    conmap = scconfig.Mapping()
    exporter.export_layer(d, conmap, 0)
    self.assertEqual(len(conmap.actions), 1)

    d = self.d_layer2
    exporter.export_layer(d, conmap, 1)
    self.assertEqual(len(conmap.actions), 1)
    self.assertEqual(len(conmap.layers), 1)

  d_action1 = {
    "name": "Default",
    "layer": [
      d_layer1,
      d_layer2
      ],
  }
  def test_export_action (self):
    exporter = domexport.ScconfigExporter(None)
    d = self.d_action1
    conmap = scconfig.Mapping()
    exporter.export_action(d, conmap)
    self.assertEqual(len(conmap.actions), 1)
    self.assertEqual(len(conmap.layers), 1)
    self.assertEqual(conmap.actions[0].title, "Default")
    self.assertEqual(conmap.layers[0].title, "Level2")

  d_config1 = {
    "title": "Sample config",
    "author": "(Anonymous)",
    "action": [
      d_action1
    ],
  }
  def test_export_conmap (self):
    exporter = domexport.ScconfigExporter(None)
    d = self.d_config1
    conmap = scconfig.Mapping()
    exporter.export_conmap(d, conmap)
    self.assertEqual(len(conmap.actions), 1)
    self.assertEqual(len(conmap.layers), 1)
    self.assertEqual(conmap.actions[0].title, "Default")
    self.assertEqual(conmap.layers[0].title, "Level2")
    self.assertNotEqual(conmap.creator, '')

  def test_export_config (self):
    exporter = domexport.ScconfigExporter(None)
    d = self.d_config1
    cfg = exporter.export_config(d)
    conmap = cfg.mappings[0]
    self.assertEqual(len(conmap.actions), 1)
    self.assertEqual(len(conmap.layers), 1)
    self.assertEqual(conmap.actions[0].title, "Default")
    self.assertEqual(conmap.layers[0].title, "Level2")
    self.assertNotEqual(conmap.creator, '')


  s_synth1 = "+<4>(ST)%^/100#s_synth1#example"
  def test_shorthand_synthesis (self):
    exporter = domexport.ScconfigExporter(None)
    d = self.s_synth1
    evlist = exporter.expand_shorthand_syntheses(d)
#    print("evlist", evlist)
    self.assertEqual(len(evlist), 1)
    self.assertEqual(evlist[0]['actsig'], "start")
    self.assertEqual(evlist[0]['settings']['repeat'], 100)

  s_cluster1 = {
    "u": [
      {
        "actsig": "full",
        "event": [
          { "evtype": "keyboard", "evcode": "4" },
        ],
      },
    ],
  }
  s_cluster2 = {
    "u": "(BK)"
  }
  def test_shorthand_cluster (self):
    exporter = domexport.ScconfigExporter(None)
    d = self.s_cluster1
    grpid = 0
    grp = scconfig.GroupFactory.make(grpid, 'dpad')
    self.assertIsNot(grp, None)
    exporter.export_cluster(d, grp)
    self.assertEqual(grp.mode, 'dpad')
    self.assertTrue(grp.inputs['dpad_north'])
    self.assertEqual(grp.inputs['dpad_north'].activators[0].signal, 'Full_Press')

    exporter = domexport.ScconfigExporter(None)
    d = self.s_cluster2
    grpid = 0
    grp = scconfig.GroupFactory.make(grpid, 'dpad')
    self.assertIsNot(grp, None)
    exporter.export_cluster(d, grp)
    self.assertEqual(grp.mode, 'dpad')
    self.assertTrue(grp.inputs['dpad_north'])
    self.assertEqual(grp.inputs['dpad_north'].activators[0].signal, 'Full_Press')

  s_layer1 = {
    "name": "Layer1",
    "LJ.c": "[1]",
    "DP.u": "(DUP)",
    "DP.d": "(DDN)",
    "BQ.s": "(A)",
  }
  def test_shorthand_layer (self):
    exporter = domexport.ScconfigExporter(None)
    d = self.s_layer1
    conmap = scconfig.Mapping()
    exporter.export_layer(d, conmap)
#    print(conmap.presets)
    self.assertEqual(len(conmap.presets[0].gsb), 3)
    self.assertTrue(conmap.presets[0].gsb['0'])
    self.assertTrue(conmap.presets[0].gsb['1'])
    self.assertTrue(conmap.presets[0].gsb['2'])
#    self.assertEqual(conmap.presets[0].gsb['0'].groupsrc, 'joystick')
#    self.assertEqual(conmap.presets[0].gsb['1'].groupsrc, 'dpad')
#    self.assertEqual(conmap.presets[0].gsb['2'].groupsrc, 'button_diamond')

  s_aliasing1 = {
      'Up': '<Up>',
      'Down': '<Down>',
      'Left': '<Left>',
      'Right': '<Right>',
      'Jump': '(B)',
      'Run': '(A)',
    }
  def test_aliases (self):
    exporter = domexport.ScconfigExporter(None)
    d = self.s_aliasing1
    conmap = scconfig.Mapping()
    exporter.load_aliases(d)
    sh = exporter.expand_shorthand_syntheses("$Jump")
    self.assertEqual(sh[0]['actsig'], 'full')
    self.assertEqual(sh[0]['event'][0]['evtype'], 'gamepad')
    self.assertEqual(sh[0]['event'][0]['evcode'], 'B')

  d_shiftaction1 = {
    "name": "Default",
    "layer": [
      d_layer1,
      d_layer2
      ],
    "shiftmap": {
      "shifter": [
        { "srcsym": "SW.LB",
          "bitmask": 1,
          },
        ],
      "overlay": [
        { "level": 1,
          "layer": [ "Level2"],
          },
        ],
      },
  }
  d_shifting1 = {
    "title": "Sample config",
    "author": "(Anonymous)",
    "action": [
      d_shiftaction1
    ],
  }
  def test_shiftmap (self):
    exporter = domexport.ScconfigExporter(None)
    d = self.d_shifting1
    conmap = scconfig.Mapping()
    exporter.export_conmap(d, conmap)
    s = scconfig.toVDF(conmap)
    pprint.pprint(s, width=180)


if __name__ == "__main__":
  unittest.main()

