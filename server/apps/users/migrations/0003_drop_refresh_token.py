from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_add_refresh_token'),
    ]

    operations = [
        migrations.DeleteModel(
            name='RefreshToken',
        ),
    ]
