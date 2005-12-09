import datetime, math, time
from django.utils.tzinfo import LocalTimezone
from django.utils.translation import ngettext

def timesince(d, now=None):
    """
    Takes two datetime objects and returns the time between then and now
    as a nicely formatted string, e.g "10 minutes"
    Adapted from http://blog.natbat.co.uk/archive/2003/Jun/14/time_since
    """
    chunks = (
      (60 * 60 * 24 * 365, lambda n: ngettext('year', 'years', n)),
      (60 * 60 * 24 * 30, lambda n: ngettext('month', 'months', n)),
      (60 * 60 * 24, lambda n : ngettext('day', 'days', n)),
      (60 * 60, lambda n: ngettext('hour', 'hours', n)),
      (60, lambda n: ngettext('minute', 'minutes', n))
    )
    if now:
        t = now.timetuple()
    else:
        t = time.localtime()
    if d.tzinfo:
        tz = LocalTimezone()
    else:
        tz = None
    now = datetime.datetime(t[0], t[1], t[2], t[3], t[4], t[5], tzinfo=tz)
    delta = now - d
    since = delta.days * 24 * 60 * 60 + delta.seconds
    for i, (seconds, name) in enumerate(chunks):
        count = since / seconds
        if count != 0:
            break
    if count < 0:
        return '%d milliseconds' % math.floor(delta.microseconds / 1000)
    s = '%d %s' % (count, name(count))
    if i + 1 < len(chunks):
        # Now get the second item
        seconds2, name2 = chunks[i + 1]
        count2 = (since - (seconds * count)) / seconds2
        if count2 != 0:
            s += ', %d %s' % (count2, name2(count2))
    return s

def timeuntil(d):
    """
    Like timesince, but returns a string measuring the time until
    the given time.
    """
    now = datetime.datetime.now()
    return timesince(now, d)
