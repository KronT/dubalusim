import six


def recursive_format(value, context=None, *args, **kwargs):
    """
    Recursively formats value

    Example:
        >>> sample = {"key": "{value}", "sub-dict": {"sub-key": "sub-{value}"}}
        >>> assert recursive_format(sample, value="Bob") == \
            {'key': 'Bob', 'sub-dict': {'sub-key': 'sub-Bob'}}
    """
    if context is None:
        context = {}
    oid = id(value)
    if oid in context:
        return value
    context[oid] = True
    if isinstance(value, dict):
        for k, v in value.items():
            value[k] = recursive_format(v, context=context, *args, **kwargs)
    elif isinstance(value, list):
        value = [recursive_format(v, context=context, *args, **kwargs) for v in value]
    elif isinstance(value, tuple):
        value = tuple(recursive_format(v, context=context, *args, **kwargs) for v in value)
    elif isinstance(value, six.string_types):
        _value = None
        while value != _value:
            _value = value
            try:
                value = value.format(*args, **kwargs)
            except:
                pass
    del context[oid]
    return value
