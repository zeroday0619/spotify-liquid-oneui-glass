"""Run the shell installer against a local CLI fixture on POSIX systems."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from test_install import installer

ROOT = Path(__file__).resolve().parents[1]


class PlatformInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='liquid one ')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.config = self.base / 'xdg config/spicetify'
        (self.config / 'modules').mkdir(parents=True)
        (self.config / 'config.toml').write_text('')
        stdlib = self.config / 'store/stdlib/1.0.0'
        stdlib.mkdir(parents=True)
        (self.config / 'modules/stdlib').symlink_to('../store/stdlib/1.0.0')
        self.vault = {'modules': {'stdlib': {'enabled': '1.0.0'}, 'other': {'enabled': '2'}}}
        (self.config / 'modules/vault.json').write_text(json.dumps(self.vault))
        self.cli = self.base / 'spicetify fixture'
        self.log = self.base / 'apply.log'
        self.cli.write_text(f'''#!{sys.executable}
import os
import sys
from pathlib import Path
if sys.argv[1] == '--version':
    print('spicetify 3.0.0-beta.17')
elif sys.argv[1] == 'path':
    if os.environ.get('LIQUID_TEST_PATH_FAIL'):
        sys.exit(1)
    print('INFO config root: ' + os.environ['LIQUID_TEST_CONFIG'], file=sys.stderr)
elif sys.argv[1] == 'apply':
    Path(os.environ['LIQUID_TEST_LOG']).write_text('apply')
else:
    sys.exit(2)
''')
        self.cli.chmod(0o755)
        self.env = dict(os.environ, XDG_CONFIG_HOME=str(self.config.parent),
                        LIQUID_TEST_CONFIG=str(self.config), LIQUID_TEST_LOG=str(self.log))

    def run_cli(self, *args, **env):
        return subprocess.run(['sh', str(ROOT / 'install.sh'), '--spicetify', str(self.cli), *args],
                              cwd=self.base, env=dict(self.env, **env), text=True, capture_output=True)

    def test_shell_install_apply_and_restore_with_spaces_and_relative_links(self):
        self.assertEqual(self.run_cli('--dry-run').returncode, 0)
        self.assertFalse((self.config / 'backups').exists())
        self.assertFalse(self.log.exists())
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.log.read_text(), 'apply')
        module = self.config / 'modules' / installer.MODULE
        self.assertEqual((module / 'LICENSE').read_bytes(), (ROOT / 'LICENSE').read_bytes())
        self.assertEqual((module / 'index.js').read_bytes(), (ROOT / 'theme/index.js').read_bytes())
        result = self.run_cli('uninstall', '--no-apply')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(module.exists())
        self.assertEqual(json.loads((self.config / 'modules/vault.json').read_text()), self.vault)

    def test_xdg_fallback_allows_no_apply_but_not_unverified_apply(self):
        result = self.run_cli(LIQUID_TEST_PATH_FAIL='1')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.config / 'backups').exists())
        result = self.run_cli('--no-apply', LIQUID_TEST_PATH_FAIL='1')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.log.exists())

    def test_explicit_config_works_when_cli_path_fails(self):
        result = self.run_cli('--config-dir', str(self.config), '--no-apply',
                              XDG_CONFIG_HOME=str(self.base / 'wrong'), LIQUID_TEST_PATH_FAIL='1')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.config / 'modules' / installer.MODULE).is_dir())

    def test_cli_path_takes_precedence_over_xdg(self):
        result = self.run_cli('--no-apply', XDG_CONFIG_HOME=str(self.base / 'wrong'))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.config / 'modules' / installer.MODULE).is_dir())

    def test_default_config_ignores_relative_xdg(self):
        with patch.dict(os.environ, {'XDG_CONFIG_HOME': 'relative'}), patch.object(Path, 'home', return_value=self.base):
            self.assertEqual(installer.default_config(), self.base / '.config/spicetify')


if __name__ == '__main__':
    unittest.main()
