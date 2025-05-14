from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Tournament(models.Model):
    name = models.CharField(max_length=200, verbose_name="Название турнира")
    description = models.TextField(verbose_name="Описание")
    creator = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Создатель")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Дата создания")
    start_date = models.DateTimeField(verbose_name="Дата начала")
    end_date = models.DateTimeField(verbose_name="Дата окончания")
    is_active = models.BooleanField(default=True, verbose_name="Активный")

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Турнир'
        verbose_name_plural = 'Турниры'

    def __str__(self):
        return self.name