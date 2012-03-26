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
import shutil
import unittest
import tempfile

from cerbero.config import Platform
from cerbero.utils import shell
from cerbero.errors import PackageNotFoundError
from cerbero.packages.packagesstore import PackagesStore
from cerbero.tests import test_packages_common as common


class PackageTest(unittest.TestCase):

    def setUp(self):
        self.config = common.DummyConfig()
        self.config.packages_dir = '/test'
        self.config.target_platform = Platform.LINUX
        self.store = PackagesStore(self.config, False)

    def testAddPackage(self):
        package = common.Package1(self.config)
        self.assertEquals(len(self.store._packages), 0)
        self.store.add_package(package)
        self.assertEquals(len(self.store._packages), 1)
        self.assertEquals(package, self.store._packages[package.name])

    def testGetPackage(self):
        package = common.Package1(self.config)
        self.store.add_package(package)
        self.assertEquals(package, self.store.get_package(package.name))

    def testPackageNotFound(self):
        self.failUnlessRaises(PackageNotFoundError, self.store.get_package,
            'unknown')

    def testPackagesList(self):
        package = common.Package1(self.config)
        metapackage = common.MetaPackage(self.config)
        self.store.add_package(package)
        self.store.add_package(metapackage)
        l = sorted([package, metapackage], key=lambda x: x.name)
        self.assertEquals(l, self.store.get_packages_list())

    def testPackageDeps(self):
        package = common.Package1(self.config)
        self.store.add_package(package)
        self.assertEquals(package.deps,
            self.store.get_package_deps(package.name))

    def testMetaPackageDeps(self):
        metapackage = common.MetaPackage(self.config)
        self.store.add_package(metapackage)
        # the metapackage depends on package that are not yet in the store
        self.failUnlessRaises(PackageNotFoundError,
            self.store.get_package_deps, metapackage.name)
        for klass in [common.Package1, common.Package2, common.Package3,
                common.Package4, common.MetaPackage]:
            p = klass(self.config)
            self.store.add_package(p)
        deps = ['gstreamer-test-bindings', 'gstreamer-test1',
                'gstreamer-test2', 'gstreamer-test3']
        self.assertEquals(deps, self.store.get_package_deps(metapackage.name))