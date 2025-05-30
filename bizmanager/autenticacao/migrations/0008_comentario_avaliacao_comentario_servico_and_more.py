# Generated by Django 5.1.7 on 2025-04-14 17:14

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('autenticacao', '0007_comentario'),
    ]

    operations = [
        migrations.AddField(
            model_name='comentario',
            name='avaliacao',
            field=models.IntegerField(blank=True, choices=[(1, '1 Estrela'), (2, '2 Estrelas'), (3, '3 Estrelas'), (4, '4 Estrelas'), (5, '5 Estrelas')], null=True),
        ),
        migrations.AddField(
            model_name='comentario',
            name='servico',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='comentarios', to='autenticacao.servico'),
        ),
        migrations.AddField(
            model_name='comentario',
            name='tipo',
            field=models.CharField(choices=[('testemunho', 'Testemunho Geral'), ('servico', 'Comentário de Serviço')], default='testemunho', max_length=20),
        ),
    ]
