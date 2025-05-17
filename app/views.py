"""
Definition of views.
"""

from datetime import datetime
from django.http import HttpRequest
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.shortcuts import render, redirect
from .models import Tournament, UserProfile
from .forms import TournamentForm, AvatarUploadForm, ExtendedUserCreationForm, User
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash

def home(request):
    """Renders the home page."""
    assert isinstance(request, HttpRequest)
    return render(
        request,
        'app/index.html',
        {
            'title':'ZXC.Tournament',
            'year':datetime.now().year,
        }
    )

def register(request):
    if request.method == 'POST':
        form = ExtendedUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            email = form.cleaned_data['email']
            user.email = email
            user.save()
            
            # Создаем профиль пользователя
            UserProfile.objects.create(user=user)
            
            messages.success(request, 'Аккаунт успешно создан! Теперь вы можете войти.')
            return redirect('login')
    else:
        form = ExtendedUserCreationForm()
    return render(request, 'app/register.html', {
        'form': form,
        'title': 'Регистрация',
        'year': datetime.now().year,
    })

def tournaments(request):
    """Renders the about page."""
    assert isinstance(request, HttpRequest)
    return render(
        request,
        'app/tournaments.html',
        {
            'title':'Последние турниры',
            'year':datetime.now().year,
        }
    )

@login_required
def profile(request):
    return render(request, 'app/profile.html', {
        'title': 'Мой профиль',
        'year': datetime.now().year,
    })

def tournaments(request):
    latest_tournaments = Tournament.objects.filter(is_active=True).order_by('-created_at')[:10]
    return render(request, 'app/tournaments.html', {
        'tournaments': latest_tournaments,
        'title': 'Турниры',
    })

@login_required
def create_tournament(request):
    if request.method == 'POST':
        form = TournamentForm(request.POST)
        if form.is_valid():
            tournament = form.save(commit=False)
            tournament.creator = request.user
            tournament.save()
            return redirect('tournaments')
    else:
        form = TournamentForm()
    return render(request, 'app/create_tournament.html', {'form': form})


@login_required
def profile(request):
    try:
        profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user, bio='')

    if request.method == 'POST':
        form = AvatarUploadForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('profile')  # Обновляем страницу
    else:
        form = AvatarUploadForm(instance=profile)
    
    return render(request, 'app/profile.html', {
        'profile': profile,
        'form': form
    })

@login_required
def edit_profile(request):
    profile = request.user.userprofile
    if request.method == 'POST':
        form = AvatarUploadForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('profile')
    else:
        form = AvatarUploadForm(instance=profile)
    
    return render(request, 'app/edit_profile.html', {
        'form': form,
        'profile': profile
    })

@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Важно, чтобы пользователь не разлогинился
            messages.success(request, 'Пароль успешно изменен!')
            return redirect('profile')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'app/change_password.html', {
        'form': form,
        'title': 'Смена пароля'
    })

def view_profile(request, username):
    user = User.objects.get(username=username)
    profile = UserProfile.objects.get(user=user)
    is_owner = (request.user == user)
    
    return render(request, 'app/view_profile.html', {
        'profile_user': user,
        'profile': profile,
        'is_owner': is_owner,
    })