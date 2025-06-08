from datetime import datetime
import random
from django.db.models import Q
from django.http import HttpRequest, JsonResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import reverse
from .models import Tournament, TournamentBracket, BracketStage, BracketMatch, TournamentRegistration, UserProfile, Team
from .forms import BracketGenerationForm, BracketStageForm, MatchResultForm, TeamCreationForm, TournamentEditForm, TournamentForm, AvatarUploadForm, ExtendedUserCreationForm, TournamentParticipationForm, User
from django.contrib.auth import update_session_auth_hash
from django.utils.crypto import get_random_string
from django.db import transaction
from django.views.decorators.http import require_POST
from django.utils import timezone

from django.utils import timezone

def home(request):
    assert isinstance(request, HttpRequest)

    # Фильтруем только будущие турниры (начало >= текущей даты)
    tournaments = Tournament.objects.filter(
        start_date__gte=timezone.now()
    ).order_by('start_date')[:6]  # Берём первые 6

    return render(
        request,
        'app/index.html',
        {
            'title': 'ZXC.Tournament',
            'year': datetime.now().year,
            'tournaments': tournaments,
        }
    )
def register(request):
    if request.method == 'POST':
        form = ExtendedUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.email = form.cleaned_data['email']
            user.save()
            
            UserProfile.objects.create(user=user)
            return render(request, 'app/auth/registration_success.html', {
                'title': 'Регистрация успешна',
                'year': datetime.now().year,
            })
    else:
        form = ExtendedUserCreationForm()
    
    return render(request, 'app/auth/register.html', {
        'form': form,
        'title': 'Регистрация',
        'year': datetime.now().year,
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
    return render(request, 'app/profile/change_password.html', {
        'form': form,
        'title': 'Смена пароля'
    })

def service_terms(request):
    return render(
        request,
        'app/service_terms.html',
        {
            'title': 'Пользовательское соглашение',
            'year': datetime.now().year,
        }
    )

def privacy_policy(request):
    return render(
        request,
        'app/privacy_policy.html',
        {
            'title': 'Политика конфиденциальности',
            'year': datetime.now().year,
        }
    )

@login_required
def profile(request, username=None):
    if username is None:
        profile_user = request.user
    else:
        profile_user = get_object_or_404(User, username=username)
    
    profile, created = UserProfile.objects.get_or_create(user=profile_user)
    
    is_owner = (request.user == profile_user)
    
    avatar_form = None
    if is_owner and request.method == 'POST':
        avatar_form = AvatarUploadForm(request.POST, request.FILES, instance=profile)
        if avatar_form.is_valid():
            avatar_form.save()
            return redirect('profile')
    elif is_owner:
        avatar_form = AvatarUploadForm(instance=profile)
    
    return render(request, 'app/profile/profile.html', {
        'profile_user': profile_user,
        'profile': profile,
        'is_owner': is_owner,
        'avatar_form': avatar_form,
        'title': 'Профиль',
        'year': datetime.now().year,
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
    
    return render(request, 'app/profile/edit_profile.html', {
        'form': form,
        'profile': profile
    })

def view_profile(request, username):
    user = User.objects.get(username=username)
    profile = UserProfile.objects.get(user=user)
    is_owner = (request.user == user)
    
    return render(request, 'app/profile/profile.html', {
        'profile_user': user,
        'profile': profile,
        'is_owner': is_owner,
    })

@login_required
def create_team(request):
    if request.method == 'POST':
        form = TeamCreationForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    team = form.save(commit=False)
                    team.captain = request.user
                    
                    team.save()
                    
                    request.user.userprofile.team = team
                    request.user.userprofile.save()
                    
                    messages.success(request, f'Команда "{team.name}" успешно создана!')
                    return redirect('team_page', team_id=team.id)
                    
            except Exception as e:
                messages.error(request, f'Ошибка при создании команды: {str(e)}')
                return redirect('create_team')
    else:
        form = TeamCreationForm()
    
    return render(request, 'app/teams/create_team.html', {'form': form})

@login_required
def join_team(request, invite_code):
    try:
        team = Team.objects.get(invite_code=invite_code)
        user_profile = request.user.userprofile
        
        if user_profile.team:
            messages.error(request, 'Вы уже состоите в команде. Покиньте текущую команду, чтобы присоединиться к новой.')
            return redirect('profile')
            
        if team.is_full():
            messages.error(request, 'Команда уже полная')
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
    
    return render(request, 'app/teams/team_page.html', {
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
            messages.error(request, 'Вы не можете покинуть команду будучи капитаном. Сначала передайте лидерство или удалите команду.')
            return redirect('team_page', team_id=team.id)
        
        team.members.remove(request.user)
        user_profile.team = None
        user_profile.save()
        
        if team.member_count() == 0:
            team.delete()
            messages.success(request, 'Вы вышли из команды. Команда удалена, так как в ней не осталось участников.')
        else:
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
def edit_team(request, team_id):
    team = get_object_or_404(Team, id=team_id)
    if not team.is_captain(request.user):
        messages.error(request, 'Только капитан может редактировать команду')
        return redirect('team_page', team_id=team.id)

    if request.method == 'POST':
        form = TeamCreationForm(request.POST, request.FILES, instance=team)
        if form.is_valid():
            form.save()
            messages.success(request, 'Команда успешно обновлена')
            return redirect('team_page', team_id=team.id)
    else:
        form = TeamCreationForm(instance=team)
    
    return render(request, 'app/teams/edit_team.html', {
        'form': form,
        'team': team
    })

@login_required
def remove_member(request, team_id, member_id):
    team = get_object_or_404(Team, id=team_id)
    member = get_object_or_404(User, id=member_id)
    
    if not team.is_captain(request.user):
        messages.error(request, 'Только капитан может удалять участников')
        return redirect('team_page', team_id=team.id)
    
    if member == request.user:
        messages.error(request, 'Используйте "Покинуть команду" для выхода из команды')
        return redirect('team_page', team_id=team.id)
    
    if not team.is_member(member):
        messages.error(request, 'Этот пользователь не состоит в вашей команде')
        return redirect('team_page', team_id=team.id)
    
    team.members.remove(member)
    member.userprofile.team = None
    member.userprofile.save()
    messages.success(request, f'Участник {member.username} удален из команды')
    
    return redirect('team_page', team_id=team.id)

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

def tournaments(request):
    region = request.GET.get('region')
    discipline = request.GET.get('discipline')
    game_format = request.GET.get('game_format')
    tournaments_qs = Tournament.objects.filter(is_active=True).order_by('-created_at')

    if region:
        tournaments_qs = tournaments_qs.filter(location=region)
    if discipline:
        tournaments_qs = tournaments_qs.filter(discipline=discipline)
    if game_format:
        tournaments_qs = tournaments_qs.filter(game_format=game_format)

    context = {
        'tournaments': tournaments_qs,
        'regions': Tournament.LOCATION_CHOICES,
        'disciplines': Tournament.DISCIPLINE_CHOICES,
        'game_formats': Tournament.FORMAT_CHOICES,
        'selected_region': region,
        'selected_discipline': discipline,
        'selected_game_format': game_format,
        'title': 'Турниры',
    }
    return render(request, 'app/tournaments/tournaments.html', context)

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
    return render(request, 'app/tournaments/create_tournament.html', {'form': form})

def tournament_detail(request, tournament_id):
    tournament = get_object_or_404(Tournament, id=tournament_id)
    is_creator = tournament.is_creator(request.user) if request.user.is_authenticated else False
    user_team = None
    is_registered = False
    
    if request.user.is_authenticated and hasattr(request.user, 'userprofile'):
        user_team = request.user.userprofile.team
        if user_team:
            is_registered = tournament.is_registered(user_team)
    
    context = {
        'tournament': tournament,
        'is_creator': is_creator,
        'user_team': user_team,
        'is_registered': is_registered,
        'registered_teams': tournament.registered_teams.all(),
        'registered_count': f"{tournament.registered_teams_count()}/{tournament.max_teams}",
    }
    
    return render(request, 'app/tournaments/tournament_detail.html', context)

@login_required
def edit_tournament(request, tournament_id):
    tournament = get_object_or_404(Tournament, id=tournament_id)
    
    if not tournament.is_creator(request.user):
        messages.error(request, 'Только создатель может редактировать турнир')
        return redirect('tournament_detail', tournament_id=tournament.id)
    
    if request.method == 'POST':
        form = TournamentEditForm(request.POST, instance=tournament)
        if form.is_valid():
            form.save()
            messages.success(request, 'Турнир успешно обновлен')
            return redirect('tournament_detail', tournament_id=tournament.id)
    else:
        form = TournamentEditForm(instance=tournament)
    
    return render(request, 'app/tournaments/edit_tournament.html', {
        'form': form,
        'tournament': tournament
    })

@login_required
def participate_tournament(request, tournament_id):
    tournament = get_object_or_404(Tournament, id=tournament_id)
    user_profile = request.user.userprofile
    
    if not user_profile.team:
        if tournament.game_format != '1x1':
            messages.error(request, 'Для участия в этом турнире вам нужно состоять в команде')
            return redirect('tournament_detail', tournament_id=tournament.id)
        team = Team.objects.create(
            name=f"{request.user.username}_temp",
            captain=request.user
        )
        user_profile.team = team
        user_profile.save()
    else:
        team = user_profile.team
        if not team.is_captain(request.user) and tournament.game_format != '1x1':
            messages.error(request, 'Только капитан может зарегистрировать команду на турнир')
            return redirect('tournament_detail', tournament_id=tournament.id)
    
    if tournament.is_registered(team):
        messages.warning(request, 'Ваша команда уже зарегистрирована на этот турнир')
        return redirect('tournament_detail', tournament_id=tournament.id)
    
    if tournament.registered_teams_count() >= tournament.max_teams:
        messages.error(request, 'Турнир уже заполнен')
        return redirect('tournament_detail', tournament_id=tournament.id)
    
    if tournament.game_format == '1x1':
        tournament.registered_teams.add(team)
        messages.success(request, 'Вы успешно зарегистрированы на турнир!')
        return redirect('tournament_detail', tournament_id=tournament.id)
    
    if request.method == 'POST':
        form = TournamentParticipationForm(request.POST, team=team, game_format=tournament.game_format)
        if form.is_valid():
            tournament.registered_teams.add(team)
            registration = TournamentRegistration.objects.get(tournament=tournament, team=team)
            registration.players.set(form.cleaned_data['players'])
            messages.success(request, 'Ваша команда успешно зарегистрирована на турнир!')
            return redirect('tournament_detail', tournament_id=tournament.id)
    else:
        form = TournamentParticipationForm(team=team, game_format=tournament.game_format)
    
    return render(request, 'app/tournaments/participate_tournament.html', {
        'form': form,
        'tournament': tournament,
        'team': team
    })

@login_required
def my_tournaments(request):
    user_teams = Team.objects.filter(Q(captain=request.user) | Q(members=request.user)).distinct()
    participating_tournaments = Tournament.objects.filter(
        registered_teams__in=user_teams,
        is_active=True
    ).order_by('start_date')
    
    created_tournaments = Tournament.objects.filter(
        creator=request.user,
        is_active=True
    ).order_by('start_date')
    
    return render(request, 'app/tournaments/my_tournaments.html', {
        'participating_tournaments': participating_tournaments,
        'created_tournaments': created_tournaments,
        'title': 'Мои турниры'
    })

@login_required
@require_POST
def remove_team_from_tournament(request, tournament_id, team_id):
    tournament = get_object_or_404(Tournament, id=tournament_id)
    team = get_object_or_404(Team, id=team_id)
    
    if not tournament.is_creator(request.user):
        return JsonResponse({'success': False, 'error': 'Только создатель может удалять команды'}, status=403)
    
    if not tournament.is_registered(team):
        return JsonResponse({'success': False, 'error': 'Эта команда не зарегистрирована на турнир'}, status=400)
    
    tournament.registered_teams.remove(team)
    return JsonResponse({'success': True})

def create_bracket_stages(bracket, teams):
    team_count = len(teams)
    current_round = team_count
    round_number = 1
    
    while current_round >= 2:
        stage_name = get_stage_name(current_round)
        stage = BracketStage.objects.create(
            bracket=bracket,
            name=stage_name,
            format=get_default_format(current_round),
            order=round_number
        )
        
        matches_in_round = current_round // 2
        for i in range(matches_in_round):
            team1 = teams[i*2] if i*2 < len(teams) else None
            team2 = teams[i*2+1] if i*2+1 < len(teams) else None
            
            BracketMatch.objects.create(
                stage=stage,
                team1=team1,
                team2=team2,
                order=i+1
            )
        
        current_round = matches_in_round
        round_number += 1

@login_required
def generate_bracket(request, tournament_id):
    tournament = get_object_or_404(Tournament, id=tournament_id)
    
    if not tournament.is_creator(request.user):
        messages.error(request, 'Только создатель турнира может формировать сетку')
        return redirect('tournament_detail', tournament_id=tournament.id)
    
    if not tournament.registered_teams.exists():
        messages.error(request, 'Нет зарегистрированных команд для формирования сетки')
        return redirect('tournament_detail', tournament_id=tournament.id)
    
    if request.method == 'POST':
        form = BracketGenerationForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    if hasattr(tournament, 'bracket'):
                        tournament.bracket.delete()
                    
                    bracket = TournamentBracket.objects.create(tournament=tournament)
                    teams = list(tournament.registered_teams.all())
                    
                    if form.cleaned_data['generation_type'] == 'random':
                        random.shuffle(teams)
                    
                    create_bracket_stages(bracket, teams)
                    
                    messages.success(request, 'Турнирная сетка успешно создана!')
                    return redirect('tournament_bracket', tournament_id=tournament.id)
            
            except Exception as e:
                messages.error(request, f'Ошибка при создании сетки: {str(e)}')
                return redirect('tournament_detail', tournament_id=tournament.id)
    else:
        form = BracketGenerationForm()
    
    return render(request, 'app/tournaments/generate_bracket.html', {
        'form': form,
        'tournament': tournament
    })

def get_stage_name(team_count):
    stages = {
        2: 'Финал',
        4: 'Полуфиналы',
        8: 'Четвертьфиналы',
        16: '1/8 финала',
        32: '1/16 финала',
        64: '1/32 финала',
        128: '1/64 финала',
        256: '1/128 финала',
        512: '1/256 финала'
    }
    return stages.get(team_count, f'Раунд на {team_count} команд')

def get_default_format(team_count):
    if team_count <= 4:
        return 'BO3'
    elif team_count <= 8:
        return 'BO3'
    else:
        return 'BO1'

@login_required
def tournament_bracket(request, tournament_id):
    tournament = get_object_or_404(Tournament, id=tournament_id)
    bracket = getattr(tournament, 'bracket', None)
    is_creator = tournament.is_creator(request.user) if request.user.is_authenticated else False
    
    return render(request, 'app/tournaments/tournament_bracket.html', {
        'tournament': tournament,
        'bracket': bracket,
        'is_creator': is_creator
    })

@login_required
def edit_stage_format(request, tournament_id, stage_id):
    tournament = get_object_or_404(Tournament, id=tournament_id)
    stage = get_object_or_404(BracketStage, id=stage_id, bracket__tournament=tournament)
    
    if not tournament.is_creator(request.user):
        messages.error(request, 'Только создатель турнира может изменять формат этапа')
        return redirect('tournament_bracket', tournament_id=tournament.id)
    
    if request.method == 'POST':
        form = BracketStageForm(request.POST, instance=stage)
        if form.is_valid():
            form.save()
            messages.success(request, 'Формат этапа успешно обновлен')
            return redirect('tournament_bracket', tournament_id=tournament.id)
    else:
        form = BracketStageForm(instance=stage)
    
    return render(request, 'app/tournaments/edit_stage_format.html', {
        'form': form,
        'tournament': tournament,
        'stage': stage
    })

@login_required
def update_match_result(request, tournament_id, match_id):
    tournament = get_object_or_404(Tournament, id=tournament_id)
    match = get_object_or_404(BracketMatch, id=match_id, stage__bracket__tournament=tournament)
    
    if not tournament.is_creator(request.user):
        messages.error(request, 'Только создатель турнира может обновлять результаты')
        return redirect('tournament_bracket', tournament_id=tournament.id)

    if not match.team1 or not match.team2:
        messages.error(request, 'Обе команды должны быть определены для матча')
        return redirect('tournament_bracket', tournament_id=tournament.id)
    
    if request.method == 'POST':
        form = MatchResultForm(request.POST, instance=match)
        if form.is_valid():
            match = form.save(commit=False)
            match.is_completed = True
            match.save()
            
            promote_winner_to_next_stage(match)
            
            messages.success(request, 'Результат матча обновлен')
            return redirect('tournament_bracket', tournament_id=tournament.id)
    else:
        form = MatchResultForm(instance=match)
    
    return render(request, 'app/tournaments/update_match_result.html', {
        'form': form,
        'tournament': tournament,
        'match': match
    })

def promote_winner_to_next_stage(match):
    if not match.winner:
        return
    
    next_stage = BracketStage.objects.filter(
        bracket=match.stage.bracket,
        order=match.stage.order + 1
    ).first()
    
    if not next_stage:
        return
    
    match_position = (match.order + 1) // 2
    next_match = BracketMatch.objects.filter(
        stage=next_stage,
        order=match_position
    ).first()
    
    if next_match:
        if match.order % 2 == 1:
            next_match.team1 = match.winner
        else:
            next_match.team2 = match.winner
        next_match.save()

@login_required
def complete_stage(request, tournament_id, stage_id):
    tournament = get_object_or_404(Tournament, id=tournament_id)
    stage = get_object_or_404(BracketStage, id=stage_id, bracket__tournament=tournament)
    
    if not tournament.is_creator(request.user):
        messages.error(request, 'Только создатель турнира может завершать этапы')
        return redirect('tournament_bracket', tournament_id=tournament.id)
    
    incomplete_matches = stage.matches.filter(is_completed=False).exists()
    if incomplete_matches:
        messages.error(request, 'Не все матчи этого этапа завершены')
        return redirect('tournament_bracket', tournament_id=tournament.id)
    
    stage.is_completed = True
    stage.save()
    
    messages.success(request, f'Этап "{stage.name}" успешно завершен')
    return redirect('tournament_bracket', tournament_id=tournament.id)

@login_required
def cancel_tournament_participation(request, tournament_id):
    tournament = get_object_or_404(Tournament, id=tournament_id)
    user_profile = request.user.userprofile
    team = user_profile.team

    # Проверяем, состоит ли пользователь в команде и является ли он капитаном
    if not team or not team.is_captain(request.user):
        messages.error(request, 'Только капитан может отменить регистрацию команды')
        return redirect('team_page', team_id=team.id)

    # Убираем команду из турнира
    try:
        registration = TournamentRegistration.objects.get(tournament=tournament, team=team)
        registration.delete()
        messages.success(request, 'Вы успешно отменили регистрацию вашей команды')
    except TournamentRegistration.DoesNotExist:
        messages.warning(request, 'Команда не была зарегистрирована на этот турнир')

    return redirect('tournament_detail', tournament_id=tournament.id)