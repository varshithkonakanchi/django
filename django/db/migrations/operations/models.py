from .base import Operation
from django.db import models, router
from django.db.migrations.state import ModelState


class CreateModel(Operation):
    """
    Create a model's table.
    """

    def __init__(self, name, fields, options=None, bases=None):
        self.name = name
        self.fields = fields
        self.options = options or {}
        self.bases = bases or (models.Model,)

    def state_forwards(self, app_label, state):
        state.models[app_label, self.name.lower()] = ModelState(app_label, self.name, self.fields, self.options, self.bases)

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        app_cache = to_state.render()
        model = app_cache.get_model(app_label, self.name)
        if router.allow_migrate(schema_editor.connection.alias, model):
            schema_editor.create_model(model)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        app_cache = from_state.render()
        model = app_cache.get_model(app_label, self.name)
        if router.allow_migrate(schema_editor.connection.alias, model):
            schema_editor.delete_model(model)

    def describe(self):
        return "Create model %s" % (self.name, )


class DeleteModel(Operation):
    """
    Drops a model's table.
    """

    def __init__(self, name):
        self.name = name

    def state_forwards(self, app_label, state):
        del state.models[app_label, self.name.lower()]

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        app_cache = from_state.render()
        model = app_cache.get_model(app_label, self.name)
        if router.allow_migrate(schema_editor.connection.alias, model):
            schema_editor.delete_model(model)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        app_cache = to_state.render()
        model = app_cache.get_model(app_label, self.name)
        if router.allow_migrate(schema_editor.connection.alias, model):
            schema_editor.create_model(model)

    def describe(self):
        return "Delete model %s" % (self.name, )


class AlterModelTable(Operation):
    """
    Renames a model's table
    """

    def __init__(self, name, table):
        self.name = name
        self.table = table

    def state_forwards(self, app_label, state):
        state.models[app_label, self.name.lower()].options["db_table"] = self.table

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        old_app_cache = from_state.render()
        new_app_cache = to_state.render()
        old_model = old_app_cache.get_model(app_label, self.name)
        new_model = new_app_cache.get_model(app_label, self.name)
        if router.allow_migrate(schema_editor.connection.alias, new_model):
            schema_editor.alter_db_table(
                new_model,
                old_model._meta.db_table,
                new_model._meta.db_table,
            )

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        return self.database_forwards(app_label, schema_editor, from_state, to_state)

    def describe(self):
        return "Rename table for %s to %s" % (self.name, self.table)


class AlterUniqueTogether(Operation):
    """
    Changes the value of index_together to the target one.
    Input value of unique_together must be a set of tuples.
    """

    def __init__(self, name, unique_together):
        self.name = name
        self.unique_together = set(tuple(cons) for cons in unique_together)

    def state_forwards(self, app_label, state):
        model_state = state.models[app_label, self.name.lower()]
        model_state.options["unique_together"] = self.unique_together

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        old_app_cache = from_state.render()
        new_app_cache = to_state.render()
        old_model = old_app_cache.get_model(app_label, self.name)
        new_model = new_app_cache.get_model(app_label, self.name)
        if router.allow_migrate(schema_editor.connection.alias, new_model):
            schema_editor.alter_unique_together(
                new_model,
                getattr(old_model._meta, "unique_together", set()),
                getattr(new_model._meta, "unique_together", set()),
            )

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        return self.database_forwards(app_label, schema_editor, from_state, to_state)

    def describe(self):
        return "Alter unique_together for %s (%s constraints)" % (self.name, len(self.unique_together))


class AlterIndexTogether(Operation):
    """
    Changes the value of index_together to the target one.
    Input value of index_together must be a set of tuples.
    """

    def __init__(self, name, index_together):
        self.name = name
        self.index_together = set(tuple(cons) for cons in index_together)

    def state_forwards(self, app_label, state):
        model_state = state.models[app_label, self.name.lower()]
        model_state.options["index_together"] = self.index_together

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        old_app_cache = from_state.render()
        new_app_cache = to_state.render()
        old_model = old_app_cache.get_model(app_label, self.name)
        new_model = new_app_cache.get_model(app_label, self.name)
        if router.allow_migrate(schema_editor.connection.alias, new_model):
            schema_editor.alter_index_together(
                new_model,
                getattr(old_model._meta, "index_together", set()),
                getattr(new_model._meta, "index_together", set()),
            )

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        return self.database_forwards(app_label, schema_editor, from_state, to_state)

    def describe(self):
        return "Alter index_together for %s (%s constraints)" % (self.name, len(self.index_together))
