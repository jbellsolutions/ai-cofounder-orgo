"""The supervised gateway: program file, lifecycle scripts, and their callers."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "services/gateway_service.py"
sys.path.insert(0, str(ROOT / "services"))
import gateway_service  # noqa: E402

# A supervisorctl that keeps program state in a JSON file and loads the program
# file on `update`, the way supervisord does for one group.
FAKE_SUPERVISORCTL = r'''
import json, os, re, sys
from pathlib import Path
state_path = Path(os.environ["FAKE_SUPERVISOR_STATE"])
state = json.loads(state_path.read_text()) if state_path.exists() else {}
args = sys.argv[1:]
with open(os.environ["FAKE_LOG"], "a") as log:
    log.write("supervisorctl " + " ".join(args) + "\n")
command, name = args[0], (args[1] if len(args) > 1 else "")
program = state.get(name)
code = 0
if command == "status":
    print(f"{name}   {program['state']}   pid 4242, uptime 0:00:05" if program else f"{name}: ERROR (no such process)")
elif command == "pid":
    print(4999999 if program and program["state"] == "RUNNING" else 0)
elif command == "reread":
    print("No config updates to processes")
elif command == "update":
    text = (Path(os.environ["COFOUNDER_SUPERVISOR_CONF_DIR"]) / f"{name}.conf").read_text()
    autostart = re.search(r"^autostart=(\w+)$", text, re.M).group(1) == "true"
    state[name] = {"state": "RUNNING" if autostart else "STOPPED"}
    print(f"{name}: {'updated' if program else 'added'} process group")
elif command in ("start", "stop", "restart"):
    if program is None:
        print(f"{name}: ERROR (no such process)")
        code = 7
    else:
        program["state"] = "STOPPED" if command == "stop" else "RUNNING"
        print(f"{name}: {command}ed")
state_path.write_text(json.dumps(state))
sys.exit(code)
'''


class SupervisedFixture:
    def __init__(self, directory: Path):
        self.bin = directory / "bin"
        self.conf_dir = directory / "conf.d"
        self.home = directory / "home"
        self.log = directory / "calls.log"
        self.state_file = directory / "supervisor.json"
        for path in (self.bin, self.conf_dir, self.home / ".hermes"):
            path.mkdir(parents=True)
        self.log.write_text("")
        self._tool("supervisorctl", f"#!{sys.executable}\n{FAKE_SUPERVISORCTL}")
        self._tool("sudo", '#!/bin/sh\nexec "$@"\n')
        self._tool("hermes", (
            '#!/bin/sh\n'
            'printf "hermes %s\\n" "$*" >> "$FAKE_LOG"\n'
            '[ "$*" = "gateway run --help" ] && echo "  --external-supervisor  Declare an external process manager"\n'
            'exit 0\n'
        ))
        inherited = {
            key: value for key, value in os.environ.items()
            if key not in {"_HERMES_GATEWAY", "SUPERVISOR_PROCESS_NAME", "HERMES_HOME"}
        }
        self.env = {
            **inherited,
            "PATH": f"{self.bin}:{os.environ.get('PATH', '')}",
            "HOME": str(self.home),
            "HERMES_HOME": str(self.home / ".hermes"),
            "FAKE_LOG": str(self.log),
            "FAKE_SUPERVISOR_STATE": str(self.state_file),
            "COFOUNDER_SUPERVISOR_CONF_DIR": str(self.conf_dir),
        }

    def _tool(self, name: str, body: str) -> None:
        path = self.bin / name
        path.write_text(body)
        path.chmod(0o755)

    def run(self, *command: str, **env: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(command, env={**self.env, **env}, text=True, capture_output=True)

    def helper(self, *args: str, **env: str) -> subprocess.CompletedProcess[str]:
        return self.run(sys.executable, str(SERVICE), *args, **env)

    def calls(self) -> list[str]:
        return self.log.read_text().splitlines()

    def clear(self) -> None:
        self.log.write_text("")

    def program_state(self) -> str | None:
        state = json.loads(self.state_file.read_text()) if self.state_file.exists() else {}
        return state.get(gateway_service.PROGRAM, {}).get("state")

    def settings(self) -> dict[str, str]:
        return gateway_service.program_settings((self.conf_dir / f"{gateway_service.PROGRAM}.conf").read_text())


class GatewayServiceTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.fx = SupervisedFixture(Path(directory.name))

    def assertOk(self, result):
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_program_file_restarts_clean_exits_and_lets_the_drain_finish(self):
        text = gateway_service.render(
            hermes="/usr/local/lib/hermes-agent/venv/bin/hermes",
            user="root",
            home=Path("/root"),
            root=Path("/root/.hermes"),
            path="/opt/100%/bin:/usr/bin",
        )
        settings = gateway_service.program_settings(text)
        self.assertEqual("/usr/local/lib/hermes-agent/venv/bin/hermes gateway run --external-supervisor", settings["command"])
        self.assertNotIn("--replace", settings["command"])
        self.assertEqual("true", settings["autostart"])
        # Mirrors Hermes's systemd unit: Restart=always, RestartPreventExitStatus=78.
        self.assertEqual("unexpected", settings["autorestart"])
        self.assertEqual("78", settings["exitcodes"])
        self.assertGreaterEqual(int(settings["stopwaitsecs"]), 70)
        self.assertEqual("false", settings["stopasgroup"])
        self.assertEqual("true", settings["killasgroup"])
        self.assertIn('HERMES_HOME="/root/.hermes"', settings["environment"])
        self.assertIn('HERMES_SUPERVISED_CHILD="1"', settings["environment"])
        self.assertIn("/opt/100%%/bin", settings["environment"])

    def test_program_name_matches_the_guard(self):
        spec = importlib.util.spec_from_file_location("gateway_guard_name", ROOT / "plugins/gateway-guard/__init__.py")
        guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guard)
        self.assertEqual(gateway_service.PROGRAM, guard.PROGRAM)

    def test_emergency_stop_and_resume_go_through_supervisorctl(self):
        fx = self.fx
        self.assertOk(fx.helper("restart"))
        self.assertEqual("RUNNING", fx.program_state())
        calls = fx.calls()
        # An unsupervised gateway for this home is stopped before the program starts.
        self.assertLess(calls.index("hermes gateway stop"), calls.index("supervisorctl update cofounder-gateway"))
        self.assertOk(fx.helper("check", "--running"))

        fx.clear()
        self.assertOk(fx.run(str(ROOT / "orgo/emergency-stop.sh")))
        calls = fx.calls()
        self.assertIn("hermes config set kanban.dispatch_in_gateway false", calls)
        self.assertIn("supervisorctl stop cofounder-gateway", calls)
        # Strays are swept only after supervisord has stopped its own program.
        self.assertLess(calls.index("supervisorctl stop cofounder-gateway"), calls.index("hermes gateway stop --all"))
        self.assertEqual("STOPPED", fx.program_state())
        self.assertEqual("false", fx.settings()["autostart"])

        # Configuration scripts restart the gateway, but never out of an emergency stop.
        fx.clear()
        result = fx.helper("restart")
        self.assertOk(result)
        self.assertIn("emergency-stopped", result.stdout)
        self.assertEqual("STOPPED", fx.program_state())
        self.assertFalse([call for call in fx.calls() if re.match(r"supervisorctl (start|restart)\b", call)])

        fx.clear()
        self.assertOk(fx.run(str(ROOT / "orgo/resume-team.sh")))
        self.assertIn("hermes config set kanban.dispatch_in_gateway true", fx.calls())
        self.assertEqual("true", fx.settings()["autostart"])
        self.assertEqual("RUNNING", fx.program_state())
        self.assertOk(fx.helper("check", "--running"))

    def test_refuses_to_restart_from_inside_the_gateway(self):
        fx = self.fx
        self.assertOk(fx.helper("restart"))
        for marker in ({"_HERMES_GATEWAY": "1"}, {"SUPERVISOR_PROCESS_NAME": gateway_service.PROGRAM}):
            with self.subTest(marker=marker):
                for action in ("restart", "install", "start", "pause"):
                    fx.clear()
                    result = fx.helper(action, **marker)
                    self.assertEqual(1, result.returncode)
                    self.assertIn("refusing", result.stderr)
                    self.assertIn("/restart", result.stderr)
                    self.assertFalse([call for call in fx.calls() if re.match(r"supervisorctl (start|stop|restart|update)\b", call)])
                    self.assertEqual("RUNNING", fx.program_state())
        # A stop still completes: supervisord finishes it even if the client dies.
        self.assertOk(fx.helper("stop", _HERMES_GATEWAY="1"))
        self.assertEqual("STOPPED", fx.program_state())

    def test_refuses_a_hermes_without_external_supervisor_support(self):
        fx = self.fx
        fx._tool("hermes", '#!/bin/sh\nprintf "hermes %s\\n" "$*" >> "$FAKE_LOG"\nexit 0\n')
        result = fx.helper("restart")
        self.assertEqual(1, result.returncode)
        self.assertIn("--external-supervisor", result.stderr)
        self.assertFalse((fx.conf_dir / f"{gateway_service.PROGRAM}.conf").exists())
        self.assertIsNone(fx.program_state())

    def test_check_rejects_a_program_that_stays_down(self):
        fx = self.fx
        self.assertOk(fx.helper("restart"))
        conf = fx.conf_dir / f"{gateway_service.PROGRAM}.conf"
        good = conf.read_text()
        for old, new, problem in (
            ("autorestart=unexpected", "autorestart=false", "autorestart=false"),
            ("exitcodes=78", "exitcodes=0,78", "leaves a clean exit down"),
            ("stopwaitsecs=90", "stopwaitsecs=10", "stopwaitsecs=10"),
            ("--external-supervisor", "--replace", "--external-supervisor"),
        ):
            with self.subTest(change=new):
                conf.write_text(good.replace(old, new))
                result = fx.helper("check")
                self.assertEqual(1, result.returncode)
                self.assertIn(problem, result.stderr)
        conf.write_text(good)
        self.assertOk(fx.helper("check"))

    def test_no_caller_controls_the_gateway_around_the_supervisor(self):
        # On Orgo, `hermes gateway restart` runs a second gateway in the caller's
        # foreground, and `stop` is undone by autorestart.
        bare = re.compile(r"""hermes["',\s]+gateway["',\s]+(?:stop|restart|start|install)\b""")
        callers = sorted((ROOT / "orgo").glob("*.sh")) + sorted((ROOT / "services").glob("*.py"))
        for path in callers:
            if path == SERVICE:
                continue
            with self.subTest(path=path.name):
                self.assertIsNone(bare.search(path.read_text()))
        for script in ("create-team.sh", "connect-channels.sh", "connect-tools.sh", "connect-a2a.sh", "connect-agent-stack.sh"):
            with self.subTest(script=script):
                self.assertIn("services/gateway_service.py\" restart", (ROOT / "orgo" / script).read_text())
        self.assertIn("gateway_service.py\" stop", (ROOT / "orgo/emergency-stop.sh").read_text())
        self.assertIn("gateway_service.py\" start", (ROOT / "orgo/resume-team.sh").read_text())

    def test_fleet_node_pauses_and_restarts_through_the_helper(self):
        import fleet_node

        quiet = contextlib.ExitStack()
        quiet.enter_context(contextlib.redirect_stdout(io.StringIO()))
        quiet.enter_context(contextlib.redirect_stderr(io.StringIO()))
        with quiet:
            with mock.patch.object(fleet_node.gateway_service, "pause", return_value="paused") as pause:
                self.assertTrue(fleet_node.gateway("pause"))
                pause.assert_called_once_with()
            with mock.patch.object(fleet_node.gateway_service, "restart", side_effect=gateway_service.GatewayServiceError("down")):
                self.assertFalse(fleet_node.gateway("restart"))
        paths = {str(path) for path in fleet_node.managed_paths(Path("/home/owner"))}
        self.assertIn("/home/owner/.hermes/plugins/gateway-guard", paths)
        self.assertIn("/home/owner/.hermes/profiles/finance-risk/plugins/gateway-guard", paths)

    def test_agent_factory_activation_installs_the_guard_and_does_not_restart(self):
        import agent_factory

        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "home"
            state = home / ".hermes/cofounder"
            calls = []

            def fake_run(*args):
                calls.append(args)
                if args[:3] == ("hermes", "profile", "create"):
                    (home / ".hermes/profiles" / args[3]).mkdir(parents=True)

            with (
                mock.patch.object(Path, "home", return_value=home),
                mock.patch.object(agent_factory.Factory, "_run", staticmethod(fake_run)),
                mock.patch.object(agent_factory.Factory, "_config_set", staticmethod(lambda *args: None)),
            ):
                factory = agent_factory.Factory(state_dir=state, assets_dir=ROOT)
                proposal = factory.propose("content-distribution", "Create a measured editorial workflow")
                with (
                    mock.patch.object(sys.stdin, "isatty", return_value=True),
                    mock.patch("builtins.input", return_value=f"APPROVE {proposal['proposal_id']}"),
                ):
                    factory.approve(proposal["proposal_id"], "owner")
                active = factory.activate(proposal["proposal_id"])

            name = active["profile_name"]
            self.assertTrue((home / ".hermes/profiles" / name / "plugins/gateway-guard/plugin.yaml").is_file())
            self.assertIn(("hermes", "-p", name, "plugins", "enable", "gateway-guard", "--no-allow-tool-override"), calls)
            self.assertFalse([call for call in calls if call[:2] == ("hermes", "gateway")])
            self.assertTrue(active["restart_required"])


if __name__ == "__main__":
    unittest.main()
