import abc

from rpython.rlib.objectmodel import not_rpython, specialize
from rpython.tool.sourcetools import compile_template
from rpython.rlib.unroll import unrolling_iterable

def skipping_iterator(i, skip_first=False):
    i = iter(i)
    if skip_first:
        i.next()

    while True:
        yield i.next()
        i.next()

class Value(object):
    _immutable_ = True

    def __init__(self):
        pass

    def get_attr(self, k, not_found=None):
        getter = self.get_shape().getter_for(k)
        if getter is None:
            return not_found
        return getter.get_value(self)

    def has_attr(self, k):
        return self.get_shape().getter_for(k) is not None;

    @abc.abstractmethod
    def get_shape(self):
        """Return a Shape object that defines the attributes supported on this instance.
        Note: Shapes are not RPython type specific, the same RPython type can return different
        shapes for different instances."""
        return

    def is_truthy(self):
        return not self.has_attr(fae_conditional_else)

    def invoke(self, state, *args):
        return self._invoke(state, list(args))


    @specialize.call_location()
    def assoc(self, *kws):
        #keys = list(unrolling_iterable(skipping_iterator(kws)))
        #vals = list(unrolling_iterable(skipping_iterator(kws, True)))

        #ctor = self.get_shape().with_keys(keys)

        new_dict = {}
        shape = self.get_shape()

        for k in shape.attr_list():
            new_dict[k] = shape.getter_for(k).get_value(self)

        for idx in range(0, len(kws), 2):
            new_dict[kws[idx]] = kws[idx + 1]

        return DictStruct(new_dict)

    def __str__(self):
        return self.__repr__()

    def _invoke(self, state, params):
        pass


class Shape(object):
    def __init__(self):
        pass

    def getter_for(self, kw):
        pass

class Getter(object):
    def __init__(self):
        pass

    def get_value(self, inst):
        pass


class DictStruct(Value):
    def __init__(self, kvs):
        super(DictStruct, self).__init__()
        self._shape = DictShape(kvs)

    def get_shape(self):
        return self._shape

    def __repr__(self):
        if self.has_attr(list_head):
            acc = []
            head = self
            while head.has_attr(list_head):
                acc.append(str(head.get_attr(list_head)))
                head = head.get_attr(list_tail, eol)

            return u"(" +  u" ".join(acc) + u")"

        return u"{" + u",".join(str(k) + u" " + str(v) for k, v in self._shape._kvs.items()) + u"}"


class DictGetter(Getter):
    def __init__(self, k):
        super(DictGetter, self).__init__()
        self._k = k

    def get_value(self, inst):
        assert isinstance(inst, DictStruct)
        return inst._shape._kvs[self._k]


class DictShape(Shape):
    def __init__(self, kvs):
        super(DictShape, self).__init__()
        self._kvs = kvs

    def getter_for(self, k):
        if k in self._kvs:
            return DictGetter(k)
        else:
            return None

    def attr_list(self):
        return list(self._kvs)


def make_getter(klass, kw, attr):
    if attr == "this":
        template = """
        class {klass}{kw}Getter(Getter):
            def __init__(self):
                super(Getter, self).__init__()

            def get_value(self, inst):
                assert isinstance(inst, {klass})
                return inst
        """.format(klass=klass, kw=kw.py_name(), attr=attr)
    else:
        template = """
        class {klass}{kw}Getter(Getter):
            def __init__(self):
                super(Getter, self).__init__()

            def get_value(self, inst):
                assert isinstance(inst, {klass})
                return inst.{attr}
        """.format(klass=klass, kw=kw.py_name(), attr=attr)
    name = "{klass}{kw}Getter".format(klass=klass, kw=kw.py_name())
    print template
    globals()[name] = compile_template(template, name)
    return globals()[name]()


class GenericShape(Shape):
    def __init__(self, attr_map):
        super(GenericShape, self).__init__()
        self._attr_map = attr_map

    def attr_list(self):
        return list(self._attr_map.keys())

    def getter_for(self, kw):
        return self._attr_map.get(kw, None)



@not_rpython
def shape_for_attrs(klass, kw_map):
    getters = {attr(k): make_getter(klass, attr(k), v) for k, v in kw_map.items()}

    return GenericShape(getters)


