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
    
    TOURNAMENT_FORMAT_CHOICES = [
        ('single_elimination', 'Single Elimination'),
        ('double_elimination', 'Double Elimination'),
        ('round_robin', 'Round Robin'),
    ]
    
    TEAM_COUNT_CHOICES = [(i, str(i)) for i in range(2, 513)]
    
    LOCATION_CHOICES = [
        ('China', 'Китай'),
        ('Western Europe', 'Западная Европа'),
        ('Eastern Europe', 'Восточная Европа'),
        ('Southeast Asia', 'ЮВ Азия'),
        ('North America', 'Северная Америка'),
        ('South America', 'Южная Америка'),
    ]

    name = models.CharField(max_length=50, verbose_name="Название турнира")
    max_teams = models.IntegerField(choices=TEAM_COUNT_CHOICES, verbose_name="Максимальное количество команд")
    start_date = models.DateTimeField(verbose_name="Дата начала")
    discipline = models.CharField(max_length=50, choices=DISCIPLINE_CHOICES, verbose_name="Дисциплина")
    game_format = models.CharField(max_length=50, choices=FORMAT_CHOICES, verbose_name="Формат игры")
    tournament_format = models.CharField(max_length=50, choices=TOURNAMENT_FORMAT_CHOICES, verbose_name="Формат турнира", blank=True, null=True)
    location = models.CharField(max_length=50, choices=LOCATION_CHOICES, verbose_name="Локация")
    description = models.TextField(max_length=1000, verbose_name="Описание", blank=True, null=True)
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
        if self.start_date and self.start_date < timezone.now():
            raise ValidationError("Невозможно назначить турнир в уже прошедшую дату")

    def get_status(self):
        """Получить статус турнира"""
        if not hasattr(self, 'bracket'):
            return 'planned'
        
        # Проверяем, есть ли завершенные матчи
        total_matches = BracketMatch.objects.filter(stage__bracket=self.bracket).count()
        completed_matches = BracketMatch.objects.filter(stage__bracket=self.bracket, is_completed=True).count()
        
        if completed_matches == 0:
            return 'planned'
        elif completed_matches < total_matches:
            return 'in_progress'
        else:
            # Проверяем, завершен ли финал
            final_stage = self.bracket.stages.filter(name='Финал').first()
            if final_stage and final_stage.matches.filter(is_completed=True).exists():
                return 'completed'
            return 'in_progress'

    def get_status_display(self):
        """Получить отображаемое название статуса"""
        status_map = {
            'planned': 'Запланирован',
            'in_progress': 'В процессе',
            'completed': 'Завершён'
        }
        return status_map.get(self.get_status(), 'Неизвестно')


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
        max_length=20,
        unique=True,
        verbose_name="Название команды",
        error_messages={
            'unique': "Команда с таким названием уже существует"
        }
    )
    avatar = models.ImageField(
        upload_to='team_avatars/',
        default='team_avatars/default_team.jpg',
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
    
    DISTRIBUTION_CHOICES = [
        ('random', 'Случайное распределение'),
        ('manual', 'Ручное распределение'),
    ]
    
    tournament = models.OneToOneField(Tournament, on_delete=models.CASCADE, related_name='bracket')
    distribution_type = models.CharField(max_length=20, choices=DISTRIBUTION_CHOICES, default='random')
    third_place_match = models.BooleanField(default=False, verbose_name="Матч за третье место")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Турнирная сетка'
        verbose_name_plural = 'Турнирные сетки'
    
    def __str__(self):
        return f"Сетка турнира {self.tournament.name}"

class BracketStage(models.Model):
    STAGE_TYPE_CHOICES = [
        ('upper', 'Верхняя сетка'),
        ('lower', 'Нижняя сетка'),
        ('final', 'Финал'),
        ('third_place', 'Матч за 3 место'),
        ('normal', 'Обычный этап'),
    ]
    
    bracket = models.ForeignKey(TournamentBracket, on_delete=models.CASCADE, related_name='stages')
    name = models.CharField(max_length=100)
    format = models.CharField(max_length=3, choices=TournamentBracket.FORMAT_CHOICES, default='BO3')
    stage_type = models.CharField(max_length=20, choices=STAGE_TYPE_CHOICES, default='normal')
    order = models.PositiveIntegerField()
    scheduled_time = models.DateTimeField(null=True, blank=True, verbose_name="Запланированное время")
    is_completed = models.BooleanField(default=False)

    class Meta:
        ordering = ['order']
        verbose_name = 'Этап турнира'
        verbose_name_plural = 'Этапы турнира'
    
    def __str__(self):
        return f"{self.name} - {self.bracket.tournament.name}"

class BracketMatch(models.Model):
    stage = models.ForeignKey(BracketStage, on_delete=models.CASCADE, related_name='matches')
    team1 = models.ForeignKey('Team', on_delete=models.CASCADE, related_name='team1_matches', null=True, blank=True)
    team2 = models.ForeignKey('Team', on_delete=models.CASCADE, related_name='team2_matches', null=True, blank=True)
    winner = models.ForeignKey('Team', on_delete=models.SET_NULL, null=True, blank=True, related_name='won_matches')
    team1_score = models.PositiveIntegerField(default=0, verbose_name="Счет первой команды")
    team2_score = models.PositiveIntegerField(default=0, verbose_name="Счет второй команды")
    order = models.PositiveIntegerField()
    scheduled_time = models.DateTimeField(null=True, blank=True, verbose_name="Запланированное время")
    is_completed = models.BooleanField(default=False)
    is_bye = models.BooleanField(default=False, verbose_name="Проход без игры")
    
    class Meta:
        ordering = ['order']
        verbose_name = 'Матч'
        verbose_name_plural = 'Матчи'
    
    def __str__(self):
        if self.team1 and self.team2:
            return f"{self.team1.name} vs {self.team2.name}"
        elif self.team1:
            return f"{self.team1.name} (проход)"
        elif self.team2:
            return f"{self.team2.name} (проход)"
        return f"Матч #{self.order}"
    
    def get_score_display(self):
        """Получить отображение счета"""
        if self.is_completed:
            return f"{self.team1_score}:{self.team2_score}"
        return "-:-"
    
    def clean(self):
        """Валидация модели"""
        if self.winner and self.winner not in [self.team1, self.team2]:
            raise ValidationError("Победитель должен быть одной из команд в матче")
        
        if self.is_completed and not self.winner and not self.is_bye:
            raise ValidationError("Для завершенного матча должен быть указан победитель")
    
    def save(self, *args, **kwargs):
        # Автоматически определяем победителя по счету
        if self.is_completed and not self.is_bye:
            if self.team1_score > self.team2_score:
                self.winner = self.team1
            elif self.team2_score > self.team1_score:
                self.winner = self.team2
        
        super().save(*args, **kwargs)


class RoundRobinTable(models.Model):
    """Таблица для турнира Round Robin"""
    tournament = models.OneToOneField(Tournament, on_delete=models.CASCADE, related_name='round_robin_table')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Таблица Round Robin'
        verbose_name_plural = 'Таблицы Round Robin'
    
    def __str__(self):
        return f"Таблица Round Robin - {self.tournament.name}"


class RoundRobinResult(models.Model):
    """Результаты команд в турнире Round Robin"""
    table = models.ForeignKey(RoundRobinTable, on_delete=models.CASCADE, related_name='results')
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    matches_played = models.PositiveIntegerField(default=0)
    wins = models.PositiveIntegerField(default=0)
    losses = models.PositiveIntegerField(default=0)
    points = models.PositiveIntegerField(default=0)  # Очки (обычно 3 за победу, 1 за ничью, 0 за поражение)
    map_difference = models.IntegerField(default=0, verbose_name="Разница карт")
    
    class Meta:
        unique_together = ('table', 'team')
        ordering = ['-points', '-wins', 'losses']
        verbose_name = 'Результат команды в Round Robin'
        verbose_name_plural = 'Результаты команд в Round Robin'
    
    def __str__(self):
        return f"{self.team.name} - {self.points} очков"
    
    def get_win_rate(self):
        """Получить процент побед"""
        if self.matches_played == 0:
            return 0
        return round((self.wins / self.matches_played) * 100, 1)


class RoundRobinMatch(models.Model):
    """Матч в турнире Round Robin"""
    table = models.ForeignKey(RoundRobinTable, on_delete=models.CASCADE, related_name='matches')
    team1 = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='rr_team1_matches')
    team2 = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='rr_team2_matches')
    winner = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name='rr_won_matches')
    team1_score = models.PositiveIntegerField(default=0)
    team2_score = models.PositiveIntegerField(default=0)
    format = models.CharField(max_length=3, choices=TournamentBracket.FORMAT_CHOICES, default='BO3')
    scheduled_time = models.DateTimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    round_number = models.PositiveIntegerField(default=1)
    
    class Meta:
        unique_together = ('table', 'team1', 'team2')
        ordering = ['round_number', 'scheduled_time']
        verbose_name = 'Матч Round Robin'
        verbose_name_plural = 'Матчи Round Robin'
    
    def __str__(self):
        return f"{self.team1.name} vs {self.team2.name} (Раунд {self.round_number})"
    
    def get_score_display(self):
        if self.is_completed:
            return f"{self.team1_score}:{self.team2_score}"
        return "-:-"
    
    def save(self, *args, **kwargs):
        # Автоматически определяем победителя по счету
        if self.is_completed:
            if self.team1_score > self.team2_score:
                self.winner = self.team1
            elif self.team2_score > self.team1_score:
                self.winner = self.team2
        
        super().save(*args, **kwargs)
        
        # Обновляем результаты в таблице
        if self.is_completed:
            self.update_table_results()
    
    def update_table_results(self):
        """Обновить результаты в таблице Round Robin"""
        # Получаем или создаем результаты для обеих команд
        result1, created1 = RoundRobinResult.objects.get_or_create(
            table=self.table, team=self.team1
        )
        result2, created2 = RoundRobinResult.objects.get_or_create(
            table=self.table, team=self.team2
        )
        # Если матч уже был учтен, не обновляем статистику повторно
        if hasattr(self, '_results_updated'):
            return
        # Обновляем статистику
        result1.matches_played += 1
        result2.matches_played += 1
        # Разница карт
        result1.map_difference += self.team1_score - self.team2_score
        result2.map_difference += self.team2_score - self.team1_score
        if self.winner == self.team1:
            result1.wins += 1
            result1.points += 3
            result2.losses += 1
        elif self.winner == self.team2:
            result2.wins += 1
            result2.points += 3
            result1.losses += 1
        result1.save()
        result2.save()
        self._results_updated = True