from django.template.base import TemplateSyntaxError
from django.template.loader import get_template
from django.test import TestCase

from .utils import render, setup


class NamedEndblockTests(TestCase):

    @setup({'namedendblocks01': '1{% block first %}_{% block second %}'
                                '2{% endblock second %}_{% endblock first %}3'})
    def test_namedendblocks01(self):
        output = render('namedendblocks01')
        self.assertEqual(output, '1_2_3')

    # Unbalanced blocks
    @setup({'namedendblocks02': '1{% block first %}_{% block second %}'
                                '2{% endblock first %}_{% endblock second %}3'})
    def test_namedendblocks02(self):
        with self.assertRaises(TemplateSyntaxError):
            get_template('namedendblocks02')

    @setup({'namedendblocks03': '1{% block first %}_{% block second %}'
                                '2{% endblock %}_{% endblock second %}3'})
    def test_namedendblocks03(self):
        with self.assertRaises(TemplateSyntaxError):
            get_template('namedendblocks03')

    @setup({'namedendblocks04': '1{% block first %}_{% block second %}'
                                '2{% endblock second %}_{% endblock third %}3'})
    def test_namedendblocks04(self):
        with self.assertRaises(TemplateSyntaxError):
            get_template('namedendblocks04')

    @setup({'namedendblocks05': '1{% block first %}_{% block second %}2{% endblock first %}'})
    def test_namedendblocks05(self):
        with self.assertRaises(TemplateSyntaxError):
            get_template('namedendblocks05')

    # Mixed named and unnamed endblocks
    @setup({'namedendblocks06': '1{% block first %}_{% block second %}'
                                '2{% endblock %}_{% endblock first %}3'})
    def test_namedendblocks06(self):
        """
        Mixed named and unnamed endblocks
        """
        output = render('namedendblocks06')
        self.assertEqual(output, '1_2_3')

    @setup({'namedendblocks07': '1{% block first %}_{% block second %}'
                                '2{% endblock second %}_{% endblock %}3'})
    def test_namedendblocks07(self):
        output = render('namedendblocks07')
        self.assertEqual(output, '1_2_3')
