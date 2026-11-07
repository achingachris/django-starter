import contextlib
import io
import unittest
from unittest import mock

from django_starter_cdc.cli import CLIError, main, prompt_api, prompt_name


def answer(prompt, answers):
    """Run ``prompt`` on a pretend terminal that types ``answers``. Returns its result, the questions asked
    and the error output."""
    stderr = io.StringIO()
    with (
        mock.patch("sys.stdin.isatty", return_value=True),
        mock.patch("builtins.input", side_effect=answers) as ask,
        contextlib.redirect_stderr(stderr),
        contextlib.redirect_stdout(io.StringIO()),
    ):
        result = prompt()
    return result, ask.call_count, stderr.getvalue()


class PromptNameTests(unittest.TestCase):
    def test_returns_a_valid_name(self):
        self.assertEqual(answer(prompt_name, ["  shop  "]), ("shop", 1, ""))

    def test_asks_again_until_the_name_is_valid(self):
        name, asked, errors = answer(prompt_name, ["", "My Shop", "my-shop"])
        self.assertEqual((name, asked), ("my-shop", 3))
        self.assertIn("Invalid project name 'My Shop'", errors)

    def test_cancelling_raises(self):
        for interrupt in (EOFError, KeyboardInterrupt):
            with self.subTest(interrupt=interrupt), self.assertRaisesRegex(CLIError, "Cancelled"):
                answer(prompt_name, interrupt)

    def test_requires_the_argument_without_a_terminal(self):
        with (
            mock.patch("sys.stdin.isatty", return_value=False),
            self.assertRaisesRegex(CLIError, "Missing project name"),
        ):
            prompt_name()


class PromptAPITests(unittest.TestCase):
    def test_choices(self):
        self.assertEqual(answer(prompt_api, [""]), (False, 1, ""))
        self.assertEqual(answer(prompt_api, ["1"]), (False, 1, ""))
        self.assertEqual(answer(prompt_api, ["2"]), (True, 1, ""))

    def test_asks_again_until_the_choice_is_valid(self):
        api, asked, errors = answer(prompt_api, ["api", "2"])
        self.assertEqual((api, asked), (True, 2))
        self.assertIn("Please enter 1 or 2", errors)


class ArgumentTests(unittest.TestCase):
    def parse(self, argv):
        with mock.patch("django_starter_cdc.cli.create_project", return_value=0) as create:
            self.assertEqual(main(argv), 0)
        return create.call_args.args[0]

    def test_type_flags(self):
        self.assertIsNone(self.parse(["shop"]).api)
        self.assertTrue(self.parse(["shop", "--api"]).api)
        self.assertFalse(self.parse(["shop", "--full"]).api)

    def test_accepts_the_old_new_subcommand(self):
        args = self.parse(["new", "shop", "--api"])
        self.assertEqual((args.name, args.api), ("shop", True))
        self.assertIsNone(self.parse(["new"]).name)


if __name__ == "__main__":
    unittest.main()
