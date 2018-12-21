#!/usr/bin/env python3
# encoding=utf-8

# VDF parser, rewritten for use in externally configuring Steam Controller.
#
# pip-installable library "vdf" left much to be desired for this use.


######################
# VDF data structure #
######################

# SCVDFDict maps keys to list of values, allowing to assign to same the key multiple times.
#
# Access by subscript yields the last value, for compatibility with dict.
# This last value may be None (for zero-length list, or using dict as set).
# The method get_all() is provided for accessing the entire list.
#
# N.B. VDF does not support a native list type, so the list type is used as a flag to trigger special handling.

class SCVDFDict (dict):
  r"""SteamController VDF
Allow multiple values per dictionary entry.

example evolution:
>>> d = SCVDFDict()             # {}
>>> d['a'] = 1                  # { "a": [1] }
>>> d['a'] = 2                  # { "a": [1,2] }
>>> d['a']                      # 2
>>> d['a'] = 3                  # { "a": [1,2,3] }
>>> d['a']                      # 3
>>> del d['a']                  # {}
>>> d['a']                      ## KeyError
>>> d['a'] = ['A', 'B', 'C' ]   # { "a": [ 'A', 'B', 'C'] }
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

Notably, VDF does not support a native list encoding, therefore a python list cannot be directly translated to VDF.
Therefore, a python list as a value indicates special handling.


VDF is the Valve KeyValue file format as used in many of their software, and Steam Client in particular.
There is nothing particularly special about VDF used by Steam Controller, but the name SCVDF was chosen to avoid conflicts with existing libraries.
"""
  def __init__ (self, src=None, **kwargs):
#    dict.__init__(self, *args, **kwargs)
    dict.__init__(self)
    self._multiset = set()
    self._keyorder = []
    self.update(src, **kwargs)

  def update (self, src=None, **kwargs):
    if src is not None:
      if _nslistlike(src):
        for k,v in src:
          self[k] = v
      elif _dictlike(src):
        for k,v in src.items():
          self[k] = v
      else:
        self[src] = None
    for k,v in kwargs.items():
      self[k] = v

  def __getitem__ (self, k):
    """Also supports tuple as keys in the form (dict_key, position:int)
1-tuple returns multivalue as list (same as get_all()), e.g. ("key0",).
"""
    if _nstuplelike(k):  # Multi-path
      primary = k[0]
      vl = self.get_all(primary)
      if len(k) == 1:
        return vl         # all instances in key.
      elif len(k) == 2:
        position = k[1]
        return vl[position]   # particular position in values.
      else:
        raise KeyError(k.__repr__())
    else:
      vl = super(SCVDFDict,self).__getitem__(k)
      if k in self._multiset:
        return vl[-1]
      else:
        return vl

  @staticmethod
  def _convert_r (x):
    if _stringlike(x) or isinstance(x, SCVDFDict):
      return x
    elif _nslistlike(x):
      if isinstance(x[0],tuple):
        return SCVDFDict(x)
      else:
        return [ SCVDFDict._convert_r(y) for y in x ]
    elif _dictlike(x):
      return SCVDFDict(x)
    else:
      return x

  def __setitem__ (self, k, v):
    v = self._convert_r(v)   # Convert nested dict into SCVDF.
    if self.__contains__(k):
      # Assigning to existing key.
      temp = super(SCVDFDict,self).__getitem__(k)
      if not k in self._multiset:
        temp = [ temp ]       # Convert to list form.
        self._multiset.add(k)
      # annex to list form.
      if _nslistlike(v):
        temp.extend(v)
      else:
        temp.append(v)
    else:
      # New dict key; prepare value.
      self._keyorder.append(k)
      temp = v
      if _nslistlike(v):
        self._multiset.add(k)   # assigned in multi form.
    super(SCVDFDict,self).__setitem__(k, temp)

  def __delitem__ (self, k):
    if k in self._multiset:
      self._multiset.remove(k)
    if k in self._keyorder:
      self._keyorder.remove(k)
    super(SCVDFDict,self).__delitem__(k)

  def __iter__ (self):
    for k in self._keyorder:
      yield k
    return

  def keys (self):
    return self._keyorder

  def values (self):
    for k in self._keyorder:
      yield self[k]
    return

  def items (self):
    # Return all pair-wise key/value as (key,value) pairs.
    for k in self._keyorder:
      vl = super(SCVDFDict,self).__getitem__(k)
      if k in self._multiset:
        for v in vl:
          yield (k,v)
      else:
        yield (k,vl)
    return

  def get (self, k, *args):
    try:
      return self[k]
    except KeyError:
      if len(args) > 0:
        return args[0]
      raise

  def get_all (self, k, *args):
    """Ensure get() is in list form."""
    try:
      if k in self._multiset:
        return super(SCVDFDict,self).__getitem__(k)  # entire list.
      else:
        return [ super(SCVDFDict,self).__getitem__(k) ]  # listify.
    except KeyError:
      if len(args) > 0:
        return args[0]
      raise

  def __repr__ (self):
    return super(SCVDFDict,self).__repr__()



