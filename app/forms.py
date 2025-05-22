from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils.translation import gettext_lazy as _
from .models import Tournament, UserProfile, Team
from django.contrib.admin import widgets
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User

class BootstrapAuthenticationForm(AuthenticationForm):
    username = forms.CharField(max_length=16,
                               widget=forms.TextInput({
                                   'class': 'form-control',
                                   'placeholder': 'User name'}))
    password = forms.CharField(label=_("Password"),
                               widget=forms.PasswordInput({
                                   'class': 'form-control',
                                   'placeholder':'Password'}))

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
    email = forms.EmailField(required=True, label="Email")

    class Meta:
        model = UserProfile
        fields = ['avatar']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['email'].initial = self.instance.user.email

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exclude(pk=self.instance.user.pk).exists():
            raise ValidationError("Пользователь с такой почтой уже зарегистрирован")
        return email

    def save(self, commit=True):
        profile = super().save(commit=False)
        if commit:
            profile.save()
            user = profile.user
            user.email = self.cleaned_data['email']
            user.save()
        return profile

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
        if Team.objects.filter(name__iexact=name).exists():
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