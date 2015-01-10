from django.core import exceptions
from django import forms
from django.utils.translation import ugettext_lazy as _

from psycopg2.extras import NumericRange, DateRange, DateTimeTZRange


__all__ = ['IntegerRangeField', 'FloatRangeField', 'DateTimeRangeField', 'DateRangeField']


class BaseRangeField(forms.MultiValueField):
    default_error_messages = {
        'invalid': _('Enter two valid values.'),
        'bound_ordering': _('The start of the range must not exceed the end of the range.'),
    }

    def __init__(self, **kwargs):
        widget = forms.MultiWidget([self.base_field.widget, self.base_field.widget])
        kwargs.setdefault('widget', widget)
        kwargs.setdefault('fields', [self.base_field(required=False), self.base_field(required=False)])
        kwargs.setdefault('required', False)
        kwargs.setdefault('require_all_fields', False)
        super(BaseRangeField, self).__init__(**kwargs)

    def prepare_value(self, value):
        if isinstance(value, self.range_type):
            return [value.lower, value.upper]
        if value is None:
            return [None, None]
        return value

    def compress(self, values):
        if not values:
            return None
        lower, upper = values
        if lower is not None and upper is not None and lower > upper:
            raise exceptions.ValidationError(
                self.error_messages['bound_ordering'],
                code='bound_ordering',
            )
        try:
            range_value = self.range_type(lower, upper)
        except TypeError:
            raise exceptions.ValidationError(
                self.error_messages['invalid'],
                code='invalid',
            )
        else:
            return range_value


class IntegerRangeField(BaseRangeField):
    base_field = forms.IntegerField
    range_type = NumericRange


class FloatRangeField(BaseRangeField):
    base_field = forms.FloatField
    range_type = NumericRange


class DateTimeRangeField(BaseRangeField):
    base_field = forms.DateTimeField
    range_type = DateTimeTZRange


class DateRangeField(BaseRangeField):
    base_field = forms.DateField
    range_type = DateRange
