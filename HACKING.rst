Vitrage Style Commandments
==========================

Read the OpenStack Style Commandments https://docs.openstack.org/hacking/latest/

Vitrage Specific Commandments
-----------------------------

[V316] assertTrue(isinstance(a, b)) sentences not allowed
[V317] assertEqual(type(A), B) sentences not allowed
[V318] assertEqual(A, None) or assertEqual(None, A) sentences not allowed
[V319] Don't translate logs
[V321] contextlib.nested is deprecated
[V322] use a dict comprehension instead of a dict constructor with a sequence of key-value pairs
[V323] Do not use xrange. Use range, or six.moves.range
[V324] Use six.iteritems() or dict.items() instead of dict.iteritems()
[V325] Use six.iterkeys() or dict.keys() instead of dict.iterkeys()
[V326] Use six.itervalues() or dict.values instead of dict.itervalues()
[V327] Method's default argument shouldn't be mutable
[V328] Disallow LOG.warn
[V329] Don't use assertEqual(True/False, observed).