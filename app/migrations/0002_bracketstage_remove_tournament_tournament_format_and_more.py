# Generated by Django 5.2 on 2025-05-24 19:01

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='BracketStage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('format', models.CharField(choices=[('BO1', 'Best of 1'), ('BO3', 'Best of 3'), ('BO5', 'Best of 5')], default='BO3', max_length=3)),
                ('order', models.PositiveIntegerField()),
                ('is_completed', models.BooleanField(default=False)),
            ],
            options={
                'ordering': ['order'],
            },
        ),
        migrations.RemoveField(
            model_name='tournament',
            name='tournament_format',
        ),
        migrations.AlterField(
            model_name='tournament',
            name='max_teams',
            field=models.IntegerField(choices=[(2, '2'), (4, '4'), (8, '8'), (16, '16'), (32, '32'), (64, '64'), (128, '128'), (256, '256'), (512, '512')], verbose_name='Максимальное количество команд'),
        ),
        migrations.CreateModel(
            name='BracketMatch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order', models.PositiveIntegerField()),
                ('is_completed', models.BooleanField(default=False)),
                ('team1', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='team1_matches', to='app.team')),
                ('team2', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='team2_matches', to='app.team')),
                ('winner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='app.team')),
                ('stage', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='matches', to='app.bracketstage')),
            ],
            options={
                'ordering': ['order'],
            },
        ),
        migrations.CreateModel(
            name='TournamentBracket',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('tournament', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='bracket', to='app.tournament')),
            ],
        ),
        migrations.AddField(
            model_name='bracketstage',
            name='bracket',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stages', to='app.tournamentbracket'),
        ),
    ]
