%global with_debug 0
%define _unpackaged_files_terminate_build 0

%{?!_pkgdocdir:%global _pkgdocdir %{_docdir}/%{name}-%{version}}

# ARM builds currently break on the Debug builds, so we'll just
# build the standard runtime until that gets sorted out.
%ifarch %{arm} aarch64 %{power64}
%global with_debug 0
%endif

# == Node.js Version ==
%global nodejs_epoch 1
%global nodejs_major 8
%global nodejs_minor 16
%global nodejs_patch 0
%global nodejs_abi %{nodejs_major}.%{nodejs_minor}
%global nodejs_version %{nodejs_major}.%{nodejs_minor}.%{nodejs_patch}
%global nodejs_release 1

# == Bundled Dependency Versions ==
# v8 - from deps/v8/include/v8-version.h
%global v8_major 6
%global v8_minor 2
%global v8_build 414
%global v8_patch 77
# V8 presently breaks ABI at least every x.y release while never bumping SONAME
%global v8_abi %{v8_major}.%{v8_minor}
%global v8_version %{v8_major}.%{v8_minor}.%{v8_build}.%{v8_patch}

# npm - from deps/npm/package.json
%global npm_epoch 1
%global npm_major 6
%global npm_minor 4
%global npm_patch 1
%global npm_version %{npm_major}.%{npm_minor}.%{npm_patch}

# In order to avoid needing to keep incrementing the release version for the
# main package forever, we will just construct one for npm that is guaranteed
# to increment safely. Changing this can only be done during an update when the
# base npm version number is increasing.
%global npm_release %{nodejs_epoch}.%{nodejs_major}.%{nodejs_minor}.%{nodejs_patch}.%{nodejs_release}

# Filter out the NPM bundled dependencies so we aren't providing them
%global __provides_exclude_from ^%{_prefix}/lib/node_modules/npm/.*$
%global __requires_exclude_from ^%{_prefix}/lib/node_modules/npm/.*$


Name: rhoar-nodejs
Epoch: %{nodejs_epoch}
Version: %{nodejs_version}
Release: %{nodejs_release}%{?dist}
Summary: JavaScript runtime
License: MIT and ASL 2.0 and ISC and BSD
Group: Development/Languages
URL: http://nodejs.org/

ExclusiveArch: %{nodejs_arches}

Source0: node-v%{nodejs_version}-rh.tar.gz
Source1: license_xml.js
Source2: license_html.js
Source3: licenses.css

# The native module Requires generator remains in the nodejs SRPM, so it knows
# the nodejs and v8 versions.  The remainder has migrated to the
# nodejs-packaging SRPM.
Source7: nodejs_native.attr

# use system certificates instead of the bundled ones
# modified version of Debian patch:
# http://patch-tracker.debian.org/patch/series/view/nodejs/0.10.26~dfsg1-1/2014_donotinclude_root_certs.patch

BuildRequires: python-devel
BuildRequires: gcc >= 4.8.0
BuildRequires: gcc-c++ >= 4.8.0
BuildRequires: systemtap-sdt-devel

# Use by tests
BuildRequires: procps-ng

#we need ABI virtual provides where SONAMEs aren't enough/not present so deps
#break when binary compatibility is broken
Provides: nodejs(abi) = %{nodejs_abi}
Provides: nodejs(abi%{nodejs_major}) = %{nodejs_abi}
Provides: nodejs(v8-abi) = %{v8_abi}
Provides: nodejs(v8-abi%{v8_major}) = %{v8_abi}

#this corresponds to the "engine" requirement in package.json
Provides: nodejs(engine) = %{nodejs_version}

# Node.js currently has a conflict with the 'node' package in Fedora
# The ham-radio group has agreed to rename their binary for us, but
# in the meantime, we're setting an explicit Conflicts: here
Conflicts: node <= 0.3.2-12

