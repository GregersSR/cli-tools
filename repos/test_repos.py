import importlib.machinery
import importlib.util
import os
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def load_repos_module():
    script = Path(os.environ.get("REPOS_SCRIPT", ROOT / "repos"))
    loader = importlib.machinery.SourceFileLoader("repos_cli", str(script))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


REPOS = load_repos_module()


@contextmanager
def chdir(path: Path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


@contextmanager
def environ(**updates):
    previous = {key: os.environ.get(key) for key in updates}
    for key, value in updates.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = str(value)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


class ReposInitTests(unittest.TestCase):
    def setUp(self):
        self.fake_config = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.fake_config.cleanup()

    def test_init_defaults_to_current_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_dir = Path(tmp)

            with environ(XDG_CONFIG_HOME=self.fake_config.name), chdir(repo_dir):
                REPOS.main(["init"])

            self.assertTrue((repo_dir / ".git").is_dir())
            self.assertTrue((repo_dir / ".gitignore").is_file())

    def test_init_creates_named_subdirectory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo_dir = root / "nested" / "repo"

            with environ(XDG_CONFIG_HOME=self.fake_config.name), chdir(root):
                REPOS.main(["init", "nested/repo"])

            self.assertTrue(repo_dir.is_dir())
            self.assertTrue((repo_dir / ".git").is_dir())
            self.assertTrue((repo_dir / ".gitignore").is_file())

    def test_init_uses_repos_template_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            template = root / "template"
            template.mkdir()
            (template / "CUSTOM_MARKER").write_text("custom\n")
            nested = template / "nested"
            nested.mkdir()
            (nested / "child.txt").write_text("nested\n")
            template_git_dir = template / ".git"
            template_git_dir.mkdir()
            (template_git_dir / "TEMPLATE_MARKER").write_text("custom\n")

            with environ(REPOS_TEMPLATE=template), chdir(root):
                REPOS.main(["init", "custom"])

            repo_dir = root / "custom"
            self.assertTrue((repo_dir / ".git").is_dir())
            self.assertTrue((repo_dir / "CUSTOM_MARKER").is_file())
            self.assertTrue((repo_dir / "nested/child.txt").is_file())
            self.assertFalse((repo_dir / ".gitignore").exists())
            self.assertTrue((repo_dir / ".git/TEMPLATE_MARKER").exists())

    def test_init_prefers_xdg_config_template(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_home = root / "config"
            template = config_home / "repos" / "template"
            template.mkdir(parents=True)
            (template / "CONFIG_MARKER").write_text("config\n")

            with environ(XDG_CONFIG_HOME=config_home), chdir(root):
                REPOS.main(["init", "configured"])

            repo_dir = root / "configured"
            self.assertFalse((repo_dir / ".git").is_dir())
            self.assertTrue((repo_dir / "CONFIG_MARKER").is_file())
            self.assertFalse((repo_dir / ".gitignore").exists())

    def test_init_converts_dot_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            template = root / "template"
            template.mkdir()
            dotgit = template / "dot-git"
            dotgit.mkdir()
            (template / "dot-gitignore").write_text("gitignore\n")

            with environ(REPOS_TEMPLATE=template), chdir(root):
                REPOS.main(["init", "custom"])

            repo_dir = root / "custom"
            self.assertTrue((repo_dir / ".git").is_dir())
            self.assertTrue((repo_dir / ".gitignore").is_file())
        

    def test_check_defaults_to_xdg_config_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_home = Path(tmp) / "config"
            expected = config_home / "repos" / "check_repos.txt"

            with environ(XDG_CONFIG_HOME=config_home):
                args = REPOS.parse_args(REPOS.create_parser(), ["check"])

            self.assertEqual(args.file, expected)


if __name__ == "__main__":
    unittest.main()
