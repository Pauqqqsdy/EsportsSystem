from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.db.models.signals import pre_delete, post_save
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
        (2, '2'),
        (4, '4'),
        (8, '8'),
        (16, '16'),
        (32, '32'),
        (64, '64'),
        (128, '128'),
        (256, '256'),
        (512, '512'),
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
    location = models.CharField(max_length=50, choices=LOCATION_CHOICES, verbose_name="Локация")
    description = models.TextField(verbose_name="Описание", blank=True, null=True)
    creator = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Создатель")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Дата создания")
    is_active = models.BooleanField(default=True, verbose_name="Активный")
    registered_teams = models.ManyToManyField(
        'Team',
        through='TournamentRegistration',
        related_name='tournaments',
        blank=True,
        verbose_name="Зарегистрированные команды"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Турнир'
        verbose_name_plural = 'Турниры'

    def __str__(self):
        return self.name

    def registered_teams_count(self):
        return self.registered_teams.count()

    def is_registered(self, team):
        return self.registered_teams.filter(pk=team.pk).exists()

    def is_creator(self, user):
        return self.creator == user

    def is_full(self):
        return self.registered_teams_count() >= self.max_teams

    def get_teams_display(self):
        return f"{self.registered_teams_count()}/{self.max_teams}"

    def clean(self):
        if self.start_date < timezone.now():
            raise ValidationError("Дата начала турнира не может быть в прошлом")


class TournamentRegistration(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    team = models.ForeignKey('Team', on_delete=models.CASCADE)
    registered_at = models.DateTimeField(auto_now_add=True)
    players = models.ManyToManyField(
        User,
        related_name='tournament_registrations',
        verbose_name="Игроки, участвующие в турнире"
    )

    class Meta:
        unique_together = ('tournament', 'team')
        verbose_name = 'Регистрация на турнир'
        verbose_name_plural = 'Регистрации на турниры'

    def __str__(self):
        return f"{self.team.name} в {self.tournament.name}"


class Team(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Название команды",
        error_messages={
            'unique': "Команда с таким названием уже существует"
        }
    )
    avatar = models.ImageField(
        upload_to='team_avatars/',
        default='team_avatars/default.jpg',
        blank=True,
        null=True,
        verbose_name="Аватар команды"
    )
    captain = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='captained_teams',
        verbose_name="Капитан"
    )
    members = models.ManyToManyField(
        User,
        related_name='teams',
        blank=True,
        verbose_name="Участники"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания"
    )
    invite_code = models.CharField(
        max_length=32,
        unique=True,
        verbose_name="Код приглашения"
    )

    class Meta:
        verbose_name = 'Команда'
        verbose_name_plural = 'Команды'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.pk:
            if not self.invite_code:
                self.invite_code = get_random_string(32)
            super().save(*args, **kwargs)
            self.members.add(self.captain)
        else:
            super().save(*args, **kwargs)

    def member_count(self):
        if not self.pk:
            return 0
        return self.members.count()

    def is_full(self):
        return self.member_count() >= 8

    def is_captain(self, user):
        return self.captain == user

    def is_member(self, user):
        return self.members.filter(pk=user.pk).exists()

    def clean(self):
        if self.member_count() > 8:
            raise ValidationError("Команда не может содержать более 8 участников")
    def get_all_members(self):
        if not self.pk:
            return []
        members = list(self.members.all())
        if self.captain not in members:
            members.insert(0, self.captain)
        return members
    def delete_if_empty(self):
        if self.member_count() == 0:
            self.delete()
            return True
        return False


@receiver(post_save, sender=Team)
def add_captain_to_members(sender, instance, created, **kwargs):
    if created and not instance.members.filter(pk=instance.captain.pk).exists():
        instance.members.add(instance.captain)


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

    def can_register_for_tournament(self, tournament):
        if tournament.game_format == '1x1':
            return True
        return self.team and self.team.is_captain(self.user)


@receiver(pre_delete, sender=User)
def user_deleted(sender, instance, **kwargs):
    try:
        profile = instance.userprofile
        if profile.team:
            team = profile.team
            profile.team = None
            profile.save()
            
            if team.captain == instance:
                if team.member_count() > 1:
                    new_captain = team.members.exclude(pk=instance.pk).first()
                    team.captain = new_captain
                    team.save()
                else:
                    team.delete()
            elif team.member_count() == 0:
                team.delete()
    except UserProfile.DoesNotExist:
        pass

class TournamentBracket(models.Model):
    FORMAT_CHOICES = [
        ('BO1', 'Best of 1'),
        ('BO3', 'Best of 3'),
        ('BO5', 'Best of 5'),
    ]
    
    tournament = models.OneToOneField(Tournament, on_delete=models.CASCADE, related_name='bracket')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class BracketStage(models.Model):
    bracket = models.ForeignKey(TournamentBracket, on_delete=models.CASCADE, related_name='stages')
    name = models.CharField(max_length=100)
    format = models.CharField(max_length=3, choices=TournamentBracket.FORMAT_CHOICES, default='BO3')
    order = models.PositiveIntegerField()
    is_completed = models.BooleanField(default=False)

    class Meta:
        ordering = ['order']

class BracketMatch(models.Model):
    stage = models.ForeignKey(BracketStage, on_delete=models.CASCADE, related_name='matches')
    team1 = models.ForeignKey('Team', on_delete=models.CASCADE, related_name='team1_matches', null=True, blank=True)
    team2 = models.ForeignKey('Team', on_delete=models.CASCADE, related_name='team2_matches', null=True, blank=True)
    winner = models.ForeignKey('Team', on_delete=models.SET_NULL, null=True, blank=True)
    order = models.PositiveIntegerField()
    is_completed = models.BooleanField(default=False)

    class Meta:
        ordering = ['order']