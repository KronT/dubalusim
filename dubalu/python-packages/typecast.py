################################################################################
# Convert stuff to objects

import re
import six
import decimal


def try_number(value):
    if isinstance(value, (float, int)):
        return value
    if isinstance(value, basestring) and '.' in value:
        try:
            return float(value)
        except:
            pass
    try:
        return int(value)
    except:
        try:
            return float(value)
        except:
            return value


def to_bool(value):
    if str(value).lower() in ('none', 'n', 'no', 'off', 'f', 'false', '0'):
        value = False
    else:
        value = bool(value)
    return value
Bool = to_bool


def to_int(value):
    try:
        value = int(value)
    except:
        value = 0
    return value
Int = to_int


def to_float(value):
    try:
        value = float(value)
    except:
        value = 0.0
    return value
Float = to_float


def to_decimal(x):
    if isinstance(x, float):
        x = '%0.2f' % x
    if x is not None:
        x = decimal.Decimal(x)
    return x
Decimal = to_decimal


def to_unicode(value):
    if isinstance(value, tuple):
        return tuple(to_unicode(v) for v in value)
    if isinstance(value, list):
        return [to_unicode(v) for v in value]
    if isinstance(value, dict):
        return dict((k, to_unicode(v)) for k, v in value.items())
    try:
        return value.decode('utf8')
    except:
        try:
            return value.decode('latin1')
        except:
            return unicode(value)
Unicode = to_unicode


class Money(float):
    def __new__(cls, value, symbol="$", decimals=2):
        if isinstance(value, six.string_types):
            value = re.sub(r'[^\d.]+', '', value)
        obj = float.__new__(cls, value)
        obj.symbol = symbol
        obj.decimals = decimals
        return obj

    def __add__(self, other):
        return Money(float.__add__(self, other), self.symbol, self.decimals)
    __radd__ = __add__

    def __sub__(self, other):
        return Money(float.__sub__(self, other), self.symbol, self.decimals)
    __rsub__ = __sub__

    def __div__(self, other):
        return Money(float.__div__(self, other), self.symbol, self.decimals)
    __rdiv__ = __div__

    def __truediv__(self, other):
        return Money(float.__truediv__(self, other), self.symbol, self.decimals)
    __rtruediv__ = __truediv__

    def __floordiv__(self, other):
        return Money(float.__floordiv__(self, other), self.symbol, self.decimals)
    __rfloordiv__ = __floordiv__

    def __mul__(self, other):
        return Money(float.__mul__(self, other), self.symbol, self.decimals)
    __rmul__ = __mul__

    def __neg__(self):
        return Money(float.__neg__(self), self.symbol, self.decimals)

    def __str__(self):
        sign = ''
        if self < 0:
            value = -self
            sign = '-'
        elif self == 0:
            value = 0  # avoiding zeros with negative sign
        else:
            value = self
        ret = ""
        if sign:
            ret += sign + " "
        ret += ('%s{:,.%sf}' % (self.symbol, self.decimals)).format(value)
        return ret.strip()
    __repr__ = __str__
