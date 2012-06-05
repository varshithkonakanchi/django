# -*- coding: utf-8 -*-

class BrokenException(Exception):
    pass

except_args = (b'Broken!',           # plain exception with ASCII text
               u'¡Broken!',         # non-ASCII unicode data
               u'¡Broken!'.encode('utf-8'), # non-ASCII, utf-8 encoded bytestring
               b'\xa1Broken!', )     # non-ASCII, latin1 bytestring