# Node.js is closely tied to the version of v8 that is used with it. It makes
# sense to use the bundled version because upstream consistently breaks ABI
# even in point releases. Node.js upstream has now removed the ability to build
# against a shared system version entirely.
# See https://github.com/nodejs/node/commit/d726a177ed59c37cf5306983ed00ecd858cfbbef
Provides: bundled(v8) = %{v8_version}


%description
Node.js is a platform built on Chrome's JavaScript runtime
for easily building fast, scalable network applications.
Node.js uses an event-driven, non-blocking I/O model that
makes it lightweight and efficient, perfect for data-intensive
real-time applications that run across distributed devices.

%package -n npm
Summary: Node.js Package Manager
Epoch: %{npm_epoch}
Version: %{npm_version}
Release: %{npm_release}%{?dist}

Obsoletes: npm < 0:3.5.4-6
Provides: npm = %{npm_epoch}:%{npm_version}
Requires: rhoar-nodejs = %{epoch}:%{nodejs_version}-%{nodejs_release}%{?dist}

# Do not add epoch to the virtual NPM provides or it will break
# the automatic dependency-generation script.
Provides: npm(npm) = %{npm_version}

%description -n npm
npm is a package manager for node.js. You can use it to install and publish
your node programs. It manages dependencies and does other cool stuff.

%package docs
Summary: Node.js API documentation
Group: Documentation
BuildArch: noarch

# We don't require that the main package be installed to
# use the docs, but if it is installed, make sure the
# version always matches
Conflicts: %{name} > %{epoch}:%{nodejs_version}-%{nodejs_release}%{?dist}
Conflicts: %{name} < %{epoch}:%{nodejs_version}-%{nodejs_release}%{?dist}

%description docs
The API documentation for the Node.js JavaScript runtime.


%prep
%setup -q -n node-v%{nodejs_version}-rh

%build
# build with debugging symbols and add defines from libuv (#892601)
# Node's v8 breaks with GCC 6 because of incorrect usage of methods on
# NULL objects. We need to pass -fno-delete-null-pointer-checks
export CFLAGS='%{optflags} -g \
               -D_LARGEFILE_SOURCE \
               -D_FILE_OFFSET_BITS=64 \
               -DZLIB_CONST \
               -fno-delete-null-pointer-checks'
export CXXFLAGS='%{optflags} -g \
                 -D_LARGEFILE_SOURCE \
                 -D_FILE_OFFSET_BITS=64 \
                 -DZLIB_CONST \
                 -fno-delete-null-pointer-checks'

# Explicit new lines in C(XX)FLAGS can break naive build scripts
export CFLAGS="$(echo ${CFLAGS} | tr '\n\\' '  ')"
export CXXFLAGS="$(echo ${CXXFLAGS} | tr '\n\\' '  ')"

git config user.email "daniel.bevenius@gmail.com"
git config user.name "Daniel Bevenius"
# Generate the headers tar-ball
make tar-headers

./configure --prefix=%{_prefix} \
           --with-dtrace \
           --openssl-system-ca-path=/etc/pki/tls/certs/ca-bundle.crt

%if %{?with_debug} == 1
# Setting BUILDTYPE=Debug builds both release and debug binaries
make V=0 BUILDTYPE=Debug %{?_smp_mflags} test-only
%else
make V=0 BUILDTYPE=Release %{?_smp_mflags} test-only
%endif

%install

./tools/install.py install %{buildroot} %{_prefix}

# Set the binary permissions properly
chmod 0755 %{buildroot}/%{_bindir}/node

%if %{?with_debug} == 1
# Install the debug binary and set its permissions
install -Dpm0755 out/Debug/node %{buildroot}/%{_bindir}/node_g
%endif

# own the sitelib directory
mkdir -p %{buildroot}%{_prefix}/lib/node_modules

