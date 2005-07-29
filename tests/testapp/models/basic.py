"""
1. Bare-bones model

This is a basic model with only two non-primary-key fields.
"""

from django.core import meta

class Article(meta.Model):
    fields = (
        meta.CharField('headline', maxlength=100),
        meta.DateTimeField('pub_date'),
    )

API_TESTS = """
# No articles are in the system yet.
>>> articles.get_list()
[]

# Create an Article.
>>> from datetime import datetime
>>> a = articles.Article(id=None, headline='Area man programs in Python', pub_date=datetime(2005, 7, 28))

# Save it into the database. You have to call save() explicitly.
>>> a.save()

# Now it has an ID. Note it's a long integer, as designated by the trailing "L".
>>> a.id
1L

# Access database columns via Python attributes.
>>> a.headline
'Area man programs in Python'
>>> a.pub_date
datetime.datetime(2005, 7, 28, 0, 0)

# Change values by changing the attributes, then calling save().
>>> a.headline = 'Area woman programs in Python'
>>> a.save()

# get_list() displays all the articles in the database. Note that the article
# is represented by "<Article object>", because we haven't given the Article
# model a __repr__() method.
>>> articles.get_list()
[<Article object>]

# Django provides a rich database lookup API that's entirely driven by
# keyword arguments.
>>> articles.get_object(id__exact=1)
<Article object>
>>> articles.get_object(headline__startswith='Area woman')
<Article object>
>>> articles.get_object(pub_date__year=2005)
<Article object>

# Django raises an ArticleDoesNotExist exception for get_object()
>>> articles.get_object(id__exact=2)
Traceback (most recent call last):
    ...
ArticleDoesNotExist: Article does not exist for {'id__exact': 2}

# Lookup by a primary key is the most common case, so Django provides a
# shortcut for primary-key exact lookups.
# The following is identical to articles.get_object(id__exact=1).
>>> articles.get_object(pk=1)
<Article object>

# Model instances of the same type and same ID are considered equal.
>>> a = articles.get_object(pk=1)
>>> b = articles.get_object(pk=1)
>>> a == b
True
"""
