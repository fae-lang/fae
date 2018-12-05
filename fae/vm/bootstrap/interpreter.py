from fae.vm.effects import Effect
from fae.vm.values import kw, Fn, Value, shape_for_attrs, Keyword, list_head, list_tail, eol, sized_size, kw, Fexpr, \
    EMPTY, symbol, to_arglist
from rpython.rlib import jit, debug

fae_stdlib_eval = kw("fae.stdlib/eval")
fae_symbol_value = kw("fae.symbol/value")
fae_keyword_value = kw("fae.keyword/value")

class Globals(Value):
    _immutable_ = True
    _shape = shape_for_attrs("Globals", {"fae.globals/value": "this"})

    def __init__(self, ns_registry=None):
        Value.__init__(self)
        #self._ns_registry = ns_registry if ns_registry else {}.setdefault({}.setdefault({}))
        self._ns_registry = ns_registry if ns_registry else {}

    def get_global(self, k):
        assert isinstance(k, Keyword)

        if k.ns_kw():
            return self._get_global(k)
            #return self._get_global(k.ns_kw(), k.name_kw())
        else:
            full_kw = kw(u"fae.stdlib/"+k.str_name()[1:])
            return self.get_global(full_kw)

    def _get_global(self, k):
        value = self._ns_registry.get(k, None)
        assert value
        return value

    def add_global(self, kw, value):
        registry = self._ns_registry.copy()
        registry[kw] = value
        return Globals(registry)


def eval((globals, locals, handlers), form):
    args = ArgList(1)
    args.set_arg(0, form)
    return globals.get_global(fae_stdlib_eval).invoke_all((globals, locals, handlers), args)


class ArgList(object):
    _virtualizable_ = ['_args[*]']

    def __init__(self, argc):
        assert isinstance(argc, int)
        self = jit.hint(self, access_directly=True, fresh_virtualizable=True)
        self._args = [None] * argc

    def arg(self, idx):
        assert 0 <= idx < len(self._args)
        return self._args[idx]

    def set_arg(self, idx, val):
        assert 0 <= idx < len(self._args)
        self._args[idx] = val

    def argc(self):
        return len(self._args)



class TailCall(Exception):
    _virtualizable = ['_args[*]', '_f', '_globals', '_handlers']

    def __init__(self, f, state, args):
        self._f = f
        self._globals, _, self._handlers = state
        self._args = args

    def state(self):
        return self._f, self._globals, self._handlers, self._args

    @staticmethod
    def resume_bare(f, globals, handlers, args):
        return f.invoke_all((globals, eol, handlers), args)


def get_location(of, f):
    if isinstance(f, InterpretedFn):
        return str(f._fn_name.str_repr())
    if isinstance(f, InterpretedFexpr):
        return str(f._fn_name.str_repr())
    else:
        return str(f.str_repr())

jitdriver = jit.JitDriver(greens=["of", "f"], reds=["globals", 'handlers', "args"], virtualizables=["args"], get_printable_location=get_location)


def eval_notail(state, form):
    try:
        result = eval(state, form)
    except TailCall as tc:
        f, globals, handlers, args = tc.state()
        of = f
        while True:
            jitdriver.jit_merge_point(of=of, f=f, globals=globals, handlers=handlers, args=args)
            try:
                result = TailCall.resume_bare(f, globals, handlers, args)
                break
            except TailCall as ex:
                f, globals, handlers, args = ex.state()
                if f is of:
                    jitdriver.can_enter_jit(of=of, f=f, globals=globals, handlers=handlers, args=args)

    return result




locals_sym = kw("fae.locals/symbol")
locals_val = kw("fae.locals/value")
fae_symbol_kw = kw("fae.symbol/kw")

