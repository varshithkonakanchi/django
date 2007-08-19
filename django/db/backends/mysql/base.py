"""
MySQL database backend for Django.

Requires MySQLdb: http://sourceforge.net/projects/mysql-python
"""

from django.db.backends import BaseDatabaseWrapper, BaseDatabaseOperations, util
try:
    import MySQLdb as Database
except ImportError, e:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured, "Error loading MySQLdb module: %s" % e

# We want version (1, 2, 1, 'final', 2) or later. We can't just use
# lexicographic ordering in this check because then (1, 2, 1, 'gamma')
# inadvertently passes the version test.
version = Database.version_info
if (version < (1,2,1) or (version[:3] == (1, 2, 1) and
        (len(version) < 5 or version[3] != 'final' or version[4] < 2))):
    raise ImportError, "MySQLdb-1.2.1p2 or newer is required; you have %s" % Database.__version__

from MySQLdb.converters import conversions
from MySQLdb.constants import FIELD_TYPE
import types
import re

DatabaseError = Database.DatabaseError
IntegrityError = Database.IntegrityError

# MySQLdb-1.2.1 supports the Python boolean type, and only uses datetime
# module for time-related columns; older versions could have used mx.DateTime
# or strings if there were no datetime module. However, MySQLdb still returns
# TIME columns as timedelta -- they are more like timedelta in terms of actual
# behavior as they are signed and include days -- and Django expects time, so
# we still need to override that.
django_conversions = conversions.copy()
django_conversions.update({
    FIELD_TYPE.TIME: util.typecast_time,
    FIELD_TYPE.DECIMAL: util.typecast_decimal,
    FIELD_TYPE.NEWDECIMAL: util.typecast_decimal,
})

# This should match the numerical portion of the version numbers (we can treat
# versions like 5.0.24 and 5.0.24a as the same). Based on the list of version
# at http://dev.mysql.com/doc/refman/4.1/en/news.html and
# http://dev.mysql.com/doc/refman/5.0/en/news.html .
server_version_re = re.compile(r'(\d{1,2})\.(\d{1,2})\.(\d{1,2})')

# MySQLdb-1.2.1 and newer automatically makes use of SHOW WARNINGS on
# MySQL-4.1 and newer, so the MysqlDebugWrapper is unnecessary. Since the
# point is to raise Warnings as exceptions, this can be done with the Python
# warning module, and this is setup when the connection is created, and the
# standard util.CursorDebugWrapper can be used. Also, using sql_mode
# TRADITIONAL will automatically cause most warnings to be treated as errors.

class DatabaseOperations(BaseDatabaseOperations):
    def date_extract_sql(self, lookup_type, field_name):
        # http://dev.mysql.com/doc/mysql/en/date-and-time-functions.html
        return "EXTRACT(%s FROM %s)" % (lookup_type.upper(), field_name)

    def date_trunc_sql(self, lookup_type, field_name):
        fields = ['year', 'month', 'day', 'hour', 'minute', 'second']
        format = ('%%Y-', '%%m', '-%%d', ' %%H:', '%%i', ':%%s') # Use double percents to escape.
        format_def = ('0000-', '01', '-01', ' 00:', '00', ':00')
        try:
            i = fields.index(lookup_type) + 1
        except ValueError:
            sql = field_name
        else:
            format_str = ''.join([f for f in format[:i]] + [f for f in format_def[i:]])
            sql = "CAST(DATE_FORMAT(%s, '%s') AS DATETIME)" % (field_name, format_str)
        return sql

