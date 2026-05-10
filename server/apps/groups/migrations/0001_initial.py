import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """Create Group, UserPinnedGroup, and ProjectMember tables."""

    initial = True
    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Group',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='UserPinnedGroup',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='pinned_groups',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('group', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='pinned_by',
                    to='groups.group',
                )),
            ],
        ),
        migrations.CreateModel(
            name='ProjectMember',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='project_memberships',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('group', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='members',
                    to='groups.group',
                )),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='userpinnedgroup',
            unique_together={('user', 'group')},
        ),
        migrations.AlterUniqueTogether(
            name='projectmember',
            unique_together={('user', 'group')},
        ),
    ]
