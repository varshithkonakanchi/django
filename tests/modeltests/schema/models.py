from django.db import models

# Because we want to test creation and deletion of these as separate things,
# these models are all marked as unmanaged and only marked as managed while
# a schema test is running.


class Author(models.Model):
    name = models.CharField(max_length=255)

    class Meta:
        managed = False


class Book(models.Model):
    author = models.ForeignKey(Author)
    title = models.CharField(max_length=100)
    pub_date = models.DateTimeField()

    class Meta:
        managed = False
