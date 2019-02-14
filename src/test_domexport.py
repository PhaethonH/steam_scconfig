#!/usr/bin/env python3
# vim: sw=2 ts=2 expandtab

import domexport, scconfig, scvdf
import unittest
import pprint
import yaml
from collections import OrderedDict


class TestDomExporter (unittest.TestCase):
  def test_export_frob (self):
    exporter = domexport.ScconfigExporter(None)
    d = {
      "toggle": True,
    }
    ss = scconfig.ActivatorFullPress.Settings()
    exporter.export_frob(d, ss)
#    expect = "Settings([('toggle', True)])"
    expect = "Settings(toggle=True)"
    self.assertEqual(repr(ss), expect)

    d = {
      "toggle": True,
      "interrupt": True,
      "repeat": 150,
    }
    ss = scconfig.ActivatorFullPress.Settings()
    exporter.export_frob(d, ss)
#    expect = "Settings([('toggle', True), ('interruptable', True), ('hold_repeats', True), ('repeat_rate', 150)])"
    expect = "Settings(hold_repeats=True, interruptable=True, repeat_rate=150, toggle=True)"
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

  d_pole1 = {
    "sym": "u",
    "synthesis": [
      d_synthesis1,
      ],
  }
  def test_export_pole (self):
    exporter = domexport.ScconfigExporter(None)
    d = self.d_pole1
    grpid = None
    grp = scconfig.GroupDpad(grpid)
    exporter.export_pole(d, grp)
    self.assertEqual(grp.MODE, 'dpad')
    self.assertEqual(len(grp.inputs), 1)
    self.assertEqual(len(grp.inputs['dpad_north'].activators), 1)
    self.assertEqual(len(grp.inputs['dpad_north'].activators[0].bindings), 2)

  d_cluster1 = {
    "sym": "DP",
    "style": "dpad",
    "pole": [
      d_pole1,
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
    grpstyle = d['style']
    grpid = 0
    grp = scconfig.GroupFactory.make(grpid, grpstyle)
    self.assertIsNot(grp, None)
    exporter.export_cluster(d, grp)
    self.assertEqual(grp.MODE, 'dpad')
    self.assertEqual(len(grp.inputs), 2)
    self.assertEqual(len(grp.inputs['dpad_north'].activators), 1)
    self.assertEqual(len(grp.inputs['dpad_north'].activators[0].bindings), 2)
    self.assertEqual(len(grp.inputs['dpad_south'].activators), 1)

  d_layer1 = {
    "name": "Default Layer",
    "cluster": [ d_cluster1 ],
  }
  d_layer2 = {
    "name": "Level2",
    "cluster": [
      { "sym": "BQ",
        "style": "four_buttons",
        "pole": [
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
    temp = exporter.normalize_layer(d, conmap, 0)
#    exporter.export_layer(d, conmap, 0)
    exporter.export_layer(temp, conmap, 0)
    self.assertEqual(len(conmap.actions), 1)

    d = self.d_layer2
#    exporter.export_layer(d, conmap, 1)
    temp = exporter.normalize_layer(d, conmap, 1)
    exporter.export_layer(temp, conmap, 1)
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
    exporter.export_action(d, conmap, phase=0)
    exporter.export_action(d, conmap, phase=1)
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
  d_config2 = {
    "title": "Sample config",
    "author": "(Anonymous)",
    "action": [
      d_action1,
      {
        "name": "Flight",
        "layer": [
          { "name": "Flight",
            "BQ.s": "(A)",
            },
          { "name": "MoreFlight",
            "BQ.s": "(DDN)",
            },
          ],
      }
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

    exporter = domexport.ScconfigExporter(None)
    d = self.d_config2
    conmap = scconfig.Mapping()
    cfg = exporter.export_conmap(d, conmap)
    s = scconfig.toVDF(cfg)
#    pprint.pprint(s)
    self.assertEqual(len(conmap.actions), 2)
    self.assertEqual(conmap.actions[0].title, "Default")
    self.assertEqual(conmap.actions[1].title, "Flight")
    self.assertEqual(len(s['actions']), 2)
#    print("keys {}".format(s['actions'].keys()))
    self.assertEqual(s['actions']["Default"]["title"], "Default")
    self.assertEqual(s['actions']["Preset_1000001"]["title"], "Flight")
#    pprint.pprint(s)

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
    "u": "(DUP)",
    "d": "(DDN)",
    "l": "(DLT)",
    "r": "(DRT)",
  }
  def test_shorthand_cluster (self):
    exporter = domexport.ScconfigExporter(None)
    d = self.s_cluster1
    grpid = 0
    grp = scconfig.GroupFactory.make(grpid, 'dpad')
    self.assertIsNot(grp, None)
    d2 = exporter.normalize_cluster(d)
    exporter.export_cluster(d2, grp)
    self.assertEqual(grp.mode, 'dpad')
    self.assertTrue(grp.inputs['dpad_north'])
    self.assertEqual(grp.inputs['dpad_north'].activators[0].signal, 'Full_Press')

    exporter = domexport.ScconfigExporter(None)
    d = self.s_cluster2
    grpid = 0
    grp = scconfig.GroupFactory.make(grpid, 'dpad')
    self.assertIsNot(grp, None)
    d2 = exporter.normalize_cluster(d)
#    pprint.pprint(d2)
    exporter.export_cluster(d2, grp)
    self.assertEqual(grp.mode, 'dpad')
    self.assertTrue(grp.inputs['dpad_north'])
    self.assertEqual(grp.inputs['dpad_north'].activators[0].signal, 'Full_Press')

  s_layer1 = {
    "name": "Layer1",
    "LJ.c": "[1]",
    "DP.u": "(DUP)",
    "DP.d": "(DDN)",
    "DP.l": "(DLT)",
    "DP.r": "(DRT)",
    "SW.LB": "(LB)",
    "BQ": {
      "s": "(A)",
      "w": "(X)",
    }
  }
  def test_shorthand_layer (self):
    exporter = domexport.ScconfigExporter(None)
    d = self.s_layer1
    conmap = scconfig.Mapping()
    temp = exporter.normalize_layer(d, conmap)
    exporter.export_layer(temp, conmap)
    self.assertEqual(len(conmap.presets[0].gsb), 4)
    self.assertTrue(conmap.presets[0].gsb['0'])
    self.assertTrue(conmap.presets[0].gsb['1'])
    self.assertTrue(conmap.presets[0].gsb['2'])
    b = [ (gsb.groupsrc == 'joystick') for gsb in conmap.presets[0].gsb.values() ]
    self.assertTrue(any([ (gsb.groupsrc == 'joystick') for gsb in conmap.presets[0].gsb.values() ]))
    self.assertTrue(any([ (gsb.groupsrc == 'dpad') for gsb in conmap.presets[0].gsb.values() ]))
    self.assertTrue(any([ (gsb.groupsrc == 'button_diamond') for gsb in conmap.presets[0].gsb.values() ]))

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
  d_shiftaction2 = {
    "name": "Default",
    "layer": [
      d_layer1,
      d_layer2,
      {
        "name": "Level3",
        "DP.u": "(A)",
        "INF": "<Left_Alt>",
      }
      ],
    "shiftmap": {
      "shifter": {
        "LB": "hold 1",
      },
      "overlay": {
        1: [ "Level2" ]
      },
      "hermit": {
        1: "-<Return>",
      },
    },
  }
  d_shifting2 = {
    "title": "Sample config",
    "author": "(Anonymous)",
    "action": [
      d_shiftaction2
    ],
  }
  def test_shiftmap (self):
    exporter = domexport.ScconfigExporter(None)
    d = self.d_shifting1
    conmap = scconfig.Mapping()
    exporter.export_conmap(d, conmap)
    s = scvdf.toDict(scconfig.toVDF(conmap))
#    pprint.pprint(s, width=180)

#    print('--2--')
    exporter = domexport.ScconfigExporter(None)
    d = self.d_shifting2
    conmap = scconfig.Mapping()
    exporter.export_conmap(d, conmap)
    s = scvdf.toDict(scconfig.toVDF(conmap))
    self.assertTrue(any([ 'always_on_action' in x['inputs'] for x in s['group'] ]))
#    pprint.pprint(s, width=180)


  def test_layerproxy (self):
    ll = domexport.LayerDict()
    self.assertEqual(ll, {"name":None, "cluster":[], "settings": None})
    cl1 = domexport.ClusterDict("DP", "dpad")
    ll.merge_cluster(cl1)
    self.assertEqual([dict(x) for x in ll.cluster], [{"sym": "DP", "style": "dpad", "modeshift": None, "pole": [], }] )

    ll = domexport.LayerDict()
    pp = domexport.PoleDict("u")
    cc = domexport.ClusterDict("DP", "dpad")
    cc.merge_pole(pp)
    ll.merge_cluster(cc)
    self.assertEqual(ll.cluster, [{"sym": "DP", "style": "dpad", "modeshift": None, "pole": [{"sym":"u", "synthesis":[]}], }] )

    ll = domexport.LayerDict()
    pp = domexport.PoleDict("u")
    ll.merge_cluster_pole("DP", "dpad", pp)
    self.assertEqual(ll.cluster, [{"sym": "DP", "style": "dpad", "modeshift": None, "pole": [{"sym":"u", "synthesis":[]}], }] )


  d_modeshifting1 = {
    'action': {
      'name': 'Default',
      'layer': [
        {
          'name': 'Default',
          'cluster': [
            {
              "sym": "BQ",
              "modeshift": None,
              "style": "four_buttons",
              "n": "<Y>",
              "w": "<X>",
              "e": "<B>",
              "s": "<A>",
            },
            {
              "sym": "BQ",
              "modeshift": "left_bumper",
              "style": "radial_menu",
              "01": "<1>",
              "02": "<2>",
              "03": "<3>",
              "04": "<4>",
              "05": "<5>",
              "06": "<6>",
              "07": "<7>",
              "08": "<8>",
            },
            ],
          },
        ],
      },
    }
  d_modeshifting2 = {
    'action': {
      'name': 'Default',
      'layer': [
        OrderedDict([
          ('name', "Default"),
          ('BQ', {
            "n": "<Y>",
            "w": "<X>",
            "e": "<B>",
            "s": "<A>",
          }),
          ("BQ&LB", {
            "01": "<1>",
            "02": "<2>",
            "03": "<3>",
            "04": "<4>",
            "05": "<5>",
            "06": "<6>",
            "07": "<7>",
            "08": "<8>",
          }),
        ]),
      ],
      },
    }
  d_modeshifting3 = {
    'action': {
      'name': 'Default',
      'layer': [
        OrderedDict([
          ('name', "Default"),
          ("BQ&LB", {
            "01": "<1>",
            "02": "<2>",
            "03": "<3>",
            "04": "<4>",
            "05": "<5>",
            "06": "<6>",
            "07": "<7>",
            "08": "<8>",
          }),
          ('BQ', {
            "n": "<Y>",
            "w": "<X>",
            "e": "<B>",
            "s": "<A>",
          }),
        ]),
      ],
      },
    }
  def test_modeshift (self):
    exporter = domexport.ScconfigExporter(None)
    d = self.d_modeshifting1
    conmap = scconfig.Mapping()
    exporter.export_conmap(d, conmap)
    z = scvdf.toDict(scconfig.toVDF(conmap))
    self.assertTrue(z['preset'])
    self.assertEqual(len(z['preset']['group_source_bindings']), 2)
    n_modeshifted = len([ x for x in z['preset']['group_source_bindings'].values() if "modeshift" in x ])
    self.assertEqual(n_modeshifted, 1)

    exporter = domexport.ScconfigExporter(None)
    d = self.d_modeshifting2
    conmap = scconfig.Mapping()
    exporter.export_conmap(d, conmap)
    z = scvdf.toDict(scconfig.toVDF(conmap))
#    print("z"); pprint.pprint(z, width=180)
    n_modeshifted = len([ x for x in z['preset']['group_source_bindings'].values() if "modeshift" in x ])
    self.assertEqual(n_modeshifted, 1)
    self.assertTrue(any([ x for x in z['group'] if 'mode_shift' in str(z['group'])]))
    found = []
    for grp in z['group']:
      inp = grp.get("inputs", None)
      if inp:
        lb = inp.get("left_bumper", None)
        if lb:
          acts = lb.get("activators", None)
          if acts:
            fp = acts.get("Full_Press", None)
            if fp:
              bb = fp.get("bindings", None)
              if bb:
                b = bb.get("binding", None)
                found.append(b)
    self.assertEqual(len(found), 1)
    parts = found[0].split()
    self.assertEqual(parts[1], "button_diamond")
    self.assertGreater(int(parts[2]), -1)

    exporter = domexport.ScconfigExporter(None)
    d = self.d_modeshifting3
    conmap = scconfig.Mapping()
    exporter.export_conmap(d, conmap)
    z = scvdf.toDict(scconfig.toVDF(conmap))
    n_modeshifted = len([ x for x in z['preset']['group_source_bindings'].values() if "modeshift" in x ])
    self.assertEqual(n_modeshifted, 1)
    self.assertTrue(any([ x for x in z['group'] if 'mode_shift' in str(z['group'])]))
    found = []
    for grp in z['group']:
      inp = grp.get("inputs", None)
      if inp:
        lb = inp.get("left_bumper", None)
        if lb:
          acts = lb.get("activators", None)
          if acts:
            fp = acts.get("Full_Press", None)
            if fp:
              bb = fp.get("bindings", None)
              if bb:
                b = bb.get("binding", None)
                found.append(b)
    self.assertEqual(len(found), 1)
    parts = found[0].split()
    self.assertEqual(parts[1], "button_diamond")
    self.assertGreater(int(parts[2]), -1)

  d_dotfrob1 = {
    'action': {
      'name': 'Default',
      'layer': [
        {
          'name': 'Default',
          'cluster': [
            {
              "sym": "BQ",
              "modeshift": None,
              "style": "dpad",
              "u": "<Y>",
              "d": "<X>",
              "l": "<B>",
              "r": "<A>",
              "settings": {
                "layout": 2,
                "analog_emulation_period": 50,
                "analog_emulation_duty_cycle_pct": 15,
              }
            },
            ],
          },
        ],
      },
    }
  d_dotfrob2 = {
    'action': {
      'name': 'Default',
      'layer': [
        {
          'name': 'Default',
          'cluster': [
            {
              "sym": "BQ",
              "modeshift": None,
              "style": "dpad",
              "u": "<Y>",
              "d": "<X>",
              "l": "<B>",
              "r": "<A>",
              ".layout": "analog",
              ".period": 50,
              ".duty": 15,
            },
            ],
          },
        ],
      },
    }

  d_dotsettings1 = {
    "layout": "analog",
    "period": 50,
    "duty": 25,
    "haptics": "off",
    }
  d_dotsettings3 = {
    "rect": "10x10+45+45",
    }
  d_dotsettings4 = {
    "rect": "16x4+22+30",
    }
  d_dotsettings5 = {
    "opacity": 33,
    "position": "30 25",
    "scale": 100,
    }
  d_dotsettings6 = {
    "position": [20,10],
    "opacity": .25,
    "scale": "0.75",
    }
  def test_dotfrob (self):
    exporter = domexport.ScconfigExporter(None)
    d = self.d_dotsettings1
    z = exporter.normalize_settings(d, scconfig.GroupDpad)
    self.assertEqual(z, { "layout": 2, "analog_emulation_period": 50, "analog_emulation_duty_cycle_pct": 25, "haptic_intensity_override": 0 })

    d = self.d_dotsettings3
    z = exporter.normalize_settings(d, scconfig.GroupMouseRegion)
    self.assertEqual(z, {
      "position_x": 50,
      "position_y": 50,
      "scale": 5,
      "sensitivity_horiz_scale": 100,
      "sensitivity_vert_scale": 100,
      })

    d = self.d_dotsettings4
    z = exporter.normalize_settings(d, scconfig.GroupMouseRegion)
    self.assertEqual(z, {
      "position_x": 30,
      "position_y": 32,
      "scale": 8,
      "sensitivity_horiz_scale": 100,
      "sensitivity_vert_scale": 25,
      })

    d = self.d_dotsettings5
    z = exporter.normalize_settings(d, scconfig.GroupRadialMenu)
    self.assertEqual(z, {
      "touch_menu_position_x": 30,
      "touch_menu_position_y": 25,
      "touch_menu_scale": 100,
      "touch_menu_opacity": 33,
      })

    d = self.d_dotsettings6
    z = exporter.normalize_settings(d, scconfig.GroupRadialMenu)
    self.assertEqual(z, {
      "touch_menu_position_x": 20,
      "touch_menu_position_y": 10,
      "touch_menu_scale": 75,
      "touch_menu_opacity": 25,
      })

    exporter = domexport.ScconfigExporter(None)
    d = self.d_dotfrob1
    conmap = scconfig.Mapping()
    exporter.export_conmap(d, conmap)
    z = scvdf.toDict(scconfig.toVDF(conmap))

    probe_ss = [ x[1] for x in z['group'].items() if x[0]=="settings" ]
    self.assertEqual(len(probe_ss), 1)
    ss = probe_ss[0]
    self.assertEqual(ss, {"layout": "2", "analog_emulation_period":"50", "analog_emulation_duty_cycle_pct":"15"})

    exporter = domexport.ScconfigExporter(None)
    d = self.d_dotfrob2
    conmap = scconfig.Mapping()
    exporter.export_conmap(d, conmap)
    z = scvdf.toDict(scconfig.toVDF(conmap))

    probe_ss = [ x[1] for x in z['group'].items() if x[0]=="settings" ]
    self.assertEqual(len(probe_ss), 1)
    ss = probe_ss[0]
    self.assertEqual(ss, {"layout": "2", "analog_emulation_period":"50", "analog_emulation_duty_cycle_pct":"15"})


  def test_sample1 (self):
    with open("../examples/x3tc_2.yaml") as f:
      d_yaml = yaml.load(f)
    exporter = domexport.ScconfigExporter(None)
    conmap = scconfig.ControllerConfig()
    exporter.export_config(d_yaml, conmap)
    vdf = scconfig.toVDF(conmap)
    s = scvdf.toDict(vdf)
#    pprint.pprint(s, width=180)
#    print(scvdf.dumps(vdf))




if __name__ == "__main__":
  unittest.main()

