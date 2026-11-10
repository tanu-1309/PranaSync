# ruff: noqa: E702
"""The demo-day launcher's helpers: it must tell a free port from a busy one and a PranaSync portal from anything else."""
import http.server
import importlib.util
import socket
import threading
from pathlib import Path

spec = importlib.util.spec_from_file_location("start_demo", Path(__file__).resolve().parents[1] / "scripts" / "start_demo.py")
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


def test_port_free_tells_busy_from_free():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0)); s.listen(); busy = s.getsockname()[1]
        assert demo.port_free(busy) is False
    assert demo.port_free(busy) is True


def test_a_portal_is_recognised_only_by_its_health_answer():
    class H(http.server.BaseHTTPRequestHandler):
        body = b'{"ok": true, "database": "sqlite", "workbooks": 5}'

        def do_GET(self):
            self.send_response(200); self.end_headers(); self.wfile.write(H.body)

        def log_message(self, *a):
            pass
    srv = http.server.HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    port = srv.server_port
    assert demo.pranasync_on(port)["workbooks"] == 5
    H.body = b'{"hello": "some other program"}'
    assert demo.pranasync_on(port) is None
    srv.shutdown()
    assert demo.pranasync_on(port) is None                      # nothing listening
