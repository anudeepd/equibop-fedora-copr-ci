# equibop-fedora-copr-ci

[Equibop](https://github.com/Equicord/Equibop) is a custom Discord desktop client with Equicord preinstalled, Linux screen sharing, Wayland support, and Discord telemetry blocked out of the box.

This repo packages Equibop for Fedora by rewrapping the upstream prebuilt Linux RPMs (`equibop-3.3.0.x86_64.rpm` / `equibop-3.3.0.aarch64.rpm`) with a Fedora spec. Both `x86_64` and `aarch64` are supported, matching upstream's prebuilt release artifacts. A GitHub Actions workflow runs daily at 12AM UTC to check the latest release from https://github.com/Equicord/Equibop and rebuilds COPR only when a new version is published. Each downloaded RPM is verified against the sha512 published for that asset in the release's `latest-linux.yml` (x86_64) / `latest-linux-arm64.yml` (aarch64) before submission.

The COPR project repository is available from: https://copr.fedorainfracloud.org/coprs/anudeepd/equibop

## Packaging compliance

This package is distributed via COPR only. It rewraps the upstream prebuilt
binary RPMs, so it is **not eligible for the official Fedora repositories**:
the Fedora Packaging Guidelines require all binaries to be built from source
in the Fedora build system, and this repo intentionally ships the upstream
blob as-is (see `specs/equibop.spec`).

Everything else follows the guidelines:

- `ExclusiveArch: x86_64 aarch64` — matches upstream's prebuilt artifacts.
  Both upstream RPMs are declared as `Source0`/`Source1` unconditionally so
  the SRPM carries a payload for either arch, and `%ifarch` selects which one
  `%prep` unpacks. (An arch-conditional source would put only the SRPM
  building host's RPM into the SRPM, and COPR builds every enabled chroot
  from that one SRPM — the aarch64 chroot would then fail `%prep` with
  `Bad file: .../equibop-<version>.aarch64.rpm`.)
- `%build` present (empty — nothing to compile) so rpm's build hooks run.
- `%check` runs `desktop-file-validate` and `appstreamcli validate` on the
  packaged files inside the build.
- `rpmlint` runs in CI on the built RPMs (both arches); every flagged pattern is
  inherent to rewrapping the Electron blob (private libs under `/opt`, required
  `$ORIGIN` runpaths, unstripped prebuilt binaries, non-setuid chrome-sandbox
  tripping the setgroups pattern, Chromium's legacy gethostbyname call,
  upstream-declared lib deps invisible to the generator, dictionary misses,
  GUI app without man page, docs not bundled by design, desktop file pointing
  at a symlinked binary) and is filtered in `rpmlintrc` with per-filter
  rationales.
- `%{_bindir}`, `%{_datadir}`, `%{_metainfodir}` macros used in `%files`.
- License provenance: the `LICENSE` text is fetched from the upstream
  release tag by `spectool` (the prebuilt RPM ships none); a fetch failure
  fails the build, so the packaged license always matches the packaged
  version. `License: GPL-3.0-or-later` (SPDX) matches upstream `package.json`
  (`GPL-3.0-or-later`) and the release metainfo (`GPL-3.0-or-later`).
- `%global debug_package %{nil}` with an explicit rationale: the prebuilt
  foreign binary cannot produce debuginfo, so the debug package is meaningless
  for a rewrap. Note that this is what *enables* Fedora's ELF-rewriting brp
  hooks rather than skipping them: `%__os_install_post` gates `brp-strip` and
  `brp-strip-comment-note` on `%__debug_package` being undefined, and with
  them active every ELF file in the bundle loses its `.comment` section
  (verified: 528 bytes off `equibop`, 248 off `libffmpeg.so`, … for all nine
  ELF files). `brp-strip-lto` and `brp-strip-static-archive` are not gated at
  all. All four hooks plus `add-det` are therefore emptied in the spec, so the
  payload ships byte-identical — and the RPM build test workflow diffs the
  packaged `/opt/Equibop` tree against the upstream RPM payload to keep it
  that way.
- The bundled Electron libs under `/opt/Equibop` carry SONAMEs, so the
  dependency generator would advertise them as system providers. They are
  private to the bundle (resolved via `$ORIGIN`, not the system loader path),
  so `Provides` from `/opt` is suppressed and the internally-satisfied
  `libffmpeg.so` requirement is excluded — same approach as the bitwarden
  rewrap, keeping the rewrap at parity with the upstream RPM's clean Provides.
- Upstream publishes `org.equicord.equibop.metainfo.xml`, but its
  `<launchable>` names `org.equicord.equibop.desktop` while the RPM ships
  `equibop.desktop`, so this repo ships a curated file under the same RDNS id
  with the launchable fixed to the shipped desktop file (remote screenshots
  dropped). The upstream desktop file and `equibop.svg` icon are kept as-is.
- Only explicit runtime deps are the upstream-declared ones invisible to the
  ELF generator (`xdg-utils`, `libnotify`, `libXScrnSaver`, `at-spi2-core`,
  `libXtst`/`libuuid` alternatives). Library deps (gtk3, nss, …) are
  auto-detected from `DT_NEEDED`. No network access inside the buildroot.
- One minimal, documented transformation: a `/usr/bin/equibop` symlink
  pointing at `/opt/Equibop/equibop` (upstream ships no `/usr/bin` entry;
  `Exec=` uses the absolute `/opt` path, so behavior is identical).
- Both downloaded RPMs are verified against the sha512 values published in
  the upstream release's `latest-linux.yml` / `latest-linux-arm64.yml`
  (same-origin integrity: guards truncated/mismatched downloads; upstream
  publishes no detached signatures) before submission to COPR.

# Instructions

Enable the COPR repository then install the package.

<pre>
sudo dnf copr enable anudeepd/equibop
sudo dnf install equibop
</pre>

## Credits

Pattern and workflow structure adapted from
[anudeepd/bitwarden-fedora-copr-ci](https://github.com/anudeepd/bitwarden-fedora-copr-ci)
(which itself descends from
[anudeepd/iloader-fedora-copr-ci](https://github.com/anudeepd/iloader-fedora-copr-ci))
— thanks for the clean reference implementation.

<h3> COPR build status </h3>

[![Copr build status](https://copr.fedorainfracloud.org/coprs/anudeepd/equibop/package/equibop/status_image/last_build.png)](https://copr.fedorainfracloud.org/coprs/anudeepd/equibop/package/equibop/)

<h3> GitHub action workflow status </h3>

[![equibop Fedora COPR CI](https://github.com/anudeepd/equibop-fedora-copr-ci/actions/workflows/equibop-ci.yml/badge.svg)](https://github.com/anudeepd/equibop-fedora-copr-ci/actions/workflows/equibop-ci.yml)

## Latest version
<a href="https://github.com/Equicord/Equibop/releases">
  <img src="https://img.shields.io/github/v/release/Equicord/Equibop" alt="equibop latest release">
</a>
