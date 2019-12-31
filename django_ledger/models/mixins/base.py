from django.db import models


class SlugNameMixIn(models.Model):
    slug = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=150, null=True, blank=True)

    class Meta:
        abstract = True

    def __str__(self):
        return self.slug


class CreateUpdateMixIn(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        abstract = True
