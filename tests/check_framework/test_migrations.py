from unittest.mock import ANY

from django.core import checks
from django.core.checks.migrations import check_migration_operations
from django.db import migrations
from django.db.migrations.operations.base import Operation
from django.test import TestCase
from django.test.utils import override_settings


class DeprecatedMigrationOperationTests(TestCase):
    def test_default_operation(self):
        class MyOperation(Operation):
            system_check_deprecated_details = {}

        my_operation = MyOperation()

        class Migration(migrations.Migration):
            operations = [my_operation]

        self.assertEqual(
            Migration("name", "app_label").check(),
            [
                checks.Warning(
                    msg="MyOperation has been deprecated.",
                    obj=my_operation,
                    id="migrations.WXXX",
                )
            ],
        )

    def test_user_specified_details(self):
        class MyOperation(Operation):
            system_check_deprecated_details = {
                "msg": "This operation is deprecated and will be removed soon.",
                "hint": "Use something else.",
                "id": "migrations.W999",
            }

        my_operation = MyOperation()

        class Migration(migrations.Migration):
            operations = [my_operation]

        self.assertEqual(
            Migration("name", "app_label").check(),
            [
                checks.Warning(
                    msg="This operation is deprecated and will be removed soon.",
                    obj=my_operation,
                    hint="Use something else.",
                    id="migrations.W999",
                )
            ],
        )

    @override_settings(
        INSTALLED_APPS=["check_framework.migrations_test_apps.index_together_app"]
    )
    def tests_check_alter_index_together(self):
        errors = check_migration_operations()
        self.assertEqual(
            errors,
            [
                checks.Warning(
                    "AlterIndexTogether is deprecated. Support for it (except in "
                    "historical migrations) will be removed in Django 5.1.",
                    obj=ANY,
                    id="migrations.W001",
                )
            ],
        )


class RemovedMigrationOperationTests(TestCase):
    def test_default_operation(self):
        class MyOperation(Operation):
            system_check_removed_details = {}

        my_operation = MyOperation()

        class Migration(migrations.Migration):
            operations = [my_operation]

        self.assertEqual(
            Migration("name", "app_label").check(),
            [
                checks.Error(
                    msg=(
                        "MyOperation has been removed except for support in historical "
                        "migrations."
                    ),
                    obj=my_operation,
                    id="migrations.EXXX",
                )
            ],
        )

    def test_user_specified_details(self):
        class MyOperation(Operation):
            system_check_removed_details = {
                "msg": "Support for this operation is gone.",
                "hint": "Use something else.",
                "id": "migrations.E999",
            }

        my_operation = MyOperation()

        class Migration(migrations.Migration):
            operations = [my_operation]

        self.assertEqual(
            Migration("name", "app_label").check(),
            [
                checks.Error(
                    msg="Support for this operation is gone.",
                    obj=my_operation,
                    hint="Use something else.",
                    id="migrations.E999",
                )
            ],
        )
