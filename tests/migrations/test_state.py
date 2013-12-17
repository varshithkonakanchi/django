from django.core.apps.cache import AppCache
from django.db import models
from django.db.migrations.state import ProjectState, ModelState, InvalidBasesError
from django.test import TestCase


class StateTests(TestCase):
    """
    Tests state construction, rendering and modification by operations.
    """

    def test_create(self):
        """
        Tests making a ProjectState from an AppCache
        """

        new_app_cache = AppCache()

        class Author(models.Model):
            name = models.CharField(max_length=255)
            bio = models.TextField()
            age = models.IntegerField(blank=True, null=True)

            class Meta:
                app_label = "migrations"
                app_cache = new_app_cache
                unique_together = ["name", "bio"]

        class AuthorProxy(Author):
            class Meta:
                app_label = "migrations"
                app_cache = new_app_cache
                proxy = True
                ordering = ["name"]

        class Book(models.Model):
            title = models.CharField(max_length=1000)
            author = models.ForeignKey(Author)
            contributors = models.ManyToManyField(Author)

            class Meta:
                app_label = "migrations"
                app_cache = new_app_cache
                verbose_name = "tome"
                db_table = "test_tome"

        project_state = ProjectState.from_app_cache(new_app_cache)
        author_state = project_state.models['migrations', 'author']
        author_proxy_state = project_state.models['migrations', 'authorproxy']
        book_state = project_state.models['migrations', 'book']

        self.assertEqual(author_state.app_label, "migrations")
        self.assertEqual(author_state.name, "Author")
        self.assertEqual([x for x, y in author_state.fields], ["id", "name", "bio", "age"])
        self.assertEqual(author_state.fields[1][1].max_length, 255)
        self.assertEqual(author_state.fields[2][1].null, False)
        self.assertEqual(author_state.fields[3][1].null, True)
        self.assertEqual(author_state.options, {"unique_together": {("name", "bio")}})
        self.assertEqual(author_state.bases, (models.Model, ))

        self.assertEqual(book_state.app_label, "migrations")
        self.assertEqual(book_state.name, "Book")
        self.assertEqual([x for x, y in book_state.fields], ["id", "title", "author", "contributors"])
        self.assertEqual(book_state.fields[1][1].max_length, 1000)
        self.assertEqual(book_state.fields[2][1].null, False)
        self.assertEqual(book_state.fields[3][1].__class__.__name__, "ManyToManyField")
        self.assertEqual(book_state.options, {"verbose_name": "tome", "db_table": "test_tome"})
        self.assertEqual(book_state.bases, (models.Model, ))

        self.assertEqual(author_proxy_state.app_label, "migrations")
        self.assertEqual(author_proxy_state.name, "AuthorProxy")
        self.assertEqual(author_proxy_state.fields, [])
        self.assertEqual(author_proxy_state.options, {"proxy": True, "ordering": ["name"]})
        self.assertEqual(author_proxy_state.bases, ("migrations.author", ))

    def test_render(self):
        """
        Tests rendering a ProjectState into an AppCache.
        """
        project_state = ProjectState()
        project_state.add_model_state(ModelState(
            "migrations",
            "Tag",
            [
                ("id", models.AutoField(primary_key=True)),
                ("name", models.CharField(max_length=100)),
                ("hidden", models.BooleanField()),
            ],
            {},
            None,
        ))

        new_app_cache = project_state.render()
        self.assertEqual(new_app_cache.get_model("migrations", "Tag")._meta.get_field_by_name("name")[0].max_length, 100)
        self.assertEqual(new_app_cache.get_model("migrations", "Tag")._meta.get_field_by_name("hidden")[0].null, False)

    def test_render_model_inheritance(self):
        class Book(models.Model):
            title = models.CharField(max_length=1000)

            class Meta:
                app_label = "migrations"
                app_cache = AppCache()

        class Novel(Book):
            class Meta:
                app_label = "migrations"
                app_cache = AppCache()

        # First, test rendering individually
        app_cache = AppCache()

        # We shouldn't be able to render yet
        ms = ModelState.from_model(Novel)
        with self.assertRaises(InvalidBasesError):
            ms.render(app_cache)

        # Once the parent model is in the app cache, it should be fine
        ModelState.from_model(Book).render(app_cache)
        ModelState.from_model(Novel).render(app_cache)

    def test_render_model_with_multiple_inheritance(self):
        class Foo(models.Model):
            class Meta:
                app_label = "migrations"
                app_cache = AppCache()

        class Bar(models.Model):
            class Meta:
                app_label = "migrations"
                app_cache = AppCache()

        class FooBar(Foo, Bar):
            class Meta:
                app_label = "migrations"
                app_cache = AppCache()

        app_cache = AppCache()

        # We shouldn't be able to render yet
        ms = ModelState.from_model(FooBar)
        with self.assertRaises(InvalidBasesError):
            ms.render(app_cache)

        # Once the parent models are in the app cache, it should be fine
        ModelState.from_model(Foo).render(app_cache)
        ModelState.from_model(Bar).render(app_cache)
        ModelState.from_model(FooBar).render(app_cache)

    def test_render_project_dependencies(self):
        """
        Tests that the ProjectState render method correctly renders models
        to account for inter-model base dependencies.
        """
        new_app_cache = AppCache()

        class A(models.Model):
            class Meta:
                app_label = "migrations"
                app_cache = new_app_cache

        class B(A):
            class Meta:
                app_label = "migrations"
                app_cache = new_app_cache

        class C(B):
            class Meta:
                app_label = "migrations"
                app_cache = new_app_cache

        class D(A):
            class Meta:
                app_label = "migrations"
                app_cache = new_app_cache

        class E(B):
            class Meta:
                app_label = "migrations"
                app_cache = new_app_cache
                proxy = True

        class F(D):
            class Meta:
                app_label = "migrations"
                app_cache = new_app_cache
                proxy = True

        # Make a ProjectState and render it
        project_state = ProjectState()
        project_state.add_model_state(ModelState.from_model(A))
        project_state.add_model_state(ModelState.from_model(B))
        project_state.add_model_state(ModelState.from_model(C))
        project_state.add_model_state(ModelState.from_model(D))
        project_state.add_model_state(ModelState.from_model(E))
        project_state.add_model_state(ModelState.from_model(F))
        final_app_cache = project_state.render()
        self.assertEqual(len(final_app_cache.get_models()), 6)

        # Now make an invalid ProjectState and make sure it fails
        project_state = ProjectState()
        project_state.add_model_state(ModelState.from_model(A))
        project_state.add_model_state(ModelState.from_model(B))
        project_state.add_model_state(ModelState.from_model(C))
        project_state.add_model_state(ModelState.from_model(F))
        with self.assertRaises(InvalidBasesError):
            project_state.render()

    def test_equality(self):
        """
        Tests that == and != are implemented correctly.
        """

        # Test two things that should be equal
        project_state = ProjectState()
        project_state.add_model_state(ModelState(
            "migrations",
            "Tag",
            [
                ("id", models.AutoField(primary_key=True)),
                ("name", models.CharField(max_length=100)),
                ("hidden", models.BooleanField()),
            ],
            {},
            None,
        ))
        other_state = project_state.clone()
        self.assertEqual(project_state, project_state)
        self.assertEqual(project_state, other_state)
        self.assertEqual(project_state != project_state, False)
        self.assertEqual(project_state != other_state, False)

        # Make a very small change (max_len 99) and see if that affects it
        project_state = ProjectState()
        project_state.add_model_state(ModelState(
            "migrations",
            "Tag",
            [
                ("id", models.AutoField(primary_key=True)),
                ("name", models.CharField(max_length=99)),
                ("hidden", models.BooleanField()),
            ],
            {},
            None,
        ))
        self.assertNotEqual(project_state, other_state)
        self.assertEqual(project_state == other_state, False)
