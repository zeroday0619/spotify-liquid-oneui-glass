#!/usr/bin/env python3
"""Install the local Spicetify v3 theme without replacing unrelated modules."""
import argparse
import copy
import datetime
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

MODULE = 'liquid-glass-local'
VERSION = '1.0.0'
FILES = tuple('index.js index.css metadata.json spicetify-module.json icons.js icons.css light-mode.js surfaces.css oneui.css sakura.css coverage.css interaction-fixes.css iv-sakura.css player-contrast.css npv-contrast.css npv-details.css regression-contrast.css artist-page-contrast.css settings-contrast.css'.split())


def read_json(path):
    with path.open(encoding='utf-8') as stream:
        return json.load(stream)


def write_json(path, value):
    """Replace a JSON document atomically on the same filesystem."""
    handle, name = tempfile.mkstemp(prefix='.liquid-one-', dir=path.parent)
    try:
        with os.fdopen(handle, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, indent=2)
            stream.write('\n')
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def replace_link(path, target):
    if target is None:
        if path.is_symlink():
            path.unlink()
        return
    temp = path.with_name(path.name + '.liquid-one-tmp')
    if temp.exists() or temp.is_symlink():
        raise ValueError(f'Temporary path already exists: {temp}')
    try:
        temp.symlink_to(target)
        os.replace(temp, path)
    finally:
        if temp.is_symlink():
            temp.unlink()


def validate(config):
    for relative in ('modules', 'store', 'store/' + MODULE, 'backups', 'backups/liquid-one-ui-glass'):
        if (config / relative).is_symlink():
            raise ValueError(f'Refusing symlinked configuration directory: {config / relative}')
    vault_path = config / 'modules/vault.json'
    if not (config / 'config.toml').is_file() or not vault_path.is_file():
        raise ValueError('Initialize Spicetify v3 first: config.toml and modules/vault.json are required.')
    vault = read_json(vault_path)
    modules = vault.get('modules')
    if not isinstance(modules, dict):
        raise ValueError('Invalid modules/vault.json: modules must be an object.')
    if not modules.get('stdlib', {}).get('enabled') or not (config / 'modules/stdlib').is_symlink() or not (config / 'modules/stdlib').is_dir():
        raise ValueError('Enable and install the Spicetify stdlib module first.')
    link = config / 'modules' / MODULE
    target = config / 'store' / MODULE / VERSION
    if link.exists() and not link.is_symlink():
        raise ValueError(f'Refusing to replace a non-symlink: {link}')
    if link.is_symlink() and link.resolve().parent != target.parent.resolve():
        raise ValueError(f'Refusing to replace a foreign module symlink: {link}')
    if target.is_symlink() or (target.exists() and not target.is_dir()):
        raise ValueError(f'Refusing unexpected store path: {target}')
    return vault, link, target


def source_files(source):
    for name in FILES:
        path = source / name
        if not path.is_file() or path.is_symlink():
            raise ValueError(f'Missing or unsafe theme file: {path}')
    metadata = read_json(source / 'metadata.json')
    if metadata.get('name') != MODULE or metadata.get('version') != VERSION:
        raise ValueError('Theme metadata does not match this installer.')


