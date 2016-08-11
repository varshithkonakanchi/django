from unittest import skipUnless

from django.db import connection
from django.test import TestCase

from .models import Article, ArticleTranslation, IndexTogetherSingleList


class SchemaIndexesTests(TestCase):
    """
    Test index handling by the db.backends.schema infrastructure.
    """

    def test_index_name_hash(self):
        """
        Index names should be deterministic.
        """
        with connection.schema_editor() as editor:
            index_name = editor._create_index_name(
                model=Article,
                column_names=("c1",),
                suffix="123",
            )
        self.assertEqual(index_name, "indexes_article_c1_a52bd80b123")

    def test_index_name(self):
        """
        Index names on the built-in database backends::
            * Are truncated as needed.
            * Include all the column names.
            * Include a deterministic hash.
        """
        long_name = 'l%sng' % ('o' * 100)
        with connection.schema_editor() as editor:
            index_name = editor._create_index_name(
                model=Article,
                column_names=('c1', 'c2', long_name),
                suffix='ix',
            )
        expected = {
            'mysql': 'indexes_article_c1_c2_looooooooooooooooooo_255179b2ix',
            'oracle': 'indexes_a_c1_c2_loo_255179b2ix',
            'postgresql': 'indexes_article_c1_c2_loooooooooooooooooo_255179b2ix',
            'sqlite': 'indexes_article_c1_c2_l%sng_255179b2ix' % ('o' * 100),
        }
        if connection.vendor not in expected:
            self.skipTest('This test is only supported on the built-in database backends.')
        self.assertEqual(index_name, expected[connection.vendor])

    def test_index_together(self):
        editor = connection.schema_editor()
        index_sql = editor._model_indexes_sql(Article)
        self.assertEqual(len(index_sql), 1)
        # Ensure the index name is properly quoted
        self.assertIn(
            connection.ops.quote_name(
                editor._create_index_name(Article, ['headline', 'pub_date'], suffix='_idx')
            ),
            index_sql[0]
        )

    def test_index_together_single_list(self):
        # Test for using index_together with a single list (#22172)
        index_sql = connection.schema_editor()._model_indexes_sql(IndexTogetherSingleList)
        self.assertEqual(len(index_sql), 1)

    @skipUnless(connection.vendor == 'postgresql', "This is a postgresql-specific issue")
    def test_postgresql_text_indexes(self):
        """Test creation of PostgreSQL-specific text indexes (#12234)"""
        from .models import IndexedArticle
        index_sql = connection.schema_editor()._model_indexes_sql(IndexedArticle)
        self.assertEqual(len(index_sql), 5)
        self.assertIn('("headline" varchar_pattern_ops)', index_sql[1])
        self.assertIn('("body" text_pattern_ops)', index_sql[3])
        # unique=True and db_index=True should only create the varchar-specific
        # index (#19441).
        self.assertIn('("slug" varchar_pattern_ops)', index_sql[4])

    @skipUnless(connection.vendor == 'postgresql', "This is a postgresql-specific issue")
    def test_postgresql_virtual_relation_indexes(self):
        """Test indexes are not created for related objects"""
        index_sql = connection.schema_editor()._model_indexes_sql(Article)
        self.assertEqual(len(index_sql), 1)

    @skipUnless(connection.vendor == 'mysql', "This is a mysql-specific issue")
    def test_no_index_for_foreignkey(self):
        """
        MySQL on InnoDB already creates indexes automatically for foreign keys.
        (#14180). An index should be created if db_constraint=False (#26171).
        """
        storage = connection.introspection.get_storage_engine(
            connection.cursor(), ArticleTranslation._meta.db_table
        )
        if storage != "InnoDB":
            self.skip("This test only applies to the InnoDB storage engine")
        index_sql = connection.schema_editor()._model_indexes_sql(ArticleTranslation)
        self.assertEqual(index_sql, [
            'CREATE INDEX `indexes_articletranslation_article_no_constraint_id_d6c0806b` '
            'ON `indexes_articletranslation` (`article_no_constraint_id`)'
        ])
