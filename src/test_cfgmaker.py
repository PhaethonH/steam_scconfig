#!/usr/bin/env python3

import unittest

import cfgmaker
from cfgmaker import Evspec, Srcspec, CfgMaker
from cfgmaker import CfgEvspec
import scconfig, scvdf
import yaml
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

    obj = Evspec.parse("{foobar bletch}")
    res = repr(obj)
    self.assertEqual(res, "Evspec(actsig=None, evsyms='{foobar bletch}', evfrob=None)")

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

    d = {
      "mode": "dpad",
      "u": "+<a><b>% _<2>%",
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
    obj = cfg.export_scconfig(sccfg, 'Default', index=None)
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
        'Default': {
          'legacy_set': '1',
					'set_layer': '1',
					'title': 'DefaultLayer',
          'parent_set_name': 'Default',
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
				'name': 'Default',
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

  def test_cfgaction (self):
    d = {
      "name": "DefaultSet",
      "layers": [ {
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
        }]}
    cfg = cfgmaker.CfgAction()
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
      'actions': {
        'Default': {
          'legacy_set': '1',
          'title': 'DefaultSet',
          },
        },
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
				'name': 'Default',
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

  def test_cfgmaker (self):
    d = {
      "name": "Sample Config",
      "revision": 7,
      "creator": "unittest",
      "desc": "Sample Configuration Dump",
      "devtype": "controller_ps3",
      "timestamp": 12345,
      "actions": [ {
        "name": "DefaultSet",
        "layers": [ {
          "name": "DefaultLayer",
          "BQ": {
            "mode": "face",
            "n": "<LeftShift><n> -<m>",
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
          }]}]}
    cfg = cfgmaker.CfgMaker()
    cfg.load(d)
    sccfg = scconfig.Mapping()
    obj = cfg.export_scconfig(sccfg)
    d = scconfig.toVDF(sccfg)
    res = {
      'version': '3',
      'title': 'Sample Config',
      'revision': '7',
			'creator': 'unittest', 'description': 'Sample Configuration Dump',
			'controller_type': 'controller_ps3',
      'Timestamp': '12345',
      'settings': {},
      'actions': {
        'Default': {
          'legacy_set': '1',
          'title': 'DefaultSet',
          },
        },
      'group': [
				{'id': '0', 'mode': 'switches', 'inputs': {}},
				{'id': '1', 'mode': 'four_buttons', 'inputs': {
            'button_y': {
              'activators': {
                'Full_Press': {
                  'bindings': {
                    'binding': [ 'key_press LeftShift',  'key_press n' ]
                    }
                  },
                'release': {
                  'bindings': {
                    'binding': 'key_press m'
                  },
                }
              }
            }
          }
        },
				{'id': '2', 'mode': 'dpad', 'inputs': {}},
				{'id': '3', 'mode': 'joystick_camera', 'inputs': {}},
				{'id': '4', 'mode': 'joystick_move', 'inputs': {}},
				{'id': '5', 'mode': 'trigger', 'inputs': {}},
				{'id': '6', 'mode': 'trigger', 'inputs': {}},
        ],
			'preset': {
				'id': '0',
				'name': 'Default',
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

  def test_inline_subparts (self):
    d = {
      'name': 'inline subparts',
      'BQ.s': '(A)',
      'BQ.e': '(B)',
      'BQ.w': '(X)',
      'BQ.n': '+(Y)',
      }
    cfg = cfgmaker.CfgLayer()
    cfg.load(d)
    sccfg = scconfig.Mapping()
    obj = cfg.export_scconfig(sccfg)
    vdf = scconfig.toVDF(obj)
    d = vdf['group',0]
    res = {
      'id': '0',
			'mode': 'four_buttons',
      'inputs': {
        'button_a': {
          'activators': {
 						'Full_Press': {
							'bindings': {
								'binding': 'xinput_button A'
								}
							}
						}
					},
        'button_b': {
          'activators': {
 						'Full_Press': {
							'bindings': {
								'binding': 'xinput_button B'
								}
							}
						}
					},
        'button_x': {
          'activators': {
 						'Full_Press': {
							'bindings': {
								'binding': 'xinput_button X'
								}
							}
						}
					},
        'button_y': {
          'activators': {
 						'Start_Press': {
							'bindings': {
								'binding': 'xinput_button Y'
								}
							}
						}
					},
				}
			}
    self.assertEqual(d, res)

  def test_inline_switches (self):
    d = {
      'name': 'inline switches',
      'BK': '(BK)',
      'ST': '(ST)',
      'LB': '(LB)',
      'RB': '(RB)',
      'LG': '(A)',
      'RG': '(X)',
      }
    cfg = cfgmaker.CfgLayer()
    cfg.load(d)
    sccfg = scconfig.Mapping()
    obj = cfg.export_scconfig(sccfg)
    vdf = scconfig.toVDF(obj)
    d = vdf['group',0]
    res = {
      'id': '0',
			'mode': 'switches',
      'inputs': {
        'button_escape': {
          'activators': {
 						'Full_Press': {
							'bindings': {
								'binding': 'xinput_button SELECT'
								}
							}
						}
					},
        'button_menu': {
          'activators': {
 						'Full_Press': {
							'bindings': {
								'binding': 'xinput_button START'
								}
							}
						}
					},
        'left_bumper': {
          'activators': {
 						'Full_Press': {
							'bindings': {
								'binding': 'xinput_button SHOULDER_LEFT'
								}
							}
						}
					},
        'right_bumper': {
          'activators': {
 						'Full_Press': {
							'bindings': {
								'binding': 'xinput_button SHOULDER_RIGHT'
								}
							}
						}
					},
        'button_back_left': {
          'activators': {
 						'Full_Press': {
							'bindings': {
								'binding': 'xinput_button A'
								}
							}
						}
					},
        'button_back_right': {
          'activators': {
 						'Full_Press': {
							'bindings': {
								'binding': 'xinput_button X'
								}
							}
						}
					},
				}
			}
    self.assertEqual(d, res)

  def test_inline_trigger (self):
    d = {
      'name': 'inline trigger',
      'LT.c': '[2]',
      'RT.c': '[1]',
      'LT.o': '<LeftControl>',
      'RT.o': '<LeftShift>',
      'LT': "LT",
      'RT': "RT",
      }
    cfg = cfgmaker.CfgLayer()
    cfg.load(d)
    sccfg = scconfig.Mapping()
    obj = cfg.export_scconfig(sccfg)
    vdf = scconfig.toVDF(obj)
    d = vdf['group',0]
#    pprint.pprint(d)
    res = {
      'id': '0',
      'mode': 'trigger',
      'inputs': {
        'click': {
          'activators': {
            'Full_Press': {
              'bindings': {
                'binding': 'mouse_button MIDDLE'
                }
              }
            }
          },
        'edge': {
          'activators': {
            'Full_Press': {
              'bindings': {
                'binding': 'key_press LeftControl'
                }
              }
            }
          }
        },
      'settings': {'output_trigger': '1'}}
    self.assertEqual(d, res)

    d = {
      'name': 'inline trigger',
      'LT': "<1>",
      'RT': "<q>",
      }
    cfg = cfgmaker.CfgLayer()
    cfg.load(d)
    sccfg = scconfig.Mapping()
    obj = cfg.export_scconfig(sccfg)
    vdf = scconfig.toVDF(obj)
    d = vdf['group',]
    res =  [
      {
        'id': '0',
        'mode': 'trigger',
        'inputs': {
          'click': {
            'activators': {
              'Full_Press': {
                'bindings': {
                  'binding': 'key_press 1'
                  }
                }
              }
            }
          },
        },
      {
        'id': '1',
        'mode': 'trigger',
        'inputs': {
          'click': {
            'activators': {
              'Full_Press': {
                'bindings': {
                  'binding': 'key_press q'
                  }
                }
              }
            }
          },
        }
      ]
    self.assertEqual(d, res)

  def test_inline_joystick (self):
    d = {
      'name': 'inline joystick',
      'LJ': 'LJ',
      'RJ': 'RJ',
      }
    cfg = cfgmaker.CfgLayer()
    cfg.load(d)
    sccfg = scconfig.Mapping()
    obj = cfg.export_scconfig(sccfg)
    vdf = scconfig.toVDF(obj)
    d = vdf['group',]
#    pprint.pprint(d)
    res = [
      { 'id': '0',
        'inputs': {},
        'mode': 'joystick_move',
        'settings': {'output_joystick': '0'}
        },
      { 'id': '1',
        'inputs': {},
        'mode': 'joystick_camera',
        'settings': {'output_joystick': '0'}
        }
      ]
    self.assertEqual(d, res)


  def test_load1 (self):
    with open("../examples/sample1.yaml") as f:
      d = yaml.load(f)
    cfg = cfgmaker.CfgMaker()
    cfg.load(d)
    sccfg = scconfig.Mapping()
    obj = cfg.export_scconfig(sccfg)
    d = scconfig.toVDF(sccfg)
    res = {
      'version': '3',
      'revision': '1',
      'title': 'Sample XB360 mimick',
      'description': 'Unnamed configuration',
      'creator': '(Auto-Generator)',
      'controller_type': 'controller_steamcontroller_gordon',
      'Timestamp': '-1',
      'actions': {
        'Default': {
          'legacy_set': '1', 'title': 'Default',
          }
        },
      'group': [
        {
          'id': '0',
          'mode': 'switches',
          'inputs': {
            'button_escape': {
              'activators': {
                'Full_Press': {
                  'bindings': {
                    'binding': 'xinput_button SELECT',
                    }
                  }
                }
              },
            'button_menu': {
              'activators': {
                'Full_Press': {
                  'bindings': {
                    'binding': 'xinput_button START',
                    },
                  }
                }
              },
            'left_bumper': {
              'activators': {
                'Full_Press': {
                  'bindings': {
                    'binding': 'xinput_button SHOULDER_LEFT',
                    }
                  }
                }
              },
            'right_bumper': {
              'activators': {
                'Full_Press': {
                  'bindings': {
                    'binding': 'xinput_button SHOULDER_RIGHT',
                    }
                  }
                }
              }
            },
          },

         {
          'id': '1',
           'mode': 'four_buttons',
           'inputs': {
             'button_a': {
               'activators': {
                 'Full_Press': {
                   'bindings': {
                     'binding': 'xinput_button A',
                     }
                   }
                 }
               },
             'button_b': {
               'activators': {
                 'Full_Press': {
                   'bindings': {
                     'binding': 'xinput_button B',
                     }
                   }
                 }
               },
             'button_x': {
               'activators': {
                 'Full_Press': {
                   'bindings': {
                     'binding': 'xinput_button X',
                     }
                   }
                 }
               },
             'button_y': {
               'activators': {
                 'Full_Press': {
                   'bindings': {
                     'binding': 'xinput_button Y',
                     }
                   }
                 }
               }
             },
           },

        {
          'id': '2',
          'mode': 'dpad',
          'inputs': {
            'dpad_east': {
              'activators': {
                'Full_Press': {
                  'bindings': {
                    'binding': 'xinput_button DPAD_RIGHT',
                    }
                  }
                }
              },
            'dpad_north': {
              'activators': {
                'Full_Press': {
                  'bindings': {
                    'binding': 'xinput_button DPAD_UP',
                    }
                  }
                }
              },
            'dpad_south': {
              'activators': {
                'Full_Press': {
                  'bindings': {
                    'binding': 'xinput_button DPAD_DOWN',
                    }
                  }
                }
              },
            'dpad_west': {
              'activators': {
                'Full_Press': {
                  'bindings': {
                    'binding': 'xinput_button DPAD_LEFT',
                    }
                  }
                }
              }
            },
          },
        {
          'id': '3',
          'inputs': {},
          'mode': 'joystick_camera',
          'settings': {'output_joystick': '0'}
          },
        {
          'id': '4',
          'mode': 'trigger',
          'inputs': {
            'click': {
              'activators': {
                'Full_Press': {
                  'bindings': {
                    'binding': 'xinput_button TRIGGER_LEFT',
                    }
                  }
                }
              }
            },
          'settings': {'output_trigger': '1'}
          },
        {
          'id': '5',
          'mode': 'trigger',
          'inputs': {
            'click': {
              'activators': {
                'Full_Press': {
                  'bindings': {
                    'binding': 'xinput_button TRIGGER_RIGHT',
                    }
                  }
                }
              }
            },
          'settings': {'output_trigger': '1'}
          },
        ],
      'preset': {
        'id': '0',
        'name': 'Default',
        'group_source_bindings': {
          '0': 'switch active',
          '1': 'button_diamond active',
          '2': 'left_trackpad active',
          '3': 'right_trackpad active',
          '4': 'left_trigger active',
          '5': 'right_trigger active',
          },
        },
      'settings': {},
      }
    self.assertEqual(d, res)

  def test_inline_touchpad (self):
    d = {
      'name': 'inline joystick',
      'LP': '<1>',
      'RP': '(RJ)',
      }
    cfg = cfgmaker.CfgLayer()
    cfg.load(d)
    sccfg = scconfig.Mapping()
    obj = cfg.export_scconfig(sccfg)
    vdf = scconfig.toVDF(obj)
    d = vdf['group',]
    res = [
      {
        'id': '0',
        'mode': 'single_button',
        'inputs': {
          'click': {
            'activators': {
              'Full_Press': {
                'bindings': {
                  'binding': 'key_press '
                    '1'
                  }
                }
              }
            }
          },
        },
      {
        'id': '1',
        'inputs': {},
        'mode': 'joystick_camera',
        'settings': {'output_joystick': '0'},
        },
      ]
    self.assertEqual(d, res)

  def test_cfgshifting (self):
    d = {
      "0": {
        "+LB": "1",
        "+RB": "4",
        },
      "1": {
        "-LB": "0",
        "+RB": "5",
        },
      "4": {
        "+LB": "5",
        "-RB": "0",
        },
      "5": {
        "-LB": "4",
        "-RB": "1",
        },
    }
    cfg = cfgmaker.CfgShifting()
    cfg.load(d)

  def test_cfgshifters (self):
    d = {
      "actions": [
        {
          "name": "Default",
          "layers": [
            {
              "ST": "<escape>",
              },
            ],
        },
        {
          "name": "TestShifts",
          "layers": [
            { "name": "Default",
              "BQ.s": "(A)",
              },
            { "name": "LeftHanded",
              "DP.u": "(DUP)",
              "LT.c": "(LT)",
              },
            { "name": "RightHanded",
              "BQ.n": "(Y)",
              },
            { "name": "Alternate",
              "BQ.n": "<n>",
              },
            ],
          "shifters": {
#            "LB": "hold 1",
#            "RB": "hold 2",
            "BK": "sanity",
            "LB": "bounce 1",
            "RB": "hold 2",
            },
          "shiftlayers": {
            0: [ "Base" ],
            1: [ "LeftHanded" , "RightHanded" ],
            2: [ "Alternate" ],
            },
          },
        ]
      }

    uppercfg = cfgmaker.CfgMaker()
    uppercfg.load(d)

#    action = uppercfg.actions[1]
#    shiftcfg = cfgmaker.CfgShifters()
#    d2 = d['actions'][1]
#    shiftcfg.load(d2)
#    shiftcfg.generate_layers(action)
#
    self.assertEqual(len(uppercfg.actions), 2)
    self.assertEqual(len(uppercfg.actions[0].layers), 1)
    self.assertEqual(len(uppercfg.actions[1].layers),
                     9)  # Default, LH, RH, Alt, Pre1, Sh1, Sh2, Pre3, Sh3
    self.assertEqual( [ lyr.name for lyr in uppercfg.actions[1].layers ],
      [ "Default", "LeftHanded", "RightHanded", "Alternate",
        "Preshift_1", "Shift_1", "Shift_2", "Preshift_3", "Shift_3" ])

#    shiftcfg.bind_shifters(1, action)

    sccfg = uppercfg.export_scconfig()
    d = dict(scconfig.toVDF(sccfg))
#    pprint.pprint(d, width=180)


  def test_load2 (self):
    with open("../examples/x3tc_1.yaml") as f:
      d = yaml.load(f)
    cfg = cfgmaker.CfgMaker()
    cfg.load(d)
    scmap = scconfig.Mapping()
    obj = cfg.export_scconfig(scmap)
    sccfg = cfg.export_controller_config()
    d = scconfig.toVDF(sccfg)
    #pprint.pprint(d)
    s = scvdf.dumps(d)
    #print(s)
    # TODO: literal or hash of 's'.


if __name__ == "__main__":
  unittest.main()
