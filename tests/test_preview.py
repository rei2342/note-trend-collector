import builtins
import contextlib
import io
import os
from pathlib import Path
import runpy
import smtplib
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock
import urllib.request

import preview

ROOT = Path(__file__).resolve().parents[1]


class OfflinePreviewTests(unittest.TestCase):
    def test_cli_runs_without_site_packages_and_ignores_secret_config(self):
        secrets = {"ANTHROPIC_API_KEY": "SENTINEL-API-DO-NOT-DISCLOSE", "GMAIL_APP_PASSWORD": "SENTINEL-MAIL-DO-NOT-DISCLOSE", "GMAIL_ADDRESS": "private-sentinel@example.invalid", "TO_EMAIL": "private-to@example.invalid", "X_MIN_LIKES": "invalid-number-proves-config-not-imported"}
        with tempfile.TemporaryDirectory() as temp:
            env = dict(os.environ, **secrets)
            (Path(temp) / ".env").write_text("ANTHROPIC_API_KEY=DOTENV-SECRET-NOT-READ\n", encoding="utf-8")
            result = subprocess.run([sys.executable, "-I", "-S", str(ROOT / "preview.py"), "--output-dir", str(Path(temp) / "out")], cwd=temp, env=env, capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            outputs = [(Path(temp) / "out" / name).read_text(encoding="utf-8") for name in ("sample_report.html", "sample_report.txt")]
            combined = result.stdout + result.stderr + "".join(outputs)
            for secret in (*secrets.values(), "DOTENV-SECRET-NOT-READ"):
                self.assertNotIn(secret, combined)
            for output in outputs:
                self.assertIn(preview.NOTICE, output)
                self.assertIn("本番メール", output)
                for source in ("N1", "N2", "N3", "H1", "H2"):
                    self.assertIn("fixture:" + source, output)

    def test_preview_cannot_call_network_or_import_production_or_read_dotenv(self):
        original_import = builtins.__import__
        original_open = builtins.open
        original_io_open = io.open
        forbidden = {"main", "config", "mailer", "summarizer", "analyzer", "collectors", "requests", "dotenv"}
        def guarded_import(name, *args, **kwargs):
            if name.split(".")[0] in forbidden:
                raise AssertionError("Production import attempted: " + name)
            return original_import(name, *args, **kwargs)
        def guard_open(original):
            def wrapped(file, *args, **kwargs):
                if isinstance(file, (str, bytes, os.PathLike)) and Path(file).name == ".env":
                    raise AssertionError("dotenv access attempted")
                return original(file, *args, **kwargs)
            return wrapped
        with tempfile.TemporaryDirectory() as temp, contextlib.ExitStack() as stack:
            stack.enter_context(patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sentinel-key", "GMAIL_APP_PASSWORD": "sentinel-mail"}))
            stack.enter_context(patch.object(builtins, "__import__", side_effect=guarded_import))
            stack.enter_context(patch.object(builtins, "open", side_effect=guard_open(original_open)))
            stack.enter_context(patch.object(io, "open", side_effect=guard_open(original_io_open)))
            calls = [stack.enter_context(patch(target, side_effect=AssertionError("External call attempted"))) for target in ("socket.socket.connect", "socket.socket.connect_ex", "socket.getaddrinfo", "socket.create_connection", "urllib.request.urlopen", "smtplib.SMTP")]
            stack.enter_context(patch.object(sys, "argv", ["preview.py", "--output-dir", temp]))
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            with self.assertRaises(SystemExit) as exit_status:
                runpy.run_path(str(ROOT / "preview.py"), run_name="__main__")
            self.assertEqual(exit_status.exception.code, 0)
            for call in calls:
                call.assert_not_called()

    def test_html_escapes_all_fixture_text_and_loads_no_external_assets(self):
        hostile = dict(preview.FIXTURES[0], id='"><img src=x onerror=alert(1)>', title="<script>alert(1)</script>", description="<iframe src=https://example.invalid>", headings=("<img src=x>",), tag="A&B")
        html = preview.render_html((hostile,))
        for forbidden in ("<script", "<img ", "<iframe", "<link ", "url(", "<form", "<a href="):
            self.assertNotIn(forbidden, html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("A&amp;B", html)
        self.assertIn("default-src 'none'", html)

    def test_unknown_counts_remain_distinct_from_zero(self):
        html, text = preview.render_html(), preview.render_text()
        for output in (html, text):
            self.assertIn("0件（架空値）", output)
            self.assertIn("未取得（架空の欠損例）", output)
            self.assertIn("0個（架空値）", output)
            self.assertNotIn("有料化位置", output)

    def test_existing_reports_are_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            report = Path(temp) / "sample_report.txt"
            report.write_text("keep-me", encoding="utf-8")
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as status:
                preview.main(["--output-dir", temp])
            self.assertEqual(status.exception.code, 2)
            self.assertEqual(report.read_text(), "keep-me")
            self.assertFalse((Path(temp) / "sample_report.html").exists())

    def test_legacy_mail_mode_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            result = subprocess.run([sys.executable, "-S", str(ROOT / "test_run.py"), "mail"], cwd=temp, capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 2)
            self.assertFalse((Path(temp) / "preview_output").exists())

    def test_legacy_default_only_creates_sample(self):
        with tempfile.TemporaryDirectory() as temp:
            result = subprocess.run([sys.executable, "-S", str(ROOT / "test_run.py")], cwd=temp, env=dict(os.environ, ANTHROPIC_API_KEY="legacy-secret", GMAIL_APP_PASSWORD="legacy-mail"), capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(preview.NOTICE, (Path(temp) / "preview_output" / "sample_report.txt").read_text())
            self.assertNotIn("legacy-secret", result.stdout + result.stderr)



if __name__ == "__main__":
    unittest.main()
