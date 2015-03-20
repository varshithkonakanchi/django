import datetime
import socket

from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Sends a test email to the email addresses specified as arguments."
    args = "<email1 email2 ...>"

    def handle(self, *args, **kwargs):
        if not args:
            raise CommandError('You must provide at least one destination email.')
        send_mail(
            subject='Test email from %s on %s' % (socket.gethostname(), datetime.datetime.now()),
            message="If you\'re reading this, it was successful.",
            from_email=None,
            recipient_list=args,
        )
