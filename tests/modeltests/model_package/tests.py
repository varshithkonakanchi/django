from django.db import models

class Advertisment(models.Model):
    customer = models.CharField(max_length=100)
    publications = models.ManyToManyField("model_package.Publication", null=True, blank=True)

    class Meta:
        app_label = 'model_package'

__test__ = {'API_TESTS': """
>>> from models.publication import Publication
>>> from models.article import Article

>>> p = Publication(title="FooBar")
>>> p.save()
>>> p
<Publication: Publication object>

>>> from django.contrib.sites.models import Site
>>> current_site = Site.objects.get_current()
>>> current_site
<Site: example.com>

# Regression for #12168: models split into subpackages still get M2M tables

>>> a = Article(headline="a foo headline")
>>> a.save()
>>> a.publications.add(p)
>>> a.sites.add(current_site)

>>> a = Article.objects.get(id=1)
>>> a
<Article: Article object>
>>> a.id
1
>>> a.sites.count()
1

# Regression for #12245 - Models can exist in the test package, too

>>> ad = Advertisment(customer="Lawrence Journal-World")
>>> ad.save()
>>> ad.publications.add(p)

>>> ad = Advertisment.objects.get(id=1)
>>> ad
<Advertisment: Advertisment object>

>>> ad.publications.count()
1

# Regression for #12386 - field names on the autogenerated intermediate class
# that are specified as dotted strings don't retain any path component for the
# field or column name

>>> Article.publications.through._meta.fields[1].name
'article'

>>> Article.publications.through._meta.fields[1].get_attname_column()
('article_id', 'article_id')

>>> Article.publications.through._meta.fields[2].name
'publication'

>>> Article.publications.through._meta.fields[2].get_attname_column()
('publication_id', 'publication_id')

# The oracle backend truncates the name to 'model_package_article_publ233f'.
>>> Article._meta.get_field('publications').m2m_db_table() \\
... in ('model_package_article_publications', 'model_package_article_publ233f')
True

>>> Article._meta.get_field('publications').m2m_column_name()
'article_id'

>>> Article._meta.get_field('publications').m2m_reverse_name()
'publication_id'

"""}


