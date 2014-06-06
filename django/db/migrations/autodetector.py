from __future__ import unicode_literals

import re
import datetime

from django.db import models
from django.db.migrations import operations
from django.db.migrations.migration import Migration
from django.db.migrations.questioner import MigrationQuestioner
from django.db.migrations.optimizer import MigrationOptimizer


class MigrationAutodetector(object):
    """
    Takes a pair of ProjectStates, and compares them to see what the
    first would need doing to make it match the second (the second
    usually being the project's current state).

    Note that this naturally operates on entire projects at a time,
    as it's likely that changes interact (for example, you can't
    add a ForeignKey without having a migration to add the table it
    depends on first). A user interface may offer single-app usage
    if it wishes, with the caveat that it may not always be possible.
    """

    def __init__(self, from_state, to_state, questioner=None):
        self.from_state = from_state
        self.to_state = to_state
        self.questioner = questioner or MigrationQuestioner()

    def changes(self, graph, trim_to_apps=None):
        """
        Main entry point to produce a list of appliable changes.
        Takes a graph to base names on and an optional set of apps
        to try and restrict to (restriction is not guaranteed)
        """
        changes = self._detect_changes()
        changes = self.arrange_for_graph(changes, graph)
        if trim_to_apps:
            changes = self._trim_to_apps(changes, trim_to_apps)
        return changes

    def deep_deconstruct(self, obj):
        """
        Recursive deconstruction for a field and its arguments.
        Used for full comparison for rename/alter; sometimes a single-level
        deconstruction will not compare correctly.
        """
        if not hasattr(obj, 'deconstruct'):
            return obj
        deconstructed = obj.deconstruct()
        if isinstance(obj, models.Field):
            # we have a field which also returns a name
            deconstructed = deconstructed[1:]
        path, args, kwargs = deconstructed
        return (
            path,
            [self.deep_deconstruct(value) for value in args],
            dict(
                (key, self.deep_deconstruct(value))
                for key, value in kwargs.items()
            ),
        )

    def only_relation_agnostic_fields(self, fields):
        """
        Return a definition of the fields that ignores field names and
        what related fields actually relate to.
        Used for detecting renames (as, of course, the related fields
        change during renames)
        """
        fields_def = []
        for name, field in fields:
            deconstruction = self.deep_deconstruct(field)
            if field.rel and field.rel.to:
                del deconstruction[2]['to']
            fields_def.append(deconstruction)
        return fields_def

    def _detect_changes(self):
        """
        Returns a dict of migration plans which will achieve the
        change from from_state to to_state. The dict has app labels
        as keys and a list of migrations as values.

        The resulting migrations aren't specially named, but the names
        do matter for dependencies inside the set.
        """

        # The first phase is generating all the operations for each app
        # and gathering them into a big per-app list.
        # We'll then go through that list later and order it and split
        # into migrations to resolve dependencies caused by M2Ms and FKs.
        self.generated_operations = {}

        # Prepare some old/new state and model lists, ignoring
        # proxy models and unmigrated apps.
        self.old_apps = self.from_state.render(ignore_swappable=True)
        self.new_apps = self.to_state.render()
        self.old_model_keys = []
        for al, mn in sorted(self.from_state.models.keys()):
            model = self.old_apps.get_model(al, mn)
            if not model._meta.proxy and model._meta.managed and al not in self.from_state.real_apps:
                self.old_model_keys.append((al, mn))
        self.new_model_keys = []
        for al, mn in sorted(self.to_state.models.keys()):
            model = self.new_apps.get_model(al, mn)
            if not model._meta.proxy and model._meta.managed and al not in self.from_state.real_apps:
                self.new_model_keys.append((al, mn))

        # Renames have to come first
        self.generate_renamed_models()

        # Prepare field lists, and prepare a list of the fields that used
        # through models in the old state so we can make dependencies
        # from the through model deletion to the field that uses it.
        self.kept_model_keys = set(self.old_model_keys).intersection(self.new_model_keys)
        self.through_users = {}
        self.old_field_keys = set()
        self.new_field_keys = set()
        for app_label, model_name in sorted(self.kept_model_keys):
            old_model_name = self.renamed_models.get((app_label, model_name), model_name)
            old_model_state = self.from_state.models[app_label, old_model_name]
            new_model_state = self.to_state.models[app_label, model_name]
            self.old_field_keys.update((app_label, model_name, x) for x, y in old_model_state.fields)
            self.new_field_keys.update((app_label, model_name, x) for x, y in new_model_state.fields)
            # Through model stuff
            for field_name, field in old_model_state.fields:
                old_field = self.old_apps.get_model(app_label, old_model_name)._meta.get_field_by_name(field_name)[0]
                if hasattr(old_field, "rel") and hasattr(old_field.rel, "through") and not old_field.rel.through._meta.auto_created:
                    through_key = (
                        old_field.rel.through._meta.app_label,
                        old_field.rel.through._meta.object_name.lower(),
                    )
                    self.through_users[through_key] = (app_label, old_model_name, field_name)

        # Generate non-rename model operations
        self.generate_created_models()
        self.generate_deleted_models()

        # Generate field operations
        self.generate_added_fields()
        self.generate_removed_fields()
        self.generate_altered_fields()
        self.generate_altered_unique_together()
        self.generate_altered_index_together()

        # Now, reordering to make things possible. The order we have already
        # isn't bad, but we need to pull a few things around so FKs work nicely
        # inside the same app
        for app_label, ops in sorted(self.generated_operations.items()):
            for i in range(10000):
                found = False
                for i, op in enumerate(ops):
                    for dep in op._auto_deps:
                        if dep[0] == app_label:
                            # Alright, there's a dependency on the same app.
                            for j, op2 in enumerate(ops):
                                if self.check_dependency(op2, dep) and j > i:
                                    ops = ops[:i] + ops[i+1:j+1] + [op] + ops[j+1:]
                                    found = True
                                    break
                        if found:
                            break
                    if found:
                        break
                if not found:
                    break
            else:
                raise ValueError("Infinite loop caught in operation dependency resolution")
            self.generated_operations[app_label] = ops

        # Now, we need to chop the lists of operations up into migrations with
        # dependencies on each other.
        # We do this by stepping up an app's list of operations until we
        # find one that has an outgoing dependency that isn't in another app's
        # migration yet (hasn't been chopped off its list). We then chop off the
        # operations before it into a migration and move onto the next app.
        # If we loop back around without doing anything, there's a circular
        # dependency (which _should_ be impossible as the operations are all
        # split at this point so they can't depend and be depended on)

        self.migrations = {}
        num_ops = sum(len(x) for x in self.generated_operations.values())
        chop_mode = False
        while num_ops:
            # On every iteration, we step through all the apps and see if there
            # is a completed set of operations.
            # If we find that a subset of the operations are complete we can
            # try to chop it off from the rest and continue, but we only
            # do this if we've already been through the list once before
            # without any chopping and nothing has changed.
            for app_label in sorted(self.generated_operations.keys()):
                chopped = []
                dependencies = set()
                for operation in list(self.generated_operations[app_label]):
                    deps_satisfied = True
                    operation_dependencies = set()
                    for dep in operation._auto_deps:
                        if dep[0] == "__setting__":
                            operation_dependencies.add((dep[0], dep[1]))
                        elif dep[0] != app_label:
                            # External app dependency. See if it's not yet
                            # satisfied.
                            for other_operation in self.generated_operations[dep[0]]:
                                if self.check_dependency(other_operation, dep):
                                    deps_satisfied = False
                                    break
                            if not deps_satisfied:
                                break
                            else:
                                if self.migrations.get(dep[0], None):
                                    operation_dependencies.add((dep[0], self.migrations[dep[0]][-1].name))
                                else:
                                    operation_dependencies.add((dep[0], "__latest__"))
                    if deps_satisfied:
                        chopped.append(operation)
                        dependencies.update(operation_dependencies)
                        self.generated_operations[app_label] = self.generated_operations[app_label][1:]
                    else:
                        break
                # Make a migration! Well, only if there's stuff to put in it
                if dependencies or chopped:
                    if not self.generated_operations[app_label] or chop_mode:
                        subclass = type(str("Migration"), (Migration,), {"operations": [], "dependencies": []})
                        instance = subclass("auto_%i" % (len(self.migrations.get(app_label, [])) + 1), app_label)
                        instance.dependencies = list(dependencies)
                        instance.operations = chopped
                        self.migrations.setdefault(app_label, []).append(instance)
                        chop_mode = False
                    else:
                        self.generated_operations[app_label] = chopped + self.generated_operations[app_label]
            new_num_ops = sum(len(x) for x in self.generated_operations.values())
            if new_num_ops == num_ops:
                if not chop_mode:
                    chop_mode = True
                else:
                    raise ValueError("Cannot resolve operation dependencies")
            num_ops = new_num_ops

        # OK, add in internal dependencies among the migrations
        for app_label, migrations in self.migrations.items():
            for m1, m2 in zip(migrations, migrations[1:]):
                m2.dependencies.append((app_label, m1.name))

        # De-dupe dependencies
        for app_label, migrations in self.migrations.items():
            for migration in migrations:
                migration.dependencies = list(set(migration.dependencies))

        # Optimize migrations
        for app_label, migrations in self.migrations.items():
            for migration in migrations:
                migration.operations = MigrationOptimizer().optimize(migration.operations, app_label=app_label)

        return self.migrations

    def check_dependency(self, operation, dependency):
        """
        Checks if an operation dependency matches an operation.
        """
        # Created model
        if dependency[2] is None and dependency[3] is True:
            return (
                isinstance(operation, operations.CreateModel) and
                operation.name.lower() == dependency[1].lower()
            )
        # Created field
        elif dependency[2] is not None and dependency[3] is True:
            return (
                (
                    isinstance(operation, operations.CreateModel) and
                    operation.name.lower() == dependency[1].lower() and
                    any(dependency[2] == x for x, y in operation.fields)
                ) or
                (
                    isinstance(operation, operations.AddField) and
                    operation.model_name.lower() == dependency[1].lower() and
                    operation.name.lower() == dependency[2].lower()
                )
            )
        # Removed field
        elif dependency[2] is not None and dependency[3] is False:
            return (
                isinstance(operation, operations.RemoveField) and
                operation.model_name.lower() == dependency[1].lower() and
                operation.name.lower() == dependency[2].lower()
            )
        # Unknown dependency. Raise an error.
        else:
            raise ValueError("Can't handle dependency %r" % dependency)

    def add_operation(self, app_label, operation, dependencies=None):
        # Dependencies are (app_label, model_name, field_name, create/delete as True/False)
        operation._auto_deps = dependencies or []
        self.generated_operations.setdefault(app_label, []).append(operation)

    def generate_renamed_models(self):
        """
        Finds any renamed models, and generates the operations for them,
        and removes the old entry from the model lists.
        Must be run before other model-level generation.
        """
        self.renamed_models = {}
        self.renamed_models_rel = {}
        added_models = set(self.new_model_keys) - set(self.old_model_keys)
        for app_label, model_name in sorted(added_models):
            model_state = self.to_state.models[app_label, model_name]
            model_fields_def = self.only_relation_agnostic_fields(model_state.fields)

            removed_models = set(self.old_model_keys) - set(self.new_model_keys)
            for rem_app_label, rem_model_name in removed_models:
                if rem_app_label == app_label:
                    rem_model_state = self.from_state.models[rem_app_label, rem_model_name]
                    rem_model_fields_def = self.only_relation_agnostic_fields(rem_model_state.fields)
                    if model_fields_def == rem_model_fields_def:
                        if self.questioner.ask_rename_model(rem_model_state, model_state):
                            self.add_operation(
                                app_label,
                                operations.RenameModel(
                                    old_name=rem_model_state.name,
                                    new_name=model_state.name,
                                )
                            )
                            self.renamed_models[app_label, model_name] = rem_model_name
                            self.renamed_models_rel['%s.%s' % (rem_model_state.app_label, rem_model_state.name)] = '%s.%s' % (model_state.app_label, model_state.name)
                            self.old_model_keys.remove((rem_app_label, rem_model_name))
                            self.old_model_keys.append((app_label, model_name))
                            break

    def generate_created_models(self):
        """
        Find all new models and make creation operations for them,
        and separate operations to create any foreign key or M2M relationships
        (we'll optimise these back in later if we can)

        We also defer any model options that refer to collections of fields
        that might be deferred (e.g. unique_together, index_together)
        """
        added_models = set(self.new_model_keys) - set(self.old_model_keys)
        for app_label, model_name in sorted(added_models):
            model_state = self.to_state.models[app_label, model_name]
            # Gather related fields
            related_fields = {}
            for field in self.new_apps.get_model(app_label, model_name)._meta.local_fields:
                if field.rel:
                    if field.rel.to:
                        related_fields[field.name] = field
                    if hasattr(field.rel, "through") and not field.rel.through._meta.auto_created:
                        related_fields[field.name] = field
            for field in self.new_apps.get_model(app_label, model_name)._meta.local_many_to_many:
                if field.rel.to:
                    related_fields[field.name] = field
                if hasattr(field.rel, "through") and not field.rel.through._meta.auto_created:
                    related_fields[field.name] = field
            # Are there unique/index_together to defer?
            unique_together = model_state.options.pop('unique_together', None)
            index_together = model_state.options.pop('index_together', None)
            # Generate creation operatoin
            self.add_operation(
                app_label,
                operations.CreateModel(
                    name=model_state.name,
                    fields=[d for d in model_state.fields if d[0] not in related_fields],
                    options=model_state.options,
                    bases=model_state.bases,
                )
            )
            # Generate operations for each related field
            for name, field in sorted(related_fields.items()):
                # Account for FKs to swappable models
                swappable_setting = getattr(field, 'swappable_setting', None)
                if swappable_setting is not None:
                    dep_app_label = "__setting__"
                    dep_object_name = swappable_setting
                else:
                    dep_app_label = field.rel.to._meta.app_label
                    dep_object_name = field.rel.to._meta.object_name
                # Make operation
                self.add_operation(
                    app_label,
                    operations.AddField(
                        model_name=model_name,
                        name=name,
                        field=field,
                    ),
                    dependencies = [
                        (dep_app_label, dep_object_name, None, True),
                    ]
                )
            # Generate other opns
            if unique_together:
                self.add_operation(
                    app_label,
                    operations.AlterUniqueTogether(
                        name=model_name,
                        unique_together=unique_together,
                    ),
                    dependencies = [
                        (app_label, model_name, name, True)
                        for name, field in sorted(related_fields.items())
                    ]
                )
            if index_together:
                self.add_operation(
                    app_label,
                    operations.AlterIndexTogether(
                        name=model_name,
                        index_together=index_together,
                    ),
                    dependencies = [
                        (app_label, model_name, name, True)
                        for name, field in sorted(related_fields.items())
                    ]
                )

    def generate_deleted_models(self):
        """
        Find all deleted models and make creation operations for them,
        and separate operations to delete any foreign key or M2M relationships
        (we'll optimise these back in later if we can)

        We also bring forward removal of any model options that refer to
        collections of fields - the inverse of generate_created_models.
        """
        deleted_models = set(self.old_model_keys) - set(self.new_model_keys)
        for app_label, model_name in sorted(deleted_models):
            model_state = self.from_state.models[app_label, model_name]
            model = self.old_apps.get_model(app_label, model_name)
            # Gather related fields
            related_fields = {}
            for field in model._meta.local_fields:
                if field.rel:
                    if field.rel.to:
                        related_fields[field.name] = field
                    if hasattr(field.rel, "through") and not field.rel.through._meta.auto_created:
                        related_fields[field.name] = field
            for field in model._meta.local_many_to_many:
                if field.rel.to:
                    related_fields[field.name] = field
                if hasattr(field.rel, "through") and not field.rel.through._meta.auto_created:
                    related_fields[field.name] = field
            # Generate option removal first
            unique_together = model_state.options.pop('unique_together', None)
            index_together = model_state.options.pop('index_together', None)
            if unique_together:
                self.add_operation(
                    app_label,
                    operations.AlterUniqueTogether(
                        name=model_name,
                        unique_together=None,
                    )
                )
            if index_together:
                self.add_operation(
                    app_label,
                    operations.AlterIndexTogether(
                        name=model_name,
                        index_together=None,
                    )
                )
            # Then remove each related field
            for name, field in sorted(related_fields.items()):
                self.add_operation(
                    app_label,
                    operations.RemoveField(
                        model_name=model_name,
                        name=name,
                    )
                )
            # Finally, remove the model.
            # This depends on both the removal of all incoming fields
            # and the removal of all its own related fields, and if it's
            # a through model the field that references it.
            dependencies = []
            for related_object in model._meta.get_all_related_objects():
                dependencies.append((
                    related_object.model._meta.app_label,
                    related_object.model._meta.object_name,
                    related_object.field.name,
                    False,
                ))
            for related_object in model._meta.get_all_related_many_to_many_objects():
                dependencies.append((
                    related_object.model._meta.app_label,
                    related_object.model._meta.object_name,
                    related_object.field.name,
                    False,
                ))
            for name, field in sorted(related_fields.items()):
                dependencies.append((app_label, model_name, name, False))
            # We're referenced in another field's through=
            through_user = self.through_users.get((app_label, model_state.name.lower()), None)
            if through_user:
                dependencies.append((through_user[0], through_user[1], through_user[2], False))
            # Finally, make the operation, deduping any dependencies
            self.add_operation(
                app_label,
                operations.DeleteModel(
                    name=model_state.name,
                ),
                dependencies = list(set(dependencies)),
            )

    def generate_added_fields(self):
        # New fields
        self.renamed_fields = {}
        for app_label, model_name, field_name in sorted(self.new_field_keys - self.old_field_keys):
            old_model_name = self.renamed_models.get((app_label, model_name), model_name)
            old_model_state = self.from_state.models[app_label, old_model_name]
            new_model_state = self.to_state.models[app_label, model_name]
            field = new_model_state.get_field_by_name(field_name)
            # Scan to see if this is actually a rename!
            field_dec = self.deep_deconstruct(field)
            found_rename = False
            for rem_app_label, rem_model_name, rem_field_name in sorted(self.old_field_keys - self.new_field_keys):
                if rem_app_label == app_label and rem_model_name == model_name:
                    old_field_dec = self.deep_deconstruct(old_model_state.get_field_by_name(rem_field_name))
                    if field.rel and field.rel.to and 'to' in old_field_dec[2]:
                        old_rel_to = old_field_dec[2]['to']
                        if old_rel_to in self.renamed_models_rel:
                            old_field_dec[2]['to'] = self.renamed_models_rel[old_rel_to]
                    if old_field_dec == field_dec:
                        if self.questioner.ask_rename(model_name, rem_field_name, field_name, field):
                            self.add_operation(
                                app_label,
                                operations.RenameField(
                                    model_name=model_name,
                                    old_name=rem_field_name,
                                    new_name=field_name,
                                )
                            )
                            self.old_field_keys.remove((rem_app_label, rem_model_name, rem_field_name))
                            self.old_field_keys.add((app_label, model_name, field_name))
                            self.renamed_fields[app_label, model_name, field_name] = rem_field_name
                            found_rename = True
                            break
            if found_rename:
                continue
            # You can't just add NOT NULL fields with no default
            if not field.null and not field.has_default() and not isinstance(field, models.ManyToManyField):
                field = field.clone()
                field.default = self.questioner.ask_not_null_addition(field_name, model_name)
                self.add_operation(
                    app_label,
                    operations.AddField(
                        model_name=model_name,
                        name=field_name,
                        field=field,
                        preserve_default=False,
                    )
                )
            else:
                self.add_operation(
                    app_label,
                    operations.AddField(
                        model_name=model_name,
                        name=field_name,
                        field=field,
                    )
                )

    def generate_removed_fields(self):
        """
        Fields that have been removed.
        """
        for app_label, model_name, field_name in sorted(self.old_field_keys - self.new_field_keys):
            self.add_operation(
                app_label,
                operations.RemoveField(
                    model_name=model_name,
                    name=field_name,
                )
            )

    def generate_altered_fields(self):
        """
        Fields that have been altered.
        """
        for app_label, model_name, field_name in sorted(self.old_field_keys.intersection(self.new_field_keys)):
            # Did the field change?
            old_model_name = self.renamed_models.get((app_label, model_name), model_name)
            old_model_state = self.from_state.models[app_label, old_model_name]
            new_model_state = self.to_state.models[app_label, model_name]
            old_field_name = self.renamed_fields.get((app_label, model_name, field_name), field_name)
            old_field_dec = self.deep_deconstruct(old_model_state.get_field_by_name(old_field_name))
            new_field_dec = self.deep_deconstruct(new_model_state.get_field_by_name(field_name))
            if old_field_dec != new_field_dec:
                self.add_operation(
                    app_label,
                    operations.AlterField(
                        model_name=model_name,
                        name=field_name,
                        field=new_model_state.get_field_by_name(field_name),
                    )
                )

    def generate_altered_unique_together(self):
        for app_label, model_name in sorted(self.kept_model_keys):
            old_model_name = self.renamed_models.get((app_label, model_name), model_name)
            old_model_state = self.from_state.models[app_label, old_model_name]
            new_model_state = self.to_state.models[app_label, model_name]
            if old_model_state.options.get("unique_together", None) != new_model_state.options.get("unique_together", None):
                self.add_operation(
                    app_label,
                    operations.AlterUniqueTogether(
                        name=model_name,
                        unique_together=new_model_state.options['unique_together'],
                    )
                )

    def generate_altered_index_together(self):
        for app_label, model_name in sorted(self.kept_model_keys):
            old_model_name = self.renamed_models.get((app_label, model_name), model_name)
            old_model_state = self.from_state.models[app_label, old_model_name]
            new_model_state = self.to_state.models[app_label, model_name]
            if old_model_state.options.get("index_together", None) != new_model_state.options.get("index_together", None):
                self.add_operation(
                    app_label,
                    operations.AlterIndexTogether(
                        name=model_name,
                        index_together=new_model_state.options['index_together'],
                    )
                )

    def arrange_for_graph(self, changes, graph):
        """
        Takes in a result from changes() and a MigrationGraph,
        and fixes the names and dependencies of the changes so they
        extend the graph from the leaf nodes for each app.
        """
        leaves = graph.leaf_nodes()
        name_map = {}
        for app_label, migrations in list(changes.items()):
            if not migrations:
                continue
            # Find the app label's current leaf node
            app_leaf = None
            for leaf in leaves:
                if leaf[0] == app_label:
                    app_leaf = leaf
                    break
            # Do they want an initial migration for this app?
            if app_leaf is None and not self.questioner.ask_initial(app_label):
                # They don't.
                for migration in migrations:
                    name_map[(app_label, migration.name)] = (app_label, "__first__")
                del changes[app_label]
                continue
            # Work out the next number in the sequence
            if app_leaf is None:
                next_number = 1
            else:
                next_number = (self.parse_number(app_leaf[1]) or 0) + 1
            # Name each migration
            for i, migration in enumerate(migrations):
                if i == 0 and app_leaf:
                    migration.dependencies.append(app_leaf)
                if i == 0 and not app_leaf:
                    new_name = "0001_initial"
                else:
                    new_name = "%04i_%s" % (
                        next_number,
                        self.suggest_name(migration.operations)[:100],
                    )
                name_map[(app_label, migration.name)] = (app_label, new_name)
                next_number += 1
                migration.name = new_name
        # Now fix dependencies
        for app_label, migrations in changes.items():
            for migration in migrations:
                migration.dependencies = [name_map.get(d, d) for d in migration.dependencies]
        return changes

    def _trim_to_apps(self, changes, app_labels):
        """
        Takes changes from arrange_for_graph and set of app labels and
        returns a modified set of changes which trims out as many migrations
        that are not in app_labels as possible.
        Note that some other migrations may still be present, as they may be
        required dependencies.
        """
        # Gather other app dependencies in a first pass
        app_dependencies = {}
        for app_label, migrations in changes.items():
            for migration in migrations:
                for dep_app_label, name in migration.dependencies:
                    app_dependencies.setdefault(app_label, set()).add(dep_app_label)
        required_apps = set(app_labels)
        # Keep resolving till there's no change
        old_required_apps = None
        while old_required_apps != required_apps:
            old_required_apps = set(required_apps)
            for app_label in list(required_apps):
                required_apps.update(app_dependencies.get(app_label, set()))
        # Remove all migrations that aren't needed
        for app_label in list(changes.keys()):
            if app_label not in required_apps:
                del changes[app_label]
        return changes

    @classmethod
    def suggest_name(cls, ops):
        """
        Given a set of operations, suggests a name for the migration
        they might represent. Names are not guaranteed to be unique,
        but we put some effort in to the fallback name to avoid VCS conflicts
        if we can.
        """
        if len(ops) == 1:
            if isinstance(ops[0], operations.CreateModel):
                return ops[0].name.lower()
            elif isinstance(ops[0], operations.DeleteModel):
                return "delete_%s" % ops[0].name.lower()
            elif isinstance(ops[0], operations.AddField):
                return "%s_%s" % (ops[0].model_name.lower(), ops[0].name.lower())
            elif isinstance(ops[0], operations.RemoveField):
                return "remove_%s_%s" % (ops[0].model_name.lower(), ops[0].name.lower())
        elif len(ops) > 1:
            if all(isinstance(o, operations.CreateModel) for o in ops):
                return "_".join(sorted(o.name.lower() for o in ops))
        return "auto_%s" % datetime.datetime.now().strftime("%Y%m%d_%H%M")

    @classmethod
    def parse_number(cls, name):
        """
        Given a migration name, tries to extract a number from the
        beginning of it. If no number found, returns None.
        """
        if re.match(r"^\d+_", name):
            return int(name.split("_")[0])
        return None
