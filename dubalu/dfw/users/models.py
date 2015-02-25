# -*- coding: utf-8 -*-
"""
Dubalu Framework
~~~~~~~~~~~~~~~~

:author: Dubalu Framework Team. See AUTHORS.
:copyright: Copyright (c) 2013-2014, deipi.com LLC. All Rights Reserved.
:license: See LICENSE for license details.

"""
from __future__ import absolute_import, unicode_literals

import re
import random
import warnings

from django.db import models
from django.conf import settings
from django.core import validators
from django.core.mail import send_mail
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from django.utils.functional import memoize
from django.utils import timezone
from django.contrib import auth
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, AnonymousUser
from django.template.defaultfilters import slugify

from autoconnect.decorators import autoconnect


def _get_anonymous_user():
    """
    Returns ``User`` instance (not ``AnonymousUser``) depending on
    ``ANONYMOUS_USER_ID`` configuration.
    """
    UserModel = auth.get_user_model()
    try:
        return UserModel.objects.get(id=settings.ANONYMOUS_USER_ID)
    except UserModel.DoesNotExist:
        if settings.ANONYMOUS_USER_ID:
            raise
        return AnonymousUser()
_get_anonymous_user._anonymous_user = {}
get_anonymous_user = memoize(_get_anonymous_user, _get_anonymous_user._anonymous_user, 0)


# Monkey patch django.auth's get_user():
def get_user(request):
    user = auth__get_user(request)
    if user.is_anonymous():
        return get_anonymous_user()
    return user
auth__get_user = auth.get_user
auth.get_user = get_user


class UserManager(BaseUserManager):

    @classmethod
    def normalize_email(cls, email):
        """
        Normalize a GMail Address.

        Example:
            My.Name.1+ABC123@gmail.com => myname1@gmail.com
            My.Name1@googlemail.com => myname1@gmail.com

        """
        email = email or ''
        try:
            email_name, domain_part = email.strip().rsplit('@', 1)
        except ValueError:
            pass
        else:
            for domain in (
                'gmail.com',
                'googlemail.com'
            ):
                if domain_part == '@' + domain:
                    email_name = re.sub(r'\+.*$', r'', email_name)  # removes +ABC123
                    email_name = email_name.replace('.', '')  # remove dots
                    if domain_part == 'googlemail.com':  # set default domain
                        domain_part = 'gmail.com'
                    email = '@'.join([email_name, domain_part.lower()])
                    return email
        return email

    def _create_user(self, email, password,
                     is_staff, is_superuser, is_active=True,
                     **extra_fields):
        """
        Creates and saves a User with the given email and password.
        """
        now = timezone.now()
        if not email:
            raise ValueError('The given email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email,
                          is_staff=is_staff, is_active=is_active,
                          is_superuser=is_superuser, last_login=now,
                          date_joined=now, **extra_fields)
        if password is not None:
            user.set_password(password)
        try:
            user.pk = self.get(email=email, is_active=False).pk
        except self.model.DoesNotExist:
            pass
        user.save(using=self.db)
        return user

    def create_user(self, username=None, email=None, password=None, **extra_fields):
        return self._create_user(email or username, password, False, False,
                                 **extra_fields)

    def create_superuser(self, username=None, email=None, password=None, **extra_fields):
        return self._create_user(email or username, password, True, True,
                                 **extra_fields)

    def latest(self, num=5):
        '''
        Get the latest entities
        '''
        return self.public()[:num]


