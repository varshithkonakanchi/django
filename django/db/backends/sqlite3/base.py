"""
SQLite3 backend for django.  Requires pysqlite2 (http://pysqlite.org/).
"""

from django.db.backends import BaseDatabaseWrapper, BaseDatabaseOperations, util
try:
    try:
        from sqlite3 import dbapi2 as Database
    except ImportError:
        from pysqlite2 import dbapi2 as Database
except ImportError, e:
    import sys
    from django.core.exceptions import ImproperlyConfigured
    if sys.version_info < (2, 5, 0):
        module = 'pysqlite2'
    else:
        module = 'sqlite3'
    raise ImproperlyConfigured, "Error loading %s module: %s" % (module, e)

try:
    import decimal
except ImportError:
    from django.utils import _decimal as decimal # for Python 2.3

DatabaseError = Database.DatabaseError
IntegrityError = Database.IntegrityError

Database.register_converter("bool", lambda s: str(s) == '1')
Database.register_converter("time", util.typecast_time)
Database.register_converter("date", util.typecast_date)
Database.register_converter("datetime", util.typecast_timestamp)
Database.register_converter("timestamp", util.typecast_timestamp)
Database.register_converter("TIMESTAMP", util.typecast_timestamp)
Database.register_converter("decimal", util.typecast_decimal)
Database.register_adapter(decimal.Decimal, util.rev_typecast_decimal)

class DatabaseOperations(BaseDatabaseOperations):
    def date_extract_sql(self, lookup_type, field_name):
        # sqlite doesn't support extract, so we fake it with the user-defined
        # function django_extract that's registered in connect().
        return 'django_extract("%s", %s)' % (lookup_type.lower(), field_name)

    def date_trunc_sql(self, lookup_type, field_name):
        # sqlite doesn't support DATE_TRUNC, so we fake it with a user-defined
        # function django_date_trunc that's registered in connect().
        return 'django_date_trunc("%s", %s)' % (lookup_type.lower(), field_name)

class DatabaseWrapper(BaseDatabaseWrapper):
    ops = DatabaseOperations()

    def _cursor(self, settings):
        if self.connection is None:
            kwargs = {
                'database': settings.DATABASE_NAME,
                'detect_types': Database.PARSE_DECLTYPES | Database.PARSE_COLNAMES,
            }
            kwargs.update(self.options)
            self.connection = Database.connect(**kwargs)
            # Register extract, date_trunc, and regexp functions.
            self.connection.create_function("django_extract", 2, _sqlite_extract)
            self.connection.create_function("django_date_trunc", 2, _sqlite_date_trunc)
            self.connection.create_function("regexp", 2, _sqlite_regexp)
        return self.connection.cursor(factory=SQLiteCursorWrapper)

    def close(self):
        from django.conf import settings
        # If database is in memory, closing the connection destroys the
        # database. To prevent accidental data loss, ignore close requests on
        # an in-memory db.
        if settings.DATABASE_NAME != ":memory:":
            BaseDatabaseWrapper.close(self)

class SQLiteCursorWrapper(Database.Cursor):
    """
    Django uses "format" style placeholders, but pysqlite2 uses "qmark" style.
    This fixes it -- but note that if you want to use a literal "%s" in a query,
    you'll need to use "%%s".
    """
    def execute(self, query, params=()):
        query = self.convert_query(query, len(params))
        return Database.Cursor.execute(self, query, params)

    def executemany(self, query, param_list):
        query = self.convert_query(query, len(param_list[0]))
        return Database.Cursor.executemany(self, query, param_list)

    def convert_query(self, query, num_params):
        return query % tuple("?" * num_params)

allows_group_by_ordinal = True
allows_unique_and_pk = True
autoindexes_primary_keys = True
needs_datetime_string_cast = True
needs_upper_for_iops = False
supports_constraints = False
supports_tablespaces = False
uses_case_insensitive_names = False

def quote_name(name):
    if name.startswith('"') and name.endswith('"'):
        return name # Quoting once is enough.
    return '"%s"' % name

dictfetchone = util.dictfetchone
dictfetchmany = util.dictfetchmany
dictfetchall  = util.dictfetchall

def get_last_insert_id(cursor, table_name, pk_name):
    return cursor.lastrowid

def _sqlite_extract(lookup_type, dt):
    try:
        dt = util.typecast_timestamp(dt)
    except (ValueError, TypeError):
        return None
    return str(getattr(dt, lookup_type))

def get_limit_offset_sql(limit, offset=None):
    sql = "LIMIT %s" % limit
    if offset and offset != 0:
        sql += " OFFSET %s" % offset
    return sql

def get_random_function_sql():
    return "RANDOM()"

def get_deferrable_sql():
    return ""

def get_fulltext_search_sql(field_name):
    raise NotImplementedError

def get_drop_foreignkey_sql():
    return ""

def get_pk_default_value():
    return "NULL"

def get_max_name_length():
    return None

def get_start_transaction_sql():
    return "BEGIN;"

def get_sql_flush(style, tables, sequences):
    """
    Return a list of SQL statements required to remove all data from
    all tables in the database (without actually removing the tables
    themselves) and put the database in an empty 'initial' state
    """
    # NB: The generated SQL below is specific to SQLite
    # Note: The DELETE FROM... SQL generated below works for SQLite databases
    # because constraints don't exist
    sql = ['%s %s %s;' % \
            (style.SQL_KEYWORD('DELETE'),
             style.SQL_KEYWORD('FROM'),
             style.SQL_FIELD(quote_name(table))
             ) for table in tables]
    # Note: No requirement for reset of auto-incremented indices (cf. other
    # get_sql_flush() implementations). Just return SQL at this point
    return sql

def get_sql_sequence_reset(style, model_list):
    "Returns a list of the SQL statements to reset sequences for the given models."
    # No sequence reset required
    return []

def _sqlite_date_trunc(lookup_type, dt):
    try:
        dt = util.typecast_timestamp(dt)
    except (ValueError, TypeError):
        return None
    if lookup_type == 'year':
        return "%i-01-01 00:00:00" % dt.year
    elif lookup_type == 'month':
        return "%i-%02i-01 00:00:00" % (dt.year, dt.month)
    elif lookup_type == 'day':
        return "%i-%02i-%02i 00:00:00" % (dt.year, dt.month, dt.day)

def _sqlite_regexp(re_pattern, re_string):
    import re
    try:
        return bool(re.search(re_pattern, re_string))
    except:
        return False

# SQLite requires LIKE statements to include an ESCAPE clause if the value
# being escaped has a percent or underscore in it.
# See http://www.sqlite.org/lang_expr.html for an explanation.
OPERATOR_MAPPING = {
    'exact': '= %s',
    'iexact': "LIKE %s ESCAPE '\\'",
    'contains': "LIKE %s ESCAPE '\\'",
    'icontains': "LIKE %s ESCAPE '\\'",
    'regex': 'REGEXP %s',
    'iregex': "REGEXP '(?i)' || %s",
    'gt': '> %s',
    'gte': '>= %s',
    'lt': '< %s',
    'lte': '<= %s',
    'startswith': "LIKE %s ESCAPE '\\'",
    'endswith': "LIKE %s ESCAPE '\\'",
    'istartswith': "LIKE %s ESCAPE '\\'",
    'iendswith': "LIKE %s ESCAPE '\\'",
}

