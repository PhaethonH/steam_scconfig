#!/usr/bin/env python3

# VDF parser, rewritten for use in externally configuring Steam Controller.
#
# pip-installable library "vdf" left much to be desired for this use.

# Yields (converts to) a list of (k,v) 2-tuples.
#   [ (first_key, first_value), (second_key, second_value), ... ]
# Any of the value may be a nested VDF list-of-tuples:
#   [ (nesting_key, [ ( keyA, valueA ), ( keyB, valueB ), ... ] ), ( second_key, second_value ), ... ]

# DictMultivalue maps keys to list of values, for assigning to same key multiple times.
# If the key was assigned only once, the value is the original assigned value (in the same sense as the built-in dict)
# If the key was already assigned before, the looked up value becomes a list of each subsequent values assigned to the key.
# e.g. d=DictMultivalue()
# d['a'] = 1     # { "a": 1 }
# d['a'] = 2     # { "a": [1,2] }
# d['a'] = 3     # { "a": [1,2,3] }
# del d['a']     # {}
# d['a'] = ['A','A', 'A']    # { "a": ['A', 'A', 'A'] }
# d['a'] = 100               # { "a": [ ['A', 'A', 'A'], 100 ] }
# d['a'] = None              # { "a": [ ['A', 'A', 'A'], 100, None ] }
#
# N.B. VDF does not support a native list type.




#############
# Tokenizer #
#############

# Character type predicates
def is_whitespace (ch): return ch and (ch in " \r\n\t")
def is_dquote (ch): return (ch == '"')
def is_escape (ch): return (ch == '\\')
def is_nestopen (ch): return (ch == '{')
def is_nestclose (ch): return (ch == '}')
def is_comment0 (ch): return (ch == '/')
def is_comment1 (ch): return (ch == '/')
def is_decomment0 (ch): return (ch == '\n') or (ch == '\r')
def is_eos (ch): return (ch == '') or (ch == '\0') or (ch is None)
def is_any (ch): return True
def is_none (ch): return False




# Convert stream of characters into stream of tokens.
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
  TOK_DENEST = 'DENEST'    # De-nest - end of nested k/v pairs.
  TOK_COMMENT = 'COMMENT'

  DEBUG = False

  def __init__ (self):
    self.ch = None      # Currently examined character.
    self.pushback = []  # Stack, characters pushed back for retokenizing.
    self.build = []     # List of characters for currently-built token.
    self.state = TokenizeBegin(self)
    # One token pending for processing
    self.pending = []

  def NOP (self):
    """op: do nothing; ignore character"""
    return self

  def UNGET (self):
    """op: copy character to pushback (re-read) stack."""
    self.pushback.append(self.ch)
    return self

  def LIT (self):
    """op: append character to token buffer."""
    self.build.append(self.ch)
    return self

  def RTRIM (self):
    """op: drop 1 character from end of token buffer."""
    self.build.pop()
    return self

  def CLR (self):
    """op: reset token buffer (discard all accumulated characters)."""
    self.build = []
    return self

  def COMMIT (self, explicit_type=None):
    """op: token is complete."""
    if self.build:
      toktype = explicit_type
      if toktype is None:
        toktype = self.state.TOKTYPE
      tokval = ''.join(self.build)
      self.pending.append((toktype, tokval))
      self.build = []
    return self

  def feed (self, ch):
    """Primary entry point -- feed character to tokenizer.
Returns boolean, whether a token is not ready.

This sense allows looping on feed() until token is ready:

while tokenizer.feed(ch):
  pass
token = tokenizer.next_token()

"""
    if not self.state:
      return False
    # continue feeding any pushed-back characters.
    while self.pushback and self.state:
      self.ch = self.pushback.pop()
      self.state = self.state.handle()
    # feed newest character.
    self.ch = ch
    self.state = self.state.handle()
    # This sense allows looping feed() until a token is ready.
    return not self.pending

  def next_token (self):
    if not self.pending:
      if not self.state:
        # no more possible.
        return (Tokenizer.END_OF_STREAM, '')
      return None   # not ready.
    retval = self.pending[0]
    self.pending = self.pending[1:]
    if self.DEBUG:
      print("yield token {!r}".format(retval))
    return retval


