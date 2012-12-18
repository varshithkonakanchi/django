from django.db import models


class Article(models.Model):
    headline = models.CharField(max_length=100)
    pub_date = models.DateTimeField()

    class Meta:
        index_together = [
            ["headline", "pub_date"],
        ]


class IndexedArticle(models.Model):
    headline = models.CharField(max_length=100, db_index=True)
    body = models.TextField(db_index=True)
    slug = models.CharField(max_length=40, unique=True, db_index=True)
