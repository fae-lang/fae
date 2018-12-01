from fae.vm.effects import Effect
from fae.vm.stdlib_fns import ResetGlobals, AssocGlobals, GetGlobals, MakeFexpr, MakeFn
from fae.vm.values import kw, Fn, Value, shape_for_attrs, Keyword, list_head, list_tail, eol, sized_size, attr, Fexpr, \
    from_list, EMPTY

fae_stdlib_eval = kw("fae.stdlib/eval")
fae_symbol_value = attr("fae.symbol/value")
fae_keyword_value = attr("fae.keyword/value")

class Globals(Value):
    _shape = shape_for_attrs("Globals", {"fae.globals/value": "this"})

    def __init__(self, ns_registry=None):
        super(Globals, self).__init__()
        #self._ns_registry = ns_registry if ns_registry else {}.setdefault({}.setdefault({}))
        self._ns_registry = ns_registry if ns_registry else {}

    def get_global(self, k):
        assert isinstance(k, Keyword)

        if k.ns_kw():
            return self._get_global(k)
            #return self._get_global(k.ns_kw(), k.name_kw())
        else:
            full_kw = kw("fae.stdlib/"+str(k)[1:])
            return self.get_global(full_kw)

    def _get_global(self, k):
        value = self._ns_registry.get(k, None)
        assert value
        return value

        # namespace = self._ns_registry.get(ns, None)
        # if namespace is None:
        #     return None
        #
        # return namespace.get(name, None)

    def add_global(self, kw, value):
        registry = self._ns_registry.copy()
        registry[kw] = value
        return Globals(registry)
        # assert kw.ns_kw()
        # cloned = self._ns_registry.copy()
        # ns = cloned[kw.ns_kw()].copy()
        # ns[kw.name_kw()] = value
        # cloned[kw.ns_kw()] = ns
        # return Globals(cloned)


def eval((globals, locals, handlers), form):
    return globals.get_global(fae_stdlib_eval).invoke((globals, locals, handlers), form)


locals_sym = kw("fae.locals/symbol")
locals_val = kw("fae.locals/value")
fae_symbol_kw = attr("fae.symbol/kw")

class EvalInner(Fn):
    def __init__(self):
        super(EvalInner, self).__init__()

    def _invoke(self, state, params):
        form = params[0]

        if form.has_attr(fae_symbol_value):
            return self.lookup_symbol(state, form.get_attr(fae_symbol_kw))
        elif form.has_attr(fae_keyword_value):
            return form
        elif form.has_attr(list_head):
            return self._eval_list(state, form)

    def lookup_symbol(self, (globals, locals, handlers), sym):
        while locals.has_attr(locals_sym):
            if locals.get_attr(locals_sym) is sym:
                return locals.get_attr(locals_val)
            locals = locals.get_attr(list_tail)

        result = globals.get_global(sym)

        assert result

        return result

    def _eval_list(self, state, form):
        idx = 0
        fn = eval(state, form.get_attr(list_head))
        form = form.get_attr(list_tail)

        if isinstance(fn, Fexpr):
            return fn.invoke(state, *from_list(form))

        if form.is_truthy():
            results = [None] * (form.get_attr(sized_size).unwrap_int())
        else:
            results = []

        while form.is_truthy():
            result = eval(state, form.get_attr(list_head))
            assert result
            results[idx] = result
            form = form.get_attr(list_tail)
            idx += 1

        return fn.invoke(state, *results)




class InterpretedFexpr(Fexpr):
    _immutable_ = True

    def __init__(self, name, args, body):
        super(InterpretedFexpr, self).__init__()
        self._fn_name = name
        self._fn_args = args
        self._fn_body = body

    def _invoke(self, (globals, locals, handlers), params):
        locals = eol
        for idx in range(len(self._fn_args)):
            locals = EMPTY.assoc(list_tail, locals,
                                 locals_sym, self._fn_args[idx],
                                 locals_val, params[idx])

        return eval((globals, locals, handlers), self._fn_body)


class InterpretedFn(Fn):
    _immutable_ = True

    def __init__(self, name, args, body):
        super(InterpretedFn, self).__init__()
        self._fn_name = name
        self._fn_args = args
        self._fn_body = body

    def _invoke(self, (globals, locals, handlers), params):
        locals = eol
        for idx in range(len(self._fn_args)):
            locals = EMPTY.assoc(list_tail, locals,
                                 locals_sym, self._fn_args[idx],
                                 locals_val, params[idx])

        return eval((globals, locals, handlers), self._fn_body)



class Evaluator(object):
    def __init__(self):
        self._globals = default_globals

    def top_eval(self, form):
        try:
            return eval((self._globals, eol, None), form)
        except Effect as eff:
            while True:
                assert isinstance(eff._value, Globals)
                self._globals = eff._value

                try:
                    return eff._k.continuation((self._globals, None), self._globals)
                except Effect as eff:
                    continue





default_globals = Globals({}) \
                  .add_global(fae_stdlib_eval, EvalInner()) \
                  .add_global(kw("fae.stdlib/reset-globals"), ResetGlobals()) \
                  .add_global(kw("fae.stdlib/assoc-globals"), AssocGlobals()) \
                  .add_global(kw("fae.stdlib/get-globals"), GetGlobals()) \
                  .add_global(kw("fae.stdlib/fexpr"), MakeFexpr()) \
                  .add_global(kw("fae.stdlib/fn"), MakeFn())