# ensure Requires are added to every native module that match the Provides from
# the nodejs build in the buildroot
install -Dpm0644 %{SOURCE7} %{buildroot}%{_rpmconfigdir}/fileattrs/nodejs_native.attr
cat << EOF > %{buildroot}%{_rpmconfigdir}/nodejs_native.req
#!/bin/sh
echo 'nodejs(abi%{nodejs_major}) >= %nodejs_abi'
echo 'nodejs(v8-abi%{v8_major}) >= %v8_abi'
EOF
chmod 0755 %{buildroot}%{_rpmconfigdir}/nodejs_native.req

#install documentation
mkdir -p %{buildroot}%{_pkgdocdir}/html
cp -pr doc/* %{buildroot}%{_pkgdocdir}/html
rm -f %{buildroot}%{_pkgdocdir}/html/nodejs.1
cp %{SOURCE3} licenses.css

#node-gyp needs common.gypi too
mkdir -p %{buildroot}%{_datadir}/node
cp -p common.gypi %{buildroot}%{_datadir}/node

cp -p node-v%{nodejs_version}-headers.tar.gz %{buildroot}%{_datadir}/node

# Install the GDB init and lldbinit tools into the documentation directory
mv %{buildroot}/%{_datadir}/doc/node/gdbinit %{buildroot}/%{_pkgdocdir}/gdbinit
mv %{buildroot}/%{_datadir}/doc/node/lldbinit %{buildroot}/%{_pkgdocdir}/lldbinit
mv %{buildroot}/%{_datadir}/doc/node/lldb_commands.py %{buildroot}/%{_pkgdocdir}/lldb_commands.py

#install -n npm

# Since the old version of NPM was unbundled, there are a lot of symlinks in
# it's node_modules directory. We need to keep these as symlinks to ensure we
# can backtrack on this if we decide to.

# Rename the npm node_modules directory to node_modules.bundled
mv %{buildroot}/%{_prefix}/lib/node_modules/npm/node_modules \
   %{buildroot}/%{_prefix}/lib/node_modules/npm/node_modules.bundled

# Recreate all the symlinks
mkdir -p %{buildroot}/%{_prefix}/lib/node_modules/npm/node_modules
FILES=%{buildroot}/%{_prefix}/lib/node_modules/npm/node_modules.bundled/*
for f in $FILES
do
  module=`basename $f`
  ln -s ../node_modules.bundled/$module %{buildroot}%{_prefix}/lib/node_modules/npm/node_modules/$module
done

# install NPM docs to mandir
mkdir -p %{buildroot}%{_mandir} \
         %{buildroot}%{_pkgdocdir}/npm

cp -pr deps/npm/man/* %{buildroot}%{_mandir}/
rm -rf %{buildroot}%{_prefix}/lib/node_modules/npm/man
ln -sf %{_mandir}  %{buildroot}%{_prefix}/lib/node_modules/npm/man

# Install Markdown and HTML documentation to %{_pkgdocdir}
cp -pr deps/npm/html deps/npm/doc %{buildroot}%{_pkgdocdir}/npm/
rm -rf %{buildroot}%{_prefix}/lib/node_modules/npm/html \
       %{buildroot}%{_prefix}/lib/node_modules/npm/doc

ln -sf %{_pkgdocdir} %{buildroot}%{_prefix}/lib/node_modules/npm/html
ln -sf %{_pkgdocdir}/npm/html %{buildroot}%{_prefix}/lib/node_modules/npm/doc

%check
# Fail the build if the versions don't match
%{buildroot}/%{_bindir}/node -e "require('assert').equal(process.versions.node, '%{nodejs_version}')"
%{buildroot}/%{_bindir}/node -e "require('assert').equal(process.versions.v8, '%{v8_version}')"

# Ensure we have npm and that the version matches
NODE_PATH=%{buildroot}%{_prefix}/lib/node_modules %{buildroot}/%{_bindir}/node -e "require(\"assert\").equal(require(\"npm\").version, '%{npm_version}')"

# Generate license.xml and license.html
%{buildroot}/%{_bindir}/node %{SOURCE1} 'node' '%{nodejs_version}' > license.xml
%{buildroot}/%{_bindir}/node %{SOURCE2} 'node' > license.html

%files
%{_bindir}/node
%dir %{_prefix}/lib/node_modules
%dir %{_datadir}/node
%dir %{_datadir}/systemtap
%dir %{_datadir}/systemtap/tapset
%{_datadir}/systemtap/tapset/node.stp
%{_datadir}/node/node-v%{nodejs_version}-headers.tar.gz
%dir %{_usr}/lib/dtrace
%{_usr}/lib/dtrace/node.d
%{_rpmconfigdir}/fileattrs/nodejs_native.attr
%{_rpmconfigdir}/nodejs_native.req
%license LICENSE
%license license.xml
%license license.html
%license licenses.css
%doc AUTHORS CHANGELOG.md COLLABORATOR_GUIDE.md GOVERNANCE.md README.md
%doc %{_mandir}/man*/*



