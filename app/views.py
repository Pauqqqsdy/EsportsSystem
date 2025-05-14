"""
Definition of views.
"""

from datetime import datetime
from django.shortcuts import render
from django.http import HttpRequest
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages

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
            'title':'Турниры',
            'message':'Список турниров.',
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