@python_2_unicode_compatible
class AbstractUser(AbstractBaseUser):
    email = models.EmailField(_("email address"), max_length=255, null=True, unique=True)
    username = models.CharField(_("username"), max_length=255, null=True, unique=True,
        help_text=_('Required. 255 characters or fewer. Letters, numbers and '
                    '@/./+/-/_ characters'),
        validators=[
            validators.RegexValidator(re.compile('^[\w.@+-]+$'), _("Enter a valid username."), 'invalid')
        ])

    first_name = models.CharField(_("first name"), max_length=255, blank=True)
    middle_name = models.CharField(_("middle name"), max_length=255, blank=True)
    last_name = models.CharField(_("last name"), max_length=255, blank=True)
    second_last_name = models.CharField(_("second last name"), max_length=255,
        blank=True)

    is_superuser = models.BooleanField(_('superuser status'), default=False,
        help_text=_('Designates that this user has all permissions without '
                    'explicitly assigning them.'))
    is_staff = models.BooleanField(_("staff status"), default=False,
        help_text=_("Designates whether the user can log into this admin "
                    'site.'))
    is_active = models.BooleanField(_("active"), default=True,
        help_text=_("Designates whether this user should be treated as "
                    'active. Unselect this instead of deleting accounts.'))

    objects = UserManager()

    USERNAME_FIELD = 'email'

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        abstract = True

    def __str__(self):
        return self.get_name()

    @staticmethod
    def get_anonymous():
        return get_anonymous_user()

    def is_anonymous(self):
        """
        Always returns False. This is a way of comparing User objects to
        anonymous users.
        """
        return self.id == settings.ANONYMOUS_USER_ID

    def is_authenticated(self):
        """
        Always return True. This is a way to tell if the user has been
        authenticated in templates.
        """
        return self.id != settings.ANONYMOUS_USER_ID

    def get_username(self):
        username_field_name = getattr(self.__class__, 'USERNAME_FIELD', 'username')
        return getattr(self, username_field_name, None)

    @property
    def date_joined(self):
        warnings.warn("The property 'date_joined' exists only for historical reasons (django's User used to have it) and will be removed soon.", PendingDeprecationWarning)
        return self.created_at

    @date_joined.setter
    def date_joined(self, value):
        self.created_at = value

    def get_name(self):
        return self.full_name or self.username or self.email and self.email.split('@')[0] or ''

    def get_short_name(self):
        "Returns the short name for the user."
        return self.first_name or self.get_full_name()

    @property
    def short_name(self):
        return self.get_short_name()

    @property
    def full_name(self):
        return self.get_full_name()

    @full_name.setter
    def full_name(self, value):
        self.set_full_name(value)

    def email_user(self, subject, message, from_email=None):
        """
        Sends an email to this User.
        """
        send_mail(subject, message, from_email, [self.email])

    def post_save(self, created, save=False):
        """
        Then, if the user has been created, update the username, in accordance
        to the project settings.
        """
        if created:
            UserModel = auth.get_user_model()

            # Normalized email:
            if self.email:
                self.email = UserModel.objects.normalize_email(self.email)

            name = self.get_full_name()
            username = self.username
            if not username and settings.SLUGIFY_USER_NAME:
                username = slugify(name)
            if username and self.username != username:
                for t in range(6):
                    if username.lower() not in settings.RESERVED_USERNAMES:
                        if not UserModel.objects.filter(username__iexact=username).exclude(id=self.id).exists():
                            break
                    if t == 0:
                        username += '-'
                    username += str(random.randint(0, 9))
                    if t == 5:
                        username = None
            if self.username != username:
                self.username = username
                save = True
        return save

    def get_tags(self):
        user_type = ['UserType:' + self.type]
        full_name = self.get_full_name()
        if full_name:
            alpha = ['UserAlphabeth:' + full_name[0]]
        else:
            alpha = []
        return ['User'] + user_type + alpha

    def get_full_name(self):
        """
        Returns the first_name plus the last_name, with a space in between.
        """
        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()


@autoconnect
class User(AbstractUser):
    """
    Entities (including users) within the Dubalu authentication system are
    represented by this model.

    Password and email are required. Other fields are optional.
    """
    class Meta(AbstractUser.Meta):
        swappable = 'AUTH_USER_MODEL'


########
#  USERPROFILE
########

from dfw.entities.models import AbstractEntity, EntityManager
from dfw.core.plugins.models.statable import STATUS_PUBLISHED, \
    STATUS_UNPUBLISHED, STATUS_HIDDEN


class UserProfileManager(EntityManager, UserManager):
    def active(self):
        return self.filter(is_active=True)

    def inactive(self):
        return self.filter(is_active=False)


@python_2_unicode_compatible
class AbstractUserProfile(AbstractEntity, AbstractUser):
    _tabbed = False

    nick_name = models.CharField(_("Nick name"), max_length=200, null=True,
        blank=True)

    signature = models.TextField(_("Signature"), null=True, blank=True,
        help_text=_("User's signature for posts and messages"))

    objects = UserProfileManager()

    class Meta(AbstractEntity.Meta, AbstractUser.Meta):
        abstract = True
        verbose_name = _("user profile")
        verbose_name_plural = _("user profiles")

    def __str__(self):
        return self.get_name()

    def get_owner(self):
        if not self.owner_id or self.owner_id == self.id:
            return self
        return self.owner

    def pre_save(self):
        if self.status in (STATUS_PUBLISHED, STATUS_UNPUBLISHED):
            self.status = STATUS_HIDDEN

    @property
    def username_code(self):
        return self.get_username() or self.username or self.code

    def get_name(self):
        """Return the first existing field: nick_name / first name / full name / email / name"""
        name = super(AbstractUserProfile, self).get_name()
        return self.nick_name or self.get_short_name() or self.full_name or self.email and self.email.split('@')[0] or name


@autoconnect
class UserProfile(AbstractUserProfile):
    class Meta(AbstractUserProfile.Meta):
        swappable = 'AUTH_USER_MODEL'
        app_label = 'users'
