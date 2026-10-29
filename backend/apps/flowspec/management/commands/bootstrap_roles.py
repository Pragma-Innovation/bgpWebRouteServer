"""
Management command to bootstrap standard RBAC groups and initial demo users.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group


class Command(BaseCommand):
    help = "Bootstrap RBAC roles (Viewer, Operator, Admin) and optional demo accounts."

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
            help='Default password for created demo users (default: bgppassword123)'
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

        if options['create_demo_users']:
            password = options['password']
            demo_accounts = [
                ('admin', 'admin@bgpweb.local', 'Admin', True, True),
                ('operator', 'operator@bgpweb.local', 'Operator', False, False),
                ('viewer', 'viewer@bgpweb.local', 'Viewer', False, False),
            ]

            self.stdout.write(self.style.NOTICE("\nSetting up demo user accounts..."))
            for username, email, role, is_staff, is_superuser in demo_accounts:
                user, created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        'email': email,
                        'is_staff': is_staff,
                        'is_superuser': is_superuser,
                    }
                )
                user.set_password(password)
                user.is_staff = is_staff
                user.is_superuser = is_superuser
                user.save()

                # Assign group
                user.groups.clear()
                user.groups.add(groups[role])

                status_label = "Created" if created else "Updated"
                self.stdout.write(
                    self.style.SUCCESS(f"  ✓ {status_label} user '{username}' with role '{role}' (password: {password})")
                )

        self.stdout.write(self.style.SUCCESS("\nRBAC bootstrap completed successfully."))
