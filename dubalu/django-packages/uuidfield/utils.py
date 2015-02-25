# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import uuid
import base64
import binascii
import hashlib

from django.conf import settings
from django.db import IntegrityError

import primes

from . import UUID
from .models import UUIDNodes


ANONYMOUS_USER_CODE = 'ANONYMOUS'
ANONYMOUS_USER_UUID = UUID(settings.ANONYMOUS_USER_ID)

_UUID_NODE_MASK = (1 << 48) - 1
_UUID_CLOCK_MASK = (1 << 14) - 1
_UUID_TIME_INITIAL = 0x1e4391800000000


PRIMES_15_2000 = list(primes.gen_primes(15, 2000))


def get_obj_for_hash(node, generator):
    seen = set()
    node_hash = int(hashlib.sha1(binascii.unhexlify('{:012x}'.format(node))).hexdigest(), 16)
    for buckets in PRIMES_15_2000:
        h = node_hash % buckets + 1
        if h not in seen:
            obj = generator(h)
            if obj is not None:
                return obj
            seen.add(h)
    raise RuntimeError("Cannot find an available bucket for the node")


def get_node(node_id):
    try:
        return UUIDNodes.objects.get_for_id(node_id).node
    except UUIDNodes.DoesNotExist:
        return None


def get_node_id(node):
    try:
        uuid_node = UUIDNodes.objects.get_for_label(node)
    except UUIDNodes.DoesNotExist:
        def generator(id):
            try:
                uuid_node, _ = UUIDNodes.objects.get_or_create_for_pk(id, defaults=dict(node=node))
            except IntegrityError:
                uuid_node = UUIDNodes.objects.get_for_label(node)
            if uuid_node.node == node:
                return uuid_node
        uuid_node = get_obj_for_hash(node, generator)
    return uuid_node.id


def encode_uuid(num):
    """
    Encode and compress a UUID (uuid1) into a smallest representation
    which doesn't have the full node part, but a node id which is
    initialized in the databse as needed (in a known nodes model).

    Time is also reduced from a date.
    Maximum number of mapped nodes is 536870912: (1 << 29) - 1

    http://tools.ietf.org/html/rfc4122

    """
    if num is None:
        raise ValueError("Cannot encode None")
    if num == ANONYMOUS_USER_UUID:
        return ANONYMOUS_USER_CODE
    if not isinstance(num, uuid.UUID):
        num = UUID(num)
    elif num.version != 1:
        raise ValueError("Cannot encode UUID which is not Version 1 (%s)" % num)
    node_id = get_node_id(num.node)
    node_bin = '{:b}'.format(node_id) + '00'
    node_size = len(node_bin) / 8
    node_len = (node_size + 1) * 8
    if node_size > 3:
        raise ValueError("Not enough space for nodes")
    node_data = int(node_bin, 2) | node_size
    time = num.time - _UUID_TIME_INITIAL
    if time < 0:
        raise ValueError("Timestamp in UUID is too old to be encoded properly (%s)" % num)
    clock = num.clock_seq & _UUID_CLOCK_MASK
    full = (time << 14) | clock
    full <<= node_len
    full |= node_data
    bytes_ = binascii.unhexlify(b'{:032x}'.format(full)).lstrip(b'\x00')
    code = base64.urlsafe_b64encode(bytes_)
    code = code.rstrip('=')
    return code


def decode_uuid(code):
    """
    Decode an encoded UUID compressed code to a full UUID.

    """
    if code is None:
        raise ValueError("Cannot decode None")
    if code == ANONYMOUS_USER_CODE:
        return ANONYMOUS_USER_UUID
    code += '=' * (4 - len(code) % 4)
    bytes_ = base64.urlsafe_b64decode(code)
    full = int(binascii.hexlify(bytes_), 16)
    node_len = ((full & 3) + 1) * 8
    node_id = (full & ((1 << node_len) - 1)) >> 2
    full >>= node_len
    time = (full >> 14) + _UUID_TIME_INITIAL
    clock = full & _UUID_CLOCK_MASK
    node = get_node(node_id)
    if node is None:
        raise ValueError("Invalid entity code (registered node not found)")
    uuid_ = UUID(fields=(
        time & 0xffffffff,
        (time >> 32) & 0xffff,
        (time >> 48) | 0x1000,  # version 1
        (clock >> 8) | 0x80,  # variant: RFC 4122
        clock & 0xff,
        node & _UUID_NODE_MASK,
    ))
    return uuid_


if __name__ == '__main__':
    # The following for testing:
    import random

    ANONYMOUS_USER_CODE = 'ANONYMOUS'
    ANONYMOUS_USER_UUID = UUID(bytes='\x00' * 16)
    RANDOM = random.randint(1, 536870911 - 100)
    nodes = [None]

    def get_node(node_id):  # NOQA
        node_id -= RANDOM
        try:
            return nodes[node_id]
        except IndexError:
            return None

    def get_node_id(node):  # NOQA
        try:
            return nodes.index(node) + RANDOM
        except ValueError:
            nodes.append(node)
            return len(nodes) - 1 + RANDOM

    u = uuid.uuid1()
    ue = encode_uuid(u)
    assert decode_uuid(ue) == u
