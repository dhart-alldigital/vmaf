#!/usr/bin/env python
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#                             Michael A.G. Aivazis
#                      California Institute of Technology
#                      (C) 1998-2005  All Rights Reserved
#
# {LicenseText}
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#


from Column import Column


class Date(Column):


    def type(self):
        return "date"


    def __init__(self, name, **kwds):
        Column.__init__(self, name, **kwds)
        return


    def __get__(self, instance, cls=None):
        ret = Column.__get__(self, instance, cls = cls)
        if ret is None:
            import time
            return time.ctime()
        return ret


# version
__id__ = "$Id: Date.py,v 1.1.1.1 2006-11-27 00:09:55 aivazis Exp $"

# End of file 
