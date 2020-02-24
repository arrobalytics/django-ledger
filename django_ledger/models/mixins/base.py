from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _l


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


class ProgressibleMixIn(models.Model):
    progressible = models.BooleanField(default=False, verbose_name=_l('Progressible Item'))
    progress = models.DecimalField(null=True, blank=True, verbose_name=_l('Progress Amount'),
                                   decimal_places=2,
                                   max_digits=3,
                                   validators=[
                                       MinValueValidator(limit_value=0),
                                       MaxValueValidator(limit_value=1)
                                   ])
