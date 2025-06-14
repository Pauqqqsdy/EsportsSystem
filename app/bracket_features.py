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
    """Создает турнирную сетку Single Elimination с динамическими стадиями и поддержкой bye"""
    if distribution_type == 'random':
        teams = list(teams)
        random.shuffle(teams)
    
    with transaction.atomic():
        if hasattr(tournament, 'bracket'):
            tournament.bracket.delete()
        bracket = TournamentBracket.objects.create(
            tournament=tournament,
            distribution_type=distribution_type,
            third_place_match=third_place_match
        )
        team_count = len(teams)
        current_time = tournament.start_date
        rounds = []
        n = team_count
        while n > 1:
            rounds.append(n)
            n = math.ceil(n / 2)
        total_rounds = len(rounds)
        for round_number, teams_in_round in enumerate(rounds, 1):
            matches_in_round = math.ceil(teams_in_round / 2)
            if matches_in_round == 0:
                continue
            if round_number == total_rounds:
                stage_name = "Финал"
                stage_type = 'final'
            elif round_number == total_rounds - 1:
                stage_name = "Полуфинал"
                stage_type = 'normal'
            elif round_number == total_rounds - 2:
                stage_name = "Четвертьфинал"
                stage_type = 'normal'
            else:
                stage_name = f"Раунд {round_number}"
                stage_type = 'normal'
            stage_format = 'BO3'
            if stage_formats and f'format_round_{round_number}' in stage_formats:
                stage_format = stage_formats[f'format_round_{round_number}']
            stage = BracketStage.objects.create(
                bracket=bracket,
                name=stage_name,
                format=stage_format,
                stage_type=stage_type,
                order=round_number,
                scheduled_time=current_time
            )
            if round_number == 1:
                create_matches_for_stage(stage, teams, matches_in_round, current_time)
            else:
                create_empty_matches_for_stage(stage, matches_in_round, current_time)
            current_time += timedelta(hours=2)
        if third_place_match and total_rounds > 1:
            create_third_place_match(bracket, current_time)
        return bracket


def create_double_elimination_bracket(tournament, teams, distribution_type='random',
                                    stage_formats=None):
    """Создает турнирную сетку Double Elimination с динамическими стадиями и поддержкой bye"""
    if distribution_type == 'random':
        teams = list(teams)
        random.shuffle(teams)
    with transaction.atomic():
        if hasattr(tournament, 'bracket'):
            tournament.bracket.delete()
        bracket = TournamentBracket.objects.create(
            tournament=tournament,
            distribution_type=distribution_type
        )
        team_count = len(teams)
        current_time = tournament.start_date
        upper_rounds = []
        n = team_count
        while n > 1:
            upper_rounds.append(n)
            n = math.ceil(n / 2)
        total_upper = len(upper_rounds)
        upper_stage_objs = []
        for round_number, teams_in_round in enumerate(upper_rounds, 1):
            matches_in_round = math.ceil(teams_in_round / 2)
            if matches_in_round == 0:
                continue
            if round_number == total_upper:
                stage_name = "Верхний финал"
            elif round_number == total_upper - 1:
                stage_name = "Верхний полуфинал"
            else:
                stage_name = f"Верхний раунд {round_number}"
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
            if round_number == 1:
                create_matches_for_stage(stage, teams, matches_in_round, current_time)
            else:
                create_empty_matches_for_stage(stage, matches_in_round, current_time)
            upper_stage_objs.append(stage)
            current_time += timedelta(hours=2)
        lower_rounds = max(1, len(upper_rounds) - 1)
        for i in range(lower_rounds):
            stage_name = f"Нижний раунд {i+1}" if lower_rounds > 1 else "Нижний полуфинал"
            stage = BracketStage.objects.create(
                bracket=bracket,
                name=stage_name,
                format='BO3',
                stage_type='lower',
                order=100 + i + 1,
                scheduled_time=current_time
            )
            create_empty_matches_for_stage(stage, 1, current_time)
            current_time += timedelta(hours=2)
        grand_final = BracketStage.objects.create(
            bracket=bracket,
            name="Гранд-финал",
            format='BO5',
            stage_type='final',
            order=200,
            scheduled_time=current_time
        )
        BracketMatch.objects.create(
            stage=grand_final,
            order=1,
            scheduled_time=current_time
        )
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
    
    bracket = match.stage.bracket
    loser = match.team1 if match.winner == match.team2 else match.team2
    
    # Для Single Elimination
    if bracket.tournament.tournament_format == 'single_elimination':
        # Находим следующий этап в обычной последовательности
        next_stage = BracketStage.objects.filter(
            bracket=bracket,
            stage_type__in=['normal', 'final'],
            order=match.stage.order + 1
        ).first()
        
        if next_stage:
            # Вычисляем позицию матча в следующем этапе
            match_position = math.ceil(match.order / 2)
            next_match = BracketMatch.objects.filter(
                stage=next_stage,
                order=match_position
            ).first()
            
            if next_match:
                # Определяем, в какую позицию (team1 или team2) поставить победителя
                if match.order % 2 == 1:  # Нечетный порядок -> team1
                    next_match.team1 = match.winner
                else:  # Четный порядок -> team2
                    next_match.team2 = match.winner
                next_match.save()
    
    # Для Double Elimination
    elif bracket.tournament.tournament_format == 'double_elimination':
        if match.stage.stage_type == 'upper':
            # Победитель идет в следующий этап верхней сетки или в гранд-финал
            next_upper_stage = BracketStage.objects.filter(
                bracket=bracket,
                stage_type='upper',
                order=match.stage.order + 1
            ).first()
            
            if next_upper_stage:
                match_position = math.ceil(match.order / 2)
                next_match = BracketMatch.objects.filter(
                    stage=next_upper_stage,
                    order=match_position
                ).first()
                
                if next_match:
                    if match.order % 2 == 1:
                        next_match.team1 = match.winner
                    else:
                        next_match.team2 = match.winner
                    next_match.save()
            else:
                # Если нет следующего этапа верхней сетки, идем в гранд-финал
                grand_final_stage = BracketStage.objects.filter(
                    bracket=bracket,
                    stage_type='final'
                ).first()
                
                if grand_final_stage:
                    grand_final_match = BracketMatch.objects.filter(
                        stage=grand_final_stage
                    ).first()
                    
                    if grand_final_match and not grand_final_match.team1:
                        grand_final_match.team1 = match.winner
                        grand_final_match.save()
            
            # Проигравший идет в нижнюю сетку
            if loser:
                lower_stage = BracketStage.objects.filter(
                    bracket=bracket,
                    stage_type='lower'
                ).first()
                
                if lower_stage:
                    lower_match = BracketMatch.objects.filter(
                        stage=lower_stage,
                        team1__isnull=True
                    ).first()
                    
                    if lower_match:
                        lower_match.team1 = loser
                        lower_match.save()
        
        elif match.stage.stage_type == 'lower':
            # Победитель нижней сетки идет в гранд-финал
            grand_final_stage = BracketStage.objects.filter(
                bracket=bracket,
                stage_type='final'
            ).first()
            
            if grand_final_stage:
                grand_final_match = BracketMatch.objects.filter(
                    stage=grand_final_stage
                ).first()
                
                if grand_final_match and not grand_final_match.team2:
                    grand_final_match.team2 = match.winner
                    grand_final_match.save()


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


