import sys

import fae.vm.bootstrap.reader as reader
from fae.vm.bootstrap.interpreter import Evaluator
from fae.vm.values import Integer


def read_bootstrap():
    global parsed

    with open("fae/stdlib.fae") as stdlib:
        stdlib_str = stdlib.read()


    parsed = reader.read_from_string(stdlib_str)


def bootstrap(input):
    e = Evaluator().add_global("fae.stdlib/*input*", Integer(input))
    for form in parsed:
        print(u"Eval:" + form.str_repr())
        print(u"Result: " + e.top_eval(form).str_repr())


def main(argv):
    if len(argv) == 2:
        input = int(argv[1])
    else:
        input = 10000
    bootstrap(input)

    return 42


def target(driver, args):
    driver.exe_name = 'fae-%(backend)s'
    return main, None

read_bootstrap()
if __name__ == "__main__":
    main(sys.argv)

