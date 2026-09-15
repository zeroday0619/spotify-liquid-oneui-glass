# Liquid One UI Glass

A light-only Sakura theme for Spotify, combining glass-like surfaces with rounded One UI-inspired controls. It includes custom outline icons, readable playback controls, and optional styling for ivLyrics.

This repository contains the theme source and a local installer. Spotify, Spicetify, ivLyrics, album artwork, and personal Spotify settings are not bundled.

## Compatibility

| Component | Verified configuration |
| --- | --- |
| Desktop rendering | macOS on Apple Silicon |
| Installer | macOS; Debian 12 Linux container with Python 3.13 |
| Spotify | 1.3.0.277 |
| Spicetify | 3.0.0-beta.17 |
| Class map | 1030000 |
| Optional ivLyrics | 6.6.21 local module |

The installer targets Spicetify **v3 modules**, not v2 theme folders. Python 3.9 or newer and an initialized Spicetify v3 installation with the `stdlib` module enabled are required. No Python or npm dependencies are needed. The installer supports Linux and macOS. Windows is not supported. Linux installer behavior is tested; Linux Spotify desktop rendering still requires verification.

Spotify and Spicetify beta updates can change CSS selectors and module formats. Compatibility with other versions is not guaranteed. The theme retains its existing internal module ID, `liquid-glass-local`, so installed settings and module paths remain compatible.

## Install

From a checkout of this repository:

```sh
./install.sh --dry-run
./install.sh
```

The installer validates the local files and Spicetify version, discovers the configuration directory through `spicetify path`, backs up the affected module, registers the theme, and runs `spicetify apply`. Applying restarts Spotify. It does not download software or install dependencies.

To specify the executable or configuration directory:

```sh
./install.sh --spicetify "$HOME/.spicetify/spicetify" --dry-run
./install.sh --config-dir "$HOME/.config/spicetify" --no-apply
spicetify apply
```

Use `--no-apply` to update module files without restarting Spotify. A custom configuration directory must match the CLI's active configuration before automatic apply is allowed. Do not run this installer concurrently with Spicetify package management.

```sh
./install.sh --help
```

### Linux

Run the same installer from your desktop user account:

```sh
spicetify --version
spicetify path
./install.sh --dry-run
./install.sh
```

Use an initialized **Spicetify v3** installation with `stdlib` enabled. The theme installer uses the Spotify paths already configured in Spicetify, so it does not assume `/usr/share/spotify`, `/opt/spotify`, or a macOS application bundle. It does not change system package permissions or run `sudo`.

Configuration selection follows this order:

1. Explicit `--config-dir`.
2. The active configuration reported by `spicetify path`.
3. `$XDG_CONFIG_HOME/spicetify` when `XDG_CONFIG_HOME` is absolute, otherwise `~/.config/spicetify`.

Fallback paths must already contain an initialized v3 configuration. When the CLI cannot confirm the selected path, only `--dry-run` or `--no-apply` is allowed. This prevents applying an unrelated Spicetify configuration.

```sh
./install.sh --config-dir "${XDG_CONFIG_HOME:-$HOME/.config}/spicetify" --no-apply
# After configuring Spicetify to use the intended installation:
spicetify apply
```

For a CLI installed outside `PATH`, pass `--spicetify "$HOME/.spicetify/spicetify"`. Check that Spicetify itself can apply to your Spotify installation before installing the theme.

Spotify packaging matters: upstream documents extra setup for native packages and Flatpak, and states that Snap installations cannot be modified. See [Spicetify's Linux setup notes](https://spicetify.app/docs/getting-started#linux-specific-setup). Those notes may describe v2 configuration commands; this theme specifically requires the v3 module workflow. Flatpak, Snap, NixOS, Wayland, and X11 desktop rendering have not been tested by this project.

Linux uses the system UI font with Noto Sans and Liberation Sans fallbacks when available. No fonts are downloaded or bundled.

### Backups and removal

Backups are stored under `<spicetify-config>/backups/liquid-one-ui-glass/`. Unrelated module entries are preserved. Reinstalling updates the theme while keeping the first installation's restore point.

```sh
./install.sh uninstall --dry-run
./install.sh uninstall
```

Removal restores the module state recorded before the first installation. If the theme was already installed manually, that previous version is restored. Without an installer receipt, removal refuses to alter a manually installed theme. Backups remain available for inspection.

If `spicetify apply` fails, the installer reports the failure. The registered files remain installed; resolve the reported Spicetify issue and run `spicetify apply` again. Restoring module files cannot undo a partially applied Spotify application bundle.

## Appearance

- Sakura pink and pearl surfaces with rose accents.
- Light mode is enforced at the Spotify document root. Native root theme changes are observed and corrected while the module is loaded.
- The **Liquid One UI Glass 설정** button controls tint strength.
- Artwork and lyrics surfaces retain their own contrast treatment.
- ivLyrics is optional and must be installed separately. Its content and preferences are not included.

The root theme lock does not guarantee that every future Spotify component follows light mode. Component-specific styles remain necessary, particularly for image overlays and dynamically loaded panels.

## Development

Edit `theme/`, then run the installer again to copy the updated files into Spicetify. The checkout is not symlinked into the running application.

```sh
node --test tests/*.test.js
python3 -m unittest discover -s tests -p 'test_*.py'
```

Node.js is needed only for the JavaScript checks. Installer tests use temporary configurations and do not modify your Spotify installation. Subprocess tests exercise the shell entry point, paths containing spaces, relative module symlinks, XDG fallback, installation, apply dispatch, and restoration with a local CLI fixture. They do not run the real Spotify client.

The GitHub Actions workflow runs the tests on Ubuntu and macOS with Python 3.9 and the latest Python 3 release. Adding the workflow does not imply a successful hosted CI run.

```text
install.sh                 Shell entry point
install.py                 Installer, backups, and restoration
theme/                    Spicetify v3 module source
tests/                    Isolated installer and theme checks
```

Visual checks on the verified configuration covered home, search, artist and album pages, playlists, playback controls, artist details, credits, concerts, queue, device connection, settings, and ivLyrics. These are representative checks, not a guarantee for every content type or interaction.

## Project status

This is an independent customization project and is not affiliated with Spotify, Apple, or Samsung. Product names describe compatibility and design inspiration.

## License

Licensed under the [MIT License](LICENSE). Copyright (c) 2026 Euiseo Cha.
