from django.db import migrations, models


def migrate_target_position_to_target_positions(apps, schema_editor):
    User = apps.get_model('users', 'User')

    for user in User.objects.exclude(target_position__isnull=True).iterator():
        user.target_positions.add(user.target_position_id)


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='target_positions',
            field=models.ManyToManyField(blank=True, related_name='target_users', to='positions.jobposition', verbose_name='目标岗位'),
        ),
        migrations.RunPython(migrate_target_position_to_target_positions, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='user',
            name='target_position',
        ),
    ]
