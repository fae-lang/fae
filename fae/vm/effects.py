

class Effect(Exception):
    def __init__(self, value, k):
        self._value = value
        self._k = k


class IContinuation(object):
    def __init__(self):
        pass

    def continuation(self, (globals, handlers), value):
        pass


class IdentityK(IContinuation):
    def __init__(self):
        IContinuation.__init__(self)

    def continuation(self, (globals, handlers), value):
        return value

IDENTITY_K = IdentityK()