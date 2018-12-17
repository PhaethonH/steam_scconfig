#!/usr/bin/env python3

import sys, unittest

import scvdf
from scvdf import Tokenizer, StreamTokenizer, StringTokenizer, TokenizeState

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
    self.assertEqual(res, [("foo","bar")])

  def test_parse2 (self):
    src = r'''
"foo" "bar"
"quux" "\"quuux\""
'''
    res = scvdf.loads(src)
    #print("res = {!r}".format(res))
    self.assertEqual(res, [("foo","bar"), ("quux", '"quuux"')])

  def test_parse1sub (self):
    src = r'''
"foo" {
 "a" "b"
}
'''
    res = scvdf.loads(src)
    #print("res = {!r}".format(res))
    self.assertEqual( res, [("foo", [("a","b")])] )

  def test_parse1sub2 (self):
    src = r'''
"foo" {
  // line comment
  "a" { "aa" "bb" }  // winged comment
}
'''
    res = scvdf.loads(src)
    #print("res = {!r}".format(res))
    self.assertEqual( res, [("foo", [ ("a",[("aa","bb")]) ])] )

  def test_empty (self):
    src = ''
    res = scvdf.loads(src)
    self.assertEqual( res, [] )

  def test_only_comment (self):
    src = '//empty vdf\n'
    res = scvdf.loads(src)
    self.assertEqual( res, [] )

  def test_bad_1 (self):
    src = r'''}'''
    res = scvdf.loads(src)
    self.assertEqual( res, None )

  def test_empty_value (self):
    src = r'''"foo" { }'''
    res = scvdf.loads(src)
    self.assertEqual(res, [ ("foo", []) ])

    src = r'''"foo" {}'''
    res = scvdf.loads(src)
    self.assertEqual(res, [ ("foo", []) ])

    src = r'''foo{}'''
    res = scvdf.loads(src)
    self.assertEqual(res, [ ("foo", []) ])

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

  def test_dictmultivalue (self):
    d = scvdf.DictMultivalue()
    d['a'] = 1
    d['a'] = 2
    d['a'] = 3
    self.assertEqual(d, {"a":[1,2,3]})

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
    res = scvdf.loads(src, scvdf.DictMultivalue)
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
    res = scvdf.loads(src, scvdf.DictMultivalue)
    self.assertEqual(res, {"example": { "group": [ {"id":'0',"first":"1"}, {"id":'1'}, {"id":'2'}]}})
    example = res['example']
    items = [ x for x in example.items() ]
    #print("items = {!r}".format(items))
    self.assertEqual(len(items), 3)


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
    res = scvdf.loads(literal, scvdf.DictMultivalue)
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




if __name__ == "__main__":
  #unittest.main(defaultTest=['TestVdfTokenizer.test_unquoted'])
  #unittest.main(defaultTest=['TestVdfTokenizer.test_unquoted_into_comment'])
  #unittest.main(defaultTest=['TestVdfTokenizer.test_quoted_esc'])
  #unittest.main(defaultTest=['TestVdfTokenizer.test_comments'])
  #unittest.main(defaultTest=['TestVdfTokenizer.test_semicomment'])
  #unittest.main(defaultTest=['TestVdfReader.test_parse1sub'])
  #unittest.main(defaultTest=['TestVdfReader.test_dictmultivalue'])
  #unittest.main(defaultTest=['TestVdfReader.test_empty_value'])
  #unittest.main(defaultTest=['TestVdfWriter.test_load_save_1'])
  unittest.main()

