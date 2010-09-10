import datetime
from decimal import Decimal

from django.core.exceptions import FieldError
from django.conf import settings
from django.test import TestCase, Approximate
from django.db import DEFAULT_DB_ALIAS
from django.db.models import Count, Max, Avg, Sum, StdDev, Variance, F

from regressiontests.aggregation_regress.models import *


def run_stddev_tests():
    """Check to see if StdDev/Variance tests should be run.

    Stddev and Variance are not guaranteed to be available for SQLite, and
    are not available for PostgreSQL before 8.2.
    """
    if settings.DATABASES[DEFAULT_DB_ALIAS]['ENGINE'] == 'django.db.backends.sqlite3':
        return False

    class StdDevPop(object):
        sql_function = 'STDDEV_POP'

    try:
        connection.ops.check_aggregate_support(StdDevPop())
    except:
        return False
    return True


class AggregationTests(TestCase):
    def assertObjectAttrs(self, obj, **kwargs):
        for attr, value in kwargs.iteritems():
            self.assertEqual(getattr(obj, attr), value)

    def test_aggregates_in_where_clause(self):
        """
        Regression test for #12822: DatabaseError: aggregates not allowed in
        WHERE clause

        Tests that the subselect works and returns results equivalent to a
        query with the IDs listed.

        Before the corresponding fix for this bug, this test passed in 1.1 and
        failed in 1.2-beta (trunk).
        """
        qs = Book.objects.values('contact').annotate(Max('id'))
        qs = qs.order_by('contact').values_list('id__max', flat=True)
        # don't do anything with the queryset (qs) before including it as a
        # subquery
        books = Book.objects.order_by('id')
        qs1 = books.filter(id__in=qs)
        qs2 = books.filter(id__in=list(qs))
        self.assertEqual(list(qs1), list(qs2))

    def test_aggregates_in_where_clause_pre_eval(self):
        """
        Regression test for #12822: DatabaseError: aggregates not allowed in
        WHERE clause

        Same as the above test, but evaluates the queryset for the subquery
        before it's used as a subquery.

        Before the corresponding fix for this bug, this test failed in both
        1.1 and 1.2-beta (trunk).
        """
        qs = Book.objects.values('contact').annotate(Max('id'))
        qs = qs.order_by('contact').values_list('id__max', flat=True)
        # force the queryset (qs) for the subquery to be evaluated in its
        # current state
        list(qs)
        books = Book.objects.order_by('id')
        qs1 = books.filter(id__in=qs)
        qs2 = books.filter(id__in=list(qs))
        self.assertEqual(list(qs1), list(qs2))

    if settings.DATABASES[DEFAULT_DB_ALIAS]['ENGINE'] != 'django.db.backends.oracle':
        def test_annotate_with_extra(self):
            """
            Regression test for #11916: Extra params + aggregation creates
            incorrect SQL.
            """
            #oracle doesn't support subqueries in group by clause
            shortest_book_sql = """
            SELECT name
            FROM aggregation_regress_book b
            WHERE b.publisher_id = aggregation_regress_publisher.id
            ORDER BY b.pages
            LIMIT 1
            """
            # tests that this query does not raise a DatabaseError due to the full
            # subselect being (erroneously) added to the GROUP BY parameters
            qs = Publisher.objects.extra(select={
                'name_of_shortest_book': shortest_book_sql,
            }).annotate(total_books=Count('book'))
            # force execution of the query
            list(qs)

    def test_aggregate(self):
        # Ordering requests are ignored
        self.assertEqual(
            Author.objects.order_by("name").aggregate(Avg("age")),
            {"age__avg": Approximate(37.444, places=1)}
        )

        # Implicit ordering is also ignored
        self.assertEqual(
            Book.objects.aggregate(Sum("pages")),
            {"pages__sum": 3703},
        )

        # Baseline results
        self.assertEqual(
            Book.objects.aggregate(Sum('pages'), Avg('pages')),
            {'pages__sum': 3703, 'pages__avg': Approximate(617.166, places=2)}
        )

        # Empty values query doesn't affect grouping or results
        self.assertEqual(
            Book.objects.values().aggregate(Sum('pages'), Avg('pages')),
            {'pages__sum': 3703, 'pages__avg': Approximate(617.166, places=2)}
        )

        # Aggregate overrides extra selected column
        self.assertEqual(
            Book.objects.extra(select={'price_per_page' : 'price / pages'}).aggregate(Sum('pages')),
            {'pages__sum': 3703}
        )

    def test_annotation(self):
        # Annotations get combined with extra select clauses
        obj = Book.objects.annotate(mean_auth_age=Avg("authors__age")).extra(select={"manufacture_cost": "price * .5"}).get(pk=2)
        self.assertObjectAttrs(obj,
            contact_id=3,
            id=2,
            isbn=u'067232959',
            manufacture_cost=11.545,
            mean_auth_age=45.0,
            name='Sams Teach Yourself Django in 24 Hours',
            pages=528,
            price=Decimal("23.09"),
            pubdate=datetime.date(2008, 3, 3),
            publisher_id=2,
            rating=3.0
        )

        # Order of the annotate/extra in the query doesn't matter
        obj = Book.objects.extra(select={'manufacture_cost' : 'price * .5'}).annotate(mean_auth_age=Avg('authors__age')).get(pk=2)
        self.assertObjectAttrs(obj,
            contact_id=3,
            id=2,
            isbn=u'067232959',
            manufacture_cost=11.545,
            mean_auth_age=45.0,
            name=u'Sams Teach Yourself Django in 24 Hours',
            pages=528,
            price=Decimal("23.09"),
            pubdate=datetime.date(2008, 3, 3),
            publisher_id=2,
            rating=3.0
        )

        # Values queries can be combined with annotate and extra
        obj = Book.objects.annotate(mean_auth_age=Avg('authors__age')).extra(select={'manufacture_cost' : 'price * .5'}).values().get(pk=2)
        self.assertEqual(obj, {
            "contact_id": 3,
            "id": 2,
            "isbn": u"067232959",
            "manufacture_cost": 11.545,
            "mean_auth_age": 45.0,
            "name": u"Sams Teach Yourself Django in 24 Hours",
            "pages": 528,
            "price": Decimal("23.09"),
            "pubdate": datetime.date(2008, 3, 3),
            "publisher_id": 2,
            "rating": 3.0,
        })

        # The order of the (empty) values, annotate and extra clauses doesn't
        # matter
        obj = Book.objects.values().annotate(mean_auth_age=Avg('authors__age')).extra(select={'manufacture_cost' : 'price * .5'}).get(pk=2)
        self.assertEqual(obj, {
            'contact_id': 3,
            'id': 2,
            'isbn': u'067232959',
            'manufacture_cost': 11.545,
            'mean_auth_age': 45.0,
            'name': u'Sams Teach Yourself Django in 24 Hours',
            'pages': 528,
            'price': Decimal("23.09"),
            'pubdate': datetime.date(2008, 3, 3),
            'publisher_id': 2,
            'rating': 3.0
        })

        # If the annotation precedes the values clause, it won't be included
        # unless it is explicitly named
        obj = Book.objects.annotate(mean_auth_age=Avg('authors__age')).extra(select={'price_per_page' : 'price / pages'}).values('name').get(pk=1)
        self.assertEqual(obj, {
            "name": u'The Definitive Guide to Django: Web Development Done Right',
        })

        obj = Book.objects.annotate(mean_auth_age=Avg('authors__age')).extra(select={'price_per_page' : 'price / pages'}).values('name','mean_auth_age').get(pk=1)
        self.assertEqual(obj, {
            'mean_auth_age': 34.5,
            'name': u'The Definitive Guide to Django: Web Development Done Right',
        })

        # If an annotation isn't included in the values, it can still be used
        # in a filter
        qs = Book.objects.annotate(n_authors=Count('authors')).values('name').filter(n_authors__gt=2)
        self.assertQuerysetEqual(
            qs, [
                {"name": u'Python Web Development with Django'}
            ],
            lambda b: b,
        )

        # The annotations are added to values output if values() precedes
        # annotate()
        obj = Book.objects.values('name').annotate(mean_auth_age=Avg('authors__age')).extra(select={'price_per_page' : 'price / pages'}).get(pk=1)
        self.assertEqual(obj, {
            'mean_auth_age': 34.5,
            'name': u'The Definitive Guide to Django: Web Development Done Right',
        })

        # Check that all of the objects are getting counted (allow_nulls) and
        # that values respects the amount of objects
        self.assertEqual(
            len(Author.objects.annotate(Avg('friends__age')).values()),
            9
        )

        # Check that consecutive calls to annotate accumulate in the query
        qs = Book.objects.values('price').annotate(oldest=Max('authors__age')).order_by('oldest', 'price').annotate(Max('publisher__num_awards'))
        self.assertQuerysetEqual(
            qs, [
                {'price': Decimal("30"), 'oldest': 35, 'publisher__num_awards__max': 3},
                {'price': Decimal("29.69"), 'oldest': 37, 'publisher__num_awards__max': 7},
                {'price': Decimal("23.09"), 'oldest': 45, 'publisher__num_awards__max': 1},
                {'price': Decimal("75"), 'oldest': 57, 'publisher__num_awards__max': 9},
                {'price': Decimal("82.8"), 'oldest': 57, 'publisher__num_awards__max': 7}
            ],
            lambda b: b,
        )

    def test_aggrate_annotation(self):
        # Aggregates can be composed over annotations.
        # The return type is derived from the composed aggregate
        vals = Book.objects.all().annotate(num_authors=Count('authors__id')).aggregate(Max('pages'), Max('price'), Sum('num_authors'), Avg('num_authors'))
        self.assertEqual(vals, {
            'num_authors__sum': 10,
            'num_authors__avg': Approximate(1.666, places=2),
            'pages__max': 1132,
            'price__max': Decimal("82.80")
        })

    def test_field_error(self):
        # Bad field requests in aggregates are caught and reported
        self.assertRaises(
            FieldError,
            lambda: Book.objects.all().aggregate(num_authors=Count('foo'))
        )

        self.assertRaises(
            FieldError,
            lambda: Book.objects.all().annotate(num_authors=Count('foo'))
        )

        self.assertRaises(
            FieldError,
            lambda: Book.objects.all().annotate(num_authors=Count('authors__id')).aggregate(Max('foo'))
        )

    def test_more(self):
        # Old-style count aggregations can be mixed with new-style
        self.assertEqual(
            Book.objects.annotate(num_authors=Count('authors')).count(),
            6
        )

        # Non-ordinal, non-computed Aggregates over annotations correctly
        # inherit the annotation's internal type if the annotation is ordinal
        # or computed
        vals = Book.objects.annotate(num_authors=Count('authors')).aggregate(Max('num_authors'))
        self.assertEqual(
            vals,
            {'num_authors__max': 3}
        )

        vals = Publisher.objects.annotate(avg_price=Avg('book__price')).aggregate(Max('avg_price'))
        self.assertEqual(
            vals,
            {'avg_price__max': 75.0}
        )

        # Aliases are quoted to protected aliases that might be reserved names
        vals = Book.objects.aggregate(number=Max('pages'), select=Max('pages'))
        self.assertEqual(
            vals,
            {'number': 1132, 'select': 1132}
        )

        # Regression for #10064: select_related() plays nice with aggregates
        obj = Book.objects.select_related('publisher').annotate(num_authors=Count('authors')).values()[0]
        self.assertEqual(obj, {
            'contact_id': 8,
            'id': 5,
            'isbn': u'013790395',
            'name': u'Artificial Intelligence: A Modern Approach',
            'num_authors': 2,
            'pages': 1132,
            'price': Decimal("82.8"),
            'pubdate': datetime.date(1995, 1, 15),
            'publisher_id': 3,
            'rating': 4.0,
        })

        # Regression for #10010: exclude on an aggregate field is correctly
        # negated
        self.assertEqual(
            len(Book.objects.annotate(num_authors=Count('authors'))),
            6
        )
        self.assertEqual(
            len(Book.objects.annotate(num_authors=Count('authors')).filter(num_authors__gt=2)),
            1
        )
        self.assertEqual(
            len(Book.objects.annotate(num_authors=Count('authors')).exclude(num_authors__gt=2)),
            5
        )

        self.assertEqual(
            len(Book.objects.annotate(num_authors=Count('authors')).filter(num_authors__lt=3).exclude(num_authors__lt=2)),
            2
        )
        self.assertEqual(
            len(Book.objects.annotate(num_authors=Count('authors')).exclude(num_authors__lt=2).filter(num_authors__lt=3)),
            2
        )

    def test_aggregate_fexpr(self):
        # Aggregates can be used with F() expressions
        # ... where the F() is pushed into the HAVING clause
        qs = Publisher.objects.annotate(num_books=Count('book')).filter(num_books__lt=F('num_awards')/2).order_by('name').values('name','num_books','num_awards')
        self.assertQuerysetEqual(
            qs, [
                {'num_books': 1, 'name': u'Morgan Kaufmann', 'num_awards': 9},
                {'num_books': 2, 'name': u'Prentice Hall', 'num_awards': 7}
            ],
            lambda p: p,
        )

        qs = Publisher.objects.annotate(num_books=Count('book')).exclude(num_books__lt=F('num_awards')/2).order_by('name').values('name','num_books','num_awards')
        self.assertQuerysetEqual(
            qs, [
                {'num_books': 2, 'name': u'Apress', 'num_awards': 3},
                {'num_books': 0, 'name': u"Jonno's House of Books", 'num_awards': 0},
                {'num_books': 1, 'name': u'Sams', 'num_awards': 1}
            ],
            lambda p: p,
        )

        # ... and where the F() references an aggregate
        qs = Publisher.objects.annotate(num_books=Count('book')).filter(num_awards__gt=2*F('num_books')).order_by('name').values('name','num_books','num_awards')
        self.assertQuerysetEqual(
            qs, [
                {'num_books': 1, 'name': u'Morgan Kaufmann', 'num_awards': 9},
                {'num_books': 2, 'name': u'Prentice Hall', 'num_awards': 7}
            ],
            lambda p: p,
        )

        qs = Publisher.objects.annotate(num_books=Count('book')).exclude(num_books__lt=F('num_awards')/2).order_by('name').values('name','num_books','num_awards')
        self.assertQuerysetEqual(
            qs, [
                {'num_books': 2, 'name': u'Apress', 'num_awards': 3},
                {'num_books': 0, 'name': u"Jonno's House of Books", 'num_awards': 0},
                {'num_books': 1, 'name': u'Sams', 'num_awards': 1}
            ],
            lambda p: p,
        )

    def test_db_col_table(self):
        # Tests on fields with non-default table and column names.
        qs = Clues.objects.values('EntryID__Entry').annotate(Appearances=Count('EntryID'), Distinct_Clues=Count('Clue', distinct=True))
        self.assertQuerysetEqual(qs, [])

        qs = Entries.objects.annotate(clue_count=Count('clues__ID'))
        self.assertQuerysetEqual(qs, [])

    def test_empty(self):
        # Regression for #10089: Check handling of empty result sets with
        # aggregates
        self.assertEqual(
            Book.objects.filter(id__in=[]).count(),
            0
        )

        vals = Book.objects.filter(id__in=[]).aggregate(num_authors=Count('authors'), avg_authors=Avg('authors'), max_authors=Max('authors'), max_price=Max('price'), max_rating=Max('rating'))
        self.assertEqual(
            vals,
            {'max_authors': None, 'max_rating': None, 'num_authors': 0, 'avg_authors': None, 'max_price': None}
        )

        qs = Publisher.objects.filter(pk=5).annotate(num_authors=Count('book__authors'), avg_authors=Avg('book__authors'), max_authors=Max('book__authors'), max_price=Max('book__price'), max_rating=Max('book__rating')).values()
        self.assertQuerysetEqual(
            qs, [
                {'max_authors': None, 'name': u"Jonno's House of Books", 'num_awards': 0, 'max_price': None, 'num_authors': 0, 'max_rating': None, 'id': 5, 'avg_authors': None}
            ],
            lambda p: p
        )

    def test_more_more(self):
        # Regression for #10113 - Fields mentioned in order_by() must be
        # included in the GROUP BY. This only becomes a problem when the
        # order_by introduces a new join.
        self.assertQuerysetEqual(
            Book.objects.annotate(num_authors=Count('authors')).order_by('publisher__name', 'name'), [
                "Practical Django Projects",
                "The Definitive Guide to Django: Web Development Done Right",
                "Paradigms of Artificial Intelligence Programming: Case Studies in Common Lisp",
                "Artificial Intelligence: A Modern Approach",
                "Python Web Development with Django",
                "Sams Teach Yourself Django in 24 Hours",
            ],
            lambda b: b.name
        )

        # Regression for #10127 - Empty select_related() works with annotate
        qs = Book.objects.filter(rating__lt=4.5).select_related().annotate(Avg('authors__age'))
        self.assertQuerysetEqual(
            qs, [
                (u'Artificial Intelligence: A Modern Approach', 51.5, u'Prentice Hall', u'Peter Norvig'),
                (u'Practical Django Projects', 29.0, u'Apress', u'James Bennett'),
                (u'Python Web Development with Django', Approximate(30.333, places=2), u'Prentice Hall', u'Jeffrey Forcier'),
                (u'Sams Teach Yourself Django in 24 Hours', 45.0, u'Sams', u'Brad Dayley')
            ],
            lambda b: (b.name, b.authors__age__avg, b.publisher.name, b.contact.name)
        )

        # Regression for #10132 - If the values() clause only mentioned extra
        # (select=) columns, those columns are used for grouping
        qs = Book.objects.extra(select={'pub':'publisher_id'}).values('pub').annotate(Count('id')).order_by('pub')
        self.assertQuerysetEqual(
            qs, [
                {'pub': 1, 'id__count': 2},
                {'pub': 2, 'id__count': 1},
                {'pub': 3, 'id__count': 2},
                {'pub': 4, 'id__count': 1}
            ],
            lambda b: b
        )

        qs = Book.objects.extra(select={'pub':'publisher_id', 'foo':'pages'}).values('pub').annotate(Count('id')).order_by('pub')
        self.assertQuerysetEqual(
            qs, [
                {'pub': 1, 'id__count': 2},
                {'pub': 2, 'id__count': 1},
                {'pub': 3, 'id__count': 2},
                {'pub': 4, 'id__count': 1}
            ],
            lambda b: b
        )

        # Regression for #10182 - Queries with aggregate calls are correctly
        # realiased when used in a subquery
        ids = Book.objects.filter(pages__gt=100).annotate(n_authors=Count('authors')).filter(n_authors__gt=2).order_by('n_authors')
        self.assertQuerysetEqual(
            Book.objects.filter(id__in=ids), [
                "Python Web Development with Django",
            ],
            lambda b: b.name
        )

    def test_pickle(self):
        # Regression for #10197 -- Queries with aggregates can be pickled.
        # First check that pickling is possible at all. No crash = success
        qs = Book.objects.annotate(num_authors=Count('authors'))
        out = pickle.dumps(qs)

        # Then check that the round trip works.
        query = qs.query.get_compiler(qs.db).as_sql()[0]
        qs2 = pickle.loads(pickle.dumps(qs))
        self.assertEqual(
            qs2.query.get_compiler(qs2.db).as_sql()[0],
            query,
        )

    def test_more_more_more(self):
        # Regression for #10199 - Aggregate calls clone the original query so
        # the original query can still be used
        books = Book.objects.all()
        books.aggregate(Avg("authors__age"))
        self.assertQuerysetEqual(
            books.all(), [
                u'Artificial Intelligence: A Modern Approach',
                u'Paradigms of Artificial Intelligence Programming: Case Studies in Common Lisp',
                u'Practical Django Projects',
                u'Python Web Development with Django',
                u'Sams Teach Yourself Django in 24 Hours',
                u'The Definitive Guide to Django: Web Development Done Right'
            ],
            lambda b: b.name
        )

        # Regression for #10248 - Annotations work with DateQuerySets
        qs = Book.objects.annotate(num_authors=Count('authors')).filter(num_authors=2).dates('pubdate', 'day')
        self.assertQuerysetEqual(
            qs, [
                datetime.datetime(1995, 1, 15, 0, 0),
                datetime.datetime(2007, 12, 6, 0, 0)
            ],
            lambda b: b
        )

        # Regression for #10290 - extra selects with parameters can be used for
        # grouping.
        qs = Book.objects.annotate(mean_auth_age=Avg('authors__age')).extra(select={'sheets' : '(pages + %s) / %s'}, select_params=[1, 2]).order_by('sheets').values('sheets')
        self.assertQuerysetEqual(
            qs, [
                150,
                175,
                224,
                264,
                473,
                566
            ],
            lambda b: int(b["sheets"])
        )

        # Regression for 10425 - annotations don't get in the way of a count()
        # clause
        self.assertEqual(
            Book.objects.values('publisher').annotate(Count('publisher')).count(),
            4
        )
        self.assertEqual(
            Book.objects.annotate(Count('publisher')).values('publisher').count(),
            6
        )

        publishers = Publisher.objects.filter(id__in=[1, 2])
        self.assertQuerysetEqual(
            publishers, [
                "Apress",
                "Sams"
            ],
            lambda p: p.name
        )

        publishers = publishers.annotate(n_books=Count("book"))
        self.assertEqual(
            publishers[0].n_books,
            2
        )

        self.assertQuerysetEqual(
            publishers, [
                "Apress",
                "Sams",
            ],
            lambda p: p.name
        )

        books = Book.objects.filter(publisher__in=publishers)
        self.assertQuerysetEqual(
            books, [
                "Practical Django Projects",
                "Sams Teach Yourself Django in 24 Hours",
                "The Definitive Guide to Django: Web Development Done Right",
            ],
            lambda b: b.name
        )
        self.assertQuerysetEqual(
            publishers, [
                "Apress",
                "Sams",
            ],
            lambda p: p.name
        )

        # Regression for 10666 - inherited fields work with annotations and
        # aggregations
        self.assertEqual(
            HardbackBook.objects.aggregate(n_pages=Sum('book_ptr__pages')),
            {'n_pages': 2078}
        )

        self.assertEqual(
            HardbackBook.objects.aggregate(n_pages=Sum('pages')),
            {'n_pages': 2078},
        )

        qs = HardbackBook.objects.annotate(n_authors=Count('book_ptr__authors')).values('name', 'n_authors')
        self.assertQuerysetEqual(
            qs, [
                {'n_authors': 2, 'name': u'Artificial Intelligence: A Modern Approach'},
                {'n_authors': 1, 'name': u'Paradigms of Artificial Intelligence Programming: Case Studies in Common Lisp'}
            ],
            lambda h: h
        )

        qs = HardbackBook.objects.annotate(n_authors=Count('authors')).values('name', 'n_authors')
        self.assertQuerysetEqual(
            qs, [
                {'n_authors': 2, 'name': u'Artificial Intelligence: A Modern Approach'},
                {'n_authors': 1, 'name': u'Paradigms of Artificial Intelligence Programming: Case Studies in Common Lisp'}
            ],
            lambda h: h,
        )

        # Regression for #10766 - Shouldn't be able to reference an aggregate
        # fields in an an aggregate() call.
        self.assertRaises(
            FieldError,
            lambda: Book.objects.annotate(mean_age=Avg('authors__age')).annotate(Avg('mean_age'))
        )

    if run_stddev_tests():
        def test_stddev(self):
            self.assertEqual(
                Book.objects.aggregate(StdDev('pages')),
                {'pages__stddev': Approximate(311.46, 1)}
            )

            self.assertEqual(
                Book.objects.aggregate(StdDev('rating')),
                {'rating__stddev': Approximate(0.60, 1)}
            )

            self.assertEqual(
                Book.objects.aggregate(StdDev('price')),
                {'price__stddev': Approximate(24.16, 2)}
            )

            self.assertEqual(
                Book.objects.aggregate(StdDev('pages', sample=True)),
                {'pages__stddev': Approximate(341.19, 2)}
            )

            self.assertEqual(
                Book.objects.aggregate(StdDev('rating', sample=True)),
                {'rating__stddev': Approximate(0.66, 2)}
            )

            self.assertEqual(
                Book.objects.aggregate(StdDev('price', sample=True)),
                {'price__stddev': Approximate(26.46, 1)}
            )

            self.assertEqual(
                Book.objects.aggregate(Variance('pages')),
                {'pages__variance': Approximate(97010.80, 1)}
            )

            self.assertEqual(
                Book.objects.aggregate(Variance('rating')),
                {'rating__variance': Approximate(0.36, 1)}
            )

            self.assertEqual(
                Book.objects.aggregate(Variance('price')),
                {'price__variance': Approximate(583.77, 1)}
            )

            self.assertEqual(
                Book.objects.aggregate(Variance('pages', sample=True)),
                {'pages__variance': Approximate(116412.96, 1)}
            )

            self.assertEqual(
                Book.objects.aggregate(Variance('rating', sample=True)),
                {'rating__variance': Approximate(0.44, 2)}
            )

            self.assertEqual(
                Book.objects.aggregate(Variance('price', sample=True)),
                {'price__variance': Approximate(700.53, 2)}
            )
