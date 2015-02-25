# -*- coding: utf-8 -*-
# python -m unittest -v lru.tests

import pickle
import unittest

from .cache import LRUCache


class LRUCacheTestCase(unittest.TestCase):
    def test_simple(self):
        d = LRUCache(3)
        d['a'] = 1
        d['b'] = 2
        d['c'] = 3
        d['a']
        d['d'] = 4
        d['e'] = Exception("Some Exception")
        self.assertEqual(len(d), 4)
        self.assertIn('a', d)
        self.assertNotIn('b', d)
        self.assertIn('c', d)
        self.assertIn('d', d)
        self.assertIn('e', d)

    def test_pickleable(self):
        cache = LRUCache(2)
        cache["foo"] = 42
        cache["bar"] = 23
        cache["foo"]
        for protocol in range(3):
            copy = pickle.loads(pickle.dumps(cache, protocol))
            self.assertEqual(copy.capacity, cache.capacity)
            self.assertEqual(copy._mapping, cache._mapping)
            self.assertEqual(copy._queues, cache._queues)
