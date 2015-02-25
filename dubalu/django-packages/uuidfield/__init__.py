# -*- coding: utf-8 -*-
from __future__ import absolute_import

import six
import uuid


class UUID(six.binary_type, uuid.UUID):
    def __new__(self, *args, **kwargs):
        return six.binary_type.__new__(self, uuid.UUID(*args, **kwargs))
