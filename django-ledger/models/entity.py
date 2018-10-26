from django.db import models


class EntityModel(models.Model):

    entity_id = models.SlugField()
    name = models.CharField(max_length=30)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name = 'Entity'
        verbose_name_plural = 'Entities'

    def __str__(self):
        return '{x1} ({x2})'.format(x1=self.name,
                                    x2=self.entity_id)
