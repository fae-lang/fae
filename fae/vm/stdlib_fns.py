from fae.vm.effects import Effect, IDENTITY_K
from fae.vm.values import Fn, Fexpr, from_list, kw, Keyword, kw, EMPTY, Integer

fn_registry = {}

def register(nm):
    def inner(cls):
        fn_registry[kw(u"fae.stdlib/" + unicode(nm))] = cls.__name__
        return cls
    return inner


@register("reset-globals")
class ResetGlobals(Fn):
    def __init__(self):
        super(ResetGlobals, self).__init__()

    def _invoke(self, state, params):
        globals = params[0]
        raise Effect(globals, IDENTITY_K)


@register("assoc-globals")
class AssocGlobals(Fn):
    def __init__(self):
        super(AssocGlobals, self).__init__()

    def _invoke(self, state, params):
        globals = params[0]

        from fae.vm.bootstrap.interpreter import Globals
        assert isinstance(globals, Globals)
        for idx in range(1, len(params), 2):
            globals = globals.add_global(params[idx], params[idx + 1])

        return globals


@register("get-globals")
class GetGlobals(Fn):
    def __init__(self):
        super(GetGlobals, self).__init__()

    def _invoke(self, (globals, locals, handlers), params):
        return globals


fae_symbol_kw = kw("fae.symbol/kw")


@register("fexpr")
class MakeFexpr(Fexpr):
    def __init__(self):
        super(MakeFexpr, self).__init__()

    def _invoke(self, state, params):
        from fae.vm.bootstrap.interpreter import InterpretedFexpr
        name, args, body = params

        arg_list = list(arg.get_attr(fae_symbol_kw) for arg in from_list(args))

        return InterpretedFexpr(name, arg_list, body)


@register("fn")
class MakeFn(Fexpr):
    def __init__(self):
        super(MakeFn, self).__init__()

    def _invoke(self, state, params):
        from fae.vm.bootstrap.interpreter import InterpretedFn
        name, args, body = params

        arg_list = list(arg.get_attr(fae_symbol_kw) for arg in from_list(args))

        return InterpretedFn(name, arg_list, body)


@register("keyword")
class KeywordFn(Fn):
    def __init__(self):
        super(KeywordFn, self).__init__()

    def _invoke(self, state, params):
        ns, name = params

        assert isinstance(ns, Keyword)
        assert isinstance(name, Keyword)

        return kw(ns._name_str + u"/" + name._name_str)


@register("struct")
class StructFn(Fn):
    def __init__(self):
        super(StructFn, self).__init__()

    def _invoke(self, state, params):
        return EMPTY.assoc(*params)


@register("if")
class IfFn(Fexpr):
    def __init__(self):
        super(IfFn, self).__init__()

    def _invoke(self, state, params):
        from fae.vm.bootstrap.interpreter import eval, eval_notail

        result = eval_notail(state, params[0])
        if result.is_truthy():
            return eval(state, params[1])
        else:
            return eval(state, params[2])


@register("int<")
class IntLessThan(Fn):
    kw_less_than = kw("fae.int.compare/less-than")
    kw_not_less_than = kw("fae.int.compare/!less-than")

    def __init__(self):
        super(IntLessThan, self).__init__()

    def _invoke(self, state, params):
        if params[0].unwrap_int() < params[1].unwrap_int():
            return IntLessThan.kw_less_than
        else:
            return IntLessThan.kw_not_less_than


@register("int+")
class IntAdd(Fn):
    def __init__(self):
        super(IntAdd, self).__init__()

    def _invoke(self, state, params):
        return Integer(params[0].unwrap_int() + params[1].unwrap_int())

