#!/usr/bin/env python3

import unittest

import cfgmaker
from cfgmaker import Evspec, Srcspec, CfgMaker
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

  def test_evspec (self):
    evspec = Evspec.parse("+(B)")
    obj = evspec.export_scconfig()
    d = scconfig.toVDF(obj)
    # singular entry for 'binding'.
    self.assertEqual(d, {'bindings': { "binding": "xinput_button B" } })

    evspec = Evspec.parse("+(B)~3@10,50")
    obj = evspec.export_scconfig()
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
    obj = evspec.export_scconfig()
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


if __name__ == "__main__":
  unittest.main()
