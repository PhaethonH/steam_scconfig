#!/usr/bin/env python3

import unittest

import cfgmaker
from cfgmaker import Evspec, Srcspec, CfgMaker
from cfgmaker import CfgEvspec
import scconfig
import pprint


class TestEvspec (unittest.TestCase):

  def test_parse1 (self):
    res = Evspec._parse("(B)")
    self.assertEqual(res, (None, "(B)", None))
    res = Evspec._parse("+(B):1000~2%^@0,200/100")
    self.assertEqual(res, ("+", "(B)", ":1000~2%^@0,200/100"))
    res = Evspec._parse("+(B)s1000h2tcd0,200/100")
    self.assertEqual(res, ("+", "(B)", "s1000h2tcd0,200/100"))
    res = Evspec._parse("_(B)(A)s1000h2tcd0,200/100")
    self.assertEqual(res, ("_", "(B)(A)", "s1000h2tcd0,200/100"))

    obj = cfgmaker.Evfrob(toggle=True, interrupt=True, delay_start=0, delay_end=100, haptic=1, cycle=True, repeat=120)
    res = str(obj)
    self.assertEqual(res, "%^@0,100~1|/120")

    obj = cfgmaker.Evfrob.parse("@0,140%^/120|~1")
    res = str(obj)
    self.assertEqual(res, "%^@0,140~1|/120")

    obj = Evspec.parse("_(B)(A)s1000h2tcd0,200/100")
    res = repr(obj)
    self.assertEqual(res, "Evspec(actsig='_', evsyms='(B)(A)', evfrob=':1000%@0,200~2|/100')")


class TestSrcspec (unittest.TestCase):
  def test_parse1 (self):
    res = Srcspec._parse("BQ")
    self.assertEqual(res, (None, "BQ", None))
    res = Srcspec._parse("+BQ.d")
    self.assertEqual(res, ("+", "BQ", "d"))
    res = Srcspec._parse("+RR.d")
    self.assertEqual(res, None)


class TestCfgMaker (unittest.TestCase):
  def test_clusters1 (self):
    d = {
      "mode": "dpad",
      "u": [
        { "signal": "Start_Press",
          "bindings": [
            { "evtype": "keyboard", "evcode": "a" },
            { "evtype": "keyboard", "evcode": "b" },
            ],
          "settings": {
            "toggle": True,
            }
          } ],
      "d": None,
      "l": None,
      "r": None,
      }
