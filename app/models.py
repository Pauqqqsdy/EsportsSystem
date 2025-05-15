from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Tournament(models.Model):
    DISCIPLINE_CHOICES = [
        ('Dota 2', 'Dota 2'),
        ('CS 2', 'CS 2'),
        ('Valorant', 'Valorant'),
        ('LoL', 'League of Legends'),
    ]
    
    FORMAT_CHOICES = [
        ('1x1', '1x1'),
        ('2x2', '2x2'),
        ('3x3', '3x3'),
        ('5x5', '5x5'),
    ]
    
    TEAM_COUNT_CHOICES = [
        (4, '4'),
        (8, '8'),
        (16, '16'),
        (32, '32'),
        (64, '64'),
        (128, '128'),
        (256, '256'),
        (512, '512'),
    ]
    
    FORMAT_TOURNAMENT_CHOICES = [
        ('BO1', 'BO1'),
        ('BO3', 'BO3'),
        ('BO5', 'BO5'),
    ]
    
    LOCATION_CHOICES = [
        ('China', 'Китай'),
        ('Western Europe', 'Западная Европа'),
        ('Eastern Europe', 'Восточная Европа'),
        ('Southeast Asia', 'ЮВ Азия'),
        ('North America', 'Северная Америка'),
        ('South America', 'Южная Америка'),
    ]

    name = models.CharField(max_length=200, verbose_name="Название турнира")
    max_teams = models.IntegerField(choices=TEAM_COUNT_CHOICES, verbose_name="Максимальное количество команд")
    start_date = models.DateTimeField(verbose_name="Дата начала")
    discipline = models.CharField(max_length=50, choices=DISCIPLINE_CHOICES, verbose_name="Дисциплина")
    game_format = models.CharField(max_length=50, choices=FORMAT_CHOICES, verbose_name="Формат игры")
    tournament_format = models.CharField(max_length=50, choices=FORMAT_TOURNAMENT_CHOICES, verbose_name="Формат турнира")
    location = models.CharField(max_length=50, choices=LOCATION_CHOICES, verbose_name="Локация")
    description = models.TextField(verbose_name="Описание", blank=True, null=True)
    creator = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Создатель")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Дата создания")
    is_active = models.BooleanField(default=True, verbose_name="Активный")

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Турнир'
        verbose_name_plural = 'Турниры'

    def __str__(self):
        return self.name

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    email_confirmed = models.BooleanField(default=False)
    avatar = models.ImageField(
        upload_to='avatars/',
        default='avatars/default.jpg',
        blank=True,
        null=True
    )
    team = models.CharField(max_length=100, blank=True, null=True)
    
    def __str__(self):
        return self.user.username