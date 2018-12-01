
# Pure Python (Not RPython) reader to be used only during bootstrap. After Fae has been started, all the
# reader functions will be replaced with pure Fae versions.

from lark import Lark, Transformer

import fae.vm.values as values

parser = Lark("""

  ?values: value*
  ?value: list
       | vector
       | STRING -> string
       | NUMBER -> number
       | KEYWORD -> keyword
       | SYMBOL -> symbol
       | quoted
       | "true" | "false"

  list: "(" value* ")"
  vector: "[" value* "]"
  NUMBER: SIGNED_NUMBER
  STRING: ESCAPED_STRING
  KEYWORD: ":" SYMBOL
  quoted: "'" value
  SYMBOL: /[a-zA-Z\*\.\!][a-zA-Z0-9\_\-\+\|\/\*\.\!]*/

  %import common.ESCAPED_STRING
  %import common.SIGNED_NUMBER
  %import common.WS
  %ignore WS

""", start="values")

class ToLisp(Transformer):

    def value(self, (itm, )):
        return itm

    def values(self, itms):
        return itms

    def string(self, (s, )):
        return values.W_String(unicode(s[1:-1]))

    def number(self, (n, )):
        return values.Integer(int(n))

    def keyword(self, (s, )):
        print("KEYWORD", s)
        return values.kw(str(s)[1:])

    def symbol(self, (s, )):
        print("SYMBOL ", s)
        return values.symbol(str(s))

    def list(self, itms):
        print("LIST", itms)
        return values.to_list(itms)

    def vector(self, itms):
        print("VECTOR", itms)
        return values.to_list(itms)

    def quoted(self, (val, )):
        return base.from_list([ToLisp.vm_quote, val])


def read_from_string(s):
    p = parser.parse(s)
    print(p)
    return ToLisp().transform(p)