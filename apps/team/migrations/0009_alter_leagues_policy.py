# Generated by Django 5.1 on 2025-04-02 10:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('team', '0008_alter_leagues_description'),
    ]

    operations = [
        migrations.AlterField(
            model_name='leagues',
            name='policy',
            field=models.BooleanField(default=False),
        ),
    ]
