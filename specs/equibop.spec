# Prebuilt foreign binary: no build-id or debuginfo can be produced, so the
# debug package is disabled. The binary ships as-is from the release RPM.
%global debug_package %{nil}

# NOTE (verified by local rpmbuild of 3.3.0): %%global debug_package %%{nil}
# is what makes the default ELF-rewriting brp hooks run, not what skips them
# — Fedora's %%__os_install_post gates brp-strip / brp-strip-comment-note on
# %%__debug_package being *undefined*. With them in place every ELF file in
# the bundle loses its .comment section (equibop shrank by 528 bytes,
# libffmpeg.so by 248, likewise the other seven ELF files), i.e. the packaged
# payload stops being byte-identical to the upstream RPM.
# brp-strip-lto and brp-strip-static-archive are not gated at all. Empty all
# four so the payload matches the upstream blob bit for bit. Set them to
# %%{nil} rather than %%undefine'ing them: with rpm 6.0.2 %%undefine does not
# mask brp-strip / brp-strip-comment-note (verified — the hooks still ran,
# while %%undefine on the lto one did take effect).
%global __brp_strip %{nil}
%global __brp_strip_comment_note %{nil}
%global __brp_strip_lto %{nil}
%global __brp_strip_static_archive %{nil}

# add-determinism's brp hook (add-det) would regenerate /usr/lib/.build-id
# links from the blob's ELF build-id notes and otherwise normalize the
# payload. The blob must ship byte-identical, so unset the hook.
%undefine __brp_add_determinism

# NOTE (verified by local rpmbuild of 3.3.0): the unpacked bundle under
# /opt/Equibop carries SONAMEs (libEGL, libGLESv2, libffmpeg, libvk_swiftshader,
# libvulkan.so.1), so the dependency generator would advertise them as system
# providers. They are private to the bundle (resolved via the $ORIGIN RPATH on
# the equibop binary, not the system loader path), so suppress Provides from
# /opt — same approach as the bitwarden rewrap. The upstream RPM ships the
# same clean Provides, so this keeps the rewrap at parity.
%global __provides_exclude_from ^/opt/Equibop/
# The equibop binary links the bundled libffmpeg.so (found via its $ORIGIN
# RPATH). Nothing in Fedora provides it, and the bundle satisfies it
# internally, so exclude it. The generated require string carries the arch
# qualifier (libffmpeg.so()(64bit)), hence the prefix match without $.
# Every other DT_NEEDED entry is a system library and stays auto-detected.
%global __requires_exclude ^libffmpeg\.so

Name:           equibop
Version:        3.3.0
Release:        %autorelease
Summary:        A snappy Discord desktop client
License:        GPL-3.0-or-later
URL:            https://github.com/Equicord/Equibop
ExclusiveArch:  x86_64 aarch64

# Upstream publishes one RPM per arch with different filenames:
# equibop-<version>.x86_64.rpm and equibop-<version>.aarch64.rpm. Both are
# listed unconditionally: a %ifarch-conditional Source would put only the
# SRPM-building host's RPM into the SRPM, and COPR builds every enabled
# chroot from that single SRPM — the aarch64 chroot would then fail %prep
# with "Bad file: .../equibop-<version>.aarch64.rpm". Carrying both keeps
# the SRPM self-contained for either chroot; %prep unpacks the one matching
# the build arch (upstream_rpm below).
Source0:        https://github.com/Equicord/Equibop/releases/download/v%{version}/equibop-%{version}.x86_64.rpm
Source1:        https://github.com/Equicord/Equibop/releases/download/v%{version}/equibop-%{version}.aarch64.rpm
# Arch -> bundled upstream RPM. ExclusiveArch below restricts the build to
# exactly these two, so upstream_rpm is always defined.
%ifarch x86_64
%global upstream_rpm %{SOURCE0}
%endif
%ifarch aarch64
%global upstream_rpm %{SOURCE1}
%endif
# Upstream prebuilt RPMs ship no GPL text (only Electron/Chromium notices
# under /opt). spectool fetches LICENSE for the exact version being
# packaged from the release tag; a failed fetch fails the build, so the
# packaged license always matches the packaged version.
Source2:        https://raw.githubusercontent.com/Equicord/Equibop/v%{version}/LICENSE
# Upstream publishes org.equicord.equibop.metainfo.xml, but its <launchable>
# names org.equicord.equibop.desktop while the RPM ships equibop.desktop,
# and its screenshots point at remote URLs. This repo ships a curated file
# under the same RDNS id with the launchable fixed to the shipped desktop
# file; CI patches the <release> version/date on each new upstream release.
Source3:        org.equicord.equibop.metainfo.xml

