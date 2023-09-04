from collections.abc import Callable, Iterable, Iterator, Mapping

from django.utils.functional import Promise


class BaseChoiceIterator:
    """Base class for lazy iterators for choices."""


class CallableChoiceIterator(BaseChoiceIterator):
    """Iterator to lazily normalize choices generated by a callable."""

    def __init__(self, func):
        self.func = func

    def __iter__(self):
        yield from normalize_choices(self.func())


def normalize_choices(value, *, depth=0):
    """Normalize choices values consistently for fields and widgets."""
    # Avoid circular import when importing django.forms.
    from django.db.models.enums import ChoicesMeta

    match value:
        case BaseChoiceIterator() | Promise() | bytes() | str():
            # Avoid prematurely normalizing iterators that should be lazy.
            # Because string-like types are iterable, return early to avoid
            # iterating over them in the guard for the Iterable case below.
            return value
        case ChoicesMeta():
            # Choices enumeration helpers already output in canonical form.
            return value.choices
        case Mapping() if depth < 2:
            value = value.items()
        case Iterator() if depth < 2:
            # Although Iterator would be handled by the Iterable case below,
            # the iterator would be consumed prematurely while checking that
            # its elements are not string-like in the guard, so we handle it
            # separately.
            pass
        case Iterable() if depth < 2 and not any(
            isinstance(x, (Promise, bytes, str)) for x in value
        ):
            # String-like types are iterable, so the guard above ensures that
            # they're handled by the default case below.
            pass
        case Callable() if depth == 0:
            # If at the top level, wrap callables to be evaluated lazily.
            return CallableChoiceIterator(value)
        case Callable() if depth < 2:
            value = value()
        case _:
            return value

    try:
        # Recursive call to convert any nested values to a list of 2-tuples.
        return [(k, normalize_choices(v, depth=depth + 1)) for k, v in value]
    except (TypeError, ValueError):
        # Return original value for the system check to raise if it has items
        # that are not iterable or not 2-tuples:
        # - TypeError: cannot unpack non-iterable <type> object
        # - ValueError: <not enough / too many> values to unpack
        return value