class EvalInner(Fn):
    _immutable_ = True

    def __init__(self):
        Fn.__init__(self)

    def _invoke(self, (globals, locals, handlers), params):
        form = params.arg(0)

        argc = params.argc()
        if argc >= 2:
            locals = params.arg(1)

        if argc >= 3:
            globals = params.arg(2)

        if argc >= 4:
            handlers = params.arg(3)

        state = (globals, locals, handlers)

        if form.has_attr(fae_symbol_value):
            return self.lookup_symbol(state, form.get_attr(fae_symbol_kw))
        elif form.has_attr(fae_keyword_value):
            return form
        elif form.has_attr(list_head):
            return self._eval_list(state, form)
        else:
            return form

    @jit.unroll_safe
    def lookup_symbol(self, (globals, locals, handlers), sym):
        while locals.has_attr(locals_sym):
            if locals.get_attr(locals_sym) is sym:
                return locals.get_attr(locals_val)
            locals = locals.get_attr(list_tail)

        result = globals.get_global(sym)

        assert result

        return result

    @jit.unroll_safe
    def _eval_list(self, state, form):
        idx = 0
        fn = eval_notail(state, form.get_attr(list_head))
        form = form.get_attr(list_tail)

        if isinstance(fn, Fexpr):
            return fn.invoke_all(state, to_arglist(form))

        if form.is_truthy():
            results = ArgList(form.get_attr(sized_size).unwrap_int())
        else:
            results = ArgList(0)

        while form.is_truthy():
            eform = form.get_attr(list_head)
            result = eval_notail(state, eform)
            assert result, "Bad Result " + str(result)
            results.set_arg(idx, result)
            form = form.get_attr(list_tail)
            idx += 1

        raise TailCall(fn, state, results)




class InterpretedFexpr(Fexpr):
    _immutable_ = True

    globals_sym = kw("*globals*")
    locals_sym = kw("*locals*")
    handlers_sym = kw("*handlers*")

    def __init__(self, name, args, body):
        Fexpr.__init__(self)
        self._fn_name = name
        self._fn_args = args
        self._fn_body = body

    @jit.unroll_safe
    def _invoke(self, (globals, locals, handlers), params):
        new_l = add_local(eol, InterpretedFexpr.globals_sym, globals)
        new_l = add_local(new_l, InterpretedFexpr.handlers_sym, handlers)
        new_l = add_local(new_l, InterpretedFexpr.locals_sym, locals)

        for idx in range(params.argc()):
            new_l = add_local(new_l, self._fn_args[idx], params.arg(idx))
        return eval((globals, new_l, handlers), self._fn_body)


def add_local(prev, sym, val):
    return EMPTY.assoc(list_tail, prev,
                         locals_sym, sym,
                         locals_val, val)


class InterpretedFn(Fn):
    _immutable_ = True

    def __init__(self, name, args, body):
        Fn.__init__(self)
        self._fn_name = name
        self._fn_args = args
        self._fn_body = body

    @jit.unroll_safe
    def _invoke(self, (globals, locals, handlers), params):
        locals = eol
        for idx in range(len(self._fn_args)):
            locals = EMPTY.assoc(list_tail, locals,
                                 locals_sym, self._fn_args[idx],
                                 locals_val, params.arg(idx))

        return eval((globals, locals, handlers), self._fn_body)



class Evaluator(object):
    _immutable_ = True

    def __init__(self):
        self._globals = default_globals

    def top_eval(self, form):
        try:
            return eval_notail((self._globals, eol, None), form)
        except Effect as eff:
            while True:
                assert isinstance(eff._value, Globals)
                self._globals = eff._value

                try:
                    return eff._k.continuation((self._globals, None), self._globals)
                except Effect as eff:
                    continue

    def add_global(self, k, v):
        self._globals = self._globals.add_global(kw(k), v)
        return self


import fae.vm.stdlib_fns as stdlib_fns

default_globals = Globals({}).add_global(fae_stdlib_eval, EvalInner())

for k, v in stdlib_fns.fn_registry.items():
    default_globals = default_globals.add_global(k, getattr(stdlib_fns, v)())
