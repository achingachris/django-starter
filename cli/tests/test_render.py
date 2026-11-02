import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from django_starter_cdc.cli import NAME_RE, main
from django_starter_cdc.fetch import archive_url, copy_local
from django_starter_cdc.render import RenderError, process_text, prune, rename, render_project, write_env

SETTINGS = """\
INSTALLED_APPS = [
    "apps.users",
    # >>> web
    "apps.web",
    # <<< web
]
# api-only: HEADLESS_ONLY = True
"""

TEMPLATE = """\
<body>
<!-- >>> web -->
<nav></nav>
<!-- <<< web -->
{# >>> web #}
<footer></footer>
{# <<< web #}
</body>
"""


class ProcessTextTests(unittest.TestCase):
    def test_full_mode_keeps_blocks_and_drops_markers(self):
        self.assertEqual(
            process_text(SETTINGS, api=False),
            'INSTALLED_APPS = [\n    "apps.users",\n    "apps.web",\n]\n',
        )

    def test_api_mode_drops_blocks(self):
        self.assertEqual(
            process_text(SETTINGS, api=True),
            'INSTALLED_APPS = [\n    "apps.users",\n]\nHEADLESS_ONLY = True\n',
        )

    def test_html_and_django_comment_markers(self):
        self.assertEqual(process_text(TEMPLATE, api=False), "<body>\n<nav></nav>\n<footer></footer>\n</body>\n")
        self.assertEqual(process_text(TEMPLATE, api=True), "<body>\n</body>\n")

    def test_api_only_keeps_indentation_and_line_endings(self):
        text = "if True:\r\n    # api-only: x = 1\r\n    y = 2\r\n"
        self.assertEqual(process_text(text, api=True), "if True:\r\n    x = 1\r\n    y = 2\r\n")
        self.assertEqual(process_text(text, api=False), "if True:\r\n    y = 2\r\n")

    def test_api_only_inside_web_block_is_dropped_in_api_mode(self):
        text = "# >>> web\n# api-only: x = 1\n# <<< web\n"
        self.assertEqual(process_text(text, api=True), "")

    def test_text_without_markers_is_unchanged(self):
        text = "# a web comment\nwebsite = 'web'\n# >>> website\n"
        self.assertEqual(process_text(text, api=True), text)

    def test_unclosed_block(self):
        with self.assertRaisesRegex(RenderError, r"settings.py:2: '>>> web' is never closed"):
            process_text("x = 1\n# >>> web\ny = 2\n", api=True, path="settings.py")

    def test_close_without_open(self):
        with self.assertRaisesRegex(RenderError, r"urls.py:1: '<<< web' without a matching"):
            process_text("# <<< web\n", api=False, path="urls.py")

    def test_nested_open(self):
        with self.assertRaisesRegex(RenderError, r"Makefile:3: '>>> web' inside the block opened on line 1"):
            process_text("# >>> web\na\n# >>> web\n# <<< web\n", api=False, path="Makefile")

    def test_starter_blocks_are_dropped_in_both_variants(self):
        text = (
            "# Docs\n<!-- >>> starter -->\nRun uvx django-starter-cdc.\n<!-- <<< starter -->\n"
            "{# >>> starter #}\nx\n{# <<< starter #}\nEnd\n"
        )
        for api in (False, True):
            self.assertEqual(process_text(text, api=api), "# Docs\nEnd\n")

    def test_web_block_inside_starter_block(self):
        text = "a\n# >>> starter\nb\n# >>> web\nc\n# <<< web\n# <<< starter\nd\n"
        self.assertEqual(process_text(text, api=False), "a\nd\n")

    def test_unbalanced_starter_markers(self):
        with self.assertRaisesRegex(RenderError, r"README.md:1: '>>> starter' is never closed"):
            process_text("<!-- >>> starter -->\n", api=False, path="README.md")
        with self.assertRaisesRegex(RenderError, r"README.md:2: '<<< starter' without a matching"):
            process_text("<!-- >>> web -->\n<!-- <<< starter -->\n", api=False, path="README.md")

    def test_makefile_markers_at_column_zero(self):
        text = (
            "init:\n\t@uv sync\n# >>> web\n\t@npm install\n# <<< web\n\t@$(MAKE) migrate\n"
            "# api-only: upgrade: requirements migrate  ## Update\n"
        )
        self.assertEqual(
            process_text(text, api=True),
            "init:\n\t@uv sync\n\t@$(MAKE) migrate\nupgrade: requirements migrate  ## Update\n",
        )
        self.assertEqual(process_text(text, api=False), "init:\n\t@uv sync\n\t@npm install\n\t@$(MAKE) migrate\n")


class RenameTests(unittest.TestCase):
    def test_names_env_prefix_and_email(self):
        text = (
            'name = "chrisdevcode"\nimage: django-starter-app\n"""django-template URLs"""\n'
            'env("CHRISDEVCODE_LOG_LEVEL")\nADMINS = ["achinga.chris@gmail.com"]\n'
        )
        self.assertEqual(
            rename(text, "my-shop", "me@shop.test"),
            'name = "my-shop"\nimage: my-shop-app\n"""my-shop URLs"""\n'
            'env("MY_SHOP_LOG_LEVEL")\nADMINS = ["me@shop.test"]\n',
        )

    def test_default_email(self):
        self.assertEqual(rename("achinga.chris@gmail.com", "shop"), "admin@example.com")

    def test_slug_containing_an_old_name_is_not_replaced_twice(self):
        self.assertEqual(
            rename("django-starter chrisdevcode", "django-template-x"), "django-template-x django-template-x"
        )


class TreeTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "project"
        files = {
            "manage.py": "print('chrisdevcode')\n",
            "package.json": '{"name": "chrisdevcode"}\n',
            "templates/web/base.html": "<html></html>\n",
            "templates/account/email/base.txt": "{# >>> web #}\nweb\n{# <<< web #}\nemail\n",
            "apps/web/views.py": "",
            "apps/web/models.py": "",
            "apps/web/templatetags/meta_tags.py": "",
            "apps/users/views.py": "",
            "apps/users/api.py": "",
            "cli/pyproject.toml": "",
            ".github/workflows/tests.yml": "",
            ".github/workflows/publish_cli.yml": "",
            ".cursor/rules/django-templates.mdc": "",
            ".cursor/rules/python.mdc": "",
            ".env.example": '# header\nSECRET_KEY="django-insecure-x"\nDEBUG=True\n',
        }
        for rel, text in files.items():
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        (self.root / "static/images").mkdir(parents=True)
        (self.root / "static/images/logo.png").write_bytes(b"\x89PNG\r\n\x1a\n\0\0chrisdevcode")

    def tearDown(self):
        self._tmp.cleanup()

    def files(self):
        return sorted(p.relative_to(self.root).as_posix() for p in self.root.rglob("*") if p.is_file())

    def test_prune_full_removes_only_the_cli(self):
        removed = prune(self.root, api=False)
        self.assertEqual(removed, [".github/workflows/publish_cli.yml", "cli/pyproject.toml"])
        self.assertFalse((self.root / "cli").exists())
        self.assertTrue((self.root / "templates/web/base.html").exists())

    def test_prune_api(self):
        prune(self.root, api=True)
        self.assertEqual(
            self.files(),
            [
                ".cursor/rules/python.mdc",
                ".env.example",
                ".github/workflows/tests.yml",
                "apps/users/api.py",
                "apps/web/models.py",
                "manage.py",
                "static/images/logo.png",
                "templates/account/email/base.txt",
            ],
        )
        self.assertFalse((self.root / "templates/web").exists())
        self.assertFalse((self.root / "apps/web/templatetags").exists())

    def test_render_project_api(self):
        render_project(self.root, api=True, slug="shop", email="me@shop.test")
        self.assertEqual((self.root / "manage.py").read_text(), "print('shop')\n")
        self.assertEqual((self.root / "templates/account/email/base.txt").read_text(), "email\n")
        self.assertIn(b"chrisdevcode", (self.root / "static/images/logo.png").read_bytes())
        env = (self.root / ".env").read_text()
        self.assertNotIn("django-insecure", env)
        self.assertRegex(env, r'SECRET_KEY="[\w-]{60,}"\nDEBUG=True\n')

    def test_render_project_reports_the_file_with_bad_markers(self):
        (self.root / "apps/web/models.py").write_text("# >>> web\n")
        with self.assertRaisesRegex(RenderError, r"apps/web/models.py:1"):
            render_project(self.root, api=False, slug="shop")

    def test_write_env_without_example(self):
        (self.root / ".env.example").unlink()
        self.assertFalse(write_env(self.root))

    def test_copy_local_skips_build_output_and_secrets(self):
        for rel in (".env", "db.sqlite3", "node_modules/x.js", "static/css/site.css", "apps/__pycache__/a.pyc"):
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("x")
        dest = Path(self._tmp.name) / "copy"
        copy_local(self.root, dest)
        copied = sorted(p.relative_to(dest).as_posix() for p in dest.rglob("*") if p.is_file())
        self.assertNotIn(".env", copied)
        self.assertNotIn("db.sqlite3", copied)
        self.assertFalse(any(p.startswith(("cli/", "node_modules/", "static/css/")) for p in copied))
        self.assertFalse(any("__pycache__" in p for p in copied))
        self.assertIn(".env.example", copied)

    def test_new_project_inside_the_source_checkout(self):
        # `new sample --source .` with the default `--dir .`: the staging directory and the target both
        # live inside the checkout being copied, and must not be copied into the project.
        with contextlib.redirect_stdout(io.StringIO()):
            args = ["new", "sample", "--source", str(self.root), "--dir", str(self.root), "--no-git", "--no-install"]
            code = main(args)
        self.assertEqual(code, 0)
        project = self.root / "sample"
        self.assertTrue((project / "manage.py").is_file())
        self.assertEqual([p.name for p in project.iterdir() if p.name == "sample" or p.name.startswith(".sample-")], [])
        self.assertEqual([p.name for p in self.root.iterdir() if p.name.startswith(".sample-")], [])


class CLITests(unittest.TestCase):
    def test_name_validation(self):
        for name in ("shop", "my-shop", "my_shop2", "a"):
            self.assertRegex(name, NAME_RE)
        for name in ("Shop", "2shop", "my shop", "shop-", "-shop", "my.shop", ""):
            self.assertNotRegex(name, NAME_RE)

    def test_archive_url(self):
        self.assertEqual(archive_url("main"), "https://github.com/achingachris/django-starter/archive/main.tar.gz")
        self.assertRegex(archive_url(), r"/archive/refs/tags/v\d+\.\d+\.\d+\.tar\.gz$")


if __name__ == "__main__":
    unittest.main()