def _stringlike (x):
  """String: sequence, character-aware."""
  if isinstance(x,str): return True
  try:
    return callable(x.isalpha)
  except AttributeError:
    return False

def _nssequencelike (x):
  """Non-String Sequence Like - elements are indexable by integer."""
  if _stringlike(x): return False
  try: return callable(x.index)       # indexable by integer.
  except AttributeError: return False

def _nstuplelike (x):
  """Tuple: immutable sequence, not string."""
  if isinstance(x, tuple): return True
  return _nssequencelike(x) and not _stringlike(x) and not _nslistlike(x)

def _nslistlike (x):
  """Non-String List Like: mutable sequence."""
  if isinstance(x, list): return True
  try: return _nssequencelike(x) and callable(x.append)  # mutability
  except AttributeError: return False

def _dictlike (x):
  """Dict: iterable keys."""
  if isinstance(x, dict): return True
  try: return callable(x.keys)
  except AttributeError: return False

# Convert SCVDF to dict.
def toDict (vdf):
  if _stringlike(vdf):
    return vdf  # leave string alone.

  if not _dictlike(vdf):
    if _nslistlike(vdf):
      if len(vdf) == 1:
        return toDict(vdf[0])  # remove list-sense.
      else:
        return [ toDict(x) for x in vdf ]  # maintain list-sense.
    else:
      # treat as scalar
      return vdf

  # recurse within dict.

  retval = dict()
  for k in vdf.keys():
    try:
      vl = vdf[k,]
    except KeyError:
      vl = vdf[k]
    # recursively convert values.
    retval[k] = toDict(vl)
  return retval






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


# Parser VDF into SCVDFDict (or other dict-like).
def _parse (tokenizer, interim=None, depth=0, storetype=SCVDFDict):
  halt = False
  if interim is None:
    interim = storetype()

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
    interim[k] = v


def load (srcstream, storetype=SCVDFDict):
  tokenizer = StreamTokenizer(srcstream)
  return _parse(tokenizer, storetype(), storetype=storetype)

def loads (srcstream, storetype=SCVDFDict):
  tokenizer = StringTokenizer(srcstream)
  return _parse(tokenizer, storetype(), storetype=storetype)




# Input is expected to be a list-of-pairs (SCVDFDict.items())
# Convert to list of strings (can be passed to ''.join() for printing).
def _toLOS (iterlop, accumulator=None, indent=""):
  if accumulator is None:
    accumulator = []
  # Head of list.
  for pair in iterlop:
    (k, v) = pair

    # Encode key part of pair.
    if not _stringlike(k):
      raise RuntimeError("Only strings may be key (rejected {!r})".format(k))
    accumulator.append(indent)
    accumulator.append('"{}"'.format(k))

    if type(v) == bool:
        v = '1' if v else '0'
    elif type(v) == int:
        v = str(v)

    # Encode value part of pair.
    if _stringlike(v):
      # one-line k/v, separator then value
      accumulator.append("\t\t")
      safer = v
      safer = safer.replace('"', '\\"')
      accumulator.append('"{}"'.format(safer))
    else:
      # formatting minutiae
      accumulator.extend(["\n", indent, "{", "\n"])
      # the nested k/v
      try:
        iv = v.items()
      except AttributeError as e:
        iv = iter(v)
      # Recurse, reuse current accumulator.
      _toLOS(iv, accumulator, "{}{}".format(indent, "\t"))
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
  parts = _toLOS(iterlop)
  return ''.join(parts)

def dump (store, f):
  try:
    iterlop = store.items()
  except AttributeError:
    iterlop = iter(store)
  parts = _toLOS(iterlop)
  for p in parts:
    f.write(p)




if __name__ == "__main__":
  import sys, pprint
  pyobj = load(sys.stdin, list)
  pprint.pprint(pyobj)

