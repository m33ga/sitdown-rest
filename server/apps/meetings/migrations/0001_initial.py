import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """Create Meeting and MemberEntry tables."""

    initial = True
    dependencies = [
        ('groups', '0001_initial'),
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Meeting',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=255)),
                ('date', models.DateField()),
                ('completed', models.BooleanField(default=False)),
                ('group', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='meetings',
                    to='groups.group',
                )),
            ],
        ),
        migrations.CreateModel(
            name='MemberEntry',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('promised', models.TextField(blank=True, default='')),
                ('done', models.TextField(blank=True, default='')),
                ('will_do', models.TextField(blank=True, default='')),
                ('discussion', models.TextField(blank=True, default='')),
                ('notes', models.TextField(blank=True, default='')),
                ('meeting', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='entries',
                    to='meetings.meeting',
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='standup_entries',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='meeting',
            unique_together={('group', 'date')},
        ),
        migrations.AlterUniqueTogether(
            name='memberentry',
            unique_together={('meeting', 'user')},
        ),
    ]
