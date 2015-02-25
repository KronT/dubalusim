# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import zlib

from django.core import signing
from django.utils.encoding import force_bytes
from django.core.exceptions import PermissionDenied

from .models import LazyForms


def dumps(obj, key=None, salt='django.core.signing', serializer=signing.JSONSerializer, compress=False):
    """
    Returns URL-safe, sha1 signed base64 compressed JSON string. If key is
    None, settings.SECRET_KEY is used instead.

    If compress is True (not the default) checks if compressing using zlib can
    save some space. Prepends a '.' to signify compression. This is included
    in the signature, to protect against zip bombs.

    Salt can be used to namespace the hash, so that a signed string is
    only valid for a given namespace. Leaving this at the default
    value or re-using a salt value across different parts of your
    application without good cause is a security risk.

    The serializer is expected to return a bytestring.
    """
    data = serializer().dumps(obj)

    # Flag for if it's been compressed or not
    is_compressed = False

    if compress:
        # Avoid zlib dependency unless compress is being used
        compressed = zlib.compress(data)
        if len(compressed) < (len(data) - 1):
            data = compressed
            is_compressed = True
    base64d = signing.b64_encode(data)
    if is_compressed:
        base64d = b'.' + base64d
    return signing.Signer(key, salt=salt).sign(base64d)


def loads(s, key=None, salt='django.core.signing', serializer=signing.JSONSerializer):
    """
    Reverse of dumps(), raises BadSignature if signature fails.

    The serializer is expected to accept a bytestring.
    """
    # TimestampSigner.unsign always returns unicode but base64 and zlib
    # compression operate on bytes.
    base64d = force_bytes(signing.Signer(key, salt=salt).unsign(s))
    decompress = False
    if base64d[:1] == b'.':
        # It's compressed; uncompress it first
        base64d = base64d[1:]
        decompress = True
    data = signing.b64_decode(base64d)
    if decompress:
        data = zlib.decompress(data)
    return serializer().loads(data)


def encode_params(key, form_class, field_name, helper, pk, *extra_params):
    try:
        lazyform = LazyForms.objects.get_by_natural_key(hash((form_class, field_name, helper)))
    except LazyForms.DoesNotExist:
        lazyform, _ = LazyForms.objects.get_or_create(
            form_class=form_class,
            field_name=field_name,
            helper=helper,
        )
    params = (key, lazyform.pk, pk) + extra_params
    params = dumps(params)
    return params


def decode_params(key, params):
    all_params = loads(params)
    _key, lazyform_pk, pk = all_params[:3]
    if _key != key:
        raise PermissionDenied
    extra_params = all_params[3:]
    lazyform = LazyForms.objects.get_for_id(lazyform_pk)
    form_class = lazyform.form_class
    field_name = lazyform.field_name
    helper = lazyform.helper
    # print 'form_class=%r' % form_class, 'field_name=%r' % field_name, 'helper=%r' % helper, 'pk=%r' % pk, 'extra_params=%r' % extra_params
    return form_class, field_name, helper, pk, extra_params
