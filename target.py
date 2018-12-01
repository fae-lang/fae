
import fae.vm.bootstrap.reader as reader
from fae.vm.bootstrap.interpreter import Evaluator


def bootstrap():
    with open("fae/stdlib.fae") as stdlib:
        stdlib_str = stdlib.read()

    e = Evaluator()

    parsed = reader.read_from_string(stdlib_str)
    for form in parsed:
        print("NEXT")
        e.top_eval(form)

def main():
    bootstrap()

if __name__ == "__main__":
    main()