class StreamTokenizer (Tokenizer):
  """Extend Tokenizer to automatically feed from a stream."""
  def __init__ (self, srcstream):
    Tokenizer.__init__(self)
    self.srcstream = srcstream

  def next_token (self):
    """Retrieve next token."""
    if self.pending:
      return super(StreamTokenizer,self).next_token()
    while self.state and not self.pending:
      ch = self.srcstream.read(1)
      self.feed(ch)
      if self.pending:
        return super(StreamTokenizer,self).next_token()
    return None

  def __iter__ (self):
    """Retrieve next token, iterator idiom."""
    while self.state:
      ch = self.srcstream.read(1)
      while self.feed(ch):
        ch = self.srcstream.read(1)
      while self.pending:
        yield super(StreamTokenizer,self).next_token()
    return


class StringTokenizer (Tokenizer):
  """Extend Tokenizer to automatically feed from a stream."""
  def __init__ (self, srcstring):
    Tokenizer.__init__(self)
    self.srcstring = srcstring
    self.srcofs = 0

  def readch (self):
    if self.srcofs < len(self.srcstring):
      ch = self.srcstring[self.srcofs]
      self.srcofs += 1
      return ch
    return ''

  def next_token (self):
    """Retrieve next token."""
    if self.pending:
      return super(StringTokenizer,self).next_token()
    while self.state and not self.pending:
      ch = self.readch()
      self.feed(ch)
      if self.pending:
        return super(StringTokenizer,self).next_token()
    return None

  def __iter__ (self):
    """Retrieve next token, iterator idiom."""
    while self.state:
      ch = self.readch()
      while self.feed(ch):
        ch = self.readch()
      while self.pending:
        yield super(StringTokenizer,self).next_token()
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
    ch = self.context.ch
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
    if is_eos(ch): return TokenizeFinish(self.context.NOP())
    if is_whitespace(ch): return self
    if is_dquote(ch): return TokenizeQuoted(self.context.NOP())
    if is_nestopen(ch): return TokenizeNesting(self.context.LIT())
    if is_nestclose(ch): return TokenizeDenesting(self.context.LIT())
    if is_comment0(ch): return TokenizeSemicomment(self.context.LIT())
    if is_any(ch): return TokenizeUnquoted(self.context.LIT())
    return TokenizeError(self.context)

### Quoted token.
class TokenizeQuoted (TokenizeState):
  TOKTYPE=Tokenizer.TOK_QUOTED
  def feed (self, ch):
    if is_eos(ch): return TokenizeFinish(self.context.COMMIT())
    if is_dquote(ch): return TokenizeBegin(self.context.COMMIT())
    if is_escape(ch): return TokenizeEscaped(self.context.NOP())
    self.context.LIT()
    return self

class TokenizeEscaped (TokenizeState):
  TOKTYPE=Tokenizer.TOK_QUOTED
  def feed (self, ch):
    if is_eos(ch): return TokenizeFinish(self.context.COMMIT())
    return TokenizeQuoted(self.context.LIT())


### Unquoted... stuff.

class TokenizeNesting (TokenizeState):
  TOKTYPE=Tokenizer.TOK_NEST
  def feed (self, ch):
    if is_eos(ch): return TokenizeFinish(self.context.COMMIT())
    # Anything: push back and redo from Begin.
    return TokenizeBegin(self.context.UNGET().COMMIT())

class TokenizeDenesting (TokenizeNesting):
  TOKTYPE=Tokenizer.TOK_DENEST
  # same methods as TokenizeNesting

class TokenizeUncomment (TokenizeState):
  """Base/common class for Unquoted and Semicomment"""
  TOKTYPE=Tokenizer.TOK_UNQUOTED
  def feed (self, ch):
    if is_eos(ch): return TokenizeFinish(self.context.COMMIT())
    if is_whitespace(ch) or is_dquote(ch) or is_nestopen(ch) or is_nestclose(ch):
      # Re-examine what caused end-of-token after advancing.
      return TokenizeBegin(self.context.UNGET().COMMIT())

    return TokenizeUnquoted(self.context.LIT())

