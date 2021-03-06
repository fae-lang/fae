from fae.vm.effects import Effect, IDENTITY_K
from fae.vm.values import Fn, Fexpr, kw, Keyword, kw, EMPTY, Integer, from_list
from rpython.rlib import jit

fn_registry = {}

def register(nm):
    def inner(cls):
        fn_registry[kw(u"fae.stdlib/" + unicode(nm))] = cls.__name__
        return cls
    return inner


@register("reset-globals")
class ResetGlobals(Fn):
    _immutable_ = True

    def __init__(self):
        Fn.__init__(self)

    def _invoke(self, state, params):
        globals = params.arg(0)
        raise Effect(globals, IDENTITY_K)


@register("assoc-globals")
class AssocGlobals(Fn):
    _immutable_ = True

    def __init__(self):
        Fn.__init__(self)

    @jit.unroll_safe
    def _invoke(self, state, params):
        globals = params.arg(0)

        from fae.vm.bootstrap.interpreter import Globals
        assert isinstance(globals, Globals)
        for idx in range(1, params.argc(), 2):
            globals = globals.add_global(params.arg(idx), params.arg(idx + 1))

        return globals


@register("get-globals")
class GetGlobals(Fn):
    _immutable_ = True

    def __init__(self):
        Fn.__init__(self)

    def _invoke(self, (globals, locals, handlers), params):
        return globals


fae_symbol_kw = kw("fae.symbol/kw")


@register("fexpr")
class MakeFexpr(Fexpr):
    _immutable_ = True

    def __init__(self):
        Fexpr.__init__(self)

    def _invoke(self, state, params):
        from fae.vm.bootstrap.interpreter import InterpretedFexpr
        name = params.arg(0)
        args = params.arg(1)
        body = params.arg(2)

        arg_list = []
        for arg in from_list(args):
            arg_list.append(arg.get_attr(fae_symbol_kw))

        return InterpretedFexpr(name, arg_list, body)


@register("fn")
class MakeFn(Fexpr):
    _immutable_ = True

    def __init__(self):
        Fexpr.__init__(self)

    def _invoke(self, state, params):
        from fae.vm.bootstrap.interpreter import InterpretedFn
        name = params.arg(0)
        args = params.arg(1)
        body = params.arg(2)

        arg_list = []

        for arg in from_list(args):
            arg_list.append(arg.get_attr(fae_symbol_kw))

        return InterpretedFn(name, arg_list, body)


@register("keyword")
class KeywordFn(Fn):
    _immutable_ = True

    def __init__(self):
        Fn.__init__(self)

    def _invoke(self, state, params):
        ns = params.arg(0)
        name = params.arg(1)

        assert isinstance(ns, Keyword)
        assert isinstance(name, Keyword)

        return kw(ns._name_str + u"/" + name._name_str)


@register("struct")
class StructFn(Fn):
    _immutable_ = True

    def __init__(self):
        Fn.__init__(self)

    def _invoke(self, state, params):
        return EMPTY.assoc_all(params)


@register("if")
class IfFn(Fexpr):
    _immutable_ = True

    def __init__(self):
        Fexpr.__init__(self)

    def _invoke(self, state, params):
        from fae.vm.bootstrap.interpreter import eval, eval_notail

        result = eval_notail(state, params.arg(0))
        if result.is_truthy():
            return eval(state, params.arg(1))
        else:
            return eval(state, params.arg(2))


@register("int<")
class IntLessThan(Fn):
    _immutable_ = True

    kw_less_than = kw("fae.int.compare/less-than")
    kw_not_less_than = kw("fae.int.compare/!less-than")

    def __init__(self):
        Fn.__init__(self)

    def _invoke(self, state, params):
        if params.arg(0).unwrap_int() < params.arg(1).unwrap_int():
            return IntLessThan.kw_less_than
        else:
            return IntLessThan.kw_not_less_than


@register("int+")
class IntAdd(Fn):
    _immutable_ = True

    def __init__(self):
        Fn.__init__(self)

    def _invoke(self, state, params):
        return Integer(params.arg(0).unwrap_int() + params.arg(1).unwrap_int())