class Keyword(Value):
    _immutable_ = True

    def __init__(self, ns, name, str_name, is_attr=False):
        super(Keyword, self).__init__()
        self._ns_str = ns
        self._name_str = name
        self._str_name = str_name
        self._is_attr = is_attr
        self._is_falsey = name.startswith(u"!")

        if ns:
            self._ns_kw = kw(ns)
            self._name_kw = kw(name)
        else:
            self._ns_kw = ns
            self._name_kw = self

    def get_shape(self):
        if self._is_attr:
            return Keyword._attr_shape
        else:
            if self._is_falsey:
                return Keyword._falsey_shape
            else:
                return Keyword._truthy_shape

    @not_rpython
    def py_name(self):
        return self._str_name.replace('.', '_').replace('/', '_')

    def str_name(self):
        return self._str_name

    def __repr__(self):
        return self._str_name

    def ns_kw(self):
        return self._ns_kw

    def name_kw(self):
        return self._name_kw




class KeywordRegistry(object):
    def __init__(self, is_attr_registry):
        self._registry = {}
        self._is_attr_registry = is_attr_registry

    def intern(self, full_name):
        if isinstance(full_name, str):
            full_name = unicode(full_name)

        result = self._registry.get(full_name, None)
        if result is not None:
            return result

        offset = full_name.find(u"/")
        if offset == -1 or offset == len(full_name) - 1:
            name = full_name
            ns = None
        else:
            name = full_name[offset + 1:]
            ns = full_name[:offset]

        str_name = (u"." if self._is_attr_registry else u":") + full_name

        found = self._registry.get(str_name, None)
        if found is not None:
            self._registry[full_name] = found
            return found

        found = Keyword(ns, name, str_name, self._is_attr_registry)
        self._registry[str_name] = found
        self._registry[full_name] = found

        return found

attr_registry = KeywordRegistry(True)
keyword_registry = KeywordRegistry(False)

def kw(s):
    return keyword_registry.intern(s)

def attr(s):
    return attr_registry.intern(s)


class Symbol(Value):
    _immutable_ = True
    _shape = shape_for_attrs("Symbol", {"fae.symbol/value": "this",
                                        "fae.symbol/kw": "_kw"})

    def __init__(self, kw):
        super(Symbol, self).__init__()
        self._kw = kw

    def __repr__(self):
        return str(self._kw)[1:]

    def get_shape(self):
        return self._shape


def symbol(s):
    if isinstance(s, str):
        s = unicode(s)

    return Symbol(keyword_registry.intern(s))

class EmptyStruct(Value):
    _shape = shape_for_attrs("EmptyStruct", {})

    def __init__(self):
        super(EmptyStruct, self).__init__()

    def get_shape(self):
        return EmptyStruct._shape



Keyword._attr_shape = shape_for_attrs("Keyword", {"fae.attr/value": "this"})
Keyword._truthy_shape = shape_for_attrs("Keyword", {"fae.keyword/value": "this"})
Keyword._falsey_shape = shape_for_attrs("Keyword", {"fae.keyword/value": "this", "fae.conditional/else": "_else_kw"})
Keyword._else_kw = kw("fae.conditional/else")

fae_conditional_else = attr("fae.conditional/else")

eol = kw(u"fae.list/!end-of-list")

EMPTY = DictStruct({})

list_head = kw("fae.list/head")
list_tail = kw("fae.list/tail")
sized_size = kw("fae.sized/size")

def to_list(lst):
    "Creates a Fae list from a python list, expects the arguments to be already wrapped"
    assert isinstance(lst, list)

    acc = eol
    count = 1
    for idx in range(len(lst) - 1, -1, -1):
        acc = EMPTY.assoc(list_head, lst[idx],
                          list_tail, acc,
                          sized_size, Integer(count))
        count += 1
    return acc

def from_list(lst):

    acc = []

    while lst.has_attr(list_head):
        acc.append(lst.get_attr(list_head))
        lst = lst.get_attr(list_tail, eol)

    return acc


class Integer(Value):
    _shape = shape_for_attrs("Integer", {"fae.integer/value": "this"})

    def __init__(self, i_val):
        super(Integer, self).__init__()
        self._i_val = i_val

    def get_shape(self):
        return Integer._shape

    def unwrap_int(self):
        return self._i_val


class Fn(Value):
    _shape = shape_for_attrs("Fn", {"fae.fn/value": "this"})

    def __init__(self):
        super(Fn, self).__init__()

    def get_shape(self):
        return Fn._shape


class Fexpr(Value):
    _shape = shape_for_attrs("Fexpr", {"fae.fexpr/value": "this"})

    def __init__(self):
        super(Fexpr, self).__init__()

    def get_shape(self):
        return Fexpr._shape

