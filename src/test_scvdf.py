#!/usr/bin/env python3

import sys, unittest

import scvdf
from scvdf import Tokenizer

class TestVdfTokenizer (unittest.TestCase):
  def prepare (self, test_string):
    try:
      from StringIO import StringIO
    except ImportError:
      from io import StringIO
    self.f = StringIO(test_string)
    self.tokenizer = Tokenizer(self.f)

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
    #TokenizeState.DEBUG = True
    self.prepare("foo//bar")
    res = self.tokenizer.next_token()
    self.assertEqual(res, (Tokenizer.TOK_UNQUOTED, "foo"))
    res = self.tokenizer.next_token()
    self.assertEqual(res[0], Tokenizer.TOK_COMMENT)
    #TokenizeState.DEBUG = False

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



if __name__ == "__main__":
  #unittest.main(defaultTest=['TestVdfTokenizer.test_unquoted_into_comment'])
  unittest.main()

