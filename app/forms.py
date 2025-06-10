from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils.translation import gettext_lazy as _
from .models import BracketMatch, BracketStage, Tournament, UserProfile, Team
from django.contrib.admin import widgets
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.utils import timezone

class BootstrapAuthenticationForm(AuthenticationForm):
    username = forms.CharField(max_length=16,
                               widget=forms.TextInput({
                                   'class': 'form-control',
                                   'placeholder': 'Логин'}))
    password = forms.CharField(label=_("Password"),
                               widget=forms.PasswordInput({
                                   'class': 'form-control',
                                   'placeholder':'Пароль'}))

class ExtendedUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True, 
        label="Email",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите ваш email',
            'oninvalid': "this.setCustomValidity('Email обязателен для заполнения')",
            'oninput': "this.setCustomValidity('')"
        }),
        error_messages={
            'required': 'Email обязателен для заполнения',
            'invalid': 'Введите корректный email адрес'
        }
    )
    privacy_policy = forms.BooleanField(
        required=True, 
        label="Я согласен с политикой конфиденциальности",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'oninvalid': "this.setCustomValidity('Требуется принять условия соглашения')",
            'oninput': "this.setCustomValidity('')"
        }),
        error_messages={
            'required': 'Требуется принять условия соглашения'
        }
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2', 'privacy_policy')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Придумайте логин',
                'pattern': '[a-zA-Z0-9]+',
                'maxlength': '16',
                'oninvalid': "this.setCustomValidity('Логин обязателен для заполнения')",
                'oninput': "this.setCustomValidity('')"
            }),
        }
        error_messages = {
            'username': {
                'required': 'Логин обязателен для заполнения',
                'max_length': 'Логин не должен превышать 16 символов',
                'invalid': 'Только латинские буквы и цифры'
            },
            'password1': {
                'required': 'Пароль обязателен для заполнения',
                'password_mismatch': 'Пароли не совпадают',
                'password_too_short': 'Пароль должен содержать минимум 8 символов',
                'password_too_common': 'Пароль слишком простой'
            },
            'password2': {
                'required': 'Пожалуйста, подтвердите пароль',
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget = forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Придумайте пароль',
            'required': 'required',
            'oninvalid': "this.setCustomValidity('Пароль обязателен для заполнения')",
            'oninput': "this.setCustomValidity('')"
        })
        self.fields['password2'].widget = forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Повторите пароль',
            'required': 'required',
            'oninvalid': "this.setCustomValidity('Пожалуйста, подтвердите пароль')",
            'oninput': "this.setCustomValidity('')"
        })

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise ValidationError("Пользователь с такой почтой уже зарегистрирован")
        return email

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise ValidationError("Этот никнейм уже занят")
        return username

class AvatarUploadForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['avatar']

class TeamCreationForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ['name', 'avatar']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'avatar': forms.FileInput(attrs={'class': 'form-control-file'})
        }
    
    def clean_name(self):
        name = self.cleaned_data['name']
        current_team = self.instance

        if Team.objects.filter(name__iexact=name).exclude(pk=current_team.pk).exists():
            raise forms.ValidationError("Команда с таким названием уже существует")
        return name

class TournamentForm(forms.ModelForm):
    class Meta:
        model = Tournament
        fields = ['name', 'max_teams', 'start_date', 'discipline', 
                 'game_format', 'tournament_format', 'location', 'description']
        widgets = {
            'start_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super(TournamentForm, self).__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        
        tournament_format_choices = [('', '--------')] + list(Tournament.TOURNAMENT_FORMAT_CHOICES)
        self.fields['tournament_format'].choices = tournament_format_choices
        
        if self.instance and self.instance.pk:
            self.fields['discipline'].disabled = True
            self.fields['game_format'].disabled = True
        
        if 'discipline' in self.data:
            try:
                discipline = self.data.get('discipline')
                self.update_game_format_choices(discipline)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk:
            self.update_game_format_choices(self.instance.discipline)
    
    def update_game_format_choices(self, discipline):
        if discipline == 'Dota 2':
            self.fields['game_format'].choices = [
                ('1x1', '1x1'),
                ('5x5', '5x5'),
            ]
        elif discipline in ['CS 2', 'LoL']:
            self.fields['game_format'].choices = [
                ('1x1', '1x1'),
                ('2x2', '2x2'),
                ('5x5', '5x5'),
            ]
        elif discipline == 'Valorant':
            self.fields['game_format'].choices = [
                ('1x1', '1x1'),
                ('2x2', '2x2'),
                ('3x3', '3x3'),
                ('5x5', '5x5'),
            ]
    
    def clean_start_date(self):
        start_date = self.cleaned_data.get('start_date')
        if start_date and start_date < timezone.now():
            raise forms.ValidationError("Невозможно назначить турнир в уже прошедшую дату")
        return start_date
    
    def clean_tournament_format(self):
        tournament_format = self.cleaned_data.get('tournament_format')
        if not tournament_format:
            raise forms.ValidationError("Необходимо выбрать формат турнира")
        return tournament_format

class TournamentParticipationForm(forms.Form):
    def __init__(self, *args, **kwargs):
        team = kwargs.pop('team', None)
        game_format = kwargs.pop('game_format', None)
        super().__init__(*args, **kwargs)
        
        if team and game_format:
            members = team.members.all()
            required_players = {
                '1x1': 1,
                '2x2': 2,
                '3x3': 3,
                '5x5': 5
            }.get(game_format, 1)
            
            self.fields['players'] = forms.ModelMultipleChoiceField(
                queryset=members,
                widget=forms.CheckboxSelectMultiple,
                label=f"Выберите {required_players} игрока(ов)",
                required=True
            )
            
            self.required_players = required_players
    
    def clean_players(self):
        players = self.cleaned_data.get('players', [])
        if len(players) != self.required_players:
            raise forms.ValidationError(f"Необходимо выбрать ровно {self.required_players} игрока(ов)")
        return players

class TournamentEditForm(TournamentForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['discipline'].disabled = True
        self.fields['game_format'].disabled = True

class BracketGenerationForm(forms.Form):
    GENERATION_CHOICES = [
        ('random', 'Случайное распределение команд'),
        ('manual', 'Ручное распределение команд'),
    ]
    
    generation_type = forms.ChoiceField(
        choices=GENERATION_CHOICES,
        widget=forms.RadioSelect,
        label='Способ формирования сетки'
    )

class BracketStageForm(forms.ModelForm):
    class Meta:
        model = BracketStage
        fields = ['name', 'format']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'format': forms.Select(attrs={'class': 'form-control'}),
        }

class MatchResultForm(forms.ModelForm):
    class Meta:
        model = BracketMatch
        fields = ['winner']
        widgets = {
            'winner': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance:
            self.fields['winner'].queryset = Team.objects.filter(
                id__in=[self.instance.team1_id, self.instance.team2_id]
            )