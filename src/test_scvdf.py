#!/usr/bin/env python3
# encoding=utf-8

import sys, unittest

import scvdf
from scvdf import Tokenizer, StreamTokenizer, StringTokenizer, TokenizeState
from scvdf import toDict, SCVDFDict


class TestScvdfDict (unittest.TestCase):
  def test_evolution_0 (self):
    # Test the example evolution is/remains valid.
    r"""
>>> d = SCVDFDict()             # {}
>>> d['a'] = 1                  # { "a": [1] }
>>> d['a'] = 2                  # { "a": [1,2] }
>>> d['a']                      # 2
>>> d['a'] = 3                  # { "a": [1,2,3] }
>>> d['a']                      # 3
>>> del d['a']                  # {}
>>> d['a']                      ## KeyError
>>> d['a'] = ['A','B', 'C']     # { "a": [ 'A', 'B', 'C' }
>>> d['a'] = 100                # { "a": [ 'A', 'B', 'C', 100 ] }
>>> d['a'] = None               # { "a": [ 'A', 'B', 'C', 100, None ] }
>>> d['a']                      # None

Accessing by subscript yields the last value for compatibility with dict.
This last value may be None (for zero-length list).
The method get_all() is provided for accessing the entire list:
>>> d.get_all('a')              # [ 'A', 'B', 'C', 100, None ]
>>> d.get_all('none')           # KeyError
>>> d.get_all('none',[])        # []           # by extension of dict.get()

Specific multivalue can be accessed with tuple of (key,position).
>>> d['a',0]                    # 'A'
>>> d['a',3]                    # 100
>>> d['a',4]                    # None
>>> d['a',5]                    ## IndexError
>>> d['a',]                     # [ 'A', 'B', 'C', 100, None ]    # all
>>> d['b',]                     ## KeyError
>>> d['b',0]                    ## KeyError
"""
    d = SCVDFDict()
    self.assertTrue(isinstance(d, SCVDFDict))
    d['a'] = 1
    d['a'] = 2
    self.assertEqual(d['a'], 2)
    d['a'] = 3
    self.assertEqual(d['a'], 3)
    del d['a']
    self.assertRaises(KeyError, lambda: d['a'])
    d['a'] = [ 'A', 'B', 'C' ]
    d['a'] = 100
    d['a'] = None
    self.assertEqual(d['a'], None)

    self.assertEqual(d.get_all('a'), [ 'A', 'B', 'C', 100, None ])
    self.assertRaises(KeyError, lambda: d.get_all('none'))
    self.assertEqual(d.get_all('none',[]), [])

    self.assertEqual( d['a',0] , 'A' )
    self.assertEqual( d['a',3] , 100 )
    self.assertEqual( d['a',4] , None )
    self.assertRaises(IndexError, lambda: d['a',5])
    self.assertEqual( d['a',], [ 'A', 'B', 'C', 100, None ] )
    self.assertRaises(KeyError, lambda: d['b',])
    self.assertRaises(KeyError, lambda: d['b',0])

  def test_primitive_predicates (self):
    s = ""
    t = ()
    l = []
    d = {}

    self.assertTrue(scvdf._stringlike(s))
    self.assertFalse(scvdf._stringlike(t))
    self.assertFalse(scvdf._stringlike(l))
    self.assertFalse(scvdf._stringlike(d))

    self.assertFalse(scvdf._nssequencelike(s))
    self.assertTrue(scvdf._nssequencelike(t))
    self.assertTrue(scvdf._nssequencelike(l))
    self.assertFalse(scvdf._nssequencelike(d))

    self.assertFalse(scvdf._nstuplelike(s))
    self.assertTrue(scvdf._nstuplelike(t))
    self.assertFalse(scvdf._nstuplelike(l))
    self.assertFalse(scvdf._nstuplelike(d))

    self.assertFalse(scvdf._nslistlike(s))
    self.assertFalse(scvdf._nslistlike(t))
    self.assertTrue(scvdf._nslistlike(l))
    self.assertFalse(scvdf._nslistlike(d))

    self.assertFalse(scvdf._dictlike(s))
    self.assertFalse(scvdf._dictlike(t))
    self.assertFalse(scvdf._dictlike(l))
    self.assertTrue(scvdf._dictlike(d))



class TestVdfTokenizer (unittest.TestCase):
  def setUp (self):
    TokenizeState.DEBUG = False
    self.buffer = False

  def prepare (self, test_string):