#    res = cfgmaker.CfgClusterFactory.make_cluster(d)
#    print("res", res)
#    obj = res.export_group({})
#    print("obj = ")
#    pprint.pprint(obj)

  def test_cfgevspec (self):
    evspec = Evspec.parse("+(B)")
    cfg = CfgEvspec(evspec)
    obj = cfg.export_scconfig()
    d = scconfig.toVDF(obj)
    # singular entry for 'binding'.
    self.assertEqual(d, {'bindings': { "binding": "xinput_button B" } })

    evspec = Evspec.parse("+(B)~3@10,50")
    cfg = CfgEvspec(evspec)
    obj = cfg.export_scconfig()
    d = scconfig.toVDF(obj)
    self.assertEqual(d, { 'bindings':
      { 'binding': "xinput_button B" },
      'settings': {
        'haptic_intensity': '3',
        'delay_start': '10',
        'delay_end': '50',
        }
      })

    evspec = Evspec.parse("_<LeftControl><C>:180%^|~1@10,50/250")
    cfg = CfgEvspec(evspec)
    obj = cfg.export_scconfig()
    d = scconfig.toVDF(obj)
    self.assertEqual(d, { 'bindings':
      { 'binding': [ "key_press LeftControl", "key_press C" ] },
      'settings': {
        'toggle': '1',
        'interruptable': '1',   # sic
        'cycle': '1',
        'haptic_intensity': '1',
        'delay_start': '10',
        'delay_end': '50',
        'hold_repeats': '1',
        'repeat_rate': '250',
        }
      })

  def test_cfgcluster_dpad (self):
    d = {
      "mode": "dpad",
      "u": [
        CfgEvspec(Evspec.parse("+<a><b>%")),
        ],
      "d": None,
      "l": None,
      "r": None,
      }
    cfg = cfgmaker.CfgClusterDpad()
    cfg.load(d)
    obj = cfg.export_scconfig(None)
    d = scconfig.toVDF(obj)
    self.assertEqual(d, {
      "id": "0",
      "mode": "dpad",
      "inputs": {
        "dpad_north": {
          "activators": {  # One/first activator.
            "Start_Press": {
              "bindings": {
                "binding": [ "key_press a", "key_press b" ],
                },
              "settings": { "toggle": "1" },
              }
            }
          },
        "dpad_south": {},
        "dpad_west": {},
        "dpad_east": {},
        }
      })

    d = {
      "mode": "dpad",
      "u": [
        CfgEvspec(Evspec.parse("+<a><b>%")),
        CfgEvspec(Evspec.parse("_<2>%")),
        ],
      "d": None,
      "l": None,
      "r": None,
      }
    cfg = cfgmaker.CfgClusterDpad()
    cfg.load(d)
    obj = cfg.export_scconfig(None)
    d = scconfig.toVDF(obj)
    ref = {
      "id": "0",
      "mode": "dpad",
      "inputs": {
        "dpad_north": {
          "activators": {  # One/first activator.
            "Start_Press": {
              "bindings": {
                "binding": [ "key_press a", "key_press b" ],
                },
              "settings": { "toggle": "1" },
              },
            "Long_Press": {
              "bindings": {
                "binding": "key_press 2"
                },
              "settings": { "toggle": "1" },
              }
            },
          },
        "dpad_south": {},
        "dpad_west": {},
        "dpad_east": {},
        }
      }
    self.assertEqual(d, ref)

  def test_cfgcluster_face (self):
    # buttons
    d = {
      "mode": "face",
      "n": [
        CfgEvspec(Evspec.parse("+<a><b>%")),
        CfgEvspec(Evspec.parse("_<2>%")),
        ],
      "e": None,
      "w": None,
      "s": None,
      }
    cfg = cfgmaker.CfgClusterFace()
    cfg.load(d)
    obj = cfg.export_scconfig(None)
    d = scconfig.toVDF(obj)
    ref = {
      "id": "0",
      "mode": "four_buttons",
      "inputs": {
        "button_y": {
          "activators": {  # One/first activator.
            "Start_Press": {
              "bindings": {
                "binding": [ "key_press a", "key_press b" ],
                },
              "settings": { "toggle": "1" },
              },
            "Long_Press": {
              "bindings": {
                "binding": "key_press 2"
                },
              "settings": { "toggle": "1" },
              }
            },
          },
        "button_x": {},
        "button_b": {},
        "button_a": {},
        }
      }
    self.assertEqual(d, ref)

  def test_cfgcluster_pen (self):
    # pen (absolute_mouse)
    d = {
      "mode": "pen",
      "c": [ CfgEvspec(Evspec.parse("[1]")) ],
      }
    cfg = cfgmaker.CfgClusterPen()
    cfg.load(d)
    obj = cfg.export_scconfig(None)
    d = scconfig.toVDF(obj)
    ref = {
      "id": "0",
      "mode": "absolute_mouse",
      "inputs": {
        "click": {
          "activators": {  # One/first activator.
            "Full_Press": {
              "bindings": {
                "binding": "mouse_button LEFT",
                },
              },
            },
          },
        }
      }
    self.assertEqual(d, ref)

  def test_cfgcluster_jsmove (self):
    # jsmove (joystick_move)
    d = {
      "mode": "jsmove",
      "c": [ CfgEvspec(Evspec.parse("(LS)")) ],
      }
    cfg = cfgmaker.CfgClusterJoystickMove()
    cfg.load(d)
    obj = cfg.export_scconfig(None)
    d = scconfig.toVDF(obj)
    ref = {
      "id": "0",
      "mode": "joystick_move",
      "inputs": {
        "click": {
          "activators": {  # One/first activator.
            "Full_Press": {
              "bindings": {
                "binding": "xinput_button JOYSTICK_LEFT",
                },
              },
            },
          },
        }
      }
    self.assertEqual(d, ref)


  def test_cfglayer (self):
    d = {
      "name": "DefaultLayer",
      "BQ": {
        "mode": "face",
        "n": [ CfgEvspec(Evspec.parse("<n>")) ],
        },
      "SW": {
        "mode": "switches",
        "inputs": {
          "BK": {
            "activators": {
              "Full_Press": {
                "bindings": {
                  "binding": "xinput_button button_escape"
                  }
                }
              }
            },
          "ST": {
            "activators": {
              "Full_Press": {
                "bindings": {
                  "binding": "xinput_button button_menu"
                  }
                }
              }
            },
          }
        },
      "LP": { "mode": "dpad" },
      "RP": { "mode": "jscam" },
      "LJ": { "mode": "jsmove" },
      "LT": { "mode": "trigger" },
      "RT": { "mode": "trigger" },
      }
    cfg = cfgmaker.CfgLayer()
    cfg.load(d)
    sccfg = scconfig.Mapping()
    obj = cfg.export_scconfig(sccfg)
    d = scconfig.toVDF(sccfg)
    res = {
      'version': '3',
      'title': 'Unnamed',
      'revision': '1',
			'creator': '(Auto-Generator)',
			'description': 'Unnamed configuration',
			'controller_type': 'controller_steamcontroller_gordon',
      'Timestamp': '-1',
      'settings': {},
      'action_layers': {
        'UnnamedLayer': {
          'legacy_set': '1',
					'set_layer': '1',
					'title': 'DefaultLayer',
          }},
      'group': [
				{'id': '0', 'mode': 'switches', 'inputs': {}},
				{'id': '1', 'mode': 'four_buttons', 'inputs': {'button_y': {'activators': {'Full_Press': {'bindings': {'binding': 'key_press n'}}}}}},
				{'id': '2', 'mode': 'dpad', 'inputs': {}},
				{'id': '3', 'mode': 'joystick_camera', 'inputs': {}},
				{'id': '4', 'mode': 'joystick_move', 'inputs': {}},
				{'id': '5', 'mode': 'trigger', 'inputs': {}},
				{'id': '6', 'mode': 'trigger', 'inputs': {}},
        ],
			'preset': {
				'id': '0',
				'name': 'DefaultLayer',
        'group_source_bindings': {'0': 'switch active',
                                  '1': 'button_diamond active',
                                  '2': 'left_trackpad active',
                                  '3': 'right_trackpad active',
                                  '4': 'joystick active',
                                  '5': 'left_trigger active',
                                  '6': 'right_trigger active'},
			  },
      }
    self.assertEqual(d, res)



if __name__ == "__main__":
  unittest.main()
