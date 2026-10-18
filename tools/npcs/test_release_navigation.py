"""Release preflight must execute the immutable candidate, not dirty local files."""
from pathlib import Path
import importlib.util
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[2]/'server/deploy/release.py'
spec = importlib.util.spec_from_file_location('npc_release', SOURCE)
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseNavigationTest(unittest.TestCase):
    def test_candidate_isolated_and_failure_propagates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def git(*args):
                return subprocess.check_output(['git', '-c', 'user.name=NPC test',
                    '-c', 'user.email=npc-test@example.invalid', *args], cwd=root, text=True).strip()
            git('init', '-q')
            script = root/'tools/npcs/rebuild.py'
            script.parent.mkdir(parents=True)
            script.write_text("from pathlib import Path\nimport sys\n"
                "assert sys.argv[1:] == ['--check']\n"
                "assert (Path(__file__).resolve().parents[2]/'data/uf/policy.json').read_text() == 'valid'\n")
            policy = root/'data/uf/policy.json'
            policy.parent.mkdir(parents=True)
            policy.write_text('valid')
            git('add', '.'); git('commit', '-qm', 'valid candidate')
            commit = git('rev-parse', 'HEAD')
            policy.write_text('stale local data')
            with patch.object(release, 'ROOT', root):
                release.validate_npc_data(commit)  # local edit must not contaminate candidate
                git('add', '.'); git('commit', '-qm', 'invalid candidate')
                with patch.object(release, 'run', side_effect=lambda args: subprocess.run(
                        args, check=True, capture_output=True)):
                    with self.assertRaises(subprocess.CalledProcessError):
                        release.validate_npc_data(git('rev-parse', 'HEAD'))


if __name__ == '__main__':
    unittest.main()
