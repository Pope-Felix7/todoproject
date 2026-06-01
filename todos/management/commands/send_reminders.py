"""
Management command: send deadline reminders for todos.

Run with:  python manage.py send_reminders
Schedule:  crontab every 5 minutes:  */5 * * * * python manage.py send_reminders

Reminder stages (bitmask bits):
  bit 0 — 50% of time elapsed
  bit 1 — 75% of time elapsed
  bit 2 — 90% of time elapsed
  bit 3 — 24 hours before deadline
  bit 4 — 2 hours before deadline
  bit 5 — 30 minutes before deadline
"""

import logging
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from todos.models import Todo

logger = logging.getLogger(__name__)

# (bit_index, label, description_for_email)
STAGES = [
    (3, '24h',   'due in 24 hours'),
    (4, '2h',    'due in 2 hours'),
    (5, '30min', 'due in 30 minutes'),
    (0, '50pct', '50% of your time has elapsed'),
    (1, '75pct', '75% of your time has elapsed'),
    (2, '90pct', '90% of your time has elapsed'),
]


def _bit(n):
    return 1 << n


class Command(BaseCommand):
    help = 'Send email reminders for upcoming todo deadlines'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print what would be sent without actually sending emails',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        now = timezone.now()
        sent_count = 0

        # Only consider active todos with a due_datetime and an email on the account
        todos = Todo.objects.filter(
            is_completed=False,
            due_datetime__isnull=False,
            user__email__isnull=False,
        ).select_related('user').exclude(user__email='')

        for todo in todos:
            deadline = todo.due_datetime
            secs_left = (deadline - now).total_seconds()

            # Already past deadline → skip (overdue notice is separate)
            if secs_left < 0:
                continue

            total_secs = (deadline - todo.created_at).total_seconds()
            if total_secs <= 0:
                continue
            elapsed_frac = 1.0 - (secs_left / total_secs)
            elapsed_frac = max(0.0, min(1.0, elapsed_frac))

            reminders_to_send = []

            # Time-based stages
            if secs_left <= 1800 and not (todo.reminders_sent & _bit(5)):   # 30 min
                reminders_to_send.append((5, 'due in 30 minutes'))
            elif secs_left <= 7200 and not (todo.reminders_sent & _bit(4)):  # 2 h
                reminders_to_send.append((4, 'due in 2 hours'))
            elif secs_left <= 86400 and not (todo.reminders_sent & _bit(3)): # 24 h
                reminders_to_send.append((3, 'due in 24 hours'))

            # Percentage-based stages
            if elapsed_frac >= 0.90 and not (todo.reminders_sent & _bit(2)):
                reminders_to_send.append((2, '90% of your time has elapsed'))
            elif elapsed_frac >= 0.75 and not (todo.reminders_sent & _bit(1)):
                reminders_to_send.append((1, '75% of your time has elapsed'))
            elif elapsed_frac >= 0.50 and not (todo.reminders_sent & _bit(0)):
                reminders_to_send.append((0, '50% of your time has elapsed'))

            for bit, label in reminders_to_send:
                email = todo.user.email
                subject = f'⏰ Reminder: "{todo.title}" — {label}'
                body = (
                    f"Hi {todo.user.first_name or todo.user.username},\n\n"
                    f"This is a reminder for your task:\n\n"
                    f"  📌 {todo.title}\n"
                    f"  ⏰ Deadline: {deadline.strftime('%A, %B %d %Y at %H:%M')}\n"
                    f"  ℹ️  Status: {label}\n\n"
                    f"Log in to mark it complete or update it.\n\n"
                    f"— TodoApp\n"
                )

                if dry_run:
                    self.stdout.write(
                        self.style.WARNING(f"[DRY-RUN] Would email {email}: {subject}")
                    )
                else:
                    try:
                        send_mail(
                            subject=subject,
                            message=body,
                            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@todoapp.local'),
                            recipient_list=[email],
                            fail_silently=False,
                        )
                        self.stdout.write(self.style.SUCCESS(f"Sent '{subject}' → {email}"))
                        sent_count += 1
                    except Exception as e:
                        logger.error(f"Failed to send reminder for todo {todo.id}: {e}")
                        self.stdout.write(self.style.ERROR(f"Failed: {e}"))

                # Mark bit regardless of dry-run so we don't double-send on next run
                if not dry_run:
                    todo.reminders_sent = todo.reminders_sent | _bit(bit)
                    todo.save(update_fields=['reminders_sent'])

        if not dry_run:
            self.stdout.write(self.style.SUCCESS(f"\nDone. {sent_count} reminder(s) sent."))
        else:
            self.stdout.write(self.style.WARNING("\n[DRY-RUN] No emails sent."))
