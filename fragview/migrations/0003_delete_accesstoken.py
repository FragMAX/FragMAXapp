# Generated by Django 3.2.10 on 2022-12-16 14:59

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("fragview", "0002_priv_fraglibs"),
    ]

    operations = [
        migrations.DeleteModel(
            name="AccessToken",
        ),
    ]