class TokenizeSemicomment (TokenizeUncomment):
  """Comment delimiter is two characters.
In this state, the first character was seen.
If the required second character does not follow, then the previous character is part of the token.
If the second character does follow, drop the first character of the comment delimiter from accumulator, and issue as pending token if any other characters were accumulated (i.e. whitespace may have preceded comment).
"""
  TOKTYPE=Tokenizer.TOK_UNQUOTED
  def feed (self, ch):
    if is_comment1(ch): return TokenizeComment(self.context.RTRIM().COMMIT())
    return super(TokenizeSemicomment,self).feed(ch)

class TokenizeUnquoted (TokenizeUncomment):
  """Extend TokenizeUncomment to expect a token to be delimited by a comment:
"foo//bar"

(otherwise intervening whitespace would be required: "foo //bar")
"""
  TOKTYPE=Tokenizer.TOK_UNQUOTED
  def feed (self, ch):
    # Might be a comment, otherwise character is part of token.
    if is_comment0(ch): return TokenizeSemicomment(self.context.LIT())
    return super(TokenizeUnquoted,self).feed(ch)


class TokenizeComment (TokenizeState):
  """Comment continues until end of line."""
  TOKTYPE=Tokenizer.TOK_COMMENT
  def feed (self, ch):
    if is_eos(ch): return TokenizeFinish(self.context.COMMIT())
    if is_decomment0(ch): return TokenizeBegin(self.context.COMMIT())
    self.context.LIT()
    return self







##########
# Parser #
##########

# Convert stream of tokens into object (list of 2-tuples).
class Parser (object):
  def __init__ (self):
    self.tokenizer = None
    self.store = []

  def parse (self, srcstream):
    pass



class DictMultivalue (dict):
  """Allow multiple values per dictionary entry.


example evolution:
d = DictMultivalue()       # {}
d['a'] = 1                 # { "a": 1 }
d['a'] = 2                 # { "a": [1,2] }
d['a'] = 3                 # { "a": [1,2,3] }
del d['a']                 # {}
d['a'] = ['A','A', 'A']    # { "a": ['A', 'A', 'A'] }
d['a'] = 100               # { "a": [ ['A', 'A', 'A'], 100 ] }
d['a'] = None              # { "a": [ ['A', 'A', 'A'], 100, None ] }

"""
  def __init__ (self, *args, **kwargs):
    super(dict,self).__init__(*args, **kwargs)
    self.multiset = set()
    self.keyorder = []

  def append (self, pair):
    """List sense, assume element is 2-tuple of (key,value).
Takes advantage of the typical behavior of appending to list-of-pairs.
"""
    (k,v) = pair
    self.__setitem__(k,v)

  def __setitem__ (self, k, v):
    if self.__contains__(k):
      # Setting existing key.
      temp = self.__getitem__(k)
      if k in self.multiset:
        # Append to existing multivalue.
        temp.append(v)
        super(DictMultivalue,self).__setitem__(k, temp)
      else:
        # Turn into multivalue.
        self.multiset.add(k)
        super(DictMultivalue,self).__setitem__(k, [temp, v])
    else:
      # New dict key.
      super(DictMultivalue,self).__setitem__(k,v)
      self.keyorder.append(k)

  def __iter__ (self):
    for k in self.keyorder:
      yield k
    return

  def keys (self):
    return self.keyorder

  def values (self):
    for k in self.keyorder:
      yield self[k]
    return

  def items (self):
    """Iterate dict's (key,value) pairs."""
    for k in self.keyorder:
      direct = self.__getitem__(k)
      if k in self.multiset:
        for mv in direct:
          yield (k, mv)
      else:
        yield (k, direct)
    return

  def get_all (self, k, defaultval):
    """Ensure get() is in list form."""
    if k in self.multiset:
      return self[k]
    elif k in self:
      return [ self[k] ]
    else:
      return defaultval

  def update_pairs (self, pairs):
    for pair in pairs:
      (k,v) = pair
      if isinstance(v,list):
        subkv = DictMultivalue()
        subkv.update_pairs(v)
        #dict.__setitem__(self, k, subkv)
        self[k] = subkv
      else:
        self[k] = v
    return self


