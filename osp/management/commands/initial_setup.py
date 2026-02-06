from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission


class Command(BaseCommand):
    help = 'Create initial groups for osp app'

    def handle(self, *args, **options):
        president_group, created = Group.objects.get_or_create(name='president')
        official_group, created2 = Group.objects.get_or_create(name='official')
        self.stdout.write(self.style.SUCCESS('Ensured groups: president, official'))
