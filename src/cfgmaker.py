#!/usr/bin/env python3

# Given a dict describing a controller configuration,
# generate Scconfig and VDF.

import re

r"""
	cfg:
  .name
  actions[]:
    layers[]:
      "srcsym": [ "evsym" ]
    modifiers[]:
      "srcsym": "shiftdesc"

srcsym:
  LT, RT : Left/Right trigger (full pull); c.f. LT.e, RT.e for soft pull
  LB, RB : Left/Right Bumper (shoulder)
  LP, RP : Left/Right Pad
  LG, RG : Left/Right Grip (bottom/behind pad)
  BK, ST : Back (aka Select), Start (aka Options, View)
  LS : Left Stick click
  LJ : Left Joystick whole
  BQ : Button Quad - face buttons
  GY : gyro(scope); pad tilt
 (PS3, XB360, PS4)
  RS : Right Stick click
  RJ : Right Joystick whole
 (PS4)
  TP : Touchpad whole (LP, RP for implicit split-pad).

  cluster accessor, suffix:
  .c = click
  .o = edge (threshold, soft pull)
  .t = touch
  .u .d .l .r = Direction Pad up, down, left, right
  .n .e .s .w = Button Quad north, east, south, west
  .a .b .x .y = Button Quad south, east, west, north
  .02 .04 .07 .09 .13 .15. 16 = TouchMenu or RadialMenu, menu item #
  .01  .03 .05.  06  .08  .10 .11 .12  .14  .17 .18 .19 .20 = Radial Menu

  Activator signal prefix
  / : Full Press (explicit)
       .toggle : bool
       .delay_start : int [ms]
       .delay_end: int [ms]
       .haptic [enum: 0, 1, 2, 3 ]
       .cycle : bool
       .repeat : int (0..9999)
  + : Start Press
      .toggle, .delay_start, .delay_end, .haptic, .cycle
  - : Release
      .delay_start, .delay_end, .haptic, .cycle
  _ : Long Press
      .long_press_time, .delay_start, .delay_end, .haptic, .cycle, .repeat
  : : Double Press
      .doubetap_max_duration, .delay_start, .delay_end, .haptic, .cycle, .repeat
  = : Double Press
  & : Chord?
      .chord, .toggle, .delay_start, .delay_end, .haptic, .cycle, .repeat


Modifiers:
  shift
  lock
  latch
  bounce



evsym indicators:
  < : keypress
  ( : gamepad
  [ : mouse
  { : verbose descriptor / everything else


activator modifer/options suffices:
  $ : activator-specific tweak (Long=>press time, Double=>duration, Chord=>chord)
  % : toggle on
  | : interruptible
  @ : delay_start '+' delay_end ("@0+10")
  ~ : haptics : 0,1,2,3 (default 2?; "~2")
  ^ : cycle on
  / : repeat on : 0..9999 (default 0; "/0")
"""


r"""
simultaneous presses

LB: <Left_Control><C>

LB:
  Full_Press:
    bindings:
      - Left_Control
      - C
    settings:
      toggle: False


On the edge:

LB: +<Up> -<Down>

+LB: <Up>
-LB: <Down>

LB:
  - +<Up>
    settings: {}
  - -<Down>
    settings: {}

LB:
  Start_Press:
    bindings:
      - Up
    settings: {}
  Release:
    bindings: - Down
    settings: {}
 
"""



r"""
evsym: keypress_evsym evsym |
       mouseswitch_evsym evsym |
       gamepad_evsym evsym |
       generic_evsym evsym |
       None
keypress_evsym: '<' IDENTIFIER '>'
mouseswitch_evsym: '[' IDENTIFIER ']
gamepad_evsym: '(' IDENTIFYER ')'
generic_evsym: '{' identifiers '}'
identifiers: IDENTIFIER identifiers |
             IDENTIFIER

subsrc: '.' dpad_sub |
        '.' buttonquad_sub |
        '.' trigger_sub |
        '.' menuitem_sub
        '.' touchpad_sub |
dpad_sub: 'u' | 'd' | 'l' | 'r' | 'c' | 'o'
button_quad_sub: 'n' | 'w' | 'e' | 's' |
                 'y' | 'x' | 'b' | 'a'
trigger_sub: 'c' | 'e'
menuitem_sub: DIGIT DIGIT
touchpad_sub: dpad_sub | 't'

genmod: specific genmod |
        may_toggle genmod |
        may_interrupt genmod |
        delay_spec genmod |
        haptic_spec genmod |
        may_cycle genmod |
        repeat_spec genmod |
        None
specific: ':' INTEGER |
          's' INTEGER
may_toggle: '%' |
            't'
may_interrupt: '|' |
               'i'
delay_spec: '@' integer_pair |
            'd' integer_pair
integer_pair: INTEGER ',' INTEGER |
              INTEGER '+' INTEGER
haptic_spec: '~' | '~' DIGIT |
             'h' DIGIT
may_cycle: '^' |
           'c'
repeat_spec: '/' INTEGER |
             'r' INTEGER

"""
evsym_re = """([-/+_=:\&]?)""" + """(<[A-Za-z_][A-Za-z0-9_]*>|\[[A-Za-z_][A-Za-z0-9_]*\]|\([A-Za-z_][A-Za-z0-9_]*\)|{[^}]*})"""
evsymmod_re = """([t%]|[i|]|[c^]|[s:][0-9]+|[d@][0-9]+[+,][0-9]+|[h~][0-9]*|[r/][0-9]+)"""

class Evsym (object):
  """Event symbol."""
  def __init__ (self):
    pass

  @staticmethod
  def parse (s):
    evsymre = re.compile(evsym_re)
    matches = evsymre.match(s)
    #print("matches = {} / {}".format(matches, matches.groups()))
    #print("rest: {}".format(s[matches.end(0):]))
    modre = re.compile(evsymmod_re)
    m2 = modre.findall(s[matches.end(0):])
    print("m2", m2)

class CfgMaker (object):
  pass



Evsym.parse("+(B):1000~2%^@0,200/100")
Evsym.parse("+(B)s1000h2tcd0,200/100")
