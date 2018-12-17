#!/usr/bin/env python3

import sys

# VDF parser, rewritten for use in externally configuring Steam Controller.
# pip-installable library "vdf" left much to be desired.

# Yields (converts to) a list of (k,v) 2-tuples.
#   [ (first_key, first_value), (second_key, second_value), ... ]
# Any of the value may be a nested VDF list-of-tuples:
#   [ (nesting_key, [ ( keyA, valueA ), ( keyB, valueB ), ... ] ), ( second_key, second_value ), ... ]

# Character type predicates
def is_whitespace (ch):
  return ch and (ch in " \r\n\t")
def is_dquote (ch):
  return (ch == '"')
def is_escape (ch):
  return (ch == '\\')
def is_nestopen (ch):
  return (ch == '{')
def is_nestclose (ch):
  return (ch == '}')
def is_comment0 (ch):
  return (ch == '/')
def is_comment1 (ch):
  return (ch == '/')
def is_decomment0 (ch):
  return (ch == '\n') or (ch == '\r')
def is_directive (ch):
  return (ch == '#')
def is_eol (ch):
  return (ch == '\n') or (ch == '\r')
def is_eos (ch):
  return (ch == '') or (ch == '\0') or (ch is None)
def is_any (ch):
  return True




class Token (object):
  def __init__ (self, toktype, tokval):
    self.toktype = toktype
    self.tokval = tokval



class Tokenizer (object):
  """Tokenizer class, instance state for tokenizing a text stream.

Token types:
  WS : any of space, tab, carriage return, line feed
  QUOTED : starts with (does not include) double-quote, include escapes double-quote, ends with unescaped double-quote
  NEST : unquoted character '{'
  DENEST : unquoted character '}'
  COMMENT : "//" until newline
  UNQUOTED : starts with none of WS,'"','{','}',"//" until any of them.
"""
  TOK_END_OF_STREAM='END_OF_STREAM'
  TOK_ERROR = 'ERROR'
  TOK_WS = 'WS'
  TOK_QUOTED = 'QUOTED'
  TOK_UNQUOTED = 'UNQUOTED'
  TOK_NEST = 'NEST'
  TOK_DENEST = 'DENEST'
  TOK_COMMENT = 'COMMENT'

  def __init__ (self, srcstream):
    self.srcstream = srcstream
    self.pushback = []  # Stack, characters pushed back for retokenizing.
    self.build = []     # List of characters for currently-built token.
    self.state = TokenizeBegin(self)
    # One token pending for processing
    # TODO: make it a queue of tokens?
    self.pending = None

  def nextch (self):
    ch = ''
    if self.pushback:
      ch = self.pushback.pop()
    else:
      ch = self.srcstream.read(1)
    return ch

  def nop (self, ch=None):
    """op: do nothing"""
    return self

  def pushch (self, ch):
    """op: copy character to pushback (re-read) stack."""
    self.pushback.append(ch)
    return self

  def discard (self, ch=None):
    """op: ignore character."""
    return self

  def consume (self, ch):
    """op: append character to token buffer."""
    self.build.append(ch)
    return self

  def drop (self, n):
    """op: drop 'n' characters from end of token buffer."""
    while n > 0:
      ch = self.build.pop()
      #self.pushch(ch)
      n -= 1
    return self

  def clear (self, _=None):
    """op: reset token buffer (discard all accumulated characters)."""
    self.build = []
    return self

  def advance (self, explicit_type=None):
    """op: token is complete."""
    if self.build:
      toktype = explicit_type
      if toktype is None:
        toktype = self.state.TOKTYPE
      tokval = ''.join(self.build)
      self.pending = (toktype, tokval)
      self.build = []
    return self

  def next_token (self):
    """Retrieve next token."""
    while self.state:
      self.state = self.state.handle()
      if self.pending is not None:
        retval = self.pending
        self.pending = None
        return retval
    return None

  def __iter__ (self):
    """Retrieve next token, iterator idiom."""
    while self.state:
      self.state = self.state.handle()
      if self.pending is not None:
        retval = self.pending
        self.pending = None
        yield retval
    return


# Tokenizer states (State Pattern)

class TokenizeState (object):
  """Base class for tokenizer state."""
  TOKTYPE=None

  DEBUG=False

  def __init__ (self, context):
    self.context = context
  def feed (self, ch):
    """per-class override."""
    raise NotImplementedError("Executing feed() on base class")
  def handle (self):
    """common entry point -- extract one character, pass to feed()."""
    if not self.context:
      return None
    ch = self.context.nextch()
    if TokenizeState.DEBUG:
      print("handling ({},{!r})".format(self.__class__, ch))
    try:
      return self.feed(ch)
    except NotImplementedError as e:
      raise NotImplementedError("Executing handle() on base class")