#    try:
#      from StringIO import StringIO
#    except ImportError:
#      from io import StringIO
#    self.f = StringIO(test_string)
#    self.tokenizer = StreamTokenizer(self.f)
    self.tokenizer = StringTokenizer(test_string)

  def test_unquoted (self):
    self.prepare("foo")
    res = self.tokenizer.next_token()
    self.assertEqual(res, (Tokenizer.TOK_UNQUOTED, "foo"))

  def test_2unquoted (self):
    self.prepare("bar quux")
    res = self.tokenizer.next_token()
    self.assertEqual(res, (Tokenizer.TOK_UNQUOTED, "bar"))
    res = self.tokenizer.next_token()
    self.assertEqual(res, (Tokenizer.TOK_UNQUOTED, "quux"))

  def test_stream_unquoted (self):
    self.prepare("lorem ipsum dolor sit amet    \r\n\t")
    res = [ x for x in self.tokenizer ]
#    print("res = {!r}".format(res))
    self.assertEqual(res, [
      (Tokenizer.TOK_UNQUOTED, "lorem"),
      (Tokenizer.TOK_UNQUOTED, "ipsum"),
      (Tokenizer.TOK_UNQUOTED, "dolor"),
      (Tokenizer.TOK_UNQUOTED, "sit"),
      (Tokenizer.TOK_UNQUOTED, "amet")
      ])

  def test_quoted (self):
    self.prepare('"kirje"')
    res = self.tokenizer.next_token()
    self.assertEqual(res, (Tokenizer.TOK_QUOTED, "kirje"))

  def test_2quoted (self):
    self.prepare('  "quux"      "quuux" ')
    res = self.tokenizer.next_token()
    self.assertEqual(res, (Tokenizer.TOK_QUOTED, "quux"))
    res = self.tokenizer.next_token()
    self.assertEqual(res, (Tokenizer.TOK_QUOTED, "quuux"))

  def test_quoted_esc (self):
    self.prepare(r'''"one\"" "\"two" "th\"ree" "\"\""''')
    res = [ x for x in self.tokenizer ]
    self.assertEqual(res, [
      (Tokenizer.TOK_QUOTED, 'one"'),
      (Tokenizer.TOK_QUOTED, '"two'),
      (Tokenizer.TOK_QUOTED, 'th"ree'),
      (Tokenizer.TOK_QUOTED, '""')
      ])

  def test_stream_quoted (self):
    self.prepare('"alpha"  "bravo" "charlie"\t"delta"\n"\\"cheeky\\""')
    res = [ x for x in self.tokenizer ]
#    print("res = {!r}".format(res))
    self.assertEqual(res, [
      (Tokenizer.TOK_QUOTED, "alpha"),
      (Tokenizer.TOK_QUOTED, "bravo"),
      (Tokenizer.TOK_QUOTED, "charlie"),
      (Tokenizer.TOK_QUOTED, "delta"),
      (Tokenizer.TOK_QUOTED, '"cheeky"'),
      ])

  def test_nesting (self):
    self.prepare("{")
    res = self.tokenizer.next_token()
    self.assertEqual(res, (Tokenizer.TOK_NEST, "{"))

  def test_denesting (self):
    self.prepare("  }  ")
    res = self.tokenizer.next_token()
    self.assertEqual(res, (Tokenizer.TOK_DENEST, "}"))

  def test_comments (self):
    self.prepare("//proper comment\n")
    res = self.tokenizer.next_token()
    self.assertEqual(res[0], Tokenizer.TOK_COMMENT)
    self.assertGreater(len(res[1]), 0)

    self.prepare("//improper comment")
    res = self.tokenizer.next_token()
    self.assertEqual(res[0], Tokenizer.TOK_COMMENT)
    self.assertGreater(len(res[1]), 0)

    self.prepare("a/not-comment")
    res = self.tokenizer.next_token()
    self.assertEqual(res[0], Tokenizer.TOK_UNQUOTED)
    self.assertEqual(res[1], "a/not-comment")

  def test_unquoted_into_comment (self):
    self.prepare("foo//bar")
    res = self.tokenizer.next_token()
    self.assertEqual(res, (Tokenizer.TOK_UNQUOTED, "foo"))
    res = self.tokenizer.next_token()
    self.assertEqual(res[0], Tokenizer.TOK_COMMENT)

    self.prepare("foo //bar")
    res = self.tokenizer.next_token()
    self.assertEqual(res, (Tokenizer.TOK_UNQUOTED, "foo"))
    res = self.tokenizer.next_token()
    self.assertEqual(res[0], Tokenizer.TOK_COMMENT)

    self.prepare("""foo
// bar
baz""")
    res = self.tokenizer.next_token()
    self.assertEqual(res, (Tokenizer.TOK_UNQUOTED, "foo"))
    res = self.tokenizer.next_token()
    self.assertEqual(res[0], Tokenizer.TOK_COMMENT)
    res = self.tokenizer.next_token()
    self.assertEqual(res, (Tokenizer.TOK_UNQUOTED, "baz"))

  def test_unquoted_into_nest (self):
    equivalents = [ "foo{}", " foo { } ", "foo {}", "foo\n{\n}\n" ]
    for src in equivalents:
      self.prepare(src)
      res = [ x for x in self.tokenizer ]
      self.assertEqual(res, [
        (Tokenizer.TOK_UNQUOTED, "foo"),
        (Tokenizer.TOK_NEST, "{"),
        (Tokenizer.TOK_DENEST, "}")
        ])

    equivalents = [ "foo{} bar", " foo { }  bar ", "foo {}bar", "foo\n{\n}\nbar" ]
    for src in equivalents:
      self.prepare(src)
      res = [ x for x in self.tokenizer ]
      self.assertEqual(res, [
        (Tokenizer.TOK_UNQUOTED, "foo"),
        (Tokenizer.TOK_NEST, "{"),
        (Tokenizer.TOK_DENEST, "}"),
        (Tokenizer.TOK_UNQUOTED, "bar")
        ])

  def test_semicomment (self):
    self.prepare("""foo "alpha, aleph/a"
""")
    res = self.tokenizer.next_token()
    self.assertEqual(res, (Tokenizer.TOK_UNQUOTED, "foo"))
    res = self.tokenizer.next_token()
    self.assertEqual(res, (Tokenizer.TOK_QUOTED, "alpha, aleph/a"))


