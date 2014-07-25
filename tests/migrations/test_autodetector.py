# -*- coding: utf-8 -*-
from django.test import TestCase, override_settings
from django.db.migrations.autodetector import MigrationAutodetector
from django.db.migrations.questioner import MigrationQuestioner
from django.db.migrations.state import ProjectState, ModelState
from django.db.migrations.graph import MigrationGraph
from django.db.migrations.loader import MigrationLoader
from django.db import models, connection
from django.contrib.auth.models import AbstractBaseUser


class DeconstructableObject(object):
    """
    A custom deconstructable object.
    """

    def deconstruct(self):
        return self.__module__ + '.' + self.__class__.__name__, [], {}


class AutodetectorTests(TestCase):
    """
    Tests the migration autodetector.
    """

    author_empty = ModelState("testapp", "Author", [("id", models.AutoField(primary_key=True))])
    author_name = ModelState("testapp", "Author", [("id", models.AutoField(primary_key=True)), ("name", models.CharField(max_length=200))])
    author_name_longer = ModelState("testapp", "Author", [("id", models.AutoField(primary_key=True)), ("name", models.CharField(max_length=400))])
    author_name_renamed = ModelState("testapp", "Author", [("id", models.AutoField(primary_key=True)), ("names", models.CharField(max_length=200))])
    author_name_default = ModelState("testapp", "Author", [("id", models.AutoField(primary_key=True)), ("name", models.CharField(max_length=200, default='Ada Lovelace'))])
    author_name_deconstructable_1 = ModelState("testapp", "Author", [("id", models.AutoField(primary_key=True)), ("name", models.CharField(max_length=200, default=DeconstructableObject()))])
    author_name_deconstructable_2 = ModelState("testapp", "Author", [("id", models.AutoField(primary_key=True)), ("name", models.CharField(max_length=200, default=DeconstructableObject()))])
    author_name_deconstructable_3 = ModelState("testapp", "Author", [("id", models.AutoField(primary_key=True)), ("name", models.CharField(max_length=200, default=models.IntegerField()))])
    author_name_deconstructable_4 = ModelState("testapp", "Author", [("id", models.AutoField(primary_key=True)), ("name", models.CharField(max_length=200, default=models.IntegerField()))])
    author_with_book = ModelState("testapp", "Author", [("id", models.AutoField(primary_key=True)), ("name", models.CharField(max_length=200)), ("book", models.ForeignKey("otherapp.Book"))])
    author_with_book_order_wrt = ModelState("testapp", "Author", [("id", models.AutoField(primary_key=True)), ("name", models.CharField(max_length=200)), ("book", models.ForeignKey("otherapp.Book"))], options={"order_with_respect_to": "book"})
    author_renamed_with_book = ModelState("testapp", "Writer", [("id", models.AutoField(primary_key=True)), ("name", models.CharField(max_length=200)), ("book", models.ForeignKey("otherapp.Book"))])
    author_with_publisher_string = ModelState("testapp", "Author", [("id", models.AutoField(primary_key=True)), ("name", models.CharField(max_length=200)), ("publisher_name", models.CharField(max_length=200))])
    author_with_publisher = ModelState("testapp", "Author", [("id", models.AutoField(primary_key=True)), ("name", models.CharField(max_length=200)), ("publisher", models.ForeignKey("testapp.Publisher"))])
    author_with_custom_user = ModelState("testapp", "Author", [("id", models.AutoField(primary_key=True)), ("name", models.CharField(max_length=200)), ("user", models.ForeignKey("thirdapp.CustomUser"))])
    author_proxy = ModelState("testapp", "AuthorProxy", [], {"proxy": True}, ("testapp.author", ))
    author_proxy_options = ModelState("testapp", "AuthorProxy", [], {"proxy": True, "verbose_name": "Super Author"}, ("testapp.author", ))
    author_proxy_notproxy = ModelState("testapp", "AuthorProxy", [], {}, ("testapp.author", ))
    author_proxy_third = ModelState("thirdapp", "AuthorProxy", [], {"proxy": True}, ("testapp.author", ))
    author_proxy_proxy = ModelState("testapp", "AAuthorProxyProxy", [], {"proxy": True}, ("testapp.authorproxy", ))
    author_unmanaged = ModelState("testapp", "AuthorUnmanaged", [], {"managed": False}, ("testapp.author", ))
    author_unmanaged_managed = ModelState("testapp", "AuthorUnmanaged", [], {}, ("testapp.author", ))
    author_with_m2m = ModelState("testapp", "Author", [
        ("id", models.AutoField(primary_key=True)),
        ("publishers", models.ManyToManyField("testapp.Publisher")),
    ])
    author_with_m2m_through = ModelState("testapp", "Author", [("id", models.AutoField(primary_key=True)), ("publishers", models.ManyToManyField("testapp.Publisher", through="testapp.Contract"))])
    author_with_options = ModelState("testapp", "Author", [("id", models.AutoField(primary_key=True))], {"verbose_name": "Authi", "permissions": [('can_hire', 'Can hire')]})
    contract = ModelState("testapp", "Contract", [("id", models.AutoField(primary_key=True)), ("author", models.ForeignKey("testapp.Author")), ("publisher", models.ForeignKey("testapp.Publisher"))])
    publisher = ModelState("testapp", "Publisher", [("id", models.AutoField(primary_key=True)), ("name", models.CharField(max_length=100))])
    publisher_with_author = ModelState("testapp", "Publisher", [("id", models.AutoField(primary_key=True)), ("author", models.ForeignKey("testapp.Author")), ("name", models.CharField(max_length=100))])
    publisher_with_book = ModelState("testapp", "Publisher", [("id", models.AutoField(primary_key=True)), ("author", models.ForeignKey("otherapp.Book")), ("name", models.CharField(max_length=100))])
    other_pony = ModelState("otherapp", "Pony", [("id", models.AutoField(primary_key=True))])
    other_stable = ModelState("otherapp", "Stable", [("id", models.AutoField(primary_key=True))])
    third_thing = ModelState("thirdapp", "Thing", [("id", models.AutoField(primary_key=True))])
    book = ModelState("otherapp", "Book", [("id", models.AutoField(primary_key=True)), ("author", models.ForeignKey("testapp.Author")), ("title", models.CharField(max_length=200))])
    book_proxy_fk = ModelState("otherapp", "Book", [("id", models.AutoField(primary_key=True)), ("author", models.ForeignKey("thirdapp.AuthorProxy")), ("title", models.CharField(max_length=200))])
    book_migrations_fk = ModelState("otherapp", "Book", [("id", models.AutoField(primary_key=True)), ("author", models.ForeignKey("migrations.UnmigratedModel")), ("title", models.CharField(max_length=200))])
    book_with_no_author = ModelState("otherapp", "Book", [("id", models.AutoField(primary_key=True)), ("title", models.CharField(max_length=200))])
    book_with_author_renamed = ModelState("otherapp", "Book", [("id", models.AutoField(primary_key=True)), ("author", models.ForeignKey("testapp.Writer")), ("title", models.CharField(max_length=200))])
    book_with_field_and_author_renamed = ModelState("otherapp", "Book", [("id", models.AutoField(primary_key=True)), ("writer", models.ForeignKey("testapp.Writer")), ("title", models.CharField(max_length=200))])
    book_with_multiple_authors = ModelState("otherapp", "Book", [("id", models.AutoField(primary_key=True)), ("authors", models.ManyToManyField("testapp.Author")), ("title", models.CharField(max_length=200))])
    book_with_multiple_authors_through_attribution = ModelState("otherapp", "Book", [("id", models.AutoField(primary_key=True)), ("authors", models.ManyToManyField("testapp.Author", through="otherapp.Attribution")), ("title", models.CharField(max_length=200))])
    book_unique = ModelState("otherapp", "Book", [("id", models.AutoField(primary_key=True)), ("author", models.ForeignKey("testapp.Author")), ("title", models.CharField(max_length=200))], {"unique_together": set([("author", "title")])})
    book_unique_2 = ModelState("otherapp", "Book", [("id", models.AutoField(primary_key=True)), ("author", models.ForeignKey("testapp.Author")), ("title", models.CharField(max_length=200))], {"unique_together": set([("title", "author")])})
    book_unique_3 = ModelState("otherapp", "Book", [("id", models.AutoField(primary_key=True)), ("newfield", models.IntegerField()), ("author", models.ForeignKey("testapp.Author")), ("title", models.CharField(max_length=200))], {"unique_together": set([("title", "newfield")])})
    attribution = ModelState("otherapp", "Attribution", [("id", models.AutoField(primary_key=True)), ("author", models.ForeignKey("testapp.Author")), ("book", models.ForeignKey("otherapp.Book"))])
    edition = ModelState("thirdapp", "Edition", [("id", models.AutoField(primary_key=True)), ("book", models.ForeignKey("otherapp.Book"))])
    custom_user = ModelState("thirdapp", "CustomUser", [("id", models.AutoField(primary_key=True)), ("username", models.CharField(max_length=255))], bases=(AbstractBaseUser, ))
    custom_user_no_inherit = ModelState("thirdapp", "CustomUser", [("id", models.AutoField(primary_key=True)), ("username", models.CharField(max_length=255))])
    aardvark = ModelState("thirdapp", "Aardvark", [("id", models.AutoField(primary_key=True))])
    aardvark_based_on_author = ModelState("testapp", "Aardvark", [], bases=("testapp.Author", ))
    aardvark_pk_fk_author = ModelState("testapp", "Aardvark", [("id", models.OneToOneField("testapp.Author", primary_key=True))])
    knight = ModelState("eggs", "Knight", [("id", models.AutoField(primary_key=True))])
    rabbit = ModelState("eggs", "Rabbit", [("id", models.AutoField(primary_key=True)), ("knight", models.ForeignKey("eggs.Knight")), ("parent", models.ForeignKey("eggs.Rabbit"))], {"unique_together": set([("parent", "knight")])})

    def repr_changes(self, changes):
        output = ""
        for app_label, migrations in sorted(changes.items()):
            output += "  %s:\n" % app_label
            for migration in migrations:
                output += "    %s\n" % migration.name
                for operation in migration.operations:
                    output += "      %s\n" % operation
        return output

    def assertNumberMigrations(self, changes, app_label, number):
        if len(changes.get(app_label, [])) != number:
            self.fail("Incorrect number of migrations (%s) for %s (expected %s)\n%s" % (
                len(changes.get(app_label, [])),
                app_label,
                number,
                self.repr_changes(changes),
            ))

    def assertOperationTypes(self, changes, app_label, index, types):
        if not changes.get(app_label, None):
            self.fail("No migrations found for %s\n%s" % (app_label, self.repr_changes(changes)))
        if len(changes[app_label]) < index + 1:
            self.fail("No migration at index %s for %s\n%s" % (index, app_label, self.repr_changes(changes)))
        migration = changes[app_label][index]
        real_types = [operation.__class__.__name__ for operation in migration.operations]
        if types != real_types:
            self.fail("Operation type mismatch for %s.%s (expected %s):\n%s" % (
                app_label,
                migration.name,
                types,
                self.repr_changes(changes),
            ))

    def assertOperationAttributes(self, changes, app_label, index, operation_index, **attrs):
        if not changes.get(app_label, None):
            self.fail("No migrations found for %s\n%s" % (app_label, self.repr_changes(changes)))
        if len(changes[app_label]) < index + 1:
            self.fail("No migration at index %s for %s\n%s" % (index, app_label, self.repr_changes(changes)))
        migration = changes[app_label][index]
        if len(changes[app_label]) < index + 1:
            self.fail("No operation at index %s for %s.%s\n%s" % (
                operation_index,
                app_label,
                migration.name,
                self.repr_changes(changes),
            ))
        operation = migration.operations[operation_index]
        for attr, value in attrs.items():
            if getattr(operation, attr, None) != value:
                self.fail("Attribute mismatch for %s.%s op #%s, %s (expected %r):\n%s" % (
                    app_label,
                    migration.name,
                    operation_index + 1,
                    attr,
                    value,
                    self.repr_changes(changes),
                ))

    def make_project_state(self, model_states):
        "Shortcut to make ProjectStates from lists of predefined models"
        project_state = ProjectState()
        for model_state in model_states:
            project_state.add_model_state(model_state.clone())
        return project_state

    def test_arrange_for_graph(self):
        "Tests auto-naming of migrations for graph matching."
        # Make a fake graph
        graph = MigrationGraph()
        graph.add_node(("testapp", "0001_initial"), None)
        graph.add_node(("testapp", "0002_foobar"), None)
        graph.add_node(("otherapp", "0001_initial"), None)
        graph.add_dependency(("testapp", "0002_foobar"), ("testapp", "0001_initial"))
        graph.add_dependency(("testapp", "0002_foobar"), ("otherapp", "0001_initial"))
        # Use project state to make a new migration change set
        before = self.make_project_state([])
        after = self.make_project_state([self.author_empty, self.other_pony, self.other_stable])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Run through arrange_for_graph
        changes = autodetector.arrange_for_graph(changes, graph)
        # Make sure there's a new name, deps match, etc.
        self.assertEqual(changes["testapp"][0].name, "0003_author")
        self.assertEqual(changes["testapp"][0].dependencies, [("testapp", "0002_foobar")])
        self.assertEqual(changes["otherapp"][0].name, "0002_pony_stable")
        self.assertEqual(changes["otherapp"][0].dependencies, [("otherapp", "0001_initial")])

    def test_trim_apps(self):
        "Tests that trim does not remove dependencies but does remove unwanted apps"
        # Use project state to make a new migration change set
        before = self.make_project_state([])
        after = self.make_project_state([self.author_empty, self.other_pony, self.other_stable, self.third_thing])
        autodetector = MigrationAutodetector(before, after, MigrationQuestioner(defaults={"ask_initial": True}))
        changes = autodetector._detect_changes()
        # Run through arrange_for_graph
        graph = MigrationGraph()
        changes = autodetector.arrange_for_graph(changes, graph)
        changes["testapp"][0].dependencies.append(("otherapp", "0001_initial"))
        changes = autodetector._trim_to_apps(changes, set(["testapp"]))
        # Make sure there's the right set of migrations
        self.assertEqual(changes["testapp"][0].name, "0001_initial")
        self.assertEqual(changes["otherapp"][0].name, "0001_initial")
        self.assertNotIn("thirdapp", changes)

    def test_new_model(self):
        "Tests autodetection of new models"
        # Make state
        before = self.make_project_state([])
        after = self.make_project_state([self.author_empty])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertEqual(len(changes['testapp']), 1)
        # Right number of actions?
        migration = changes['testapp'][0]
        self.assertEqual(len(migration.operations), 1)
        # Right action?
        action = migration.operations[0]
        self.assertEqual(action.__class__.__name__, "CreateModel")
        self.assertEqual(action.name, "Author")

    def test_old_model(self):
        "Tests deletion of old models"
        # Make state
        before = self.make_project_state([self.author_empty])
        after = self.make_project_state([])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertEqual(len(changes['testapp']), 1)
        # Right number of actions?
        migration = changes['testapp'][0]
        self.assertEqual(len(migration.operations), 1)
        # Right action?
        action = migration.operations[0]
        self.assertEqual(action.__class__.__name__, "DeleteModel")
        self.assertEqual(action.name, "Author")

    def test_add_field(self):
        "Tests autodetection of new fields"
        # Make state
        before = self.make_project_state([self.author_empty])
        after = self.make_project_state([self.author_name])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertEqual(len(changes['testapp']), 1)
        # Right number of actions?
        migration = changes['testapp'][0]
        self.assertEqual(len(migration.operations), 1)
        # Right action?
        action = migration.operations[0]
        self.assertEqual(action.__class__.__name__, "AddField")
        self.assertEqual(action.name, "name")

    def test_remove_field(self):
        "Tests autodetection of removed fields"
        # Make state
        before = self.make_project_state([self.author_name])
        after = self.make_project_state([self.author_empty])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertEqual(len(changes['testapp']), 1)
        # Right number of actions?
        migration = changes['testapp'][0]
        self.assertEqual(len(migration.operations), 1)
        # Right action?
        action = migration.operations[0]
        self.assertEqual(action.__class__.__name__, "RemoveField")
        self.assertEqual(action.name, "name")

    def test_alter_field(self):
        "Tests autodetection of new fields"
        # Make state
        before = self.make_project_state([self.author_name])
        after = self.make_project_state([self.author_name_longer])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertEqual(len(changes['testapp']), 1)
        # Right number of actions?
        migration = changes['testapp'][0]
        self.assertEqual(len(migration.operations), 1)
        # Right action?
        action = migration.operations[0]
        self.assertEqual(action.__class__.__name__, "AlterField")
        self.assertEqual(action.name, "name")

    def test_rename_field(self):
        "Tests autodetection of renamed fields"
        # Make state
        before = self.make_project_state([self.author_name])
        after = self.make_project_state([self.author_name_renamed])
        autodetector = MigrationAutodetector(before, after, MigrationQuestioner({"ask_rename": True}))
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertEqual(len(changes['testapp']), 1)
        # Right number of actions?
        migration = changes['testapp'][0]
        self.assertEqual(len(migration.operations), 1)
        # Right action?
        action = migration.operations[0]
        self.assertEqual(action.__class__.__name__, "RenameField")
        self.assertEqual(action.old_name, "name")
        self.assertEqual(action.new_name, "names")

    def test_rename_model(self):
        "Tests autodetection of renamed models"
        # Make state
        before = self.make_project_state([self.author_with_book, self.book])
        after = self.make_project_state([self.author_renamed_with_book, self.book_with_author_renamed])
        autodetector = MigrationAutodetector(before, after, MigrationQuestioner({"ask_rename_model": True}))
        changes = autodetector._detect_changes()

        # Right number of migrations for model rename?
        self.assertNumberMigrations(changes, 'testapp', 1)
        # Right number of actions?
        migration = changes['testapp'][0]
        self.assertEqual(len(migration.operations), 1)
        # Right action?
        action = migration.operations[0]
        self.assertEqual(action.__class__.__name__, "RenameModel")
        self.assertEqual(action.old_name, "Author")
        self.assertEqual(action.new_name, "Writer")
        # Now that RenameModel handles related fields too, there should be
        # no AlterField for the related field.
        self.assertNumberMigrations(changes, 'otherapp', 0)

    def test_rename_model_with_renamed_rel_field(self):
        """
        Tests autodetection of renamed models while simultaneously renaming one
        of the fields that relate to the renamed model.
        """
        # Make state
        before = self.make_project_state([self.author_with_book, self.book])
        after = self.make_project_state([self.author_renamed_with_book, self.book_with_field_and_author_renamed])
        autodetector = MigrationAutodetector(before, after, MigrationQuestioner({"ask_rename_model": True, "ask_rename": True}))
        changes = autodetector._detect_changes()
        # Right number of migrations for model rename?
        self.assertNumberMigrations(changes, 'testapp', 1)
        # Right number of actions?
        migration = changes['testapp'][0]
        self.assertEqual(len(migration.operations), 1)
        # Right actions?
        action = migration.operations[0]
        self.assertEqual(action.__class__.__name__, "RenameModel")
        self.assertEqual(action.old_name, "Author")
        self.assertEqual(action.new_name, "Writer")
        # Right number of migrations for related field rename?
        # Alter is already taken care of.
        self.assertNumberMigrations(changes, 'otherapp', 1)
        # Right number of actions?
        migration = changes['otherapp'][0]
        self.assertEqual(len(migration.operations), 1)
        # Right actions?
        action = migration.operations[0]
        self.assertEqual(action.__class__.__name__, "RenameField")
        self.assertEqual(action.old_name, "author")
        self.assertEqual(action.new_name, "writer")

    def test_fk_dependency(self):
        "Tests that having a ForeignKey automatically adds a dependency"
        # Make state
        # Note that testapp (author) has no dependencies,
        # otherapp (book) depends on testapp (author),
        # thirdapp (edition) depends on otherapp (book)
        before = self.make_project_state([])
        after = self.make_project_state([self.author_name, self.book, self.edition])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertEqual(len(changes['testapp']), 1)
        self.assertEqual(len(changes['otherapp']), 1)
        self.assertEqual(len(changes['thirdapp']), 1)
        # Right number of actions?
        migration1 = changes['testapp'][0]
        self.assertEqual(len(migration1.operations), 1)
        migration2 = changes['otherapp'][0]
        self.assertEqual(len(migration2.operations), 1)
        migration3 = changes['thirdapp'][0]
        self.assertEqual(len(migration3.operations), 1)
        # Right actions?
        action = migration1.operations[0]
        self.assertEqual(action.__class__.__name__, "CreateModel")
        action = migration2.operations[0]
        self.assertEqual(action.__class__.__name__, "CreateModel")
        action = migration3.operations[0]
        self.assertEqual(action.__class__.__name__, "CreateModel")
        # Right dependencies?
        self.assertEqual(migration1.dependencies, [])
        self.assertEqual(migration2.dependencies, [("testapp", "auto_1")])
        self.assertEqual(migration3.dependencies, [("otherapp", "auto_1")])

    def test_proxy_fk_dependency(self):
        "Tests that FK dependencies still work on proxy models"
        # Make state
        # Note that testapp (author) has no dependencies,
        # otherapp (book) depends on testapp (authorproxy)
        before = self.make_project_state([])
        after = self.make_project_state([self.author_empty, self.author_proxy_third, self.book_proxy_fk])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertNumberMigrations(changes, 'testapp', 1)
        self.assertNumberMigrations(changes, 'otherapp', 1)
        self.assertNumberMigrations(changes, 'thirdapp', 1)
        # Right number of actions?
        # Right actions?
        self.assertOperationTypes(changes, 'otherapp', 0, ["CreateModel"])
        self.assertOperationTypes(changes, 'testapp', 0, ["CreateModel"])
        self.assertOperationTypes(changes, 'thirdapp', 0, ["CreateModel"])
        # Right dependencies?
        self.assertEqual(changes['testapp'][0].dependencies, [])
        self.assertEqual(changes['otherapp'][0].dependencies, [("thirdapp", "auto_1")])
        self.assertEqual(changes['thirdapp'][0].dependencies, [("testapp", "auto_1")])

    def test_same_app_no_fk_dependency(self):
        """
        Tests that a migration with a FK between two models of the same app
        does not have a dependency to itself.
        """
        # Make state
        before = self.make_project_state([])
        after = self.make_project_state([self.author_with_publisher, self.publisher])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertEqual(len(changes['testapp']), 1)
        # Right number of actions?
        migration = changes['testapp'][0]
        self.assertEqual(len(migration.operations), 3)
        # Right actions?
        action = migration.operations[0]
        self.assertEqual(action.__class__.__name__, "CreateModel")
        action = migration.operations[1]
        self.assertEqual(action.__class__.__name__, "CreateModel")
        # Third action might vanish one day if the optimizer improves.
        action = migration.operations[2]
        self.assertEqual(action.__class__.__name__, "AddField")
        # Right dependencies?
        self.assertEqual(migration.dependencies, [])

    def test_circular_fk_dependency(self):
        """
        Tests that having a circular ForeignKey dependency automatically
        resolves the situation into 2 migrations on one side and 1 on the other.
        """
        # Make state
        before = self.make_project_state([])
        after = self.make_project_state([self.author_with_book, self.book, self.publisher_with_book])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertEqual(len(changes['testapp']), 1)
        self.assertEqual(len(changes['otherapp']), 2)
        # Right number of actions?
        migration1 = changes['testapp'][0]
        self.assertEqual(len(migration1.operations), 2)
        migration2 = changes['otherapp'][0]
        self.assertEqual(len(migration2.operations), 1)
        migration3 = changes['otherapp'][1]
        self.assertEqual(len(migration3.operations), 1)
        # Right actions?
        action = migration1.operations[0]
        self.assertEqual(action.__class__.__name__, "CreateModel")
        self.assertEqual(action.name, "Author")
        self.assertEqual(len(action.fields), 3)
        action = migration2.operations[0]
        self.assertEqual(action.__class__.__name__, "CreateModel")
        self.assertEqual(len(action.fields), 2)
        action = migration3.operations[0]
        self.assertEqual(action.__class__.__name__, "AddField")
        self.assertEqual(action.name, "author")
        # Right dependencies?
        self.assertEqual(migration1.dependencies, [("otherapp", "auto_1")])
        self.assertEqual(migration2.dependencies, [])
        self.assertEqual(set(migration3.dependencies), set([("testapp", "auto_1"), ("otherapp", "auto_1")]))

    def test_same_app_circular_fk_dependency(self):
        """
        Tests that a migration with a FK between two models of the same app
        does not have a dependency to itself.
        """
        # Make state
        before = self.make_project_state([])
        after = self.make_project_state([self.author_with_publisher, self.publisher_with_author])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertEqual(len(changes['testapp']), 1)
        # Right number of actions?
        migration1 = changes['testapp'][0]
        self.assertEqual(len(migration1.operations), 4)
        # Right actions?
        action = migration1.operations[0]
        self.assertEqual(action.__class__.__name__, "CreateModel")
        action = migration1.operations[1]
        self.assertEqual(action.__class__.__name__, "CreateModel")
        action = migration1.operations[2]
        self.assertEqual(action.__class__.__name__, "AddField")
        self.assertEqual(action.name, "publisher")
        action = migration1.operations[3]
        self.assertEqual(action.__class__.__name__, "AddField")
        self.assertEqual(action.name, "author")
        # Right dependencies?
        self.assertEqual(migration1.dependencies, [])

    def test_same_app_circular_fk_dependency_and_unique_together(self):
        """
        Tests that a migration with circular FK dependency does not try to
        create unique together constraint before creating all required fields first.
        See ticket #22275.
        """
        # Make state
        before = self.make_project_state([])
        after = self.make_project_state([self.knight, self.rabbit])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertEqual(len(changes['eggs']), 1)
        # Right number of actions?
        migration1 = changes['eggs'][0]
        self.assertEqual(len(migration1.operations), 3)
        # Right actions?
        action = migration1.operations[0]
        self.assertEqual(action.__class__.__name__, "CreateModel")
        action = migration1.operations[1]
        self.assertEqual(action.__class__.__name__, "CreateModel")
        self.assertEqual(action.name, "Rabbit")
        self.assertFalse("unique_together" in action.options)
        action = migration1.operations[2]
        self.assertEqual(action.__class__.__name__, "AlterUniqueTogether")
        self.assertEqual(action.name, "rabbit")
        # Right dependencies?
        self.assertEqual(migration1.dependencies, [])

    def test_unique_together(self):
        "Tests unique_together detection"
        # Make state
        before = self.make_project_state([self.author_empty, self.book])
        after = self.make_project_state([self.author_empty, self.book_unique])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertEqual(len(changes['otherapp']), 1)
        # Right number of actions?
        migration = changes['otherapp'][0]
        self.assertEqual(len(migration.operations), 1)
        # Right action?
        action = migration.operations[0]
        self.assertEqual(action.__class__.__name__, "AlterUniqueTogether")
        self.assertEqual(action.name, "book")
        self.assertEqual(action.unique_together, set([("author", "title")]))

    def test_unique_together_no_changes(self):
        "Tests that unique_togther doesn't generate a migration if no changes have been made"
        # Make state
        before = self.make_project_state([self.author_empty, self.book_unique])
        after = self.make_project_state([self.author_empty, self.book_unique])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertEqual(len(changes), 0)

    def test_unique_together_ordering(self):
        "Tests that unique_together also triggers on ordering changes"
        # Make state
        before = self.make_project_state([self.author_empty, self.book_unique])
        after = self.make_project_state([self.author_empty, self.book_unique_2])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertEqual(len(changes['otherapp']), 1)
        # Right number of actions?
        migration = changes['otherapp'][0]
        self.assertEqual(len(migration.operations), 1)
        # Right action?
        action = migration.operations[0]
        self.assertEqual(action.__class__.__name__, "AlterUniqueTogether")
        self.assertEqual(action.name, "book")
        self.assertEqual(action.unique_together, set([("title", "author")]))

    def test_add_field_and_unique_together(self):
        "Tests that added fields will be created before using them in unique together"
        before = self.make_project_state([self.author_empty, self.book])
        after = self.make_project_state([self.author_empty, self.book_unique_3])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertEqual(len(changes['otherapp']), 1)
        # Right number of actions?
        migration = changes['otherapp'][0]
        self.assertEqual(len(migration.operations), 2)
        # Right actions order?
        action1 = migration.operations[0]
        action2 = migration.operations[1]
        self.assertEqual(action1.__class__.__name__, "AddField")
        self.assertEqual(action2.__class__.__name__, "AlterUniqueTogether")
        self.assertEqual(action2.unique_together, set([("title", "newfield")]))

    def test_remove_index_together(self):
        author_index_together = ModelState("testapp", "Author", [
            ("id", models.AutoField(primary_key=True)), ("name", models.CharField(max_length=200))
        ], {"index_together": set([("id", "name")])})

        before = self.make_project_state([author_index_together])
        after = self.make_project_state([self.author_name])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertEqual(len(changes['testapp']), 1)
        migration = changes['testapp'][0]
        # Right number of actions?
        self.assertEqual(len(migration.operations), 1)
        # Right actions?
        action = migration.operations[0]
        self.assertEqual(action.__class__.__name__, "AlterIndexTogether")
        self.assertEqual(action.index_together, None)

    def test_remove_unique_together(self):
        author_unique_together = ModelState("testapp", "Author", [
            ("id", models.AutoField(primary_key=True)), ("name", models.CharField(max_length=200))
        ], {"unique_together": set([("id", "name")])})

        before = self.make_project_state([author_unique_together])
        after = self.make_project_state([self.author_name])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertEqual(len(changes['testapp']), 1)
        migration = changes['testapp'][0]
        # Right number of actions?
        self.assertEqual(len(migration.operations), 1)
        # Right actions?
        action = migration.operations[0]
        self.assertEqual(action.__class__.__name__, "AlterUniqueTogether")
        self.assertEqual(action.unique_together, None)

    def test_proxy(self):
        "Tests that the autodetector correctly deals with proxy models"
        # First, we test adding a proxy model
        before = self.make_project_state([self.author_empty])
        after = self.make_project_state([self.author_empty, self.author_proxy])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["CreateModel"])
        self.assertOperationAttributes(changes, "testapp", 0, 0, name="AuthorProxy", options={"proxy": True})

        # Now, we test turning a proxy model into a non-proxy model
        # It should delete the proxy then make the real one
        before = self.make_project_state([self.author_empty, self.author_proxy])
        after = self.make_project_state([self.author_empty, self.author_proxy_notproxy])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        self.assertOperationTypes(changes, "testapp", 0, ["DeleteModel", "CreateModel"])
        self.assertOperationAttributes(changes, "testapp", 0, 0, name="AuthorProxy")
        self.assertOperationAttributes(changes, "testapp", 0, 1, name="AuthorProxy", options={})

    def test_unmanaged_ignorance(self):
        "Tests that the autodetector correctly ignores managed models"
        # First, we test adding an unmanaged model
        before = self.make_project_state([self.author_empty])
        after = self.make_project_state([self.author_empty, self.author_unmanaged])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertEqual(len(changes), 0)

        # Now, we test turning an unmanaged model into a managed model
        before = self.make_project_state([self.author_empty, self.author_unmanaged])
        after = self.make_project_state([self.author_empty, self.author_unmanaged_managed])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertEqual(len(changes['testapp']), 1)
        # Right number of actions?
        migration = changes['testapp'][0]
        self.assertEqual(len(migration.operations), 1)
        # Right action?
        action = migration.operations[0]
        self.assertEqual(action.__class__.__name__, "CreateModel")
        self.assertEqual(action.name, "AuthorUnmanaged")

    @override_settings(AUTH_USER_MODEL="thirdapp.CustomUser")
    def test_swappable(self):
        before = self.make_project_state([self.custom_user])
        after = self.make_project_state([self.custom_user, self.author_with_custom_user])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertEqual(len(changes), 1)
        # Check the dependency is correct
        migration = changes['testapp'][0]
        self.assertEqual(migration.dependencies, [("__setting__", "AUTH_USER_MODEL")])

    def test_add_field_with_default(self):
        """
        Adding a field with a default should work (#22030).
        """
        # Make state
        before = self.make_project_state([self.author_empty])
        after = self.make_project_state([self.author_name_default])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertEqual(len(changes['testapp']), 1)
        # Right number of actions?
        migration = changes['testapp'][0]
        self.assertEqual(len(migration.operations), 1)
        # Right action?
        action = migration.operations[0]
        self.assertEqual(action.__class__.__name__, "AddField")
        self.assertEqual(action.name, "name")

    def test_custom_deconstructable(self):
        """
        Two instances which deconstruct to the same value aren't considered a
        change.
        """
        before = self.make_project_state([self.author_name_deconstructable_1])
        after = self.make_project_state([self.author_name_deconstructable_2])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        self.assertEqual(changes, {})

    def test_deconstruct_field_kwarg(self):
        """
        Field instances are handled correctly by nested deconstruction.
        """
        before = self.make_project_state([self.author_name_deconstructable_3])
        after = self.make_project_state([self.author_name_deconstructable_4])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        self.assertEqual(changes, {})

    def test_replace_string_with_foreignkey(self):
        """
        Adding an FK in the same "spot" as a deleted CharField should work. (#22300).
        """
        # Make state
        before = self.make_project_state([self.author_with_publisher_string])
        after = self.make_project_state([self.author_with_publisher, self.publisher])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertEqual(len(changes['testapp']), 1)
        # Right number of actions?
        migration = changes['testapp'][0]
        self.assertEqual(len(migration.operations), 3)
        # Right actions?
        action = migration.operations[0]
        self.assertEqual(action.__class__.__name__, "CreateModel")
        self.assertEqual(action.name, "Publisher")
        action = migration.operations[1]
        self.assertEqual(action.__class__.__name__, "AddField")
        self.assertEqual(action.name, "publisher")
        action = migration.operations[2]
        self.assertEqual(action.__class__.__name__, "RemoveField")
        self.assertEqual(action.name, "publisher_name")

    def test_foreign_key_removed_before_target_model(self):
        """
        Removing an FK and the model it targets in the same change must remove
        the FK field before the model to maintain consistency.
        """
        before = self.make_project_state([self.author_with_publisher, self.publisher])
        after = self.make_project_state([self.author_name])  # removes both the model and FK
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertEqual(len(changes['testapp']), 1)
        # Right number of actions?
        migration = changes['testapp'][0]
        self.assertEqual(len(migration.operations), 2)
        # Right actions in right order?
        action = migration.operations[0]
        self.assertEqual(action.__class__.__name__, "RemoveField")
        self.assertEqual(action.name, "publisher")
        action = migration.operations[1]
        self.assertEqual(action.__class__.__name__, "DeleteModel")
        self.assertEqual(action.name, "Publisher")

    def test_add_many_to_many(self):
        """
        Adding a ManyToManyField should not prompt for a default (#22435).
        """
        class CustomQuestioner(MigrationQuestioner):
            def ask_not_null_addition(self, field_name, model_name):
                raise Exception("Should not have prompted for not null addition")

        before = self.make_project_state([self.author_empty, self.publisher])
        # Add ManyToManyField to author model
        after = self.make_project_state([self.author_with_m2m, self.publisher])
        autodetector = MigrationAutodetector(before, after, CustomQuestioner())
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertEqual(len(changes['testapp']), 1)
        migration = changes['testapp'][0]
        # Right actions in right order?
        self.assertEqual(len(migration.operations), 1)
        action = migration.operations[0]
        self.assertEqual(action.__class__.__name__, "AddField")
        self.assertEqual(action.name, "publishers")

    def test_create_with_through_model(self):
        """
        Adding a m2m with a through model and the models that use it should
        be ordered correctly.
        """
        before = self.make_project_state([])
        after = self.make_project_state([self.author_with_m2m_through, self.publisher, self.contract])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        # Right actions in right order?
        self.assertOperationTypes(changes, "testapp", 0, ["CreateModel", "CreateModel", "CreateModel", "AddField", "AddField"])

    def test_many_to_many_removed_before_through_model(self):
        """
        Removing a ManyToManyField and the "through" model in the same change must remove
        the field before the model to maintain consistency.
        """
        before = self.make_project_state([self.book_with_multiple_authors_through_attribution, self.author_name, self.attribution])
        after = self.make_project_state([self.book_with_no_author, self.author_name])  # removes both the through model and ManyToMany
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertEqual(len(changes['otherapp']), 1)
        # Right number of actions?
        migration = changes['otherapp'][0]
        self.assertEqual(len(migration.operations), 4)
        # Right actions in right order?
        # The first two are because we can't optimise RemoveField
        # into DeleteModel reliably.
        action = migration.operations[0]
        self.assertEqual(action.__class__.__name__, "RemoveField")
        self.assertEqual(action.name, "author")
        action = migration.operations[1]
        self.assertEqual(action.__class__.__name__, "RemoveField")
        self.assertEqual(action.name, "book")
        action = migration.operations[2]
        self.assertEqual(action.__class__.__name__, "RemoveField")
        self.assertEqual(action.name, "authors")
        action = migration.operations[3]
        self.assertEqual(action.__class__.__name__, "DeleteModel")
        self.assertEqual(action.name, "Attribution")

    def test_many_to_many_removed_before_through_model_2(self):
        """
        Removing a model that contains a ManyToManyField and the
        "through" model in the same change must remove
        the field before the model to maintain consistency.
        """
        before = self.make_project_state([self.book_with_multiple_authors_through_attribution, self.author_name, self.attribution])
        after = self.make_project_state([self.author_name])  # removes both the through model and ManyToMany
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertNumberMigrations(changes, 'otherapp', 1)
        # Right number of actions?
        self.assertOperationTypes(changes, 'otherapp', 0, ["RemoveField", "RemoveField", "RemoveField", "DeleteModel", "DeleteModel"])

    def test_m2m_w_through_multistep_remove(self):
        """
        A model with a m2m field that specifies a "through" model cannot be removed in the same
        migration as that through model as the schema will pass through an inconsistent state.
        The autodetector should produce two migrations to avoid this issue.
        """
        before = self.make_project_state([self.author_with_m2m_through, self.publisher, self.contract])
        after = self.make_project_state([self.publisher])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        # Right actions in right order?
        self.assertOperationTypes(changes, "testapp", 0, ["RemoveField", "RemoveField", "DeleteModel", "RemoveField", "DeleteModel"])
        # Actions touching the right stuff?
        self.assertOperationAttributes(changes, "testapp", 0, 0, name="publishers")
        self.assertOperationAttributes(changes, "testapp", 0, 1, name="author")
        self.assertOperationAttributes(changes, "testapp", 0, 2, name="Author")
        self.assertOperationAttributes(changes, "testapp", 0, 3, name="publisher")
        self.assertOperationAttributes(changes, "testapp", 0, 4, name="Contract")

    def test_non_circular_foreignkey_dependency_removal(self):
        """
        If two models with a ForeignKey from one to the other are removed at the same time,
        the autodetector should remove them in the correct order.
        """
        before = self.make_project_state([self.author_with_publisher, self.publisher_with_author])
        after = self.make_project_state([])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        # Right actions in right order?
        self.assertOperationTypes(changes, "testapp", 0, ["RemoveField", "RemoveField", "DeleteModel", "DeleteModel"])

    def test_alter_model_options(self):
        """
        Changing a model's options should make a change
        """
        before = self.make_project_state([self.author_empty])
        after = self.make_project_state([self.author_with_options])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        # Right actions in right order?
        self.assertOperationTypes(changes, "testapp", 0, ["AlterModelOptions"])

    def test_alter_model_options_proxy(self):
        """
        Changing a proxy model's options should also make a change
        """
        before = self.make_project_state([self.author_proxy, self.author_empty])
        after = self.make_project_state([self.author_proxy_options, self.author_empty])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertNumberMigrations(changes, "testapp", 1)
        # Right actions in right order?
        self.assertOperationTypes(changes, "testapp", 0, ["AlterModelOptions"])

    def test_set_alter_order_with_respect_to(self):
        "Tests that setting order_with_respect_to adds a field"
        # Make state
        before = self.make_project_state([self.book, self.author_with_book])
        after = self.make_project_state([self.book, self.author_with_book_order_wrt])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertNumberMigrations(changes, 'testapp', 1)
        self.assertOperationTypes(changes, 'testapp', 0, ["AlterOrderWithRespectTo"])
        self.assertOperationAttributes(changes, 'testapp', 0, 0, name="author", order_with_respect_to="book")

    def test_add_alter_order_with_respect_to(self):
        """
        Tests that setting order_with_respect_to when adding the FK too
        does things in the right order.
        """
        # Make state
        before = self.make_project_state([self.author_name])
        after = self.make_project_state([self.book, self.author_with_book_order_wrt])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertNumberMigrations(changes, 'testapp', 1)
        self.assertOperationTypes(changes, 'testapp', 0, ["AddField", "AlterOrderWithRespectTo"])
        self.assertOperationAttributes(changes, 'testapp', 0, 0, model_name="author", name="book")
        self.assertOperationAttributes(changes, 'testapp', 0, 1, name="author", order_with_respect_to="book")

    def test_remove_alter_order_with_respect_to(self):
        """
        Tests that removing order_with_respect_to when removing the FK too
        does things in the right order.
        """
        # Make state
        before = self.make_project_state([self.book, self.author_with_book_order_wrt])
        after = self.make_project_state([self.author_name])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertNumberMigrations(changes, 'testapp', 1)
        self.assertOperationTypes(changes, 'testapp', 0, ["AlterOrderWithRespectTo", "RemoveField"])
        self.assertOperationAttributes(changes, 'testapp', 0, 0, name="author", order_with_respect_to=None)
        self.assertOperationAttributes(changes, 'testapp', 0, 1, model_name="author", name="book")

    def test_add_model_order_with_respect_to(self):
        """
        Tests that setting order_with_respect_to when adding the whole model
        does things in the right order.
        """
        # Make state
        before = self.make_project_state([])
        after = self.make_project_state([self.book, self.author_with_book_order_wrt])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertNumberMigrations(changes, 'testapp', 1)
        self.assertOperationTypes(changes, 'testapp', 0, ["CreateModel", "AlterOrderWithRespectTo"])
        self.assertOperationAttributes(changes, 'testapp', 0, 1, name="author", order_with_respect_to="book")
        # Make sure the _order field is not in the CreateModel fields
        self.assertNotIn("_order", [name for name, field in changes['testapp'][0].operations[0].fields])

    def test_swappable_first_inheritance(self):
        """
        Tests that swappable models get their CreateModel first.
        """
        # Make state
        before = self.make_project_state([])
        after = self.make_project_state([self.custom_user, self.aardvark])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertNumberMigrations(changes, 'thirdapp', 1)
        self.assertOperationTypes(changes, 'thirdapp', 0, ["CreateModel", "CreateModel"])
        self.assertOperationAttributes(changes, 'thirdapp', 0, 0, name="CustomUser")
        self.assertOperationAttributes(changes, 'thirdapp', 0, 1, name="Aardvark")

    @override_settings(AUTH_USER_MODEL="thirdapp.CustomUser")
    def test_swappable_first_setting(self):
        """
        Tests that swappable models get their CreateModel first.
        """
        # Make state
        before = self.make_project_state([])
        after = self.make_project_state([self.custom_user_no_inherit, self.aardvark])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertNumberMigrations(changes, 'thirdapp', 1)
        self.assertOperationTypes(changes, 'thirdapp', 0, ["CreateModel", "CreateModel"])
        self.assertOperationAttributes(changes, 'thirdapp', 0, 0, name="CustomUser")
        self.assertOperationAttributes(changes, 'thirdapp', 0, 1, name="Aardvark")

    def test_bases_first(self):
        """
        Tests that bases of other models come first.
        """
        # Make state
        before = self.make_project_state([])
        after = self.make_project_state([self.aardvark_based_on_author, self.author_name])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertNumberMigrations(changes, 'testapp', 1)
        self.assertOperationTypes(changes, 'testapp', 0, ["CreateModel", "CreateModel"])
        self.assertOperationAttributes(changes, 'testapp', 0, 0, name="Author")
        self.assertOperationAttributes(changes, 'testapp', 0, 1, name="Aardvark")

    def test_proxy_bases_first(self):
        """
        Tests that bases of proxies come first.
        """
        # Make state
        before = self.make_project_state([])
        after = self.make_project_state([self.author_empty, self.author_proxy, self.author_proxy_proxy])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertNumberMigrations(changes, 'testapp', 1)
        self.assertOperationTypes(changes, 'testapp', 0, ["CreateModel", "CreateModel", "CreateModel"])
        self.assertOperationAttributes(changes, 'testapp', 0, 0, name="Author")
        self.assertOperationAttributes(changes, 'testapp', 0, 1, name="AuthorProxy")
        self.assertOperationAttributes(changes, 'testapp', 0, 2, name="AAuthorProxyProxy")

    def test_pk_fk_included(self):
        """
        Tests that a relation used as the primary key is kept as part of CreateModel.
        """
        # Make state
        before = self.make_project_state([])
        after = self.make_project_state([self.aardvark_pk_fk_author, self.author_name])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertNumberMigrations(changes, 'testapp', 1)
        self.assertOperationTypes(changes, 'testapp', 0, ["CreateModel", "CreateModel"])
        self.assertOperationAttributes(changes, 'testapp', 0, 0, name="Author")
        self.assertOperationAttributes(changes, 'testapp', 0, 1, name="Aardvark")

    def test_first_dependency(self):
        """
        Tests that a dependency to an app with no migrations uses __first__.
        """
        # Load graph
        loader = MigrationLoader(connection)
        # Make state
        before = self.make_project_state([])
        after = self.make_project_state([self.book_migrations_fk])
        after.real_apps = ["migrations"]
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes(graph=loader.graph)
        # Right number of migrations?
        self.assertNumberMigrations(changes, 'otherapp', 1)
        self.assertOperationTypes(changes, 'otherapp', 0, ["CreateModel"])
        self.assertOperationAttributes(changes, 'otherapp', 0, 0, name="Book")
        # Right dependencies?
        self.assertEqual(changes['otherapp'][0].dependencies, [("migrations", "__first__")])

    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations"})
    def test_last_dependency(self):
        """
        Tests that a dependency to an app with existing migrations uses the
        last migration of that app.
        """
        # Load graph
        loader = MigrationLoader(connection)
        # Make state
        before = self.make_project_state([])
        after = self.make_project_state([self.book_migrations_fk])
        after.real_apps = ["migrations"]
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes(graph=loader.graph)
        # Right number of migrations?
        self.assertNumberMigrations(changes, 'otherapp', 1)
        self.assertOperationTypes(changes, 'otherapp', 0, ["CreateModel"])
        self.assertOperationAttributes(changes, 'otherapp', 0, 0, name="Book")
        # Right dependencies?
        self.assertEqual(changes['otherapp'][0].dependencies, [("migrations", "0002_second")])
