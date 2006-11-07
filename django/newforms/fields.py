"""
Field classes
"""

from util import ValidationError, DEFAULT_ENCODING
from widgets import TextInput, CheckboxInput, Select, SelectMultiple
import datetime
import re
import time

__all__ = (
    'Field', 'CharField', 'IntegerField',
    'DEFAULT_DATE_INPUT_FORMATS', 'DateField',
    'DEFAULT_DATETIME_INPUT_FORMATS', 'DateTimeField',
    'RegexField', 'EmailField', 'URLField', 'BooleanField',
    'ChoiceField', 'MultipleChoiceField',
    'ComboField',
)

# These values, if given to to_python(), will trigger the self.required check.
EMPTY_VALUES = (None, '')

try:
    set # Only available in Python 2.4+
except NameError:
    from sets import Set as set # Python 2.3 fallback

class Field(object):
    widget = TextInput # Default widget to use when rendering this type of Field.

    def __init__(self, required=True, widget=None):
        self.required = required
        widget = widget or self.widget
        if isinstance(widget, type):
            widget = widget()
        self.widget = widget

    def clean(self, value):
        """
        Validates the given value and returns its "cleaned" value as an
        appropriate Python object.

        Raises ValidationError for any errors.
        """
        if self.required and value in EMPTY_VALUES:
            raise ValidationError(u'This field is required.')
        return value

class CharField(Field):
    def __init__(self, max_length=None, min_length=None, required=True, widget=None):
        Field.__init__(self, required, widget)
        self.max_length, self.min_length = max_length, min_length

    def clean(self, value):
        "Validates max_length and min_length. Returns a Unicode object."
        Field.clean(self, value)
        if value in EMPTY_VALUES: value = u''
        if not isinstance(value, basestring):
            value = unicode(str(value), DEFAULT_ENCODING)
        elif not isinstance(value, unicode):
            value = unicode(value, DEFAULT_ENCODING)
        if self.max_length is not None and len(value) > self.max_length:
            raise ValidationError(u'Ensure this value has at most %d characters.' % self.max_length)
        if self.min_length is not None and len(value) < self.min_length:
            raise ValidationError(u'Ensure this value has at least %d characters.' % self.min_length)
        return value

class IntegerField(Field):
    def clean(self, value):
        """
        Validates that int() can be called on the input. Returns the result
        of int().
        """
        super(IntegerField, self).clean(value)
        try:
            return int(value)
        except (ValueError, TypeError):
            raise ValidationError(u'Enter a whole number.')

DEFAULT_DATE_INPUT_FORMATS = (
    '%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y', # '2006-10-25', '10/25/2006', '10/25/06'
    '%b %d %Y', '%b %d, %Y',            # 'Oct 25 2006', 'Oct 25, 2006'
    '%d %b %Y', '%d %b, %Y',            # '25 Oct 2006', '25 Oct, 2006'
    '%B %d %Y', '%B %d, %Y',            # 'October 25 2006', 'October 25, 2006'
    '%d %B %Y', '%d %B, %Y',            # '25 October 2006', '25 October, 2006'
)

class DateField(Field):
    def __init__(self, input_formats=None, required=True, widget=None):
        Field.__init__(self, required, widget)
        self.input_formats = input_formats or DEFAULT_DATE_INPUT_FORMATS

    def clean(self, value):
        """
        Validates that the input can be converted to a date. Returns a Python
        datetime.date object.
        """
        Field.clean(self, value)
        if value in EMPTY_VALUES:
            return None
        if isinstance(value, datetime.datetime):
            return value.date()
        if isinstance(value, datetime.date):
            return value
        for format in self.input_formats:
            try:
                return datetime.date(*time.strptime(value, format)[:3])
            except ValueError:
                continue
        raise ValidationError(u'Enter a valid date.')

DEFAULT_DATETIME_INPUT_FORMATS = (
    '%Y-%m-%d %H:%M:%S',     # '2006-10-25 14:30:59'
    '%Y-%m-%d %H:%M',        # '2006-10-25 14:30'
    '%Y-%m-%d',              # '2006-10-25'
    '%m/%d/%Y %H:%M:%S',     # '10/25/2006 14:30:59'
    '%m/%d/%Y %H:%M',        # '10/25/2006 14:30'
    '%m/%d/%Y',              # '10/25/2006'
    '%m/%d/%y %H:%M:%S',     # '10/25/06 14:30:59'
    '%m/%d/%y %H:%M',        # '10/25/06 14:30'
    '%m/%d/%y',              # '10/25/06'
)

class DateTimeField(Field):
    def __init__(self, input_formats=None, required=True, widget=None):
        Field.__init__(self, required, widget)
        self.input_formats = input_formats or DEFAULT_DATETIME_INPUT_FORMATS

    def clean(self, value):
        """
        Validates that the input can be converted to a datetime. Returns a
        Python datetime.datetime object.
        """
        Field.clean(self, value)
        if value in EMPTY_VALUES:
            return None
        if isinstance(value, datetime.datetime):
            return value
        if isinstance(value, datetime.date):
            return datetime.datetime(value.year, value.month, value.day)
        for format in self.input_formats:
            try:
                return datetime.datetime(*time.strptime(value, format)[:6])
            except ValueError:
                continue
        raise ValidationError(u'Enter a valid date/time.')