class TestVdfReader (unittest.TestCase):
  def test_parse1 (self):
    src = '''"foo" "bar"'''
    res = scvdf.loads(src)
    #print("res = {!r}".format(res))
    self.assertEqual(res, { "foo": "bar" })

  def test_parse2 (self):
    src = r'''
"foo" "bar"
"quux" "\"quuux\""
'''
    res = scvdf.loads(src)
    #print("res = {!r}".format(res))
    self.assertEqual(res, {"foo":"bar", "quux":'"quuux"'})

  def test_parse1sub (self):
    src = r'''
"foo" {
 "a" "b"
}
'''
    res = scvdf.loads(src)
    #print("res = {!r}".format(res))
    self.assertEqual( res, { "foo": { "a": "b" } } )

  def test_parse1sub2 (self):
    src = r'''
"foo" {
  // line comment
  "a" { "aa" "bb" }  // winged comment
}
'''
    res = scvdf.loads(src)
    #print("res = {!r}".format(res))
    self.assertEqual( res, { "foo": { "a": { "aa": "bb" }}} )

  def test_empty (self):
    src = ''
    res = scvdf.loads(src)
    self.assertFalse(res)

  def test_only_comment (self):
    src = '//empty vdf\n'
    res = scvdf.loads(src)
    self.assertFalse(res)

  def test_bad_1 (self):
    src = r'''}'''
    res = scvdf.loads(src)
    self.assertEqual( res, None )

  def test_empty_value (self):
    src = r'''"foo" { }'''
    res = scvdf.loads(src)
    self.assertEqual(res, { "foo": {} })

    src = r'''"foo" {}'''
    res = scvdf.loads(src)
    self.assertEqual(res, { "foo": {} })

    src = r'''foo{}'''
    res = scvdf.loads(src)
    self.assertEqual(res, { "foo": {} })

  def test_load_1 (self):
    fname = '../examples/defaults1_0.vdf'
    f = open(fname, 'rt')
    res = scvdf.load(f)
    f.close()
#    import pprint
#    pprint.pprint(res)
    #print("res = {!r}".format(res))
    self.assertIsNot(res, None)
    self.assertNotEqual(res, [])

  def test_multivalue (self):
    d = scvdf.SCVDFDict()
    d['a'] = 1
    d['a'] = 2
    d['a'] = 3
    self.assertEqual(d, {"a":[1,2,3]})
    self.assertEqual(d['a'], 3)
    self.assertEqual(d['a',1], 2)

  def test_load_othertype (self):
    src = r'''
"foo" "bar"
'''
    res = scvdf.loads(src, dict)
    self.assertEqual(res, {"foo": "bar"})

    src = r'''
"group" "1"
"group" "2"
'''
    res = scvdf.loads(src, dict)
    self.assertEqual(res, {"group": "2"})

    src = r'''
"group" "1"
"group" "2"
"group" "3"
'''
    res = scvdf.loads(src, scvdf.SCVDFDict)
    self.assertEqual(res, {"group": [ "1", "2", "3" ] })

    src = r'''
"example"
{
  "group" { "id" "0"
  "first" "1"
  }
  "group"
  {
    "id" "1" }
  "group"
  {
    "id" "2"
  }
}
'''
    res = scvdf.loads(src, scvdf.SCVDFDict)
    self.assertEqual(res, {"example": { "group": [ {"id":'0',"first":"1"}, {"id":'1'}, {"id":'2'}]}})
    example = res['example']
    items = [ x for x in example.items() ]
    #print("items = {!r}".format(items))
    self.assertEqual(len(items), 3)

  def test_multipath (self):
    src = r'''
"example"
{
  "group" { "id" "0"
  "first" "1"
  }
  "group"
  {
    "id" "1" }
  "group"
  {
    "id" "2"
  }
}
'''
    res = scvdf.loads(src, scvdf.SCVDFDict)
    self.assertEqual(res, {"example": { "group": [ {"id":'0',"first":"1"}, {"id":'1'}, {"id":'2'}]}})
    example = res['example']
    items = [ x for x in example.items() ]
    #print("items = {!r}".format(items))
    self.assertEqual(len(items), 3)

    group = example['group',]   # all groups
    self.assertEqual(len(group), 3)
    group = example['group',0]   # first of group
    self.assertEqual(group, { "id": '0', "first": "1" })
    group = example['group',1]   # second of group
    self.assertEqual(group, { "id": '1' })
    group = example['group',2]   # third of group
    self.assertEqual(group, { "id": '2' })


