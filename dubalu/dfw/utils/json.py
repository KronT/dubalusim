# -*- coding: utf-8 -*-
"""
Dubalu Framework
~~~~~~~~~~~~~~~~

:author: Dubalu Framework Team. See AUTHORS.
:copyright: Copyright (c) 2013-2014, deipi.com LLC. All Rights Reserved.
:license: See LICENSE for license details.

"""
from __future__ import absolute_import, unicode_literals

import datetime
import decimal
import codecs
import uuid

try:
    from uuidfield import UUID
except ImportError:
    from uuid import UUID  # NOQA

try:
    from pytz import FixedOffset
except ImportError:
    class FixedOffset(datetime.tzinfo):
        def __init__(self, minutes):
            self._offset = datetime.timedelta(minutes=minutes)

        def utcoffset(self, dt):
            return self._offset

try:
    import simplejson as json
except ImportError:
    import json

from django.utils.encoding import force_text


try:
    JSONDecodeError = json.JSONDecodeError
except AttributeError:
    JSONDecodeError = ValueError


def datetime_repr(o):
    seconds = 0
    if o.tzinfo is not None:
        utcoffset = o.tzinfo.utcoffset(o)
        seconds = utcoffset and utcoffset.total_seconds() or 0
    if o.microsecond:
        r = o.strftime('%Y-%m-%dT%H:%M:%S.%f')[:23]
    else:
        r = o.strftime('%Y-%m-%dT%H:%M:%S')
    if seconds:
        TZ = "%s%02d:%02d" % (('-' if seconds < 0 else '+',) + divmod(abs(seconds // 60), 60))
    else:
        TZ = "Z"
    return r + TZ


def time_repr(o):
    if o.tzinfo is not None and o.tzinfo.utcoffset(o):
        raise ValueError("JSON can't represent timezone-aware times.")
    r = o.isoformat()
    if o.microsecond:
        r = r[:12]
    return r


def to_datetime(r):
    if len(r) >= 19:
        if r.endswith("Z"):
            minutes = 0
            value = r[:-1]
        elif r[-3] == ':' and r[-6] in ('-', '+'):
            minutes = (int(r[-5:-3]) * 60 + int(r[-2:]))
            if r[-6] == '-':
                minutes = -minutes
            value = r[:-6]
        else:
            minutes = None
            value = r
        if minutes is not None:
            tzinfo = FixedOffset(minutes)
        else:
            tzinfo = None
        try:
            o = datetime.datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%f')
            return o.replace(tzinfo=tzinfo)
        except ValueError:
            pass
        try:
            o = datetime.datetime.strptime(value, '%Y-%m-%dT%H:%M:%S')
            return o.replace(tzinfo=tzinfo)
        except ValueError:
            pass
    raise ValueError


def to_date(r):
    value = r
    return datetime.datetime.strptime(value, '%Y-%m-%d').date()


def to_time(r):
    value = r
    try:
        return datetime.datetime.strptime(value, '%H:%M:%S.%f').time()
    except ValueError:
        pass
    try:
        return datetime.datetime.strptime(value, '%H:%M:%S').time()
    except ValueError:
        pass
    raise ValueError


class BetterJSONEncoder(json.JSONEncoder):
    """
    JSONEncoder subclass that knows how to encode date/time and decimal types.

    """

    ENCODER_BY_TYPE = {
        uuid.UUID: lambda o: "%s" % o,
        datetime.datetime: datetime_repr,  # See "Date Time String Format" in the ECMA-262 specification.
        datetime.date: lambda o: o.isoformat(),
        datetime.time: time_repr,
        decimal.Decimal: lambda o: force_text(o),
        set: list,
        frozenset: list,
        bytes: lambda o: o.decode('utf-8', errors='replace'),
    }

    def default(self, obj):
        try:
            encoder = self.ENCODER_BY_TYPE[type(obj)]
        except KeyError:
            return super(BetterJSONEncoder, self).default(obj)
        return encoder(obj)


def better_decoder(json_data):
    for key in json_data:
        value = json_data[key]
        if isinstance(value, basestring):
            try:
                json_data[key] = UUID(value)
                continue
            except ValueError:
                pass
            try:
                json_data[key] = to_datetime(value)
                continue
            except ValueError:
                pass
            try:
                json_data[key] = to_date(value)
                continue
            except ValueError:
                pass
            try:
                json_data[key] = to_time(value)
                continue
            except ValueError:
                pass
    return json_data


def dumps(value, **kwargs):
    if 'ensure_ascii' not in kwargs:
        kwargs['ensure_ascii'] = False
    if 'encoding' not in kwargs:
        kwargs['encoding'] = 'safe-utf-8'
    if 'cls' not in kwargs:
        kwargs['cls'] = BetterJSONEncoder
    return json.dumps(value, **kwargs)


def loads(value, **kwargs):
    if 'encoding' not in kwargs:
        kwargs['encoding'] = 'safe-utf-8'
    if 'object_hook' not in kwargs:
        kwargs['object_hook'] = better_decoder
    return json.loads(value, **kwargs)


_utf8_encoder = codecs.getencoder('utf-8')


def safe_encode(input, errors='backslashreplace'):
    return _utf8_encoder(input, errors)


_utf8_decoder = codecs.getdecoder('utf-8')


def safe_decode(input, errors='replace'):
    return _utf8_decoder(input, errors)


class Codec(codecs.Codec):

    def encode(self, input, errors='backslashreplace'):
        return safe_encode(input, errors)

    def decode(self, input, errors='replace'):
        return safe_decode(input, errors)


class IncrementalEncoder(codecs.IncrementalEncoder):
    def encode(self, input, final=False):
        return safe_encode(input, self.errors)[0]


class IncrementalDecoder(codecs.IncrementalDecoder):
    def decode(self, input, final=False):
        return safe_decode(input, self.errors)[0]


class StreamWriter(Codec, codecs.StreamWriter):
    pass


class StreamReader(Codec, codecs.StreamReader):
    pass


def getregentry(name):
    if name != 'safe-utf-8':
        return None
    return codecs.CodecInfo(
        name='safe-utf-8',
        encode=safe_encode,
        decode=safe_decode,
        incrementalencoder=IncrementalEncoder,
        incrementaldecoder=IncrementalDecoder,
        streamreader=StreamReader,
        streamwriter=StreamWriter,
    )


codecs.register(getregentry)