class RegexField(Field):
    def __init__(self, regex, error_message=None, required=True, widget=None):
        """
        regex can be either a string or a compiled regular expression object.
        error_message is an optional error message to use, if
        'Enter a valid value' is too generic for you.
        """
        Field.__init__(self, required, widget)
        if isinstance(regex, basestring):
            regex = re.compile(regex)
        self.regex = regex
        self.error_message = error_message or u'Enter a valid value.'

    def clean(self, value):
        """
        Validates that the input matches the regular expression. Returns a
        Unicode object.
        """
        Field.clean(self, value)
        if value in EMPTY_VALUES: value = u''
        if not isinstance(value, basestring):
            value = unicode(str(value), DEFAULT_ENCODING)
        elif not isinstance(value, unicode):
            value = unicode(value, DEFAULT_ENCODING)
        if not self.regex.search(value):
            raise ValidationError(self.error_message)
        return value

email_re = re.compile(
    r"(^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*"  # dot-atom
    r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]|\\[\001-011\013\014\016-\177])*"' # quoted-string
    r')@(?:[A-Z0-9-]+\.)+[A-Z]{2,6}$', re.IGNORECASE)  # domain

class EmailField(RegexField):
    def __init__(self, required=True, widget=None):
        RegexField.__init__(self, email_re, u'Enter a valid e-mail address.', required, widget)

url_re = re.compile(
    r'^https?://' # http:// or https://
    r'(?:[A-Z0-9-]+\.)+[A-Z]{2,6}' # domain
    r'(?::\d+)?' # optional port
    r'(?:/?|/\S+)$', re.IGNORECASE)

try:
    from django.conf import settings
    URL_VALIDATOR_USER_AGENT = settings.URL_VALIDATOR_USER_AGENT
except ImportError:
    # It's OK if Django settings aren't configured.
    URL_VALIDATOR_USER_AGENT = 'Django (http://www.djangoproject.com/)'

class URLField(RegexField):
    def __init__(self, required=True, verify_exists=False, widget=None,
            validator_user_agent=URL_VALIDATOR_USER_AGENT):
        RegexField.__init__(self, url_re, u'Enter a valid URL.', required, widget)
        self.verify_exists = verify_exists
        self.user_agent = validator_user_agent

    def clean(self, value):
        value = RegexField.clean(self, value)
        if self.verify_exists:
            import urllib2
            from django.conf import settings
            headers = {
                "Accept": "text/xml,application/xml,application/xhtml+xml,text/html;q=0.9,text/plain;q=0.8,image/png,*/*;q=0.5",
                "Accept-Language": "en-us,en;q=0.5",
                "Accept-Charset": "ISO-8859-1,utf-8;q=0.7,*;q=0.7",
                "Connection": "close",
                "User-Agent": self.user_agent,
            }
            try:
                req = urllib2.Request(field_data, None, headers)
                u = urllib2.urlopen(req)
            except ValueError:
                raise ValidationError(u'Enter a valid URL.')
            except: # urllib2.URLError, httplib.InvalidURL, etc.
                raise ValidationError(u'This URL appears to be a broken link.')
        return value

class BooleanField(Field):
    widget = CheckboxInput

    def clean(self, value):
        "Returns a Python boolean object."
        Field.clean(self, value)
        return bool(value)

class ChoiceField(Field):
    def __init__(self, choices=(), required=True, widget=Select):
        if isinstance(widget, type):
            widget = widget(choices=choices)
        Field.__init__(self, required, widget)
        self.choices = choices

    def clean(self, value):
        """
        Validates that the input is in self.choices.
        """
        value = Field.clean(self, value)
        if value in EMPTY_VALUES: value = u''
        if not isinstance(value, basestring):
            value = unicode(str(value), DEFAULT_ENCODING)
        elif not isinstance(value, unicode):
            value = unicode(value, DEFAULT_ENCODING)
        valid_values = set([str(k) for k, v in self.choices])
        if value not in valid_values:
            raise ValidationError(u'Select a valid choice. %s is not one of the available choices.' % value)
        return value

class MultipleChoiceField(ChoiceField):
    def __init__(self, choices=(), required=True, widget=SelectMultiple):
        ChoiceField.__init__(self, choices, required, widget)

    def clean(self, value):
        """
        Validates that the input is a list or tuple.
        """
        if not isinstance(value, (list, tuple)):
            raise ValidationError(u'Enter a list of values.')
        if self.required and not value:
            raise ValidationError(u'This field is required.')
        new_value = []
        for val in value:
            if not isinstance(val, basestring):
                value = unicode(str(val), DEFAULT_ENCODING)
            elif not isinstance(val, unicode):
                value = unicode(val, DEFAULT_ENCODING)
            new_value.append(value)
        # Validate that each value in the value list is in self.choices.
        valid_values = set([k for k, v in self.choices])
        for val in new_value:
            if val not in valid_values:
                raise ValidationError(u'Select a valid choice. %s is not one of the available choices.' % val)
        return new_value

class ComboField(Field):
    def __init__(self, fields=(), required=True, widget=None):
        Field.__init__(self, required, widget)
        self.fields = fields

    def clean(self, value):
        """
        Validates the given value against all of self.fields, which is a
        list of Field instances.
        """
        Field.clean(self, value)
        for field in self.fields:
            value = field.clean(value)
        return value
