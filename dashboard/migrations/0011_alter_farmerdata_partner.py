# Generated by Django 5.1.4 on 2025-03-02 14:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0010_farmerdata_index'),
    ]

    operations = [
        migrations.AlterField(
            model_name='farmerdata',
            name='partner',
            field=models.CharField(max_length=100, null=True),
        ),
    ]
