import copy

from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator, MinLengthValidator
from django.utils.deconstruct import deconstructible
from django.utils.translation import ungettext_lazy, ugettext_lazy as _


class ArrayMaxLengthValidator(MaxLengthValidator):
    message = ungettext_lazy(
        'List contains %(show_value)d item, it should contain no more than %(limit_value)d.',
        'List contains %(show_value)d items, it should contain no more than %(limit_value)d.',
        'limit_value')


class ArrayMinLengthValidator(MinLengthValidator):
    message = ungettext_lazy(
        'List contains %(show_value)d item, it should contain no fewer than %(limit_value)d.',
        'List contains %(show_value)d items, it should contain no fewer than %(limit_value)d.',
        'limit_value')


@deconstructible
class KeysValidator(object):
    """A validator designed for HStore to require/restrict keys."""

    messages = {
        'missing_keys': _('Some keys were missing: %(keys)s'),
        'extra_keys': _('Some unknown keys were provided: %(keys)s'),
    }
    strict = False

    def __init__(self, keys, strict=False, messages=None):
        self.keys = set(keys)
        self.strict = strict
        if messages is not None:
            self.messages = copy.copy(self.messages)
            self.messages.update(messages)

    def __call__(self, value):
        keys = set(value.keys())
        missing_keys = self.keys - keys
        if missing_keys:
            raise ValidationError(self.messages['missing_keys'],
                code='missing_keys',
                params={'keys': ', '.join(missing_keys)},
            )
        if self.strict:
            extra_keys = keys - self.keys
            if extra_keys:
                raise ValidationError(self.messages['extra_keys'],
                    code='extra_keys',
                    params={'keys': ', '.join(extra_keys)},
                )

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__)
            and (self.keys == other.keys)
            and (self.messages == other.messages)
            and (self.strict == other.strict)
        )

    def __ne__(self, other):
        return not (self == other)
