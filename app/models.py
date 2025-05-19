from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.db.models.signals import pre_delete
from django.dispatch import receiver

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
    bio = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.user.username

class Team(models.Model):
    name = models.CharField(max_length=100, unique=True)
    avatar = models.ImageField(
        upload_to='team_avatars/',
        default='team_avatars/default.jpg',
        blank=True,
        null=True
    )
    captain = models.ForeignKey(User, on_delete=models.CASCADE, related_name='captained_teams')
    members = models.ManyToManyField(User, related_name='teams')
    created_at = models.DateTimeField(auto_now_add=True)
    invite_code = models.CharField(max_length=32, unique=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.invite_code:
            self.invite_code = get_random_string(32)
        super().save(*args, **kwargs)

    def member_count(self):
        return self.members.count()

    def is_full(self):
        return self.member_count() >= 8

    def is_captain(self, user):
        return self.captain == user

    def is_member(self, user):
        return self.members.filter(pk=user.pk).exists()

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    email_confirmed = models.BooleanField(default=False)
    avatar = models.ImageField(
        upload_to='avatars/',
        default='avatars/default.jpg',
        blank=True,
        null=True
    )
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name='team_members')
    bio = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.user.username

@receiver(pre_delete, sender=User)
def user_deleted(sender, instance, **kwargs):
    """Удаляем команду, если при удалении пользователя она осталась пустой"""
    try:
        profile = instance.userprofile
        if profile.team:
            team = profile.team
            profile.team = None
            profile.save()
            
            # Если пользователь был капитаном, передаем лидерство или удаляем команду
            if team.captain == instance:
                if team.member_count() > 1:
                    # Назначаем нового капитана (первого попавшегося участника)
                    new_captain = team.members.exclude(pk=instance.pk).first()
                    team.captain = new_captain
                    team.save()
                else:
                    # Если участник был один, удаляем команду
                    team.delete()
            elif team.member_count() == 0:
                team.delete()
    except UserProfile.DoesNotExist:
        pass