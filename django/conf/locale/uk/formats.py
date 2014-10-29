# -*- encoding: utf-8 -*-
# This file is distributed under the same license as the Django package.
#

from __future__ import unicode_literals

# The *_FORMAT strings use the Django date format syntax,
# see http://docs.djangoproject.com/en/dev/ref/templates/builtins/#date
DATE_FORMAT = 'j E Y р.'
TIME_FORMAT = 'H:i'
DATETIME_FORMAT = 'j E Y р. H:i'
YEAR_MONTH_FORMAT = 'F Y'
MONTH_DAY_FORMAT = 'j F'
SHORT_DATE_FORMAT = 'j M Y'
# SHORT_DATETIME_FORMAT =
FIRST_DAY_OF_WEEK = 1  # Monday

# The *_INPUT_FORMATS strings use the Python strftime format syntax,
# see http://docs.python.org/library/datetime.html#strftime-strptime-behavior
# DATE_INPUT_FORMATS =
# TIME_INPUT_FORMATS =
# DATETIME_INPUT_FORMATS =
DECIMAL_SEPARATOR = ','
THOUSAND_SEPARATOR = ' '
# NUMBER_GROUPING =
