# cerbero - a multi-platform build system for Open Source software
# Copyright (C) 2014 Thibault Saunier <tsaunier@gnome.org>
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

from cerbero.commands import gensdkshell
from cerbero.errors import FatalError
from cerbero.utils import _, N_, shell
from cerbero.utils import messages as m
from cerbero.packages import PackagerBase
from cerbero.config import DistroVersion


LAUNCH_BUNDLE_COMMAND = """# Try to discover plugins only once
PLUGINS_SYMLINK=${HOME}/.cache/gstreamer-1.0/%(appname)s-gstplugins
rm ${PLUGINS_SYMLINK}
ln -s ${APPDIR}/lib/gstreamer-1.0/ ${PLUGINS_SYMLINK}
if [ $? -ne 0 ]; then
    export GST_PLUGIN_PATH=${APPDIR}/lib/gstreamer-1.0/
else
    export GST_PLUGIN_PATH=${PLUGINS_SYMLINK}
fi

if test -z ${APP_IMAGE_TEST}; then
    # Invoke the app with the arguments passed
    cd ${APPDIR}
    ${APPDIR}/%(executable_path)s $*
else
    # Run a shell in test mode
    bash;
fi

# Cleaning up the link to gstplugins
rm ${PLUGINS_SYMLINK}
"""

