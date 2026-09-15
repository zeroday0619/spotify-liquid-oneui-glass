"""Exercise module changes in isolated configuration directories."""
import importlib.util
import json
from pathlib import Path
import tempfile
import subprocess
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('installer', ROOT / 'install.py')
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.config = Path(self.temp.name) / 'config'
        (self.config / 'modules').mkdir(parents=True)
        (self.config / 'config.toml').write_text('')
        stdlib = self.config / 'store/stdlib/1.0.0'
        stdlib.mkdir(parents=True)
        (self.config / 'modules/stdlib').symlink_to(stdlib)
        self.vault = {'modules': {'stdlib': {'enabled': '1.0.0'}, 'other': {'enabled': '2', 'custom': True}}}
        installer.write_json(self.config / 'modules/vault.json', self.vault)
        self.source = Path(self.temp.name) / 'theme'
        self.source.mkdir()
        for name in installer.FILES:
            (self.source / name).write_text('{}' if name.endswith('.json') else 'test')
        installer.write_json(self.source / 'metadata.json', {'name': installer.MODULE, 'version': installer.VERSION})
        self.target = self.config / 'store' / installer.MODULE / installer.VERSION
        self.link = self.config / 'modules' / installer.MODULE

    def run_install(self, **options):
        installer.operate(self.config, self.source, **options)

    def test_install_repeat_uninstall_preserves_other_modules(self):
        self.run_install()
        self.run_install()
        vault = installer.read_json(self.config / 'modules/vault.json')
        self.assertEqual(vault['modules']['other'], self.vault['modules']['other'])
        self.assertEqual(set(p.name for p in self.target.iterdir()), set(installer.FILES))
        self.run_install(uninstall=True)
        self.assertFalse(self.link.is_symlink())
        self.assertFalse(self.target.exists())
        self.assertEqual(installer.read_json(self.config / 'modules/vault.json'), self.vault)

    def test_uninstall_restores_previous_theme(self):
        self.target.mkdir(parents=True)
        (self.target / 'custom.css').write_text('old')
        self.link.symlink_to(self.target)
        self.vault['modules'][installer.MODULE] = {'enabled': '1.0.0', 'v': {'1.0.0': {'custom': True}}}
        installer.write_json(self.config / 'modules/vault.json', self.vault)
        self.run_install()
        self.run_install()
        self.run_install(uninstall=True)
        self.assertEqual((self.target / 'custom.css').read_text(), 'old')
        self.assertEqual(installer.read_json(self.config / 'modules/vault.json'), self.vault)
        self.assertEqual(self.link.resolve(), self.target.resolve())

    def test_dry_run_has_no_writes(self):
        before = set(self.config.rglob('*'))
        self.run_install(dry_run=True)
        self.assertEqual(set(self.config.rglob('*')), before)

    def test_refuses_foreign_link(self):
        self.link.symlink_to(self.source)
        with self.assertRaisesRegex(ValueError, 'foreign'):
            self.run_install()

    def test_refuses_regular_module_directory(self):
        self.link.mkdir()
        with self.assertRaisesRegex(ValueError, 'non-symlink'):
            self.run_install()

    def test_refuses_missing_file_and_unowned_uninstall(self):
        (self.source / 'index.js').unlink()
        with self.assertRaises(ValueError):
            self.run_install()
        with self.assertRaisesRegex(ValueError, 'receipt'):
            self.run_install(uninstall=True)

    def test_rolls_back_failed_copy(self):
        self.target.mkdir(parents=True)
        (self.target / 'old.css').write_text('old')
        self.link.symlink_to(self.target)
        original = installer.shutil.copy2
        def fail(source, target, *args, **kwargs):
            if Path(source) == self.source / 'index.js':
                raise OSError('simulated copy failure')
            return original(source, target, *args, **kwargs)
        with patch.object(installer.shutil, 'copy2', side_effect=fail):
            with self.assertRaises(OSError):
                self.run_install()
        self.assertEqual((self.target / 'old.css').read_text(), 'old')
        self.assertEqual(installer.read_json(self.config / 'modules/vault.json'), self.vault)
        self.assertEqual(self.link.resolve(), self.target.resolve())

    def test_symlinked_store_parent_is_rejected(self):
        foreign = Path(self.temp.name) / 'foreign'
        foreign.mkdir()
        (self.config / 'store' / installer.MODULE).symlink_to(foreign)
        with self.assertRaisesRegex(ValueError, 'symlinked'):
            self.run_install()
        self.assertEqual(list(foreign.iterdir()), [])

    def test_failed_vault_replace_restores_files(self):
        self.run_install()
        (self.target / 'index.css').write_text('before')
        original = installer.write_json
        failed = False
        def fail(path, value):
            nonlocal failed
            if path == self.config / 'modules/vault.json' and not failed:
                failed = True
                raise OSError('simulated vault failure')
            return original(path, value)
        with patch.object(installer, 'write_json', side_effect=fail):
            with self.assertRaises(OSError):
                self.run_install()
        self.assertEqual((self.target / 'index.css').read_text(), 'before')
        self.assertEqual(self.link.resolve(), self.target.resolve())

    def test_uninstall_preserves_later_unrelated_updates(self):
        self.run_install()
        vault = installer.read_json(self.config / 'modules/vault.json')
        vault['modules']['other']['enabled'] = 'new-version'
        installer.write_json(self.config / 'modules/vault.json', vault)
        self.run_install(uninstall=True)
        self.assertEqual(installer.read_json(self.config / 'modules/vault.json')['modules']['other']['enabled'], 'new-version')

    def test_cli_discovers_logged_config_and_reports_apply_failure(self):
        def command(args, **kwargs):
            if args[-1] == '--version':
                return subprocess.CompletedProcess(args, 0, 'spicetify 3.0.0-beta.17\n', '')
            if args[-1] == 'path':
                return subprocess.CompletedProcess(args, 0, '', f'\x1b[32m INFO config root: {self.config}\x1b[0m\n INFO config file: {self.config}/config.toml\n')
            return subprocess.CompletedProcess(args, 7)
        with patch.object(installer.subprocess, 'run', side_effect=command), patch.object(installer, 'operate') as operation:
            self.assertEqual(installer.main([]), 7)
            self.assertEqual(operation.call_args.args[0], self.config.resolve())

    def test_cli_rejects_v2_before_mutation(self):
        result = subprocess.CompletedProcess([], 0, 'spicetify 2.43.0\n', '')
        with patch.object(installer.subprocess, 'run', return_value=result), patch.object(installer, 'operate') as operation:
            self.assertEqual(installer.main(['--config-dir', str(self.config)]), 1)
            operation.assert_not_called()

    def test_cli_refuses_apply_to_different_config(self):
        results = [subprocess.CompletedProcess([], 0, 'spicetify 3.0.0-beta.17\n', ''), subprocess.CompletedProcess([], 0, 'INFO config root: /not-the-selected-config\n', '')]
        with patch.object(installer.subprocess, 'run', side_effect=results), patch.object(installer, 'operate') as operation:
            self.assertEqual(installer.main(['--config-dir', str(self.config)]), 1)
            operation.assert_not_called()


if __name__ == '__main__':
    unittest.main()
