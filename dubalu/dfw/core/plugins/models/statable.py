# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import warnings

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

from django_extensions.db.fields import CreationDateTimeField, ModificationDateTimeField


STATUS_HIDDEN = 'H'
STATUS_DRAFT = 'D'
STATUS_SCRAP = 'S'
STATUS_PSEUDO = 'P'
STATUS_PUBLISHED = 'U'
STATUS_UNPUBLISHED = 'R'
STATUS_CHOICES = (
    (STATUS_HIDDEN, _("Hidden")),
    (STATUS_DRAFT, _("Draft")),
    (STATUS_SCRAP, _("Scrap")),
    (STATUS_PSEUDO, _("Pseudo")),
    (STATUS_PUBLISHED, _("Published")),
    (STATUS_UNPUBLISHED, _("Unpublished")),
)


PUBLISHED_STATUSES = (STATUS_PUBLISHED, STATUS_PSEUDO,)
UNPUBLISHED_STATUSES = (STATUS_UNPUBLISHED,)
VISIBLE_STATUSES = (STATUS_PUBLISHED, STATUS_PSEUDO,)
DRAFT_STATUSES = (STATUS_DRAFT,)
HIDDEN_STATUSES = (STATUS_HIDDEN,)
AVAILABLE_STATUSES = (STATUS_PUBLISHED, STATUS_UNPUBLISHED, STATUS_HIDDEN, STATUS_SCRAP)


class StatableManager(models.Manager):
    def cleanup(self):
        getattr(super(StatableManager, self), 'cleanup', lambda: None)()  # Propagate cleanup()
        # FIXME: need to call indexing haystack methods for these!
        self.filter(status=STATUS_SCRAP, created_at__lt=timezone.now() - timezone.timedelta(days=2)).delete()
        self.filter(status=STATUS_PUBLISHED, active_to__gt=timezone.now()).update(status=STATUS_UNPUBLISHED)
        self.filter(status=STATUS_PUBLISHED, active_from__lt=timezone.now()).update(status=STATUS_UNPUBLISHED)
        self.filter(status=STATUS_UNPUBLISHED, active_from__gte=timezone.now(), active_to__lt=timezone.now()).update(status=STATUS_PUBLISHED)

    def published(self):
        now = timezone.now()
        return self.filter(
            models.Q(
                models.Q(active_from=None, active_to=None) |
                models.Q(active_from__gte=now, active_to__lt=now),
                status__in=PUBLISHED_STATUSES,
            ),
            deleted_at=None,
        )

    def unpublished(self):
        now = timezone.now()
        return self.filter(
            models.Q(status__in=UNPUBLISHED_STATUSES) |
            ~models.Q(
                models.Q(active_from=None, active_to=None) |
                models.Q(active_from__gte=now, active_to__lt=now),
                status__in=PUBLISHED_STATUSES,
            ),
            deleted_at=None,
        )

    def visible(self):
        return self.filter(deleted_at=None, status__in=VISIBLE_STATUSES)

    def active(self):
        warnings.warn("The active() method is now deprecated: use visible() instead", DeprecationWarning)
        return self.visible()

    def drafts(self):
        return self.filter(deleted_at=None, status__in=DRAFT_STATUSES)

    def hidden(self):
        return self.filter(deleted_at=None, status__in=HIDDEN_STATUSES)

    def available(self):
        """Objects available for the user."""
        return self.filter(deleted_at=None, status__in=AVAILABLE_STATUSES)

    #########################
    # CREATED_AT FILTERS
    #########################
    def created_years_ago(self, years=1):
        year = timezone.now().year - years
        return self.filter(created_at__year=year)

    def created_this_year(self):
        return self.created_years_ago()

    def created_this_month(self):
        date = timezone.now()
        return self.filter(created_at__year=date.year, created_at__month=date.month)

    def created_months_ago(self, months=1):
        date = timezone.now()
        month = date.month - 1  # enable modular arithmetic (months: 0-11)

        prev_month = (month - months) % 12
        prev_year = date.year
        if months and months >= date.month:
            prev_year = prev_year - 1 - (months - date.month) // 12

        prev_month += 1  # restore months (1-12)
        return self.filter(created_at__year=prev_year, created_at__month=prev_month)

    def created_last_month(self):
        return self.created_months_ago()

    def created_weeks_ago(self, weeks=1):
        date = timezone.now()
        offset = timezone.timedelta(7 * weeks)
        start_week = date - timezone.timedelta(date.weekday()) - offset
        end_week = start_week + timezone.timedelta(7)
        return self.filter(created_at__range=[start_week, end_week])

    def created_this_week(self):
        return self.created_weeks_ago(0)

    def created_last_week(self):
        return self.created_weeks_ago()

    def created_days_ago(self, days=1):
        date = timezone.now() - timezone.timedelta(days)
        return self.filter(created_at__year=date.year, created_at__month=date.month, created_at__day=date.day)

    def created_today(self):
        return self.created_days_ago(0)

    def created_yesterday(self):
        return self.created_days_ago()