class DatabaseWrapper(BaseDatabaseWrapper):
    ops = DatabaseOperations()

    def __init__(self, **kwargs):
        super(DatabaseWrapper, self).__init__(**kwargs)
        self.server_version = None

    def _valid_connection(self):
        if self.connection is not None:
            try:
                self.connection.ping()
                return True
            except DatabaseError:
                self.connection.close()
                self.connection = None
        return False

    def _cursor(self, settings):
        from warnings import filterwarnings
        if not self._valid_connection():
            kwargs = {
                'conv': django_conversions,
                'charset': 'utf8',
                'use_unicode': True,
            }
            if settings.DATABASE_USER:
                kwargs['user'] = settings.DATABASE_USER
            if settings.DATABASE_NAME:
                kwargs['db'] = settings.DATABASE_NAME
            if settings.DATABASE_PASSWORD:
                kwargs['passwd'] = settings.DATABASE_PASSWORD
            if settings.DATABASE_HOST.startswith('/'):
                kwargs['unix_socket'] = settings.DATABASE_HOST
            elif settings.DATABASE_HOST:
                kwargs['host'] = settings.DATABASE_HOST
            if settings.DATABASE_PORT:
                kwargs['port'] = int(settings.DATABASE_PORT)
            kwargs.update(self.options)
            self.connection = Database.connect(**kwargs)
        cursor = self.connection.cursor()
        if settings.DEBUG:
            filterwarnings("error", category=Database.Warning)
        return cursor

    def _rollback(self):
        try:
            BaseDatabaseWrapper._rollback(self)
        except Database.NotSupportedError:
            pass

    def get_server_version(self):
        if not self.server_version:
            if not self._valid_connection():
                self.cursor()
            m = server_version_re.match(self.connection.get_server_info())
            if not m:
                raise Exception('Unable to determine MySQL version from version string %r' % self.connection.get_server_info())
            self.server_version = tuple([int(x) for x in m.groups()])
        return self.server_version

allows_group_by_ordinal = True
allows_unique_and_pk = True
autoindexes_primary_keys = False
needs_datetime_string_cast = True     # MySQLdb requires a typecast for dates
needs_upper_for_iops = False
supports_constraints = True
supports_tablespaces = False
uses_case_insensitive_names = False

def quote_name(name):
    if name.startswith("`") and name.endswith("`"):
        return name # Quoting once is enough.
    return "`%s`" % name

dictfetchone = util.dictfetchone
dictfetchmany = util.dictfetchmany
dictfetchall  = util.dictfetchall

def get_last_insert_id(cursor, table_name, pk_name):
    return cursor.lastrowid

def get_limit_offset_sql(limit, offset=None):
    sql = "LIMIT "
    if offset and offset != 0:
        sql += "%s," % offset
    return sql + str(limit)

def get_random_function_sql():
    return "RAND()"

def get_fulltext_search_sql(field_name):
    return 'MATCH (%s) AGAINST (%%s IN BOOLEAN MODE)' % field_name

def get_drop_foreignkey_sql():
    return "DROP FOREIGN KEY"

def get_pk_default_value():
    return "DEFAULT"

def get_max_name_length():
    return None;

def get_start_transaction_sql():
    return "BEGIN;"

def get_sql_flush(style, tables, sequences):
    """Return a list of SQL statements required to remove all data from
    all tables in the database (without actually removing the tables
    themselves) and put the database in an empty 'initial' state

    """
    # NB: The generated SQL below is specific to MySQL
    # 'TRUNCATE x;', 'TRUNCATE y;', 'TRUNCATE z;'... style SQL statements
    # to clear all tables of all data
    if tables:
        sql = ['SET FOREIGN_KEY_CHECKS = 0;'] + \
              ['%s %s;' % \
                (style.SQL_KEYWORD('TRUNCATE'),
                 style.SQL_FIELD(quote_name(table))
                )  for table in tables] + \
              ['SET FOREIGN_KEY_CHECKS = 1;']

        # 'ALTER TABLE table AUTO_INCREMENT = 1;'... style SQL statements
        # to reset sequence indices
        sql.extend(["%s %s %s %s %s;" % \
            (style.SQL_KEYWORD('ALTER'),
             style.SQL_KEYWORD('TABLE'),
             style.SQL_TABLE(quote_name(sequence['table'])),
             style.SQL_KEYWORD('AUTO_INCREMENT'),
             style.SQL_FIELD('= 1'),
            ) for sequence in sequences])
        return sql
    else:
        return []

def get_sql_sequence_reset(style, model_list):
    "Returns a list of the SQL statements to reset sequences for the given models."
    # No sequence reset required
    return []

OPERATOR_MAPPING = {
    'exact': '= %s',
    'iexact': 'LIKE %s',
    'contains': 'LIKE BINARY %s',
    'icontains': 'LIKE %s',
    'regex': 'REGEXP BINARY %s',
    'iregex': 'REGEXP %s',
    'gt': '> %s',
    'gte': '>= %s',
    'lt': '< %s',
    'lte': '<= %s',
    'startswith': 'LIKE BINARY %s',
    'endswith': 'LIKE BINARY %s',
    'istartswith': 'LIKE %s',
    'iendswith': 'LIKE %s',
}
