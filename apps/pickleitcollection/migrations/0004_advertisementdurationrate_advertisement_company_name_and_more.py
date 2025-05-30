# Generated by Django 5.1 on 2025-02-17 13:28

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pickleitcollection', '0003_facilityimage'),
    ]

    operations = [
        migrations.CreateModel(
            name='AdvertisementDurationRate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('duration', models.PositiveIntegerField()),
                ('duration_type', models.CharField(choices=[('Days', 'Days'), ('Weeks', 'Weeks'), ('Months', 'Months'), ('Year', 'Year')], default='Days', max_length=10)),
                ('rate', models.DecimalField(decimal_places=2, max_digits=10)),
            ],
        ),
        migrations.AddField(
            model_name='advertisement',
            name='company_name',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='advertisement',
            name='company_website',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='advertisement',
            name='duration',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='pickleitcollection.advertisementdurationrate'),
        ),
    ]
