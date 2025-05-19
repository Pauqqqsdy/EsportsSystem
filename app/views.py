"""
Definition of views.
"""

from datetime import datetime
from django.http import HttpRequest
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import reverse
from .models import Tournament, UserProfile, Team
from .forms import TeamCreationForm, TournamentForm, AvatarUploadForm, ExtendedUserCreationForm, User
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.utils.crypto import get_random_string

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
            return redirect('profile')
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
            update_session_auth_hash(request, user)
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
    
    return render(request, 'app/profile.html', {
        'profile_user': user,
        'profile': profile,
        'is_owner': is_owner,
    })

@login_required
def create_team(request):
    if request.method == 'POST':
        form = TeamCreationForm(request.POST, request.FILES)
        if form.is_valid():
            team = form.save(commit=False)
            team.captain = request.user
            team.save()
            team.members.add(request.user)
            request.user.userprofile.team = team
            request.user.userprofile.save()
            return redirect('team_page', team_id=team.id)
    else:
        form = TeamCreationForm()
    return render(request, 'app/create_team.html', {'form': form})

@login_required
def join_team(request, invite_code):
    try:
        team = Team.objects.get(invite_code=invite_code)
        user_profile = request.user.userprofile
        
        if user_profile.team:
            messages.error(request, 'Вы уже состоите в команде. Покиньте текущую команду, чтобы присоединиться к новой.')
            return redirect('profile')
            
        if team.is_full():
            messages.error(request, 'Команда уже полная (максимум 8 игроков)')
        elif team.is_member(request.user):
            messages.warning(request, 'Вы уже в этой команде')
        else:
            team.members.add(request.user)
            user_profile.team = team
            user_profile.save()
            messages.success(request, f'Вы присоединились к команде {team.name}')
            
        return redirect('team_page', team_id=team.id)
    except Team.DoesNotExist:
        messages.error(request, 'Неверная ссылка приглашения')
        return redirect('profile')

@login_required
def team_page(request, team_id):
    team = get_object_or_404(Team, id=team_id)
    is_member = team.is_member(request.user)
    is_captain = team.is_captain(request.user)
    
    return render(request, 'app/team_page.html', {
        'team': team,
        'is_member': is_member,
        'is_captain': is_captain,
        'invite_link': request.build_absolute_uri(
            reverse('join_team', kwargs={'invite_code': team.invite_code}))
    })

@login_required
def leave_team(request):
    user_profile = request.user.userprofile
    if user_profile.team:
        team = user_profile.team
        if team.is_captain(request.user) and team.member_count() > 1:
            messages.error(request, 'Вы не можете покинуть команду как капитан. Сначала передайте лидерство.')
            return redirect('team_page', team_id=team.id)
        
        team.members.remove(request.user)
        user_profile.team = None
        user_profile.save()
        messages.success(request, 'Вы вышли из команды')
    return redirect('profile')

@login_required
def delete_team(request, team_id):
    team = get_object_or_404(Team, id=team_id)
    if not team.is_captain(request.user):
        messages.error(request, 'Только капитан может удалить команду')
        return redirect('team_page', team_id=team.id)
    
    team.delete()
    messages.success(request, 'Команда успешно удалена')
    return redirect('profile')

@login_required
def transfer_leadership(request, team_id, new_captain_id):
    team = get_object_or_404(Team, id=team_id)
    if not team.is_captain(request.user):
        messages.error(request, 'Только капитан может передать лидерство')
        return redirect('team_page', team_id=team.id)
    
    new_captain = get_object_or_404(User, id=new_captain_id)
    if not team.is_member(new_captain):
        messages.error(request, 'Новый капитан должен быть участником команды')
        return redirect('team_page', team_id=team.id)
    
    team.captain = new_captain
    team.save()
    messages.success(request, f'Лидерство передано {new_captain.username}')
    return redirect('team_page', team_id=team.id)