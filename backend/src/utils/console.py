import warnings
import functools

CONSOLE_STYLE = {
    "ERROR": "\033[91m",
    "SECONDARY_ERROR": "\033[31m",
    "WARNING": "\033[93m",
    "SECONDARY_WARNING": "\033[33m",
    "SUCCESS": "\033[92m",
    "SECONDARY_SUCCESS": "\033[32m",
    "INFO": "\033[94m",
    "SECONDARY_INFO": "\033[96m",
    "END": "\033[0m",
    None: ""
}

class Style:
    """
    A class to represent a styled console message.
    """

    def __init__(self, style, message, auto_break=False, max_length=None):
        if style not in CONSOLE_STYLE:
            raise ValueError(f"Invalid style: {style}, must be one of:\n{CONSOLE_STYLE.keys()}")
        self.style = style

        if auto_break and max_length is not None:
            self.message = ""
            last_space = -1

            idx = 0
            for char in message:
                if idx % max_length == 0:
                    if last_space != -1:
                        cutted = self.message[idx:]
                        self.message = self.message[:idx]
                        self.message += "\n" + cutted.strip()
                        idx += 1 + len(cutted.strip()) - len(cutted)
                        char = char.strip()
                        last_space = -1
                    else:
                        self.message += "\n"
                        idx += 1
                
                
                if char in [" ", "\n", ""]:
                    last_space = idx

                self.message += char
                idx += len(char)
        
        elif auto_break:
            raise ValueError("If auto_break is True, max_length must be specified.")
        
        else:
            self.message = str(message)


    def __repr__(self):
        if self.style is None:
            return self.message
        return f"{CONSOLE_STYLE[self.style]}{self.message}{CONSOLE_STYLE['END']}"
    
    def __str__(self):
        return self.__repr__()
    
    def __add__(self, other):
        return self.__repr__() + str(other)
    
class deprecated:
    """Decorator to mark a function or class as deprecated.

    Issue a warning when the function is called/the class is instantiated and
    adds a warning to the docstring.

    The optional extra argument will be appended to the deprecation message
    and the docstring. Note: to use this with the default value for extra, put
    in an empty of parentheses:

    >>> from sklearn.utils import deprecated
    >>> deprecated()
    <sklearn.utils.deprecation.deprecated object at ...>

    >>> @deprecated()
    ... def some_function(): pass

    Parameters
    ----------
    extra : str, default=''
          To be added to the deprecation messages.
    """

    # Adapted from https://wiki.python.org/moin/PythonDecoratorLibrary,
    # but with many changes.

    def __init__(self, extra=""):
        self.extra = extra

    def __call__(self, obj):
        """Call method

        Parameters
        ----------
        obj : object
        """
        if isinstance(obj, type):
            return self._decorate_class(obj)
        elif isinstance(obj, property):
            # Note that this is only triggered properly if the `property`
            # decorator comes before the `deprecated` decorator, like so:
            #
            # @deprecated(msg)
            # @property
            # def deprecated_attribute_(self):
            #     ...
            return self._decorate_property(obj)
        else:
            return self._decorate_fun(obj)

    def _decorate_class(self, cls):
        msg = "Class %s is deprecated" % cls.__name__
        if self.extra:
            msg += "; %s" % self.extra

        msg = Style("WARNING", msg).__str__()

        # FIXME: we should probably reset __new__ for full generality
        init = cls.__init__

        def wrapped(*args, **kwargs):
            warnings.warn(msg, category=FutureWarning, stacklevel=2)
            return init(*args, **kwargs)

        cls.__init__ = wrapped

        wrapped.__name__ = "__init__"
        wrapped.__doc__ = self._update_doc(init.__doc__)
        wrapped.deprecated_original = init

        return cls

    def _decorate_fun(self, fun):
        """Decorate function fun"""

        msg = "Function %s is deprecated" % fun.__name__
        if self.extra:
            msg += "; %s" % self.extra

        msg = Style("WARNING", msg).__str__()

        @functools.wraps(fun)
        def wrapped(*args, **kwargs):
            warnings.warn(msg, category=FutureWarning, stacklevel=2)
            return fun(*args, **kwargs)

        wrapped.__doc__ = self._update_doc(wrapped.__doc__)
        # Add a reference to the wrapped function so that we can introspect
        # on function arguments in Python 2 (already works in Python 3)
        wrapped.__wrapped__ = fun

        return wrapped

    def _decorate_property(self, prop):
        msg = self.extra

        @property
        @functools.wraps(prop)
        def wrapped(*args, **kwargs):
            warnings.warn(msg, category=FutureWarning)
            return prop.fget(*args, **kwargs)

        wrapped.__doc__ = self._update_doc(wrapped.__doc__)

        return wrapped

    def _update_doc(self, olddoc):
        newdoc = "DEPRECATED"
        if self.extra:
            newdoc = "%s: %s" % (newdoc, self.extra)
        if olddoc:
            newdoc = "%s\n\n    %s" % (newdoc, olddoc)
        return newdoc


def _is_deprecated(func):
    """Helper to check if func is wrapped by our deprecated decorator"""
    closures = getattr(func, "__closure__", [])
    if closures is None:
        closures = []
    is_deprecated = "deprecated" in "".join(
        [c.cell_contents for c in closures if isinstance(c.cell_contents, str)]
    )
    return is_deprecated
