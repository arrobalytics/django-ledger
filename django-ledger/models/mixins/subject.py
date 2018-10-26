from django.db import models


class BaseSubjectModel(models.Model):
    subject_id = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=50, null=True, blank=True)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        abstract = True

    def __str__(self):
        return self.subject_id