BuildRequires:  desktop-file-utils
BuildRequires:  appstream
BuildRequires:  cpio

# Runtime-only deps the ELF dependency generator cannot see. Everything
# linked (gtk3, nss, ...) is auto-detected from DT_NEEDED and deliberately
# not duplicated here:
# - xdg-utils, libnotify, libXScrnSaver: declared by the upstream RPM; not
#   in any DT_NEEDED (xdg-open shell-outs, indirect notification/idle
#   loads), kept at parity so behavior matches upstream.
# - at-spi2-core: declared by the upstream RPM; kept at parity.
# - (libXtst or libXtst6), (libuuid or libuuid1): upstream-declared with
#   distro alternatives; Fedora satisfies them via libXtst and libuuid.
Requires:       xdg-utils
Requires:       libnotify
Requires:       libXScrnSaver
Requires:       at-spi2-core
Requires:       (libXtst or libXtst6)
Requires:       (libuuid or libuuid1)

%description
Equibop is a custom Discord desktop client aiming to give you better
performance and a range of useful features. It ships Equicord
preinstalled, with Linux screen sharing, Wayland support, and Discord
telemetry blocked out of the box. This package rewraps the upstream
prebuilt Linux RPM for Fedora (COPR only).

%prep
rpm2cpio %{upstream_rpm} | cpio -idmu
cp %{SOURCE2} LICENSE

%build
# Nothing to compile: the prebuilt upstream binary is unpacked in %%prep.
# The section exists so rpm's build hooks (e.g. macro-injected steps) run.

%install
cp -a opt %{buildroot}/
cp -a usr %{buildroot}/
install -Dm0644 %{SOURCE3} %{buildroot}%{_metainfodir}/org.equicord.equibop.metainfo.xml
# Upstream ships no /usr/bin entry (Exec= points at /opt directly). Add one
# symlink so `equibop` is on PATH. The /opt/Equibop/equibop launcher takes no
# path-relative arguments (Exec=/opt/Equibop/equibop %U with an absolute
# path), so launching via the symlink behaves identically. The blob itself
# is untouched; this symlink is the single documented delta.
install -d %{buildroot}%{_bindir}
ln -s /opt/Equibop/equibop %{buildroot}%{_bindir}/equibop

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/equibop.desktop
appstreamcli validate --no-net %{buildroot}%{_metainfodir}/org.equicord.equibop.metainfo.xml

%files
%license LICENSE
%{_bindir}/equibop
/opt/Equibop/
%{_datadir}/applications/equibop.desktop
%{_datadir}/icons/hicolor/scalable/apps/equibop.svg
%{_metainfodir}/org.equicord.equibop.metainfo.xml
# Release is %%autorelease. COPR builds this repo from an uploaded SRPM, where
# rpm's plain %%autorelease fallback applies: the release is a literal 1 plus
# the chroot's dist tag, NOT the changelog entry count (verified against the
# published builds: iloader's 2.3.3-1 was built from a spec with three
# changelog entries, and the only unique NVRs any of these projects ever
# published came from the CI's force_build path). A %%changelog entry therefore
# documents a spec change but does not on its own give an already-built
# upstream version a new NVR — publish it with the force_build workflow input,
# which rewrites Release to %%{autorelease}.f<run_id> (a unique, higher
# release), exactly as the earlier forced builds in these projects did.

%changelog
* Sat Sep 12 2026 Anudeep D <anudeepd2@gmail.com> - 3.3.0-1
- Initial Fedora repackaging of upstream prebuilt RPM (x86_64 + aarch64)
