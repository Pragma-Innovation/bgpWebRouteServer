"""
Management command to bootstrap standard RBAC groups, initial production superuser, and optional demo users.
"""
import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group


class Command(BaseCommand):
    help = "Bootstrap RBAC roles (Viewer, Operator, Admin), optional initial superuser from env, and optional demo accounts."

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-demo-users',
            action='store_true',
            default=False,
            help='Create demo user accounts (viewer, operator, admin) for development and testing.'
        )
        parser.add_argument(
            '--password',
            type=str,
            default='bgppassword123',
            help='Default password for newly created demo users (default: bgppassword123)'
        )
        parser.add_argument(
            '--reset-passwords',
            action='store_true',
            default=False,
            help='Force-reset passwords on existing demo users.'
        )
        parser.add_argument(
            '--ensure-superuser',
            action='store_true',
            default=False,
            help='Create initial Admin superuser from DJANGO_SUPERUSER_USERNAME / DJANGO_SUPERUSER_PASSWORD if not yet present.'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Configuring RBAC groups..."))

        roles = ['Viewer', 'Operator', 'Admin']
        groups = {}
        for role in roles:
            group, created = Group.objects.get_or_create(name=role)
            groups[role] = group
            status_text = "created" if created else "already exists"
            self.stdout.write(f"  • Group '{role}' {status_text}.")

        if options['ensure_superuser']:
            su_username = os.environ.get('DJANGO_SUPERUSER_USERNAME', '').strip()
            su_password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', '')
            su_email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@gabu.local').strip()

            if su_username and su_password:
                existing = User.objects.filter(username=su_username).first()
                if not existing:
                    su = User.objects.create_superuser(
                        username=su_username,
                        email=su_email,
                        password=su_password,
                    )
                    su.groups.add(groups['Admin'])
                    self.stdout.write(
                        self.style.SUCCESS(f"  ✓ Created initial superuser '{su_username}' with role 'Admin'.")
                    )
                else:
                    if not existing.groups.filter(name='Admin').exists():
                        existing.groups.add(groups['Admin'])
                    self.stdout.write(f"  • Superuser '{su_username}' already exists.")

        if options['create_demo_users']:
            password = options['password']
            reset_passwords = options['reset_passwords']
            demo_accounts = [
                ('admin', 'admin@gabu.local', 'Admin', True, True),
                ('operator', 'operator@gabu.local', 'Operator', False, False),
                ('viewer', 'viewer@gabu.local', 'Viewer', False, False),
            ]

            self.stdout.write(self.style.NOTICE("\nEnsuring demo user accounts..."))
            for username, email, role, is_staff, is_superuser in demo_accounts:
                user, created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        'email': email,
                        'is_staff': is_staff,
                        'is_superuser': is_superuser,
                    }
                )
                if created or reset_passwords:
                    user.set_password(password)
                    user.is_staff = is_staff
                    user.is_superuser = is_superuser
                    user.save()
                    user.groups.clear()
                    user.groups.add(groups[role])
                    status_label = "Created" if created else "Reset"
                    self.stdout.write(
                        self.style.SUCCESS(f"  ✓ {status_label} demo user '{username}' with role '{role}'")
                    )
                else:
                    if not user.groups.exists():
                        user.groups.add(groups[role])
                    self.stdout.write(f"  • Demo user '{username}' already exists (kept existing credentials).")

        self.stdout.write(self.style.SUCCESS("\nRBAC bootstrap completed successfully."))
