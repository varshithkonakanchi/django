from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import (
    GenericForeignKey, GenericRelation,
)
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Book(models.Model):
    title = models.CharField(max_length=50)
    year = models.PositiveIntegerField(null=True, blank=True)
    author = models.ForeignKey(
        User,
        models.SET_NULL,
        verbose_name="Verbose Author",
        related_name='books_authored',
        blank=True, null=True,
    )
    contributors = models.ManyToManyField(
        User,
        verbose_name="Verbose Contributors",
        related_name='books_contributed',
        blank=True,
    )
    employee = models.ForeignKey(
        'Employee',
        models.SET_NULL,
        verbose_name='Employee',
        blank=True, null=True,
    )
    is_best_seller = models.NullBooleanField(default=0)
    date_registered = models.DateField(null=True)
    # This field name is intentionally 2 characters long (#16080).
    no = models.IntegerField(verbose_name='number', blank=True, null=True)

    def __str__(self):
        return self.title


@python_2_unicode_compatible
class Department(models.Model):
    code = models.CharField(max_length=4, unique=True)
    description = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return self.description


@python_2_unicode_compatible
class Employee(models.Model):
    department = models.ForeignKey(Department, models.CASCADE, to_field="code")
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class TaggedItem(models.Model):
    tag = models.SlugField()
    content_type = models.ForeignKey(ContentType, models.CASCADE, related_name='tagged_items')
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    def __str__(self):
        return self.tag


@python_2_unicode_compatible
class Bookmark(models.Model):
    url = models.URLField()
    tags = GenericRelation(TaggedItem)

    CHOICES = [
        ('a', 'A'),
        (None, 'None'),
        ('', '-'),
    ]
    none_or_null = models.CharField(max_length=20, choices=CHOICES, blank=True, null=True)

    def __str__(self):
        return self.url
