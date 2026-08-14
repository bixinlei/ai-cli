"""端到端测试:用本地 mock 服务器模拟 OpenAI 流式 API,验证 ai-cli 核心功能。

运行: python -m unittest discover -s tests -v
零外部依赖,离线可跑。
"""
from __future__ import annotations

import contextlib
import io
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from aicli import client, history
from aicli.config import Config
from aicli.md_render import render_markdown


class MockHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        assert body["messages"][0]["role"] == "system"
        assert body["messages"][-1]["role"] == "user"

        # 按模型返回不同回复
        model = body.get("model", "mock")
        reply = f"{model}: 这是针对你的回答。"

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()

        if body.get("stream", False):
            for piece in [reply[:6], reply[6:12], reply[12:]]:
                chunk = json.dumps({"choices": [{"delta": {"content": piece}}]}, ensure_ascii=False)
                self.wfile.write(f"data: {chunk}\n\n".encode("utf-8"))
                self.wfile.flush()
            self.wfile.write(b"data: [DONE]\n\n")
        else:
            full = json.dumps({"choices": [{"message": {"content": reply}}], "usage": {"total_tokens": 10}}, ensure_ascii=False)
            self.wfile.write(full.encode("utf-8"))
        self.wfile.flush()

    def log_message(self, *args):  # 静默日志
        pass


class MockServer(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.httpd = HTTPServer(("127.0.0.1", 0), MockHandler)
        self.port = self.httpd.server_address[1]

    def run(self):
        self.httpd.serve_forever()

    def stop(self):
        self.httpd.shutdown()


def make_config(server: MockServer) -> Config:
    cfg = Config()
    cfg.api_key = "test-key"
    cfg.base_url = f"http://127.0.0.1:{server.port}/v1"
    cfg.model = "mock-model"
    return cfg


class TestStreaming(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = MockServer()
        cls.server.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def test_chat_stream_returns_full_reply(self):
        cfg = make_config(self.server)
        full, usage = client.chat_stream(cfg, [], "你好")
        self.assertEqual(full, "mock-model: 这是针对你的回答。")

    def test_chat_stream_on_delta_called(self):
        cfg = make_config(self.server)
        pieces = []
        full, _ = client.chat_stream(cfg, [], "你好", on_delta=pieces.append)
        self.assertEqual("".join(pieces), full)

    def test_chat_once_non_stream(self):
        cfg = make_config(self.server)
        reply, usage = client.chat_once(cfg, [], "你好")
        self.assertTrue(reply.startswith("mock-model:"))
        self.assertEqual(usage["total_tokens"], 10)


class TestBattle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = MockServer()
        cls.server.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def test_battle_two_models(self):
        from aicli import cli

        cfg = make_config(self.server)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = cli.main(
                ["--base-url", cfg.base_url, "--api-key", "test-key", "battle", "你好", "--models", "mock-a,mock-b"]
            )
        out = buf.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("mock-a", out)
        self.assertIn("mock-b", out)
        self.assertIn("mock-a: 这是针对你的回答。", out)
        self.assertIn("mock-b: 这是针对你的回答。", out)


class TestMdRender(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import aicli.console as console

        cls._old_enabled = console._ENABLED
        console._ENABLED = True  # 测试环境强制启用颜色

    @classmethod
    def tearDownClass(cls):
        import aicli.console as console

        console._ENABLED = cls._old_enabled

    def test_title_and_bold(self):
        out = render_markdown("# 标题\n**加粗**")
        self.assertIn("\033[", out)
        self.assertIn("标题", out)
        self.assertIn("加粗", out)

    def test_code_block(self):
        out = render_markdown("```python\nprint(1)\n```")
        self.assertIn("python", out)
        self.assertIn("print(1)", out)
        self.assertIn("\033[", out)

    def test_plain_text_when_disabled(self):
        # 非 tty 时 _ENABLED 为 False,应原样返回
        import aicli.console as console

        old = console._ENABLED
        console._ENABLED = False
        try:
            self.assertEqual(render_markdown("# 标题"), "# 标题")
        finally:
            console._ENABLED = old


class TestHistory(unittest.TestCase):
    def test_roundtrip(self):
        session = "unittest-session"
        history.delete_session(session)
        history.append_message(session, "user", "你好")
        history.append_message(session, "assistant", "你好!我是AI")
        msgs = history.load_messages(session)
        self.assertEqual(len(msgs), 2)
        self.assertEqual(msgs[0]["role"], "user")
        self.assertEqual(msgs[1]["content"], "你好!我是AI")
        names = [n for n, _, _ in history.list_sessions()]
        self.assertIn(session, names)
        history.delete_session(session)
        self.assertEqual(history.load_messages(session), [])


if __name__ == "__main__":
    unittest.main()
