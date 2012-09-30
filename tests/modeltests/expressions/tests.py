from __future__ import absolute_import, unicode_literals

from django.core.exceptions import FieldError
from django.db.models import F
from django.test import TestCase
from django.utils import six

from .models import Company, Employee


class ExpressionsTests(TestCase):
    def setUp(self):
        Company.objects.create(
            name="Example Inc.", num_employees=2300, num_chairs=5, is_large=False,
            ceo=Employee.objects.create(firstname="Joe", lastname="Smith")
        )
        Company.objects.create(
            name="Foobar Ltd.", num_employees=3, num_chairs=4, is_large=False,
            ceo=Employee.objects.create(firstname="Frank", lastname="Meyer")
        )
        Company.objects.create(
            name="Test GmbH", num_employees=32, num_chairs=1, is_large=False,
            ceo=Employee.objects.create(firstname="Max", lastname="Mustermann")
        )


    def test_filter(self):
        company_query = Company.objects.values(
            "name", "num_employees", "num_chairs", "is_large"
        ).order_by(
            "name", "num_employees", "num_chairs", "is_large"
        )

        # We can filter for companies where the number of employees is greater
        # than the number of chairs.
        self.assertQuerysetEqual(
            company_query.filter(num_employees__gt=F("num_chairs")), [
                {
                    "num_chairs": 5,
                    "name": "Example Inc.",
                    "num_employees": 2300,
                    "is_large": False
                },
                {
                    "num_chairs": 1,
                    "name": "Test GmbH",
                    "num_employees": 32,
                    "is_large": False
                },
            ],
            lambda o: o
        )

        # We can set one field to have the value of another field
        # Make sure we have enough chairs
        company_query.update(num_chairs=F("num_employees"))
        self.assertQuerysetEqual(
            company_query, [
                {
                    "num_chairs": 2300,
                    "name": "Example Inc.",
                    "num_employees": 2300,
                    "is_large": False
                },
                {
                    "num_chairs": 3,
                    "name": "Foobar Ltd.",
                    "num_employees": 3,
                    "is_large": False
                },
                {
                    "num_chairs": 32,
                    "name": "Test GmbH",
                    "num_employees": 32,
                    "is_large": False
                }
            ],
            lambda o: o
        )

        # We can perform arithmetic operations in expressions
        # Make sure we have 2 spare chairs
        company_query.update(num_chairs=F("num_employees")+2)
        self.assertQuerysetEqual(
            company_query, [
                {
                    'num_chairs': 2302,
                    'name': 'Example Inc.',
                    'num_employees': 2300,
                    'is_large': False
                },
                {
                    'num_chairs': 5,
                    'name': 'Foobar Ltd.',
                    'num_employees': 3,
                    'is_large': False
                },
                {
                    'num_chairs': 34,
                    'name': 'Test GmbH',
                    'num_employees': 32,
                    'is_large': False
                }
            ],
            lambda o: o,
        )

        # Law of order of operations is followed
        company_query.update(
            num_chairs=F('num_employees') + 2 * F('num_employees')
        )
        self.assertQuerysetEqual(
            company_query, [
                {
                    'num_chairs': 6900,
                    'name': 'Example Inc.',
                    'num_employees': 2300,
                    'is_large': False
                },
                {
                    'num_chairs': 9,
                    'name': 'Foobar Ltd.',
                    'num_employees': 3,
                    'is_large': False
                },
                {
                    'num_chairs': 96,
                    'name': 'Test GmbH',
                    'num_employees': 32,
                    'is_large': False
                }
            ],
            lambda o: o,
        )

        # Law of order of operations can be overridden by parentheses
        company_query.update(
            num_chairs=((F('num_employees') + 2) * F('num_employees'))
        )
        self.assertQuerysetEqual(
            company_query, [
                {
                    'num_chairs': 5294600,
                    'name': 'Example Inc.',
                    'num_employees': 2300,
                    'is_large': False
                },
                {
                    'num_chairs': 15,
                    'name': 'Foobar Ltd.',
                    'num_employees': 3,
                    'is_large': False
                },
                {
                    'num_chairs': 1088,
                    'name': 'Test GmbH',
                    'num_employees': 32,
                    'is_large': False
                }
            ],
            lambda o: o,
        )

    def test_comparisons(self):
        company_query = Company.objects.values(
            "name", "num_employees", "num_chairs", "is_large"
        ).order_by(
            "name", "num_employees", "num_chairs", "is_large"
        )
        # The comparison operators and the bitwise unary not can be used
        # to assign to boolean fields
        for expression in (
            # Check boundaries
            ~(F('num_employees') < 33),
            ~(F('num_employees') <= 32),
            (F('num_employees') > 2299),
            (F('num_employees') >= 2300),
            (F('num_employees') == 2300),
            ((F('num_employees') + 1 != 4) & (32 != F('num_employees'))),
            # Inverted argument order works too
            (2299 < F('num_employees')),
            (2300 <= F('num_employees'))
        ):
            # Test update by F-expression
            company_query.update(
                is_large=expression
            )
            # Compare results
            self.assertQuerysetEqual(
                company_query, [
                    {
                        'num_chairs': 5,
                        'name': 'Example Inc.',
                        'num_employees': 2300,
                        'is_large': True
                    },
                    {
                        'num_chairs': 4,
                        'name': 'Foobar Ltd.',
                        'num_employees': 3,
                        'is_large': False
                    },
                    {
                        'num_chairs': 1,
                        'name': 'Test GmbH',
                        'num_employees': 32,
                        'is_large': False
                    }
                ],
                lambda o: o,
            )
            # Reset values
            company_query.update(
                is_large=False
            )

        # The python boolean operators should be avoided as they yield
        # unexpected results
        test_gmbh = Company.objects.get(name="Test GmbH")
        with self.assertRaises(TypeError):
            test_gmbh.is_large = not F('is_large')
        with self.assertRaises(TypeError):
            test_gmbh.is_large = F('is_large') and F('is_large')
        with self.assertRaises(TypeError):
            test_gmbh.is_large = F('is_large') or F('is_large')

        # The relation of a foreign key can become copied over to an other
        # foreign key.
        self.assertEqual(
            Company.objects.update(point_of_contact=F('ceo')),
            3
        )
        self.assertQuerysetEqual(
            Company.objects.all(), [
                "Joe Smith",
                "Frank Meyer",
                "Max Mustermann",
            ],
            lambda c: six.text_type(c.point_of_contact),
        )

    def test_joins(self):
        c = Company.objects.all()[0]
        c.point_of_contact = Employee.objects.create(
            firstname="Guido", lastname="van Rossum")
        old_ceo = c.ceo
        c.ceo = c.point_of_contact
        c.save()

        # F Expressions can also span joins
        self.assertQuerysetEqual(
            Company.objects.filter(
                ceo__firstname=F("point_of_contact__firstname")),
            [
                "Example Inc.",
            ],
            lambda c: c.name
        )
        c.ceo = old_ceo
        c.save()
        # Guido is point of contanct but not CEO. For the null cases we do
        # not generate a match.
        Company.objects.exclude(
            ceo__firstname=F("point_of_contact__firstname")
        ).update(name="foo")
        self.assertEqual(Company.objects.filter(name="foo").count(), 1)

        self.assertRaises(FieldError,
            lambda: Company.objects.exclude(
                ceo__firstname=F('point_of_contact__firstname')
            ).update(name=F('point_of_contact__lastname'))
        )

    def test_save(self):
        # F expressions can be used to update attributes on single objects
        test_gmbh = Company.objects.get(name="Test GmbH")
        self.assertEqual(test_gmbh.num_employees, 32)
        test_gmbh.num_employees = F("num_employees") + 4
        test_gmbh.save()
        test_gmbh = Company.objects.get(pk=test_gmbh.pk)
        self.assertEqual(test_gmbh.num_employees, 36)

        # F expressions cannot be used to update attributes which are foreign
        # keys, or attributes which involve joins.
        test_gmbh.point_of_contact = None
        test_gmbh.save()
        self.assertTrue(test_gmbh.point_of_contact is None)
        with self.assertRaises(ValueError):
            test_gmbh.point_of_contact = F("ceo")

        test_gmbh.point_of_contact = test_gmbh.ceo
        test_gmbh.save()
        test_gmbh.name = F("ceo__last_name")
        self.assertRaises(FieldError, test_gmbh.save)

        # F expressions cannot be used to update attributes on objects which do
        # not yet exist in the database
        acme = Company(
            name="The Acme Widget Co.", num_employees=12, num_chairs=5,
            ceo=test_gmbh.ceo
        )
        acme.num_employees = F("num_employees") + 16
        self.assertRaises(TypeError, acme.save)
