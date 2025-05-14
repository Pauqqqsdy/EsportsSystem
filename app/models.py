from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Tournament(models.Model):
    name = models.CharField(max_length=200, verbose_name="Название турнира")
    description = models.TextField(verbose_name="Описание")
    creator = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']