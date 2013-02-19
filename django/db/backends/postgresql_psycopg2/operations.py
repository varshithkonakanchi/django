from __future__ import unicode_literals

from django.conf import settings
from django.db.backends import BaseDatabaseOperations


class DatabaseOperations(BaseDatabaseOperations):
    def __init__(self, connection):
        super(DatabaseOperations, self).__init__(connection)

    def date_extract_sql(self, lookup_type, field_name):
        # http://www.postgresql.org/docs/8.0/static/functions-datetime.html#FUNCTIONS-DATETIME-EXTRACT
        if lookup_type == 'week_day':
            # For consistency across backends, we return Sunday=1, Saturday=7.
            return "EXTRACT('dow' FROM %s) + 1" % field_name
        else:
            return "EXTRACT('%s' FROM %s)" % (lookup_type, field_name)

    def date_interval_sql(self, sql, connector, timedelta):
        """
        implements the interval functionality for expressions
        format for Postgres:
            (datefield + interval '3 days 200 seconds 5 microseconds')
        """
        modifiers = []
        if timedelta.days:
            modifiers.append('%s days' % timedelta.days)
        if timedelta.seconds:
            modifiers.append('%s seconds' % timedelta.seconds)
        if timedelta.microseconds:
            modifiers.append('%s microseconds' % timedelta.microseconds)
        mods = ' '.join(modifiers)
        conn = ' %s ' % connector
        return '(%s)' % conn.join([sql, 'interval \'%s\'' % mods])

    def date_trunc_sql(self, lookup_type, field_name):
        # http://www.postgresql.org/docs/8.0/static/functions-datetime.html#FUNCTIONS-DATETIME-TRUNC
        return "DATE_TRUNC('%s', %s)" % (lookup_type, field_name)

    def datetime_extract_sql(self, lookup_type, field_name, tzname):
        if settings.USE_TZ:
            field_name = "%s AT TIME ZONE %%s" % field_name
            params = [tzname]
        else:
            params = []
        # http://www.postgresql.org/docs/8.0/static/functions-datetime.html#FUNCTIONS-DATETIME-EXTRACT
        if lookup_type == 'week_day':
            # For consistency across backends, we return Sunday=1, Saturday=7.
            sql = "EXTRACT('dow' FROM %s) + 1" % field_name
        else:
            sql = "EXTRACT('%s' FROM %s)" % (lookup_type, field_name)
        return sql, params

    def datetime_trunc_sql(self, lookup_type, field_name, tzname):
        if settings.USE_TZ:
            field_name = "%s AT TIME ZONE %%s" % field_name
            params = [tzname]
        else:
            params = []
        # http://www.postgresql.org/docs/8.0/static/functions-datetime.html#FUNCTIONS-DATETIME-TRUNC
        sql = "DATE_TRUNC('%s', %s)" % (lookup_type, field_name)
        return sql, params

    def deferrable_sql(self):
        return " DEFERRABLE INITIALLY DEFERRED"

    def lookup_cast(self, lookup_type):
        lookup = '%s'

        # Cast text lookups to text to allow things like filter(x__contains=4)
        if lookup_type in ('iexact', 'contains', 'icontains', 'startswith',
                           'istartswith', 'endswith', 'iendswith'):
            lookup = "%s::text"

        # Use UPPER(x) for case-insensitive lookups; it's faster.
        if lookup_type in ('iexact', 'icontains', 'istartswith', 'iendswith'):
            lookup = 'UPPER(%s)' % lookup

        return lookup

    def field_cast_sql(self, db_type):
        if db_type == 'inet':
            return 'HOST(%s)'
        return '%s'

    def last_insert_id(self, cursor, table_name, pk_name):
        # Use pg_get_serial_sequence to get the underlying sequence name
        # from the table name and column name (available since PostgreSQL 8)
        cursor.execute("SELECT CURRVAL(pg_get_serial_sequence('%s','%s'))" % (
            self.quote_name(table_name), pk_name))
        return cursor.fetchone()[0]

    def no_limit_value(self):
        return None

    def quote_name(self, name):
        if name.startswith('"') and name.endswith('"'):
            return name # Quoting once is enough.
        return '"%s"' % name

    def set_time_zone_sql(self):
        return "SET TIME ZONE %s"

    def sql_flush(self, style, tables, sequences):
        if tables:
            # Perform a single SQL 'TRUNCATE x, y, z...;' statement.  It allows
            # us to truncate tables referenced by a foreign key in any other
            # table.
            sql = ['%s %s;' % \
                (style.SQL_KEYWORD('TRUNCATE'),
                    style.SQL_FIELD(', '.join([self.quote_name(table) for table in tables]))
            )]
            sql.extend(self.sequence_reset_by_name_sql(style, sequences))
            return sql
        else:
            return []

    def sequence_reset_by_name_sql(self, style, sequences):
        # 'ALTER SEQUENCE sequence_name RESTART WITH 1;'... style SQL statements
        # to reset sequence indices
        sql = []
        for sequence_info in sequences:
            table_name = sequence_info['table']
            column_name = sequence_info['column']
            if not (column_name and len(column_name) > 0):
                # This will be the case if it's an m2m using an autogenerated
                # intermediate table (see BaseDatabaseIntrospection.sequence_list)
                column_name = 'id'
            sql.append("%s setval(pg_get_serial_sequence('%s','%s'), 1, false);" % \
                (style.SQL_KEYWORD('SELECT'),
                style.SQL_TABLE(self.quote_name(table_name)),
                style.SQL_FIELD(column_name))
            )
        return sql

    def tablespace_sql(self, tablespace, inline=False):
        if inline:
            return "USING INDEX TABLESPACE %s" % self.quote_name(tablespace)
        else:
            return "TABLESPACE %s" % self.quote_name(tablespace)

    def sequence_reset_sql(self, style, model_list):
        from django.db import models
        output = []
        qn = self.quote_name
        for model in model_list:
            # Use `coalesce` to set the sequence for each model to the max pk value if there are records,
            # or 1 if there are none. Set the `is_called` property (the third argument to `setval`) to true
            # if there are records (as the max pk value is already in use), otherwise set it to false.
            # Use pg_get_serial_sequence to get the underlying sequence name from the table name
            # and column name (available since PostgreSQL 8)

            for f in model._meta.local_fields:
                if isinstance(f, models.AutoField):
                    output.append("%s setval(pg_get_serial_sequence('%s','%s'), coalesce(max(%s), 1), max(%s) %s null) %s %s;" % \
                        (style.SQL_KEYWORD('SELECT'),
                        style.SQL_TABLE(qn(model._meta.db_table)),
                        style.SQL_FIELD(f.column),
                        style.SQL_FIELD(qn(f.column)),
                        style.SQL_FIELD(qn(f.column)),
                        style.SQL_KEYWORD('IS NOT'),
                        style.SQL_KEYWORD('FROM'),
                        style.SQL_TABLE(qn(model._meta.db_table))))
                    break # Only one AutoField is allowed per model, so don't bother continuing.
            for f in model._meta.many_to_many:
                if not f.rel.through:
                    output.append("%s setval(pg_get_serial_sequence('%s','%s'), coalesce(max(%s), 1), max(%s) %s null) %s %s;" % \
                        (style.SQL_KEYWORD('SELECT'),
                        style.SQL_TABLE(qn(f.m2m_db_table())),
                        style.SQL_FIELD('id'),
                        style.SQL_FIELD(qn('id')),
                        style.SQL_FIELD(qn('id')),
                        style.SQL_KEYWORD('IS NOT'),
                        style.SQL_KEYWORD('FROM'),
                        style.SQL_TABLE(qn(f.m2m_db_table()))))
        return output

    def savepoint_create_sql(self, sid):
        return "SAVEPOINT %s" % sid

    def savepoint_commit_sql(self, sid):
        return "RELEASE SAVEPOINT %s" % sid

    def savepoint_rollback_sql(self, sid):
        return "ROLLBACK TO SAVEPOINT %s" % sid

    def prep_for_iexact_query(self, x):
        return x

    def check_aggregate_support(self, aggregate):
        """Check that the backend fully supports the provided aggregate.

        The implementation of population statistics (STDDEV_POP and VAR_POP)
        under Postgres 8.2 - 8.2.4 is known to be faulty. Raise
        NotImplementedError if this is the database in use.
        """
        if aggregate.sql_function in ('STDDEV_POP', 'VAR_POP'):
            if 80200 <= self.connection.pg_version <= 80204:
                raise NotImplementedError('PostgreSQL 8.2 to 8.2.4 is known to have a faulty implementation of %s. Please upgrade your version of PostgreSQL.' % aggregate.sql_function)

    def max_name_length(self):
        """
        Returns the maximum length of an identifier.

        Note that the maximum length of an identifier is 63 by default, but can
        be changed by recompiling PostgreSQL after editing the NAMEDATALEN
        macro in src/include/pg_config_manual.h .

        This implementation simply returns 63, but can easily be overridden by a
        custom database backend that inherits most of its behavior from this one.
        """

        return 63

    def distinct_sql(self, fields):
        if fields:
            return 'DISTINCT ON (%s)' % ', '.join(fields)
        else:
            return 'DISTINCT'

    def last_executed_query(self, cursor, sql, params):
        # http://initd.org/psycopg/docs/cursor.html#cursor.query
        # The query attribute is a Psycopg extension to the DB API 2.0.
        if cursor.query is not None:
            return cursor.query.decode('utf-8')
        return None

    def return_insert_id(self):
        return "RETURNING %s", ()

    def bulk_insert_sql(self, fields, num_values):
        items_sql = "(%s)" % ", ".join(["%s"] * len(fields))
        return "VALUES " + ", ".join([items_sql] * num_values)