def _operate(config, source, uninstall=False, dry_run=False):
    vault, link, target = validate(config)
    backup_root = config / 'backups/liquid-one-ui-glass'
    receipt_path = backup_root / 'receipt.json'
    receipt = read_json(receipt_path) if receipt_path.exists() else None
    if uninstall and receipt is None:
        raise ValueError('No installer receipt exists; refusing to remove a manually installed theme.')
    if not uninstall:
        source_files(source)
    if receipt:
        baseline = Path(receipt['backup'])
        if baseline.parent != backup_root or not baseline.is_dir():
            raise ValueError('Installer receipt has an invalid backup path.')
    if dry_run:
        print(f'Would {"uninstall" if uninstall else "install"} {MODULE}@{VERSION} in {config}')
        return
    backup_root.mkdir(parents=True, exist_ok=True)
    backup = Path(tempfile.mkdtemp(prefix=datetime.datetime.now().strftime('%Y%m%d-%H%M%S-'), dir=backup_root))
    old_module = copy.deepcopy(vault['modules'].get(MODULE))
    old_link = os.readlink(link) if link.is_symlink() else None
    old_target = target.exists()
    if old_target:
        shutil.copytree(target, backup / 'store', symlinks=True)
    write_json(backup / 'state.json', {'module': old_module, 'link': old_link, 'had_store': old_target})
    shutil.copy2(config / 'modules/vault.json', backup / 'vault.json')
    desired = read_json(baseline / 'state.json') if uninstall else None
    stage = target.with_name(VERSION + '.liquid-one-tmp')
    if stage.exists() or stage.is_symlink():
        raise ValueError(f'Temporary store path already exists: {stage}')
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        if uninstall:
            if desired['had_store']:
                shutil.copytree(baseline / 'store', stage, symlinks=True)
        else:
            stage.mkdir()
            for name in FILES:
                shutil.copy2(source / name, stage / name)
        if target.exists():
            shutil.rmtree(target)
        if stage.exists():
            os.replace(stage, target)
        if uninstall:
            if desired['module'] is None:
                vault['modules'].pop(MODULE, None)
            else:
                vault['modules'][MODULE] = desired['module']
            replace_link(link, desired['link'])
        else:
            module = vault['modules'].setdefault(MODULE, {})
            module.setdefault('v', {})[VERSION] = {'installed': True, 'artifacts': []}
            module['enabled'] = VERSION
            replace_link(link, str(target))
        write_json(config / 'modules/vault.json', vault)
        if uninstall:
            receipt_path.unlink()
        elif receipt is None:
            write_json(receipt_path, {'backup': str(backup)})
    except Exception:
        if target.exists():
            shutil.rmtree(target)
        if old_target:
            shutil.copytree(backup / 'store', target, symlinks=True)
        replace_link(link, old_link)
        original = read_json(backup / 'vault.json')
        write_json(config / 'modules/vault.json', original)
        raise
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    print(f'{"Restored previous theme state" if uninstall else "Installed Liquid One UI Glass"}. Backup: {backup}')


def operate(config, source, uninstall=False, dry_run=False):
    """Serialize installer operations using a lock on the configuration directory."""
    descriptor = os.open(config, os.O_RDONLY)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _operate(config, source, uninstall, dry_run)
    finally:
        os.close(descriptor)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('install', 'uninstall'), nargs='?', default='install')
    parser.add_argument('--config-dir', type=Path, help='Initialized Spicetify configuration directory')
    parser.add_argument('--spicetify', default='spicetify', help='Spicetify executable path')
    parser.add_argument('--dry-run', action='store_true', help='Validate and print changes without writing or applying')
    parser.add_argument('--no-apply', action='store_true', help='Change module files only; run spicetify apply separately')
    args = parser.parse_args(argv)
    try:
        version = subprocess.run([args.spicetify, '--version'], capture_output=True, text=True, check=True)
        if not re.search(r'(?m)^\s*(?:spicetify\s+)?v?3\.\d+\.\d+(?:-[\w.]+)?\s*$', version.stdout + version.stderr):
            raise ValueError('This installer requires Spicetify v3 (including v3 beta); v2 is unsupported.')
        result = subprocess.run([args.spicetify, 'path'], capture_output=True, text=True, check=True)
        output = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', result.stdout + '\n' + result.stderr)
        candidates = []
        for line in output.splitlines():
            match = re.search(r'config (?:root|file):\s*(.+)$', line)
            candidate = Path(match.group(1).strip() if match else line.strip()).expanduser()
            if candidate.is_absolute():
                if candidate.name == 'config.toml':
                    candidate = candidate.parent
                if (candidate / 'config.toml').is_file():
                    candidates.append(candidate.resolve())
        discovered = candidates[0] if len(set(candidates)) == 1 else None
        config = args.config_dir
        if config is None:
            if discovered is None:
                raise ValueError('Cannot discover configuration; pass --config-dir explicitly.')
            config = discovered
        config = config.expanduser().resolve()
        if not args.no_apply and not args.dry_run and config != discovered:
            raise ValueError('The selected directory differs from the CLI configuration. Use --no-apply for an alternate directory.')
        operate(config, Path(__file__).resolve().parent / 'theme', args.action == 'uninstall', args.dry_run)
        if not args.no_apply and not args.dry_run:
            # Apply only after confirming the CLI uses the selected configuration.
            result = subprocess.run([args.spicetify, 'apply'])
            if result.returncode:
                print('Module files were updated, but spicetify apply failed. Fix the reported error and apply again.', file=sys.stderr)
                return result.returncode
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        print(f'Error: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
