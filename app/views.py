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
from .forms import TournamentForm, AvatarUploadForm

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

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Аккаунт создан! Теперь вы можете войти.')
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'app/register.html', {
        'form': form,
        'title': 'Регистрация',
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
    # Получаем или создаём профиль
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
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