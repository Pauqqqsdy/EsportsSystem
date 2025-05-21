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

class ExtendedUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True, 
        label="Email",
        error_messages={
            'required': 'Email обязателен для заполнения'
        }
    )
    privacy_policy = forms.BooleanField(
        required=True, 
        label="Я согласен с политикой конфиденциальности",
        error_messages={
            'required': 'Вы должны принять условия соглашения'
        }
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2', 'privacy_policy')
        error_messages = {
            'username': {
                'required': 'Логин обязателен для заполнения',
            },
            'password1': {
                'required': 'Пароль обязателен для заполнения',
            },
            'password2': {
                'required': 'Пожалуйста, подтвердите пароль',
            },
        }

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget = forms.PasswordInput(attrs={
            'class': 'form-control',
            'required': 'required',
            'oninvalid': "this.setCustomValidity('Пожалуйста, введите пароль')",
            'oninput': "this.setCustomValidity('')"
        })
        self.fields['password2'].widget = forms.PasswordInput(attrs={
            'class': 'form-control',
            'required': 'required',
            'oninvalid': "this.setCustomValidity('Пожалуйста, подтвердите пароль')",
            'oninput': "this.setCustomValidity('')"
        })

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