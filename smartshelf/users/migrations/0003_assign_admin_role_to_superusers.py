from django.db import migrations


def assign_admin_role_to_superusers(apps, schema_editor):
    User = apps.get_model("users", "User")
    User.objects.filter(is_superuser=True).update(role="ADMIN")


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0002_user_department_user_member_id_user_phone_number_and_more"),
    ]

    operations = [
        migrations.RunPython(
            assign_admin_role_to_superusers,
            migrations.RunPython.noop,
        ),
    ]