class LinuxBundler(PackagerBase):
    doc = N_('Bundle after building packages')
    name = 'bundle'

    def __init__(self, config, package, store):
        PackagerBase.__init__(self, config, package, store)
        self.bundle_name = "%s-%s-%s" %(self.package.name, self.package.version, self.config.arch)
        if not hasattr(self.package, "desktop_file"):
            raise FatalError("Can not create a linux bundle if the package does "
                             "not have a 'desktop_file' property set")


    def pack(self, output_dir, devel=True, force=False, keep_temp=False):
        self.tmp_install_dir = os.path.join(output_dir, "bundle_root")
        self.desktop_file = os.path.join(self.tmp_install_dir, self.package.desktop_file)
        self.output_dir = output_dir
        self.devel = devel
        self.keep_temp = keep_temp

        self.bundle()

        return []

    def _copy_installdir(self):
        '''
        Copy all the files that are going to be packaged to the bundle's
        temporary directory
        '''
        os.makedirs(self.tmp_install_dir)
        for f in set(self.package.files_list()):
            in_path = os.path.join(self.config.prefix, f)
            if not os.path.exists(in_path):
                m.warning("File %s is missing and won't be added to the "
                          "package" % in_path)
                continue
            out_path = os.path.join(self.tmp_install_dir, f)
            odir = os.path.split(out_path)[0]
            if not os.path.exists(odir):
                os.makedirs(odir)
            shutil.copy(in_path, out_path)

    def _make_paths_relative(self):
        sofiles = shell.find_files('*.so', self.tmp_install_dir)
        for sof in sofiles:
            try:
                shell.call("chrpath -d %s" % sof, self.tmp_install_dir,
                           fail=False)
            except FatalError:
                m.warning("Could not 'chrpath' %s" % sof)

        shell.call("ln -s . usr", self.tmp_install_dir, fail=False)

        # FIXME Fix the root of that issue !
        # Make libbz2.so symlinks relative
        for command in ["rm libbz2.so libbz2.so.1.0",
                        "ln -s libbz2.so.1.0.6 libbz2.so",
                        "ln -s libbz2.so.1.0.6 libbz2.so.1.0",
                        ]:
            shell.call(command, os.path.join(self.tmp_install_dir, "lib"), False)

        # Make gd-pixbuf loader.cache file use relative paths
        cache = os.path.join(self.tmp_install_dir, 'lib', 'gdk-pixbuf-2.0',
            '2.10.0', 'loaders.cache')
        shell.replace(cache, {self.config.install_dir: '.'})

        for icondir in os.listdir(os.path.join(self.tmp_install_dir, "share/icons/")):
            if os.path.exists(os.path.join(icondir, "index.theme")):
                shell.call("gtk-update-icon-cache %s" % icondir, fail=False)

        shell.call("update-mime-database %s" % os.path.join(self.tmp_install_dir, "share", "mime"), fail=False)

        # Use system wide applications in case the bundle needs to open apps not included in
        # the bundle (to show the documentation most probably)
        shell.call("rm -rf %s" % os.path.join(self.tmp_install_dir, "share", "applications"), fail=False)
        shell.call("ln -s %s %s" % (os.path.join("/usr", "share", "applications"),
                                    os.path.join(self.tmp_install_dir, "share", "applications")),
                   fail=False)

    def _install_bundle_specific_files(self):
        # Installing desktop file and runner script
        shell.call("cp %s %s" % (self.desktop_file, self.tmp_install_dir), fail=False)
        filepath = os.path.join(self.tmp_install_dir, "AppRun")
        # Base environment variables
        env = {}
        env['GSETTINGS_SCHEMA_DIR'] = '${APPDIR}/share/glib-2.0/schemas/:${GSETTINGS_SCHEMA_DIR}'
        env['GDK_PIXBUF_MODULE_FILE'] = './lib/gdk-pixbuf-2.0/2.10.0/loaders.cache'
        env['GST_REGISTRY'] = '${HOME}/.cache/gstreamer-1.0/%s-bundle-registry' % self.package.name
        env['GST_REGISTRY_1_0'] = '${HOME}/.cache/gstreamer-1.0/%s-bundle-registry' % self.package.name
        if hasattr(self.package, "default_gtk_theme"):
            env['GTK_THEME'] = self.package.default_gtk_theme

        launch_command = LAUNCH_BUNDLE_COMMAND % ({
                                "prefix": self.tmp_install_dir,
                                "executable_path": self.package.commands[0][1],
                                "appname": self.package.name})

        shellvarsgen = gensdkshell.GenSdkShell()

        shellvarsgen.runargs(self.config, "AppRun", self.tmp_install_dir,
                             "${APPDIR}", "${APPDIR}/lib",
                             self.config.py_prefix,
                             cmd=launch_command,
                             env=env,
                             prefix_env_name="APPDIR")

    def _generate_bundle(self):
        shell.call("AppImageAssistant %s %s" % (self.tmp_install_dir, self.bundle_name),
                   self.output_dir)

    def _clean_tmps(self):
        shell.call("rm -rf %s" % self.tmp_install_dir)

    def _generate_md5sum(self):
        md5name = "%s.md5sum" % self.bundle_name
        shell.call("md5sum %s > %s" % (self.bundle_name, md5name),
                   self.output_dir)
        m.action(_("Bundle avalaible in: %s") % os.path.join(self.output_dir, self.bundle_name))

    def bundle(self):
        # If not devel wanted, we make a clean bundle with only
        # file needed to execute
        steps = [
            ("prepare-install-dir",
             [(_("Copy install path"), self._copy_installdir, True),
              (_("Installing bundle files"), self._install_bundle_specific_files, True),
              (_("Make all paths relatives"), self._make_paths_relative, True),
              ]
            ),
            ("generate-tarball",
             [(_("Running AppImageAssistant"), self._generate_bundle, True),
              (_("Generating md5"), self._generate_md5sum, True)
             ]
            ),
            ("clean-install-dir",
             [(_("Clean tmp dirs"), self._clean_tmps, not self.keep_temp)]
            )
        ]

        for step in steps:
            shell.set_logfile_output("%s/%s-bundle-%s.log" % (self.config.logs, self.package.name, step[0]))
            for substep in step[1]:
                m.build_step('1', '1', self.package.name + " linux bundle", substep[0])
                if substep[2] is True:
                    substep[1]()
                else:
                    m.action(_("Step not wanted"))
            shell.close_logfile_output()
