from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from osp.models import Unit, Firefighter, Request, RequestResponse


class Command(BaseCommand):
    help = 'Create initial groups for osp app (PL roles)'

    def handle(self, *args, **options):
        # Create groups with Polish display names
        president_group, _ = Group.objects.get_or_create(name='Prezes OSP')
        official_group, _ = Group.objects.get_or_create(name='Urzędnik gminy')

        # Also keep backward-compatible technical groups if they already exist
        legacy_pres, _ = Group.objects.get_or_create(name='president')
        legacy_off, _ = Group.objects.get_or_create(name='official')

        # Basic permissions for OSP domain models
        models = [Unit, Firefighter, Request, RequestResponse]
        perms = []
        for m in models:
            ct = ContentType.objects.get_for_model(m)
            perms.extend(Permission.objects.filter(content_type=ct))

        # Assign permissions: both groups can view domain objects; officials can change requests/responses
        # (We simply attach all model perms to both to keep admin usable; can be tightened later.)
        for g in (president_group, official_group, legacy_pres, legacy_off):
            g.permissions.set(perms)

        # Create default users for Prezes OSP and Urzędnik gminy
        from django.contrib.auth import get_user_model
        User = get_user_model()

        # Prezes OSP
        prez_username = 'prezes_osp'
        prez_email = 'prezes@osp.pl'
        prez_password = 'prezesosp123'
        prez_user, created = User.objects.get_or_create(username=prez_username, defaults={
            'email': prez_email
        })
        if created:
            prez_user.set_password(prez_password)
            prez_user.save()
        prez_user.groups.add(president_group)

        # Urzędnik gminy
        urz_username = 'urzednik_gminy'
        urz_email = 'urzednik@gmina.pl'
        urz_password = 'urzednik123'
        urz_user, created = User.objects.get_or_create(username=urz_username, defaults={
            'email': urz_email
        })
        if created:
            urz_user.set_password(urz_password)
            urz_user.save()
        urz_user.groups.add(official_group)

        self.stdout.write(self.style.SUCCESS('Utworzono domyślne konta:'))
        self.stdout.write(self.style.SUCCESS(f'Prezes OSP: {prez_username} / {prez_password}'))
        self.stdout.write(self.style.SUCCESS(f'Urzędnik gminy: {urz_username} / {urz_password}'))

        self.stdout.write(self.style.SUCCESS('Ensured groups: Prezes OSP, Urzędnik gminy (and legacy: president, official)'))
