
import random
import math
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from .models import (
    Tournament, TournamentBracket, BracketStage, BracketMatch,
    RoundRobinTable, RoundRobinMatch, RoundRobinResult, Team
)


def create_single_elimination_bracket(tournament, teams, distribution_type='random', 
                                     third_place_match=False, stage_formats=None):
    """Создает турнирную сетку Single Elimination"""
    
    if distribution_type == 'random':
        teams = list(teams)
        random.shuffle(teams)
    
    with transaction.atomic():
        # Удаляем существующую сетку если есть
        if hasattr(tournament, 'bracket'):
            tournament.bracket.delete()
        
        # Создаем новую сетку
        bracket = TournamentBracket.objects.create(
            tournament=tournament,
            distribution_type=distribution_type,
            third_place_match=third_place_match
        )
        
        # Создаем этапы
        team_count = len(teams)
        current_round = team_count
        round_number = 1
        current_time = tournament.start_date
        
        while current_round >= 2:
            stage_name = get_stage_name(current_round)
            stage_format = 'BO3'  # По умолчанию
            
            if stage_formats and f'format_round_{round_number}' in stage_formats:
                stage_format = stage_formats[f'format_round_{round_number}']
            
            stage = BracketStage.objects.create(
                bracket=bracket,
                name=stage_name,
                format=stage_format,
                stage_type='final' if current_round == 2 else 'normal',
                order=round_number,
                scheduled_time=current_time
            )
            
            # Создаем матчи для этого этапа
            matches_in_round = current_round // 2
            create_matches_for_stage(stage, teams, matches_in_round, current_time)
            
            current_round = matches_in_round
            round_number += 1
            current_time += timedelta(hours=2)  # 2 часа между этапами
        
        # Создаем матч за третье место если нужно
        if third_place_match:
            create_third_place_match(bracket, current_time)
        
        return bracket


def create_double_elimination_bracket(tournament, teams, distribution_type='random',
                                    stage_formats=None):
    """Создает турнирную сетку Double Elimination"""
    
    if distribution_type == 'random':
        teams = list(teams)
        random.shuffle(teams)
    
    with transaction.atomic():
        # Удаляем существующую сетку если есть
        if hasattr(tournament, 'bracket'):
            tournament.bracket.delete()
        
        # Создаем новую сетку
        bracket = TournamentBracket.objects.create(
            tournament=tournament,
            distribution_type=distribution_type
        )
        
        team_count = len(teams)
        current_time = tournament.start_date
        
        # Создаем верхнюю сетку (Winner's Bracket)
        create_upper_bracket(bracket, teams, current_time, stage_formats)
        
        # Создаем нижнюю сетку (Loser's Bracket) - упрощенная версия
        create_lower_bracket(bracket, team_count, current_time, stage_formats)
        
        # Создаем гранд-финал
        create_grand_final(bracket, current_time + timedelta(hours=6))
        
        return bracket


def create_round_robin_bracket(tournament, teams, default_format='BO3'):
    """Создает турнирную таблицу Round Robin"""
    
    with transaction.atomic():
        # Удаляем существующую таблицу если есть
        if hasattr(tournament, 'round_robin_table'):
            tournament.round_robin_table.delete()
        
        # Создаем новую таблицу
        table = RoundRobinTable.objects.create(tournament=tournament)
        
        # Создаем результаты для всех команд
        for team in teams:
            RoundRobinResult.objects.create(table=table, team=team)
        
        # Создаем все возможные матчи
        teams_list = list(teams)
        current_time = tournament.start_date
        
        # Генерируем матчи по круговой системе
        for i in range(len(teams_list)):
            for j in range(i + 1, len(teams_list)):
                RoundRobinMatch.objects.create(
                    table=table,
                    team1=teams_list[i],
                    team2=teams_list[j],
                    format=default_format,
                    scheduled_time=current_time,
                    round_number=1
                )
                current_time += timedelta(hours=1)  # 1 час между матчами
        
        return table


