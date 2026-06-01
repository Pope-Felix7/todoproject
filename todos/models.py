from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Category(models.Model):
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=7, default='#0d6efd')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='categories')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'categories'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.user.username})"


class Todo(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='todos')
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='todos'
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    is_completed = models.BooleanField(default=False)
    due_date = models.DateField(null=True, blank=True)
    # NEW: full datetime for precise countdown + reminders
    due_datetime = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Reminder tracking — bitmask stored as int:
    # bit 0 = 50%, bit 1 = 75%, bit 2 = 90%, bit 3 = 24h, bit 4 = 2h, bit 5 = 30min
    reminders_sent = models.IntegerField(default=0)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.user.username}"

    def is_overdue(self):
        if self.due_datetime and not self.is_completed:
            return self.due_datetime < timezone.now()
        if self.due_date and not self.is_completed:
            return self.due_date < timezone.now().date()
        return False

    def deadline_ts(self):
        """Return Unix timestamp of the deadline (ms) for JS."""
        if self.due_datetime:
            dt = self.due_datetime
            if timezone.is_naive(dt):
                dt = timezone.make_aware(dt, timezone.utc)
            return int(dt.timestamp() * 1000)
        if self.due_date:
            import datetime
            dt = datetime.datetime.combine(self.due_date, datetime.time(23, 59, 59))
            dt = timezone.make_aware(dt)
            return int(dt.timestamp() * 1000)
        return None

    def seconds_until_deadline(self):
        """Seconds remaining until deadline (negative = overdue)."""
        if self.due_datetime:
            dt = self.due_datetime
            if timezone.is_naive(dt):
                dt = timezone.make_aware(dt, timezone.utc)
            return (dt - timezone.now()).total_seconds()
        if self.due_date:
            import datetime
            dt = datetime.datetime.combine(self.due_date, datetime.time(23, 59, 59))
            dt = timezone.make_aware(dt)
            return (dt - timezone.now()).total_seconds()
        return None

    def time_elapsed_fraction(self):
        """Fraction of time elapsed between created_at and deadline (0.0–1.0)."""
        secs = self.seconds_until_deadline()
        if secs is None:
            return None
        total = (self.due_datetime or timezone.now()) - self.created_at
        total_secs = total.total_seconds()
        if total_secs <= 0:
            return 1.0
        elapsed = total_secs - secs
        return max(0.0, min(1.0, elapsed / total_secs))


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True, null=True)
    avatar_color = models.CharField(max_length=7, default='#0d6efd')

    def __str__(self):
        return f"Profile of {self.user.username}"
