#!/usr/bin/env python3

import sys, unittest

import scvdf
from scvdf import Tokenizer, StreamTokenizer, StringTokenizer, TokenizeState

class TestVdfTokenizer (unittest.TestCase):
  def setUp (self):
    TokenizeState.DEBUG = False
#    self.buffer = False

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


class TestVdfWriter (unittest.TestCase):
  def test_save1 (self):
    data = [ ("foo", "bar") ]
    res = scvdf.dumps(data)
    self.assertEqual(res, '''"foo" "bar"\n''')

  def test_save2 (self):
    data = [ ("foo", "bar"), ("quux", "quuux") ]
    res = scvdf.dumps(data)
    self.assertEqual(res, '''"foo" "bar"\n"quux" "quuux"\n''')



if __name__ == "__main__":
  #unittest.main(defaultTest=['TestVdfTokenizer.test_unquoted'])
  #unittest.main(defaultTest=['TestVdfTokenizer.test_unquoted_into_comment'])
  #unittest.main(defaultTest=['TestVdfTokenizer.test_quoted_esc'])
  #unittest.main(defaultTest=['TestVdfParser.test_parse1sub'])
  unittest.main()