def create_upper_bracket(bracket, teams, start_time, stage_formats=None):
    """Создает верхнюю сетку для Double Elimination"""
    team_count = len(teams)
    current_round = team_count
    round_number = 1
    current_time = start_time
    
    while current_round >= 2:
        stage_name = f"Верхняя сетка - {get_stage_name(current_round)}"
        stage_format = 'BO3'
        
        if stage_formats and f'format_round_{round_number}' in stage_formats:
            stage_format = stage_formats[f'format_round_{round_number}']
        
        stage = BracketStage.objects.create(
            bracket=bracket,
            name=stage_name,
            format=stage_format,
            stage_type='upper',
            order=round_number,
            scheduled_time=current_time
        )
        
        matches_in_round = current_round // 2
        create_matches_for_stage(stage, teams, matches_in_round, current_time)
        
        current_round = matches_in_round
        round_number += 1
        current_time += timedelta(hours=2)


def create_lower_bracket(bracket, team_count, start_time, stage_formats=None):
    """Создает нижнюю сетку для Double Elimination (упрощенная версия)"""
    lower_rounds = max(2, team_count // 4)  # Упрощенное количество раундов
    current_time = start_time + timedelta(hours=1)
    
    for round_num in range(1, lower_rounds + 1):
        stage_name = f"Нижняя сетка - Раунд {round_num}"
        
        stage = BracketStage.objects.create(
            bracket=bracket,
            name=stage_name,
            format='BO3',
            stage_type='lower',
            order=100 + round_num,
            scheduled_time=current_time
        )
        
        # Создаем матчи без команд - они будут назначены позже
        for i in range(max(1, team_count // (2 ** (round_num + 1)))):
            BracketMatch.objects.create(
                stage=stage,
                order=i + 1,
                scheduled_time=current_time + timedelta(minutes=i * 30)
            )
        
        current_time += timedelta(hours=2)


def create_grand_final(bracket, start_time):
    """Создает гранд-финал для Double Elimination"""
    stage = BracketStage.objects.create(
        bracket=bracket,
        name="Гранд-финал",
        format='BO5',
        stage_type='final',
        order=200,
        scheduled_time=start_time
    )
    
    BracketMatch.objects.create(
        stage=stage,
        order=1,
        scheduled_time=start_time
    )


def create_third_place_match(bracket, start_time):
    """Создает матч за третье место"""
    stage = BracketStage.objects.create(
        bracket=bracket,
        name="Матч за 3 место",
        format='BO3',
        stage_type='third_place',
        order=999,
        scheduled_time=start_time
    )
    
    BracketMatch.objects.create(
        stage=stage,
        order=1,
        scheduled_time=start_time
    )


def create_matches_for_stage(stage, teams, matches_count, start_time):
    """Создает матчи для этапа"""
    for i in range(matches_count):
        team1 = teams[i * 2] if i * 2 < len(teams) else None
        team2 = teams[i * 2 + 1] if i * 2 + 1 < len(teams) else None
        
        # Если команда только одна, она проходит автоматически
        is_bye = team2 is None
        
        match_time = start_time + timedelta(minutes=i * 30)
        
        match = BracketMatch.objects.create(
            stage=stage,
            team1=team1,
            team2=team2,
            order=i + 1,
            scheduled_time=match_time,
            is_bye=is_bye
        )
        
        # Если это проход, автоматически определяем победителя
        if is_bye and team1:
            match.winner = team1
            match.is_completed = True
            match.save()


def get_stage_name(team_count):
    """Получает название этапа по количеству команд"""
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


def promote_winner_to_next_stage(match):
    """Продвигает победителя в следующий этап"""
    if not match.winner:
        return
    
    # Для обычной сетки на выбывание
    if match.stage.stage_type in ['normal', 'upper']:
        next_stage = BracketStage.objects.filter(
            bracket=match.stage.bracket,
            stage_type=match.stage.stage_type,
            order=match.stage.order + 1
        ).first()
        
        if next_stage:
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


def get_upcoming_matches(tournament):
    """Получает предстоящие матчи турнира"""
    upcoming_matches = []
    
    if tournament.tournament_format == 'round_robin':
        if hasattr(tournament, 'round_robin_table'):
            matches = tournament.round_robin_table.matches.filter(
                is_completed=False,
                scheduled_time__isnull=False
            ).order_by('scheduled_time')[:10]
            upcoming_matches.extend(matches)
    else:
        if hasattr(tournament, 'bracket'):
            matches = BracketMatch.objects.filter(
                stage__bracket=tournament.bracket,
                is_completed=False,
                scheduled_time__isnull=False,
                team1__isnull=False,
                team2__isnull=False
            ).order_by('scheduled_time')[:10]
            upcoming_matches.extend(matches)
    
    return upcoming_matches