class AbstractStatableModel(models.Model):
    denorm_always_skip = ('updated_at',)

    status = models.CharField(_("status"), max_length=1,
        choices=STATUS_CHOICES, default=STATUS_PUBLISHED, editable=False)

    created_at = CreationDateTimeField(_('date published'), db_index=True)
    updated_at = ModificationDateTimeField(_('updated at'))
    deleted_at = models.DateTimeField(null=True, editable=False)

    active_from = models.DateTimeField(_('expiration date'), null=True, editable=False, db_index=True)
    active_to = models.DateTimeField(_('expiration date'), null=True, editable=False, db_index=True)

    class Meta:
        index_together = (
            ('deleted_at', 'status'),
            ('active_from', 'active_to', 'deleted_at', 'status'),
        )
        abstract = True

    @property
    def is_expired(self):
        now = timezone.now()
        return self.deleted_at is None and \
            self.active_from is not None and now > self.active_from and \
            self.active_to is not None and now > self.active_to

    @property
    def is_published(self):
        return (
            self.deleted_at is None and (
                not self.is_expired and self.status in PUBLISHED_STATUSES
            )
        )

    @property
    def is_unpublished(self):
        return (
            self.deleted_at is None and (
                self.status in UNPUBLISHED_STATUSES or not (
                    not self.is_expired and self.status in PUBLISHED_STATUSES
                )
            )
        )

    @property
    def is_visible(self):
        return self.deleted_at is None and self.status in VISIBLE_STATUSES

    @property
    def is_draft(self):
        return self.deleted_at is None and self.status in DRAFT_STATUSES

    @property
    def is_hidden(self):
        return self.deleted_at is None and self.status in HIDDEN_STATUSES

    @property
    def is_available(self):
        return self.deleted_at is None and self.status in AVAILABLE_STATUSES

    @property
    def is_deleted(self):
        return bool(self.deleted_at)

    @property
    def is_scrap(self):
        return self.status == STATUS_SCRAP

    def set_published_status(self, save=False):
        self.status = STATUS_PUBLISHED
        if save:
            self.save()

    def set_draft_status(self, save=False):
        self.status = STATUS_DRAFT
        if save:
            self.save()

    def set_hidden_status(self, save=False):
        self.status = STATUS_HIDDEN
        if save:
            self.save()

    def set_unpublished_status(self, save=False):
        self.status = STATUS_UNPUBLISHED
        if save:
            self.save()

    def set_scrap_status(self, save=False):
        self.status = STATUS_SCRAP
        if save:
            self.save()

    def drop(self, save=True):
        """
        Drops an object by marking it as deleted. Dropped objects can be recovered
        using the ``recover()`` method.

        """
        if not self.deleted_at:
            self.deleted_at = timezone.now()
            if save:
                self.save()

    def recover(self, save=True):
        """
        Recovers a dropped object.

        """
        if self.deleted_at:
            self.deleted_at = None
            if save:
                self.save()


class AbstractDatedModel(models.Model):
    class Meta:
        abstract = True

    def get_date(self):
        """
        This method should return the date the object is to be dated at.
        """
        raise NotImplemented

    @property
    def dated_at(self):
        return self.get_date()

    @property
    def dated_at_year(self):
        dated_at = self.get_date()
        dated_at = dated_at.timetuple()
        return dated_at.tm_year

    @property
    def dated_at_month(self):
        dated_at = self.get_date()
        dated_at = dated_at.timetuple()
        return dated_at.tm_mon

    @property
    def dated_at_day(self):
        dated_at = self.get_date()
        dated_at = dated_at.timetuple()
        return dated_at.tm_mday

    @property
    def dated_at_weekday(self):
        dated_at = self.get_date()
        dated_at = dated_at.timetuple()
        return dated_at.tm_wday

    @property
    def dated_at_hour(self):
        dated_at = self.get_date()
        dated_at = dated_at.timetuple()
        return dated_at.tm_hour

    @property
    def dated_at_yearday(self):
        dated_at = self.get_date()
        dated_at = dated_at.timetuple()
        return dated_at.tm_yday
