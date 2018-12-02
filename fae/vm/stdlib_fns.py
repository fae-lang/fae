from fae.vm.effects import Effect, IDENTITY_K
from fae.vm.values import Fn, Fexpr, from_list, kw, Keyword, kw, EMPTY


class ResetGlobals(Fn):
    def __init__(self):
        super(ResetGlobals, self).__init__()

    def _invoke(self, state, params):
        globals = params[0]
        raise Effect(globals, IDENTITY_K)

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


class GetGlobals(Fn):
    def __init__(self):
        super(GetGlobals, self).__init__()

    def _invoke(self, (globals, locals, handlers), params):
        return globals


fae_symbol_kw = kw("fae.symbol/kw")


class MakeFexpr(Fexpr):
    def __init__(self):
        super(MakeFexpr, self).__init__()

    def _invoke(self, state, params):
        from fae.vm.bootstrap.interpreter import InterpretedFexpr
        name, args, body = params

        arg_list = list(arg.get_attr(fae_symbol_kw) for arg in from_list(args))

        return InterpretedFexpr(name, arg_list, body)


class MakeFn(Fexpr):
    def __init__(self):
        super(MakeFn, self).__init__()

    def _invoke(self, state, params):
        from fae.vm.bootstrap.interpreter import InterpretedFn
        name, args, body = params

        arg_list = list(arg.get_attr(fae_symbol_kw) for arg in from_list(args))

        return InterpretedFn(name, arg_list, body)


class KeywordFn(Fn):
    def __init__(self):
        super(KeywordFn, self).__init__()

    def _invoke(self, state, params):
        ns, name = params

        assert isinstance(ns, Keyword)
        assert isinstance(name, Keyword)

        return kw(ns._name_str + u"/" + name._name_str)

class StructFn(Fn):
    def __init__(self):
        super(StructFn, self).__init__()

    def _invoke(self, state, params):
        return EMPTY.assoc(*params)

class IfFn(Fexpr):
    def __init__(self):
        super(IfFn, self).__init__()

    def _invoke(self, state, params):
        from fae.vm.bootstrap.interpreter import eval

        result = eval(state, params[0])
        if result.is_truthy():
            return eval(state, params[1])
        else:
            return eval(state, params[2])