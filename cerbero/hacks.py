# cerbero - a multi-platform build system for Open Source software
# Copyright (C) 2012 Andoni Morales Alastruey <ylatuya@gmail.com>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Library General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Library General Public License for more details.
#
# You should have received a copy of the GNU Library General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

import os
import sys


# On windows, python transforms all enviroment variables to uppercase,
# but we need lowercase ones to override configure options like
# am_cv_python_platform

environclass = os.environ.__class__
import UserDict


class _Environ(environclass):

    def __init__(self, environ):
        UserDict.UserDict.__init__(self)
        self.data = {}
        for k, v in environ.items():
            self.data[k] = v

    def __setitem__(self, key, item):
        os.putenv(key, item)
        self.data[key] = item

    def __getitem__(self, key):
        return self.data[key]

    def __delitem__(self, key):
        os.putenv(key, '')
        del self.data[key]

    def pop(self, key, *args):
        os.putenv(key, '')
        return self.data.pop(key, *args)

    def has_key(self, key):
        return key in self.data

    def __contains__(self, key):
        return key in self.data

    def get(self, key, failobj=None):
        return self.data.get(key, failobj)


if sys.platform.startswith('win'):
    os.environ = _Environ(os.environ)