%files -n npm
%{_bindir}/npm
%{_bindir}/npx
%{_prefix}/lib/node_modules/npm
%ghost %{_sysconfdir}/npmrc
%ghost %{_sysconfdir}/npmignore

%files docs
%dir %{_pkgdocdir}
%{_pkgdocdir}/html
%{_pkgdocdir}/npm/html
%{_pkgdocdir}/npm/doc

%changelog
* Wed Apr 16 2019 Lucas Holmquist <lholmqui@redhat.com> - 8.16.0
- Updated to use 8.15.1
* Wed Mar 6 2019 Helio Frota <hesilva@redhat.com> - 8.15.1
- Updated to use 8.15.1
* Wed Dec 26 2018 Helio Frota <hesilva@redhat.com> - 8.15.0
- Updated to use 8.15.0
* Tue Dec 18 2018 Helio Frota <hesilva@redhat.com> - 8.14.1
- Updated to use 8.14.1
* Wed Nov 28 2018 Helio Frota <hesilva@redhat.com> - 8.14.0
- Updated to use 8.14.0
* Wed Nov 21 2018 Helio Frota <hesilva@redhat.com> - 8.13.0
- Updated to use 8.13.0
* Wed Sep 19 2018 Daniel Bevenius <daniel.bevenius@gmail.com> - 8.12.0
- Updated to use 8.12.0
* Thu Aug 16 2018 Helio Frota <hesilva@redhat.com> - 8.11.4
- Updated to use 8.11.4
* Wed Jun 13 2018 Helio Frota <hesilva@redhat.com> - 8.11.3
- Updated to use 8.11.3
* Thu Mar 29 2018 Daniel Bevenius <dbeveniu@redhat.com> - 8.11.0
- Updated to use 8.11.0
* Wed Mar 7 2018 Daniel Bevenius <dbeveniu@redhat.com> - 8.10.0
- Updated to use 8.10.0
* Sat Jan 27 2018 Daniel Bevenius <dbeveniu@redhat.com> - 8.9.4-2
- Removed devel package
* Mon Jan 8 2018 Daniel Bevenius <dbeveniu@redhat.com> - 8.9.4-1
- Updated to use version 8.9.4
* Wed Dec 13 2017 Daniel Bevenius <dbeveniu@redhat.com> - 8.9.3-1
- Updated to use version 8.9.3
* Tue Dec 12 2017 Daniel Bevenius <dbeveniu@redhat.com> - 8.9.2-1
- Updated to use version 8.9.2
* Wed Nov 1 2017 Daniel Bevenius <dbeveniu@redhat.com> - 8.9.0-1
- Updated to use version 8.9.0
* Fri Oct 20 2017 Andrea Vibelli <avibelli@redhat.com> - 8.7.0-1
- Added procps-ng into build requirements list, to fix V8 related tests
- Added patch to manage DNS lookup failures due to no internet connection
- First build for RHOAR Node runtime
