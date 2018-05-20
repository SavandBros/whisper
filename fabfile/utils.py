from fabric.colors import green
from functools import wraps


def grintify(method):
    """
    Take the docstring from the method and print-out with green font with
        help of grint().
    """
    @wraps(method)
    def wrapped_method(*args, **kwrags):
        grint("------> {0}".format(method.__doc__.strip()))
        return method(*args, **kwrags)

    return wrapped_method


def grint(msg, level=1):
    """Print in bold green."""
    if level == 2:
        msg = "------------> {0}".format(msg)

    print(green(msg, True))