class TokenizeError (TokenizeState):
  TOKTYPE=Tokenizer.TOK_ERROR
  def feed (self, ch):
    return None

class TokenizeFinish (TokenizeState):
  TOKTYPE=Tokenizer.TOK_END_OF_STREAM
  def feed (self, ch):
    return None

class TokenizeBegin (TokenizeState):
  TOKTYPE=Tokenizer.TOK_WS
  def feed (self, ch):
    if is_eos(ch): return TokenizeFinish(self.context.discard(ch))
    if is_whitespace(ch): return self
    if is_dquote(ch): return TokenizeQuoted(self.context.discard(ch))
    if is_nestopen(ch): return TokenizeNesting(self.context.consume(ch))
    if is_nestclose(ch): return TokenizeDenesting(self.context.consume(ch))
    if is_comment0(ch): return TokenizeSemicomment(self.context.consume(ch))
    if is_any(ch): return TokenizeUnquoted(self.context.consume(ch))
    return TokenizeError(self.context)

### Quoted token.
class TokenizeQuoted (TokenizeState):
  TOKTYPE=Tokenizer.TOK_QUOTED
  def feed (self, ch):
    if is_eos(ch): return TokenizeFinish(self.context.advance())
    if is_dquote(ch): return TokenizeBegin(self.context.advance())
    if is_escape(ch): return TokenizeEscaped(self.context.discard(ch))
    if is_comment0(ch): return TokenizeSemicomment(self.context.discard(ch))
    self.context.consume(ch)
    return self

class TokenizeEscaped (TokenizeState):
  TOKTYPE=Tokenizer.TOK_QUOTED
  def feed (self, ch):
    if is_eos(ch): return TokenizeFinish(self.context.advance())
    return TokenizeQuoted(self.context.consume(ch))


### Unquoted... stuff.

class TokenizeNesting (TokenizeState):
  TOKTYPE=Tokenizer.TOK_NEST
  def feed (self, ch):
    if is_eos(ch): return TokenizeFinish(self.context.advance())
    # Anything: push back and redo from Begin.
    return TokenizeBegin(self.context.pushch(ch).advance())

class TokenizeDenesting (TokenizeNesting):
  TOKTYPE=Tokenizer.TOK_DENEST
  # same methods as TokenizeNesting

class TokenizeUncomment (TokenizeState):
  """Base/common class for Unquoted and Semicomment"""
  TOKTYPE=Tokenizer.TOK_UNQUOTED
  def feed (self, ch):
    if is_eos(ch): return TokenizeFinish(self.context.advance())
    if is_whitespace(ch) or is_dquote(ch) or is_nestopen(ch) or is_nestclose(ch):
      # Re-examine what caused end-of-token after advancing.
      return TokenizeBegin(self.context.pushch(ch).advance())

    return TokenizeUnquoted(self.context.consume(ch))

class TokenizeSemicomment (TokenizeUncomment):
  """Comment delimiter is two characters.
In this state, the first character was seen.
If the required second character does not follow, then the previous character is part of the token.
If the second character does follow, drop the first character of the comment delimiter from accumulator, and issue as pending token if any other characters were accumulated (i.e. whitespace may have preceded comment).
"""
  TOKTYPE=Tokenizer.TOK_UNQUOTED
  def feed (self, ch):
    if is_comment1(ch): return TokenizeComment(self.context.drop(1).advance())
    return super(TokenizeSemicomment,self).feed(ch)

class TokenizeUnquoted (TokenizeUncomment):
  """Extend TokenizeUncomment to expect a token to be delimited by a comment:
"foo//bar"

(otherwise intervening whitespace would be required: "foo //bar")
"""
  TOKTYPE=Tokenizer.TOK_UNQUOTED
  def feed (self, ch):
    # Might be a comment, otherwise character is part of token.
    if is_comment0(ch): return TokenizeSemicomment(self.context.consume(ch))
    return super(TokenizeUnquoted,self).feed(ch)


class TokenizeComment (TokenizeState):
  """Comment continues until end of line."""
  TOKTYPE=Tokenizer.TOK_COMMENT
  def feed (self, ch):
    if is_eos(ch): return TokenizeFinish(self.context.advance())
    if is_eol(ch): return TokenizeBegin(self.context.advance())
    self.context.consume(ch)
    return self



