from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail

User = get_user_model()

OFFICIAL_GROUPS = ['Urzędnik gminy', 'official']


def _send(subject, message, recipients):
    emails = [email for email in recipients if email]
    if not emails:
        return 0
    return send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        emails,
        fail_silently=True,
    )


def notify_officials(subject, message):
    emails = (
        User.objects.filter(groups__name__in=OFFICIAL_GROUPS)
        .exclude(email='')
        .values_list('email', flat=True)
        .distinct()
    )
    return _send(subject, message, list(emails))


def notify_user(user, subject, message):
    if not user or not user.email:
        return 0
    return _send(subject, message, [user.email])
