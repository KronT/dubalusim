import math


def gen_primes(start, end):
    """
    Generate a sequence of prime numbers using Sieve of Eratosthenes.

    Code by David Eppstein, UC Irvine, 28 Feb 2002
    http://code.activestate.com/recipes/117119/

    """
    # Maps composites to primes witnessing their compositeness.
    # This is memory efficient, as the sieve is not "run forward"
    # indefinitely, but only as long as required by the current
    # number being tested.
    #
    D = {}

    # The running integer that's checked for primeness
    q = 2

    while q <= end:
        if q not in D:
            # q is a new prime.
            # Yield it and mark its first multiple that isn't
            # already marked in previous iterations
            #
            if q >= start:
                yield q
            D[q * q] = set([q])
        else:
            # q is composite. D[q] is the list of primes that
            # divide it. Since we've reached q, we no longer
            # need it in the map, but we'll mark the next
            # multiples of its witnesses to prepare for larger
            # numbers
            #
            for p in D[q]:
                D.setdefault(p + q, set()).add(p)
            del D[q]
        q += 1


def is_prime(num):
    """
    Returns True if the number is prime else False.

    """
    if num == 0 or num == 1:
        return False
    for x in range(2, int(math.sqrt(num) + 1)):
        if not num % x:
            return False
    else:
        return True
