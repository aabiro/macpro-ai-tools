"""Where the provider API keys go, checked offline.

Each key must reach only its own provider, in a header, and never land in a
URL (which ends up in logs) or on a command line (which every local user can
read through `ps`). No real network call or subprocess is made: the outbound
call is intercepted and inspected instead.

    .venv/bin/python -m unittest discover -s tests -v
"""

import importlib.machinery
import importlib.util
import io
import logging
import os
import unittest
import urllib.parse
from unittest import mock

import httpx

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIT = os.path.join(ROOT, "g5-handoff", "kit")

TEST_KEYS = {
    "OPENAI_API_KEY": "test-openai-key",
    "ANTHROPIC_API_KEY": "test-anthropic-key",
    "GEMINI_API_KEY": "test-gemini-key",
}
EXPECTED_HOST = {
    "OPENAI_API_KEY": "api.openai.com",
    "ANTHROPIC_API_KEY": "api.anthropic.com",
    "GEMINI_API_KEY": "generativelanguage.googleapis.com",
}


def load(path, name):
    loader = importlib.machinery.SourceFileLoader(name, path)
    spec = importlib.util.spec_from_loader(name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


class FastAPIGateway(unittest.TestCase):
    """gateway.py -- the FastAPI proxy."""

    @classmethod
    def setUpClass(cls):
        # Test keys are set first, so load_dotenv() leaves them alone and never
        # pulls real keys from .env into this process.
        with mock.patch.dict(os.environ, TEST_KEYS):
            cls.gw = load(os.path.join(ROOT, "gateway.py"), "gateway")
        logging.getLogger("httpx").setLevel(logging.WARNING)
        from fastapi.testclient import TestClient
        cls.client = TestClient(cls.gw.app)

    def setUp(self):
        self.sent = []
        real = httpx.AsyncClient

        def handler(request):
            self.sent.append(request)
            return httpx.Response(200, json={"ok": True})

        patcher = mock.patch.object(
            self.gw.httpx, "AsyncClient",
            lambda **kw: real(transport=httpx.MockTransport(handler)))
        patcher.start()
        self.addCleanup(patcher.stop)

    def assert_key_only_in_header(self, request, env, header):
        key = TEST_KEYS[env]
        self.assertEqual(request.url.host, EXPECTED_HOST[env])
        self.assertEqual(request.url.scheme, "https")
        self.assertNotIn(key, str(request.url))
        self.assertIn(key, request.headers[header])
        self.assertNotIn(key, request.content.decode())

    def test_gemini_key_goes_in_a_header_not_the_url(self):
        r = self.client.post("/v1/chat/gemini", json={"contents": []})
        self.assertEqual(r.status_code, 200)
        req = self.sent[0]
        self.assertEqual(req.url.path,
                         "/v1beta/models/gemini-flash-latest:generateContent")
        self.assertEqual(req.url.query, b"")
        self.assert_key_only_in_header(req, "GEMINI_API_KEY", "x-goog-api-key")

    def test_gemini_rejects_a_model_name_that_could_bend_the_url(self):
        for model in ("../../v1/x", "m?key=leak", "m#frag", "a/b", "", 42,
                      "@evil.example", "m\n"):
            with self.subTest(model=model):
                r = self.client.post("/v1/chat/gemini", json={"model": model})
                self.assertEqual(r.status_code, 400)
        self.assertEqual(self.sent, [])

    def test_gemini_accepts_real_model_ids(self):
        for model in ("gemini-2.5-flash", "gemini-3.1-pro-preview",
                      "gemini-flash-latest"):
            with self.subTest(model=model):
                r = self.client.post("/v1/chat/gemini", json={"model": model})
                self.assertEqual(r.status_code, 200)
                self.assertEqual(self.sent[-1].url.path,
                                 "/v1beta/models/%s:generateContent" % model)

    def test_openai_key_goes_only_to_openai(self):
        self.client.post("/v1/chat/openai", json={"model": "gpt-4o"})
        self.assert_key_only_in_header(
            self.sent[0], "OPENAI_API_KEY", "authorization")

    def test_anthropic_key_goes_only_to_anthropic(self):
        self.client.post("/v1/chat/anthropic", json={"model": "claude-sonnet-5"})
        self.assert_key_only_in_header(
            self.sent[0], "ANTHROPIC_API_KEY", "x-api-key")


class _Reply(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class StdlibGateway(unittest.TestCase):
    """kit/gateway/aigw.py and kit/shared/aigw.py -- the zero-dependency gateway."""

    COPIES = [os.path.join(KIT, "gateway", "aigw.py"),
              os.path.join(KIT, "shared", "aigw.py")]

    def call(self, aigw, provider, model):
        sent = []

        def urlopen(req, timeout=None, context=None):
            sent.append(req)
            return _Reply(b'{"ok": true}')

        with mock.patch.dict(os.environ, TEST_KEYS), \
                mock.patch.object(aigw.urllib.request, "urlopen", urlopen):
            aigw.call_provider(provider, {}, model)
        return sent[0]

    def test_every_key_goes_in_a_header_to_its_own_host(self):
        for i, path in enumerate(self.COPIES):
            aigw = load(path, "aigw_%d" % i)
            for provider, spec in aigw.PROVIDERS.items():
                with self.subTest(copy=path, provider=provider):
                    req = self.call(aigw, provider, spec["default_model"])
                    url = urllib.parse.urlsplit(req.full_url)
                    key = TEST_KEYS[spec["env"]]
                    self.assertEqual(url.scheme, "https")
                    self.assertEqual(url.hostname, EXPECTED_HOST[spec["env"]])
                    self.assertNotIn(key, req.full_url)
                    self.assertTrue(any(key in v for v in req.headers.values()))

    def test_a_model_name_that_could_bend_the_url_is_refused(self):
        for i, path in enumerate(self.COPIES):
            aigw = load(path, "aigw_bad_%d" % i)
            for model in ("../x", "m?key=1", "a/b", "@evil.example", ""):
                with self.subTest(copy=path, model=model):
                    with mock.patch.object(aigw.urllib.request, "urlopen") as u:
                        with mock.patch.dict(os.environ, TEST_KEYS):
                            with self.assertRaises(ValueError):
                                aigw.call_provider("gemini", {}, model)
                        u.assert_not_called()


class SetupTool(unittest.TestCase):
    """kit/linux/ai -- the `ai setup` helper on the Debian side."""

    @classmethod
    def setUpClass(cls):
        cls.ai = load(os.path.join(KIT, "linux", "ai"), "ai_tool")

    def test_verify_key_sends_the_gemini_key_in_a_header(self):
        sent = []

        def urlopen(req, timeout=None):
            sent.append(req)
            return _Reply(b"{}")

        with mock.patch.object(self.ai.urllib.request, "urlopen", urlopen):
            good, _ = self.ai.verify_key("gemini", "test-gemini-key")
        self.assertTrue(good)
        self.assertNotIn("test-gemini-key", sent[0].full_url)
        self.assertEqual(sent[0].get_header("X-goog-api-key"), "test-gemini-key")

    def write_env(self, newkeys, env_file=b"", read_rc=0, gateway=None):
        """Run write_env against a fake env file. Returns the subprocess calls.

        The first call reads the file (no stdin); a later one writes it (stdin).
        """
        calls = []

        def run(argv, capture_output=None, timeout=None, input=None):
            calls.append((argv, input))
            if input is None:
                return mock.Mock(returncode=read_rc, stdout=env_file)
            return mock.Mock(returncode=0, stdout=b"")

        with mock.patch.object(self.ai, "sudo_prefix", lambda: ["sudo"]), \
                mock.patch.object(self.ai, "gateway_health", lambda: gateway), \
                mock.patch.object(self.ai.subprocess, "run", run), \
                mock.patch("builtins.print"):
            self.saved = self.ai.write_env(newkeys)
        return calls

    def test_write_env_passes_keys_on_stdin_never_in_argv(self):
        calls = self.write_env({"GEMINI_API_KEY": "sk-secret-1"},
                               env_file=b"ANTHROPIC_API_KEY=sk-ant-old\n")
        self.assertTrue(self.saved)
        for argv, _ in calls:
            self.assertFalse(any("sk-secret-1" in a or "sk-ant-old" in a
                                 for a in argv))
        argv, stdin = calls[-1]
        self.assertIn(b"GEMINI_API_KEY=sk-secret-1\n", stdin)
        self.assertIn("umask 077", argv[-1])

    def test_adding_a_second_provider_keeps_the_first_key(self):
        # The gateway is up and already serving Anthropic, so read_env() would
        # say ANTHROPIC_API_KEY=configured. That placeholder must not be saved.
        calls = self.write_env(
            {"GEMINI_API_KEY": "gm-new"},
            env_file=b"# keys\nANTHROPIC_API_KEY=sk-ant-real\nOPENAI_API_KEY=\n"
                     b"GEMINI_API_KEY=\nTELEMETRY_PATH=/srv/t.json\n",
            gateway={"providers_configured": ["anthropic"]})
        self.assertTrue(self.saved)
        written = calls[-1][1].decode()
        self.assertNotIn("configured", written)
        self.assertIn("ANTHROPIC_API_KEY=sk-ant-real\n", written)
        self.assertIn("GEMINI_API_KEY=gm-new\n", written)
        self.assertIn("OPENAI_API_KEY=\n", written)
        self.assertIn("TELEMETRY_PATH=/srv/t.json\n", written)

    def test_a_new_key_replaces_the_old_one_for_that_provider(self):
        calls = self.write_env({"GEMINI_API_KEY": "gm-new"},
                               env_file=b"GEMINI_API_KEY=gm-old\n")
        written = calls[-1][1].decode()
        self.assertIn("GEMINI_API_KEY=gm-new\n", written)
        self.assertNotIn("gm-old", written)

    def test_nothing_is_written_when_the_file_cannot_be_read(self):
        calls = self.write_env({"GEMINI_API_KEY": "gm-new"}, read_rc=1)
        self.assertFalse(self.saved)
        self.assertEqual(len(calls), 1)
        self.assertIsNone(calls[0][1])


if __name__ == "__main__":
    unittest.main()