class TestVdfWriter (unittest.TestCase):
  # Interfield separator to expect.
  IFS="\t\t"

  def setUp (self):
    self.buffer = False
    return

  def test_save1 (self):
    data = [ ("foo", "bar") ]
    res = scvdf.dumps(data)
    self.assertEqual(res, '''"foo"{IFS}"bar"\n'''.format(IFS=self.IFS))

  def test_save2 (self):
    data = [ ("foo", "bar"), ("quux", "quuux") ]
    res = scvdf.dumps(data)
    self.assertEqual(res, '''"foo"{IFS}"bar"\n"quux"{IFS}"quuux"\n'''.format(IFS=self.IFS))

  def test_sub1 (self):
    data = [ ("foo", [ ("a","b") ] ) ]
    res = scvdf.dumps(data)
    self.assertEqual(res, '''\
"foo"
{{
\t"a"{IFS}"b"
}}
'''.format(IFS=self.IFS))

  def test_sub2 (self):
    data = [ ("foo", [ ("a", [ ("aa","bb") ] ) ] ) ]
    res = scvdf.dumps(data)
    self.assertEqual(res, '''\
"foo"
{{
\t"a"
\t{{
\t\t"aa"{IFS}"bb"
\t}}
}}
'''.format(IFS=self.IFS))

  def test_load_save_1 (self):
    fname = '../examples/defaults1_0.vdf'
    f = open(fname, 'rt')
    literal = f.read()
    f.close()
    res = scvdf.loads(literal, scvdf.SCVDFDict)
    out = scvdf.dumps(res)
    self.assertEqual(literal, out)

    import hashlib
    try:
      from StringIO import StringIO
    except ImportError:
      from io import StringIO
#    OUTFNAME = "output.txt"
    g = StringIO()
    scvdf.dump(res, g)
    summer = hashlib.new("md5")
    summer.update(g.getvalue().encode("utf-8"))
    digested = summer.hexdigest()
    self.assertEqual(digested, "99d8c4ded89ec867519792db86d3bffc")

  def test_load_save_2 (self):
    fname = '../examples/com³-wip3_0.vdf'
    f = open(fname, 'rt')
    literal = f.read()
    f.close()
    res = scvdf.loads(literal, scvdf.SCVDFDict)
    out = scvdf.dumps(res)
    self.assertEqual(literal, out)

    import hashlib
    try:
      from StringIO import StringIO
    except ImportError:
      from io import StringIO
#    OUTFNAME = "output.txt"
    g = StringIO()
    scvdf.dump(res, g)
    summer = hashlib.new("md5")
    summer.update(g.getvalue().encode("utf-8"))
    digested = summer.hexdigest()
    self.assertEqual(digested, "01dc2f4e9b6c8f86e2d1678c2763540d")


if __name__ == "__main__":
  #unittest.main(defaultTest=['TestVdfTokenizer.test_unquoted'])
  #unittest.main(defaultTest=['TestVdfTokenizer.test_unquoted_into_comment'])
  #unittest.main(defaultTest=['TestVdfTokenizer.test_quoted_esc'])
  #unittest.main(defaultTest=['TestVdfTokenizer.test_comments'])
  #unittest.main(defaultTest=['TestVdfTokenizer.test_semicomment'])
  #unittest.main(defaultTest=['TestVdfReader.test_parse1sub'])
  #unittest.main(defaultTest=['TestVdfReader.test_multivalue'])
  #unittest.main(defaultTest=['TestVdfReader.test_empty_value'])
  #unittest.main(defaultTest=['TestVdfWriter.test_load_save_1'])
  #unittest.main(defaultTest=['TestScvdfDict.test_evolution_0'])
  unittest.main()