def _parse (tokenizer, interim=None, depth=0, storetype=list):
  halt = False
  if interim is None:
    interim = []

  while not halt:
    # First token: accept scalar || end of k/v pairs.
    k = None
    token = tokenizer.next_token()
    while k is None:
      if not token:  # end of stream.
        return interim  # whatever has been built so far.
      (toktype,tokval) = token
      if toktype in (Tokenizer.TOK_UNQUOTED, Tokenizer.TOK_QUOTED):
        k = tokval
      elif toktype == Tokenizer.TOK_DENEST:
        if depth > 0:
          return interim
        else:
          return None   # error in nesting depth
      elif toktype == Tokenizer.TOK_END_OF_STREAM:
        return interim
      else:
        token = tokenizer.next_token()

    # Second: accept either a scalar, nested k/v pairs
    v = None
    token = tokenizer.next_token()
    while v is None:
      if not token:  # end of stream || unpaired key.
        raise RuntimeError("Unpaired key")
      (toktype,tokval) = token
      if toktype in (Tokenizer.TOK_QUOTED, Tokenizer.TOK_UNQUOTED):
        v = tokval
        break
      elif toktype in (Tokenizer.TOK_DENEST, Tokenizer.TOK_END_OF_STREAM):
        # unpaired key
        raise RuntimeError("Unpaired key")
      elif toktype == Tokenizer.TOK_NEST:
        v = _parse(tokenizer, None, depth+1, storetype)
        break
      else:
        token = tokenizer.next_token()

    # TODO: interpret directives here.

    if not interim:
      interim = storetype()
    try:
      interim.append((k,v))
    except AttributeError as e:
      interim[k] = v



def load (srcstream, storetype=list):
  tokenizer = StreamTokenizer(srcstream)
  return _parse(tokenizer, storetype(), storetype=storetype)

def loads (srcstream, storetype=list):
  tokenizer = StringTokenizer(srcstream)
  return _parse(tokenizer, storetype(), storetype=storetype)




def _stringlike (x):
  try:
    x.strip
    return True
  except AttributeError:
    return False

# Convert to list of strings (can be passed to ''.join() for printing).
def _toLOS (iterlop, accumulator, indent=""):
  # Head of list.
  for pair in iterlop:
    (k, v) = pair

    # Encode key part of pair.
    if not _stringlike(k):
      raise RuntimeError("Only strings may be key")
    accumulator.append(indent)
    accumulator.append('"{}"'.format(k))

    # Encode value part of pair.
    if _stringlike(v):
      # one-line k/v, separator then value
      accumulator.append("\t\t")
      accumulator.append('"{}"'.format(v))
    else:
      # formatting minutiae
      accumulator.extend(["\n", indent, "{", "\n"])
      # the nested k/v
      try:
        iv = v.items()
      except AttributeError as e:
        iv = iter(v)
      accumulator.extend(_toLOS(iv, [], "{}{}".format(indent, "\t")))
      # formatting minutiae
      accumulator.extend([indent, "}"])
    accumulator.append("\n")
  return accumulator


def dumps (store):
  """Dump list of 2-tuples in VDF format."""
  try:
    iterlop = store.items()
  except AttributeError:
    iterlop = iter(store)
  parts = _toLOS(iterlop, [])
  return ''.join(parts)

def dump (store, f):
  try:
    iterlop = store.items()
  except AttributeError:
    iterlop = iter(store)
  parts = _toLOS(iterlop, [])
  for p in parts:
    f.write(p)



if __name__ == "__main__":
  import sys, pprint
  pyobj = load(sys.stdin, list)
  pprint.pprint(pyobj)

