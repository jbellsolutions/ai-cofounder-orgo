"""Block/allow contract for the gateway-guard Hermes plugin.

The first 63 cases (37 block, 26 allow) are the suite the plugin passed on the
live co-founder on 2026-10-21, including the two commands that took its
gateway offline. The rest cover Hermes v2026.8.31 (``mcp__server__tool``
names, ``gateway run --replace``), per-profile plugin paths, and this
repository's own gateway lifecycle scripts.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import sys
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DIR = ROOT / "plugins/gateway-guard"


def load_guard():
    spec = importlib.util.spec_from_file_location("gateway_guard_test", PLUGIN_DIR / "__init__.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


guard = load_guard()

T, X, P = "terminal", "execute_code", "process"

LIVE_BLOCK = [
    # The two commands the co-founder actually ran on 2026-10-21.
    (T, {"command": "hermes gateway restart", "background": True, "notify_on_complete": True, "timeout": 300}),
    (T, {"command": "env -u _HERMES_GATEWAY hermes gateway restart 2>&1", "background": True, "notify_on_complete": True, "timeout": 300}),
    (T, {"command": "/usr/local/lib/hermes-agent/venv/bin/hermes gateway stop"}),
    (T, {"command": "python -m hermes_cli.main gateway restart"}),
    (T, {"command": "unset _HERMES_GATEWAY; hermes gateway restart"}),
    (T, {"command": "bash -lc 'hermes gateway restart'"}),
    (T, {"command": "hermes update"}),
    (T, {"command": "supervisorctl restart cofounder-gateway"}),
    (T, {"command": "supervisorctl stop all"}),
    (T, {"command": "supervisorctl reload"}),
    (T, {"command": "supervisorctl update"}),
    (T, {"command": "pkill -f 'hermes gateway'"}),
    (T, {"command": "kill $(pgrep -f hermes)"}),
    (T, {"command": "pgrep -f 'gateway run' | xargs kill -TERM"}),
    (T, {"command": "kill -TERM $PPID"}),
    (T, {"command": f"kill -9 {os.getpid()}"}),
    (T, {"command": "pid=$(cat ~/.hermes/gateway.pid)\nkill $pid"}),
    (T, {"command": "systemctl --user restart hermes-gateway"}),
    (T, {"command": "hermes plugins disable gateway-guard"}),
    (T, {"command": "hermes config set plugins.enabled '[]'"}),
    (T, {"command": "rm -rf ~/.hermes/plugins/gateway-guard"}),
    (T, {"command": "sed -i 's/autorestart=true/autorestart=false/' /etc/supervisor/conf.d/cofounder-gateway.conf"}),
    (T, {"command": "echo autorestart=false > /etc/supervisor/conf.d/cofounder-gateway.conf"}),
    (X, {"code": 'import subprocess\nsubprocess.run(["hermes", "gateway", "restart"])'}),
    (X, {"code": "import subprocess\nsubprocess.run([\n    'supervisorctl',\n    'restart',\n    'cofounder-gateway',\n])"}),
    (X, {"code": "import os, signal\nos.kill(os.getppid(), signal.SIGTERM)"}),
    (X, {"code": "import os\nos.environ.pop('_HERMES_GATEWAY', None)"}),
    (X, {"code": "import subprocess, os, signal\npid = int(subprocess.check_output(['pgrep', '-f', 'hermes gateway']))\nos.kill(pid, signal.SIGTERM)"}),
    (P, {"action": "submit", "session_id": "proc_1", "data": "hermes gateway restart\n"}),
    ("mcp_orgo_screen_desktop_action", {"operation": "type", "text": "hermes gateway restart"}),
    ("mcp_orgo_screen_desktop_action", {"operation": "type", "text": "supervisorctl stop cofounder-gateway"}),
    ("mcp_orgo_screen_browser_action", {"operation": "type", "text": "pkill -f hermes"}),
    ("write_file", {"path": "/etc/supervisor/conf.d/cofounder-gateway.conf", "content": "[program:x]"}),
    ("write_file", {"path": "~/.hermes/plugins/gateway-guard/__init__.py", "content": ""}),
    ("write_file", {"path": "~/.hermes/config.yaml", "content": "approvals:\n  mode: smart\n"}),
    ("patch", {"path": "/root/.hermes/config.yaml", "old_string": "  - gateway-guard\n", "new_string": ""}),
    ("patch", {"mode": "patch", "patch": "*** Update File: /root/.hermes/config.yaml\n-  - gateway-guard\n"}),
]

LIVE_ALLOW = [
    (T, {"command": "hermes gateway status"}),
    (T, {"command": "supervisorctl status"}),
    (T, {"command": "supervisorctl status cofounder-gateway"}),
    (T, {"command": "ps aux | grep -i hermes | grep -v grep"}),
    (T, {"command": "tail -n 50 ~/.hermes/logs/gateway.log"}),
    (T, {"command": "grep -i kill ~/.hermes/logs/gateway.log"}),
    (T, {"command": "ls ~/.hermes/plugins/gateway-guard"}),
    (T, {"command": "cat /etc/supervisor/conf.d/cofounder-gateway.conf 2>/dev/null"}),
    (T, {"command": "cd ~/.hermes && git status"}),
    (T, {"command": "hermes plugins list"}),
    (T, {"command": "hermes kanban list"}),
    (T, {"command": "kill %1"}),
    (T, {"command": "grep -rn 'Refusing to restart the gateway from inside' /usr/local/lib/hermes-agent"}),
    (T, {"command": "ls -la /root/company-vault/02\\ Clients/", "background": False}),
    (X, {"code": "print(sum(range(10)))"}),
    (X, {"code": "import subprocess\np = subprocess.Popen(['sleep', '5'])\np.kill()"}),
    (P, {"action": "kill", "session_id": "proc_abc123"}),
    (P, {"action": "poll", "session_id": "proc_abc123"}),
    ("write_file", {"path": "/root/company-vault/00 HQ/notes.md", "content": "hello"}),
    ("write_file", {"path": "~/.hermes/config.yaml", "content": "plugins:\n  enabled:\n  - gateway-guard\n"}),
    ("patch", {"path": "/root/.hermes/config.yaml", "old_string": "timeout: 600", "new_string": "timeout: 300"}),
    ("read_file", {"path": "/etc/supervisor/conf.d/cofounder-gateway.conf"}),
    ("mcp_orgo_screen_desktop_action", {"operation": "type", "text": "Quarterly plan for a customer"}),
    ("mcp_orgo_screen_desktop_action", {"operation": "click", "x": 100, "y": 200}),
    ("mcp_orgo_screen_desktop_action", {"operation": "key", "text": "Return"}),
    ("web_search", {"query": "hermes gateway restart"}),
]

PINNED_AND_REPOSITORY_BLOCK = [
    # Hermes v2026.8.31 names MCP tools mcp__<server>__<tool>.
    ("mcp__orgo_screen__desktop_action", {"operation": "type", "text": "supervisorctl restart cofounder-gateway"}),
    ("mcp__orgo_screen__desktop_action", {"operation": "type", "text": "env -u _HERMES_GATEWAY hermes gateway restart"}),
    # On v2026.8.31 `gateway run --replace` kills the live gateway.
    (T, {"command": "hermes gateway run --replace"}),
    (X, {"code": 'import subprocess\nsubprocess.Popen(["hermes", "gateway", "run", "--replace"])'}),
    (T, {"command": "hermes gateway uninstall"}),
    (T, {"command": "hermes -p head-of-ops plugins disable gateway-guard"}),
    # Named profiles load plugins from their own home.
    ("write_file", {"path": "~/.hermes/profiles/head-of-ops/plugins/gateway-guard/plugin.yaml", "content": ""}),
    ("write_file", {"path": "~/.hermes/profiles/finance-risk/config.yaml", "content": "plugins:\n  enabled: []\n"}),
    (T, {"command": "rm -rf /root/.hermes/profiles/research-analysis/plugins/gateway-guard"}),
    # This repository's lifecycle scripts stop or restart the gateway.
    (T, {"command": "./orgo/emergency-stop.sh"}),
    (T, {"command": "bash orgo/resume-team.sh"}),
    (T, {"command": "env -i ./orgo/emergency-stop.sh"}),
    (T, {"command": "cd ~/ai-cofounder-orgo && ./orgo/connect-tools.sh --profile default"}),
    (T, {"command": "cat orgo/create-team.sh | bash"}),
    (T, {"command": "python3 ~/.hermes/cofounder/services/gateway_service.py restart"}),
    (T, {"command": "sudo python3 services/gateway_service.py stop"}),
    (X, {"code": "import sys\nsys.path.insert(0, '/root/.hermes/cofounder/services')\nimport gateway_service\ngateway_service.restart()"}),
    (T, {"command": "python3 services/fleet_node.py deploy --release /tmp/r --run-id r1 --target-id t1"}),
    (P, {"action": "submit", "session_id": "proc_2", "data": "./orgo/resume-team.sh\n"}),
]

PINNED_AND_REPOSITORY_ALLOW = [
    ("mcp__orgo_screen__desktop_action", {"operation": "type", "text": "Weekly revenue review"}),
    (T, {"command": "cat orgo/emergency-stop.sh"}),
    (T, {"command": "grep -n supervisorctl orgo/emergency-stop.sh orgo/resume-team.sh"}),
    (T, {"command": "sed -n 1,40p orgo/connect-channels.sh"}),
    (T, {"command": "git diff orgo/resume-team.sh"}),
    (T, {"command": "python3 services/gateway_service.py status"}),
    (T, {"command": "python3 ~/.hermes/cofounder/services/gateway_service.py check --running"}),
    (T, {"command": "cat ~/.hermes/profiles/head-of-ops/plugins/gateway-guard/plugin.yaml"}),
]


def call(tool, args, **extra):
    return guard._on_pre_tool_call(tool_name=tool, args=args, task_id="t", session_id="s", **extra)


class GatewayGuardTests(unittest.TestCase):
    def test_live_suite_has_sixty_three_cases(self):
        self.assertEqual(37, len(LIVE_BLOCK))
        self.assertEqual(26, len(LIVE_ALLOW))

    def test_blocks_every_self_restart_path(self):
        for tool, args in LIVE_BLOCK + PINNED_AND_REPOSITORY_BLOCK:
            with self.subTest(tool=tool, args=args):
                result = call(tool, args)
                self.assertIsNotNone(result, "should block")
                self.assertEqual("block", result["action"])

    def test_allows_reading_and_ordinary_work(self):
        for tool, args in LIVE_ALLOW + PINNED_AND_REPOSITORY_ALLOW:
            with self.subTest(tool=tool, args=args):
                result = call(tool, args)
                self.assertIsNone(result, result and result["message"][:120])

    def test_block_matches_pinned_hermes_directive_contract(self):
        # Hermes v2026.8.31 passes these keyword arguments to pre_tool_call and
        # ignores a block directive whose message is missing or empty.
        result = call(
            T,
            {"command": "hermes gateway restart"},
            tool_call_id="call-1",
            turn_id="turn-1",
            api_request_id="req-1",
            middleware_trace=[],
        )
        self.assertEqual({"action", "message"}, set(result))
        self.assertIsInstance(result["message"], str)
        self.assertTrue(result["message"])
        self.assertIn(f"supervisorctl restart {guard.PROGRAM}", result["message"])
        self.assertIn("/restart", result["message"])
        self.assertNotIn("Justin", result["message"])

    def test_fails_open_on_unexpected_arguments(self):
        for args in (None, "hermes gateway restart", 42, {"command": None}):
            with self.subTest(args=args):
                if isinstance(args, str):
                    self.assertIsNone(call("write_file", args))
                else:
                    self.assertIsNone(call(T, args))
        with mock.patch.object(guard, "_check_exec", side_effect=RuntimeError("boom")):
            self.assertIsNone(call(T, {"command": "hermes gateway restart"}))

    def test_registers_only_pre_tool_call(self):
        class Context:
            def __init__(self):
                self.hooks = []

            def register_hook(self, name, callback):
                self.hooks.append((name, callback))

        context = Context()
        guard.register(context)
        self.assertEqual(["pre_tool_call"], [name for name, _ in context.hooks])

    def test_manifest_declares_the_hook_and_matches_its_directory(self):
        manifest = (PLUGIN_DIR / "plugin.yaml").read_text().splitlines()
        self.assertIn("name: gateway-guard", manifest)
        self.assertIn("hooks:", manifest)
        self.assertIn("  - pre_tool_call", manifest)
        self.assertEqual("gateway-guard", PLUGIN_DIR.name)


if __name__ == "__main__":
    unittest.main()
