# Generated by Django 5.2 on 2025-06-11 06:04

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0004_alter_tournament_tournament_format'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='bracketmatch',
            options={'ordering': ['order'], 'verbose_name': 'Матч', 'verbose_name_plural': 'Матчи'},
        ),
        migrations.AlterModelOptions(
            name='bracketstage',
            options={'ordering': ['order'], 'verbose_name': 'Этап турнира', 'verbose_name_plural': 'Этапы турнира'},
        ),
        migrations.AlterModelOptions(
            name='tournamentbracket',
            options={'verbose_name': 'Турнирная сетка', 'verbose_name_plural': 'Турнирные сетки'},
        ),
        migrations.AddField(
            model_name='bracketmatch',
            name='is_bye',
            field=models.BooleanField(default=False, verbose_name='Проход без игры'),
        ),
        migrations.AddField(
            model_name='bracketmatch',
            name='scheduled_time',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Запланированное время'),
        ),
        migrations.AddField(
            model_name='bracketmatch',
            name='team1_score',
            field=models.PositiveIntegerField(default=0, verbose_name='Счет первой команды'),
        ),
        migrations.AddField(
            model_name='bracketmatch',
            name='team2_score',
            field=models.PositiveIntegerField(default=0, verbose_name='Счет второй команды'),
        ),
        migrations.AddField(
            model_name='bracketstage',
            name='scheduled_time',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Запланированное время'),
        ),
        migrations.AddField(
            model_name='bracketstage',
            name='stage_type',
            field=models.CharField(choices=[('upper', 'Верхняя сетка'), ('lower', 'Нижняя сетка'), ('final', 'Финал'), ('third_place', 'Матч за 3 место'), ('normal', 'Обычный этап')], default='normal', max_length=20),
        ),
        migrations.AddField(
            model_name='tournamentbracket',
            name='distribution_type',
            field=models.CharField(choices=[('random', 'Случайное распределение'), ('manual', 'Ручное распределение')], default='random', max_length=20),
        ),
        migrations.AddField(
            model_name='tournamentbracket',
            name='third_place_match',
            field=models.BooleanField(default=False, verbose_name='Матч за третье место'),
        ),
        migrations.AlterField(
            model_name='bracketmatch',
            name='winner',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='won_matches', to='app.team'),
        ),
        migrations.CreateModel(
            name='RoundRobinTable',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('tournament', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='round_robin_table', to='app.tournament')),
            ],
            options={
                'verbose_name': 'Таблица Round Robin',
                'verbose_name_plural': 'Таблицы Round Robin',
            },
        ),
        migrations.CreateModel(
            name='RoundRobinResult',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('matches_played', models.PositiveIntegerField(default=0)),
                ('wins', models.PositiveIntegerField(default=0)),
                ('losses', models.PositiveIntegerField(default=0)),
                ('points', models.PositiveIntegerField(default=0)),
                ('team', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='app.team')),
                ('table', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='results', to='app.roundrobintable')),
            ],
            options={
                'verbose_name': 'Результат команды в Round Robin',
                'verbose_name_plural': 'Результаты команд в Round Robin',
                'ordering': ['-points', '-wins', 'losses'],
                'unique_together': {('table', 'team')},
            },
        ),
        migrations.CreateModel(
            name='RoundRobinMatch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('team1_score', models.PositiveIntegerField(default=0)),
                ('team2_score', models.PositiveIntegerField(default=0)),
                ('format', models.CharField(choices=[('BO1', 'Best of 1'), ('BO3', 'Best of 3'), ('BO5', 'Best of 5')], default='BO3', max_length=3)),
                ('scheduled_time', models.DateTimeField(blank=True, null=True)),
                ('is_completed', models.BooleanField(default=False)),
                ('round_number', models.PositiveIntegerField(default=1)),
                ('team1', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rr_team1_matches', to='app.team')),
                ('team2', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rr_team2_matches', to='app.team')),
                ('winner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='rr_won_matches', to='app.team')),
                ('table', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='matches', to='app.roundrobintable')),
            ],
            options={
                'verbose_name': 'Матч Round Robin',
                'verbose_name_plural': 'Матчи Round Robin',
                'ordering': ['round_number', 'scheduled_time'],
                'unique_together': {('table', 'team1', 'team2')},
            },
        ),
    ]
