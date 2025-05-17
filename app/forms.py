from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils.translation import gettext_lazy as _
from .models import Tournament, UserProfile
from django.contrib.admin import widgets
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User


class BootstrapAuthenticationForm(AuthenticationForm):
    username = forms.CharField(max_length=254,
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
    email = forms.EmailField(required=True, label="Email")
    privacy_policy = forms.BooleanField(required=True, label="Я согласен с политикой конфиденциальности")

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2', 'privacy_policy')

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
        self.fields['username'].widget.attrs.update({'class': 'form-control'})
        self.fields['email'].widget.attrs.update({'class': 'form-control'})
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})
        self.fields['privacy_policy'].widget.attrs.update({'class': 'form-check-input'})