def get_stage_name_by_round(round_number, total_rounds, matches_count):
    """Получает название этапа по номеру раунда и общему количеству раундов"""
    if round_number == total_rounds:
        return "Финал"
    elif round_number == total_rounds - 1:
        return "Полуфиналы" if matches_count > 1 else "Полуфинал"
    elif round_number == total_rounds - 2:
        return "Четвертьфиналы" if matches_count > 1 else "Четвертьфинал"
    else:
        return f"Раунд {round_number}"


def create_empty_matches_for_stage(stage, matches_count, start_time):
    """Создает пустые матчи для этапа (команды будут назначены позже)"""
    for i in range(matches_count):
        match_time = start_time + timedelta(minutes=i * 30)
        
        BracketMatch.objects.create(
            stage=stage,
            order=i + 1,
            scheduled_time=match_time
        )


def create_simple_double_elimination(bracket, teams, start_time, stage_formats=None):
    """Создает упрощенную Double Elimination сетку для 2-3 команд"""
    team_count = len(teams)
    current_time = start_time
    
    if team_count == 2:
        # Для 2 команд: 1 матч верхней сетки, возможный реванш в гранд-финале
        
        # Верхняя сетка - финал
        upper_final = BracketStage.objects.create(
            bracket=bracket,
            name="Верхний финал",
            format='BO3',
            stage_type='upper',
            order=1,
            scheduled_time=current_time
        )
        
        BracketMatch.objects.create(
            stage=upper_final,
            team1=teams[0],
            team2=teams[1],
            order=1,
            scheduled_time=current_time
        )
        
        current_time += timedelta(hours=2)
        
        # Гранд-финал
        grand_final = BracketStage.objects.create(
            bracket=bracket,
            name="Гранд-финал",
            format='BO5',
            stage_type='final',
            order=100,
            scheduled_time=current_time
        )
        
        BracketMatch.objects.create(
            stage=grand_final,
            order=1,
            scheduled_time=current_time
        )
        
    elif team_count == 3:
        # Для 3 команд: полуфинал верхней сетки, матч нижней сетки, гранд-финал
        
        # Верхняя сетка - полуфинал
        upper_semi = BracketStage.objects.create(
            bracket=bracket,
            name="Верхний полуфинал",
            format='BO3',
            stage_type='upper',
            order=1,
            scheduled_time=current_time
        )
        
        BracketMatch.objects.create(
            stage=upper_semi,
            team1=teams[0],
            team2=teams[1],
            order=1,
            scheduled_time=current_time
        )
        
        current_time += timedelta(hours=1)
        
        # Нижняя сетка - матч на выживание
        lower_match = BracketStage.objects.create(
            bracket=bracket,
            name="Матч на выживание",
            format='BO3',
            stage_type='lower',
            order=50,
            scheduled_time=current_time
        )
        
        # Матч между проигравшим верхнего полуфинала и третьей командой
        BracketMatch.objects.create(
            stage=lower_match,
            team2=teams[2],  # Третья команда сразу попадает в нижнюю сетку
            order=1,
            scheduled_time=current_time
        )
        
        current_time += timedelta(hours=2)
        
        # Гранд-финал
        grand_final = BracketStage.objects.create(
            bracket=bracket,
            name="Гранд-финал",
            format='BO5',
            stage_type='final',
            order=100,
            scheduled_time=current_time
        )
        
        BracketMatch.objects.create(
            stage=grand_final,
            order=1,
            scheduled_time=current_time
        )
