#!/usr/bin/env python3
"""Run the co-founder's Hermes gateway as one supervisord program.

On an Orgo computer, Hermes v2026.8.31 sees a container with neither systemd
nor s6. There, ``hermes gateway install`` and ``start`` only print guidance,
and ``restart`` stops the gateway and then runs a new one in the foreground
of the calling shell, so nothing restarts the gateway when it exits. This
helper owns the lifecycle instead:

* one supervisord program, started with ``--external-supervisor`` so Hermes
  hands /restart and ``hermes update`` back to supervisord;
* every stop and start goes through supervisorctl, so supervisord never
  undoes a stop;
* an emergency stop also sets ``autostart=false`` in the program file, so the
  gateway stays down across a reboot until the owner resumes it;
* nothing that could restart the gateway runs from inside the gateway.
  supervisorctl restart is a stop RPC followed by a start RPC from the
  client, and the gateway's drain kills that client before the start.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import pwd
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from typing import Optional


PROGRAM = "cofounder-gateway"
# Hermes's own stop budget with default settings is 70 s: a 30 s cron drain,
# a 10 s cleanup reserve and 30 s of headroom. Its systemd unit uses the same.
STOP_WAIT_SECONDS = 90
MIN_STOP_WAIT_SECONDS = 60
# EX_CONFIG. Hermes exits 78 on a fatal configuration error, and its systemd
# unit sets RestartPreventExitStatus=78. Every other exit, 0 and 1 included,
# is restarted.
FATAL_CONFIG_EXIT = 78
HERMES_CANDIDATES = ("/usr/local/lib/hermes-agent/venv/bin/hermes",)
LIVE_STATES = {"RUNNING", "STARTING"}


class GatewayServiceError(RuntimeError):
    pass


def conf_dir() -> Path:
    return Path(os.environ.get("COFOUNDER_SUPERVISOR_CONF_DIR", "/etc/supervisor/conf.d"))


def conf_path() -> Path:
    return conf_dir() / f"{PROGRAM}.conf"


def hermes_home() -> Path:
    return Path(os.environ.get("HERMES_HOME") or Path.home() / ".hermes").expanduser().resolve()


def elevate() -> list[str]:
    if os.geteuid() == 0:
        return []
    if shutil.which("sudo") is None:
        raise GatewayServiceError("supervisord is controlled as root and this account has no sudo")
    return ["sudo"]


def supervisor_available() -> bool:
    return shutil.which("supervisorctl") is not None


def supervisorctl(*args: str) -> subprocess.CompletedProcess[str]:
    if not supervisor_available():
        raise GatewayServiceError("this computer has no supervisorctl; the Orgo Hermes template ships supervisord")
    return subprocess.run([*elevate(), "supervisorctl", *args], text=True, capture_output=True)


def state() -> Optional[str]:
    """The program's supervisord state, or None when supervisord has not loaded it."""
    for line in supervisorctl("status", PROGRAM).stdout.splitlines():
        parts = line.split()
        if len(parts) > 1 and parts[0] == PROGRAM:
            return parts[1].upper()
    return None


def supervised_pid() -> int:
    if not supervisor_available():
        return 0
    value = supervisorctl("pid", PROGRAM).stdout.strip()
    return int(value) if value.isdigit() else 0


def ancestors() -> set[int]:
    pids: set[int] = set()
    pid = os.getppid()
    while pid > 1 and pid not in pids:
        pids.add(pid)
        try:
            status = Path(f"/proc/{pid}/status").read_text()
        except OSError:
            break
        match = re.search(r"^PPid:\s+(\d+)", status, re.MULTILINE)
        pid = int(match.group(1)) if match else 0
    return pids


def inside_gateway() -> bool:
    """True when this process descends from the running gateway."""
    if os.environ.get("_HERMES_GATEWAY") == "1" or os.environ.get("SUPERVISOR_PROCESS_NAME") == PROGRAM:
        return True
    # The environment can be stripped; the process tree cannot.
    pid = supervised_pid()
    return pid > 1 and pid in ancestors()


def refuse_inside_gateway(action: str) -> None:
    if inside_gateway():
        raise GatewayServiceError(
            f"refusing to {action} {PROGRAM} from inside the gateway it would stop. "
            "Ask the owner to send /restart in Slack or Telegram, or to run "
            f"`supervisorctl restart {PROGRAM}` from a shell on this computer"
        )


def hermes_binary(home: Path) -> str:
    """The Hermes the setup scripts use, so the gateway runs the verified install."""
    found = shutil.which("hermes")
    if found is not None:
        return os.path.realpath(found)
    for candidate in (*HERMES_CANDIDATES, str(home / "hermes-agent/venv/bin/hermes")):
        if os.access(candidate, os.X_OK):
            return candidate
    raise GatewayServiceError("Hermes is not installed; run ./orgo/setup.sh first")


def require_external_supervisor_flag(hermes: str) -> None:
    """Fail before touching the program file if this Hermes predates the flag."""
    result = subprocess.run([hermes, "gateway", "run", "--help"], text=True, capture_output=True)
    if "--external-supervisor" not in result.stdout + result.stderr:
        raise GatewayServiceError(
            f"{hermes} does not support `gateway run --external-supervisor`; "
            "install the reviewed Hermes release with ./orgo/setup.sh first"
        )


def service_path(hermes: str, home: Path) -> str:
    entries = [str(Path(hermes).parent), str(home / ".local/bin")]
    node = shutil.which("node")
    if node:
        entries.append(str(Path(node).parent))
    entries += ["/usr/local/sbin", "/usr/local/bin", "/usr/sbin", "/usr/bin", "/sbin", "/bin"]
    return ":".join(dict.fromkeys(entries))


def _conf_value(value: str) -> str:
    if any(character in value for character in '"\r\n'):
        raise GatewayServiceError(f"unsupported character in supervisor setting {value!r}")
    return value.replace("%", "%%")


def render(*, hermes: str, user: str, home: Path, root: Path, path: str, autostart: bool = True) -> str:
    environment = ",".join(f'{key}="{_conf_value(value)}"' for key, value in (
        ("HOME", str(home)),
        ("HERMES_HOME", str(root)),
        ("PATH", path),
        # The marker Hermes's own systemd unit exports: the default gateway
        # then ignores `hermes profile use` instead of switching identity.
        ("HERMES_SUPERVISED_CHILD", "1"),
    ))
    command = shlex.join((hermes, "gateway", "run", "--external-supervisor"))
    return f"""; {PROGRAM}: the AI Co-Founder's Hermes gateway (Slack, Telegram, A2A,
; Kanban dispatch and cron for every multiplexed profile). Written by
; services/gateway_service.py in the ai-cofounder-orgo repository; rerunning
; ./orgo/create-team.sh rewrites it.
;
; Owner commands, from a shell on this computer:
;   supervisorctl status {PROGRAM}
;   supervisorctl restart {PROGRAM}   (or /restart in Slack or Telegram)
;   ./orgo/emergency-stop.sh and ./orgo/resume-team.sh
; Do not run `hermes gateway stop|restart` from a shell. Hermes does not see
; supervisord here: stop is undone by autorestart, and restart starts a second
; gateway in the foreground of that shell. The gateway-guard plugin stops the
; agent itself from doing any of this.
;
; autostart=false means the team is emergency-stopped.
; stopasgroup stays off so the gateway can drain and clean up its own tool
; processes; killasgroup covers the SIGKILL after stopwaitsecs.
[program:{PROGRAM}]
command={_conf_value(command)}
directory={_conf_value(str(home))}
user={_conf_value(user)}
environment={environment}
autostart={"true" if autostart else "false"}
autorestart=unexpected
exitcodes={FATAL_CONFIG_EXIT}
startsecs=10
startretries=5
stopsignal=TERM
stopwaitsecs={STOP_WAIT_SECONDS}
stopasgroup=false
killasgroup=true
stdout_logfile=/var/log/{PROGRAM}.log
redirect_stderr=true
stdout_logfile_maxbytes=10MB
stdout_logfile_backups=3
"""


def program_settings(text: str) -> dict[str, str]:
    match = re.search(rf"^\[program:{re.escape(PROGRAM)}\]\s*$(.*?)(?=^\[|\Z)", text, re.MULTILINE | re.DOTALL)
    if match is None:
        return {}
    settings = {}
    for line in match.group(1).splitlines():
        key, sep, value = line.partition("=")
        if sep and not key.lstrip().startswith(";"):
            settings[key.strip()] = value.strip()
    return settings


def configured_autostart() -> Optional[bool]:
    try:
        value = program_settings(conf_path().read_text()).get("autostart")
    except OSError:
        return None
    return None if value is None else value.lower() == "true"


def write_conf(text: str) -> bool:
    target = conf_path()
    try:
        if target.read_text() == text:
            return False
    except OSError:
        pass
    with tempfile.NamedTemporaryFile("w", delete=False, prefix=f".{PROGRAM}.", suffix=".conf") as handle:
        handle.write(text)
        temp = handle.name
    try:
        result = subprocess.run([*elevate(), "install", "-m", "0644", temp, str(target)], text=True, capture_output=True)
        if result.returncode:
            raise GatewayServiceError(f"could not write {target}: {result.stderr.strip()}")
    finally:
        os.unlink(temp)
    return True


def set_autostart(enabled: bool) -> None:
    text = conf_path().read_text()
    updated, count = re.subn(r"^autostart\s*=.*$", f"autostart={'true' if enabled else 'false'}", text, flags=re.MULTILINE)
    if count != 1:
        raise GatewayServiceError(f"{conf_path()} does not have exactly one autostart setting")
    write_conf(updated)


def apply_config() -> None:
    """Load this program's file into supervisord without touching other programs."""
    for args in (("reread",), ("update", PROGRAM)):
        result = supervisorctl(*args)
        if result.returncode or "ERROR" in result.stdout:
            raise GatewayServiceError(f"supervisorctl {' '.join(args)} failed: {(result.stdout + result.stderr).strip()}")


def ensure_running() -> None:
    if state() not in LIVE_STATES:
        supervisorctl("start", PROGRAM)
    current = state()
    if current not in LIVE_STATES:
        raise GatewayServiceError(f"{PROGRAM} did not start ({current or 'not loaded'}); see /var/log/{PROGRAM}.log")


def stop_program() -> None:
    supervisorctl("stop", PROGRAM)
    current = state()
    if current in LIVE_STATES or current == "STOPPING":
        raise GatewayServiceError(f"{PROGRAM} did not stop ({current})")


def stop_unsupervised_gateway(all_profiles: bool = False) -> None:
    """Stop gateways supervisord does not own.

    A tmux, foreground or template-started gateway for this HERMES_HOME holds
    the profile lock, and the supervised program would exit "already running"
    until it went FATAL. Hermes's `gateway stop` is safe here only because the
    supervised program is not running when this is called.
    """
    if shutil.which("hermes"):
        subprocess.run(["hermes", "gateway", "stop", *(["--all"] if all_profiles else [])], text=True, capture_output=True)


def install(restart: bool = False, reapply: bool = False) -> str:
    refuse_inside_gateway("restart" if restart else "install")
    root = hermes_home()
    home = Path(os.environ.get("HOME") or pwd.getpwuid(os.getuid()).pw_dir)
    hermes = hermes_binary(root)
    require_external_supervisor_flag(hermes)
    autostart = configured_autostart() is not False
    text = render(
        hermes=hermes,
        user=pwd.getpwuid(os.getuid()).pw_name,
        home=home,
        root=root,
        path=service_path(hermes, home),
        autostart=autostart,
    )
    current = state()
    if current not in LIVE_STATES:
        stop_unsupervised_gateway()
    changed = write_conf(text)
    if changed or reapply or current is None:
        # Adds the program, or restarts it with the new settings.
        apply_config()
    elif restart and current in LIVE_STATES and autostart:
        result = supervisorctl("restart", PROGRAM)
        if result.returncode:
            raise GatewayServiceError(f"supervisorctl restart failed: {(result.stdout + result.stderr).strip()}")
    if not autostart:
        return (f"{PROGRAM} is emergency-stopped and stays stopped. New settings load when "
                "the owner runs ./orgo/resume-team.sh.")
    ensure_running()
    return f"{PROGRAM} is running under supervisord."


def restart() -> str:
    return install(restart=True)


def start() -> str:
    """Resume after an emergency stop."""
    refuse_inside_gateway("start")
    reapply = configured_autostart() is False
    if reapply:
        set_autostart(True)
    return install(reapply=reapply)


def stop() -> str:
    """Emergency stop: down now and after a reboot, until start().

    Allowed from inside the gateway, because supervisord finishes a stop even
    if this client is killed during the drain.
    """
    problems = []
    if supervisor_available():
        if conf_path().exists():
            # Persist first, so a reboot keeps the gateway down even if this
            # process is killed during the drain below.
            try:
                set_autostart(False)
            except (GatewayServiceError, OSError) as exc:
                problems.append(f"it may start again after a reboot: {exc}")
        if state() is not None:
            stop_program()
            try:
                apply_config()
            except GatewayServiceError as exc:
                problems.append(str(exc))
    # Supervised or not, no gateway runs during an emergency stop.
    stop_unsupervised_gateway(all_profiles=True)
    if problems:
        raise GatewayServiceError(f"{PROGRAM} is stopped, but " + "; ".join(problems))
    return f"{PROGRAM} is stopped and stays stopped across a reboot."


def pause() -> str:
    """Stop for a managed update; restart() brings it back unless emergency-stopped."""
    refuse_inside_gateway("pause")
    if supervisor_available() and state() is not None:
        stop_program()
    else:
        stop_unsupervised_gateway()
    return f"{PROGRAM} is paused."


def check(require_running: bool = False) -> list[str]:
    try:
        settings = program_settings(conf_path().read_text())
    except OSError:
        return [f"{conf_path()} is missing; run ./orgo/create-team.sh"]
    if not settings:
        return [f"{conf_path()} has no [program:{PROGRAM}] section"]
    problems = []
    autorestart = settings.get("autorestart", "").lower()
    codes = {code.strip() for code in settings.get("exitcodes", "0").split(",")}
    if autorestart == "unexpected" and codes & {"0", "1"}:
        problems.append(f"autorestart=unexpected with exitcodes={settings.get('exitcodes', '0')} leaves a clean exit down")
    elif autorestart not in {"true", "unexpected"}:
        problems.append(f"autorestart={autorestart or 'unset'} leaves the gateway down after it exits")
    try:
        stop_wait = int(settings.get("stopwaitsecs", "10"))
    except ValueError:
        stop_wait = 0
    if stop_wait < MIN_STOP_WAIT_SECONDS:
        problems.append(f"stopwaitsecs={stop_wait} SIGKILLs the gateway before its drain finishes")
    command = settings.get("command", "")
    if "gateway run" not in command or "--external-supervisor" not in command:
        problems.append("command must be `hermes gateway run --external-supervisor`")
    if "--replace" in command:
        problems.append("a supervised gateway must not run with --replace")
    current = state() if supervisor_available() else None
    if current is None:
        problems.append(f"supervisord has not loaded {PROGRAM}")
    elif require_running and current != "RUNNING":
        stopped = settings.get("autostart", "").lower() == "false"
        problems.append(f"{PROGRAM} is {current}" + (" (emergency-stopped)" if stopped else ""))
    return problems


def status() -> str:
    current = state() if supervisor_available() else None
    stopped = configured_autostart() is False
    return f"{PROGRAM}: {current or 'not loaded'}" + (" (emergency-stopped)" if stopped else "")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("install", "restart", "start", "stop", "pause", "status"):
        commands.add_parser(name)
    check_parser = commands.add_parser("check")
    check_parser.add_argument("--running", action="store_true")
    args = parser.parse_args()

    if args.command == "check":
        problems = check(require_running=args.running)
        for problem in problems:
            print(f"Gateway service: {problem}", file=sys.stderr)
        return 1 if problems else 0
    action = {
        "install": install,
        "restart": restart,
        "start": start,
        "stop": stop,
        "pause": pause,
        "status": status,
    }[args.command]
    print(action())
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GatewayServiceError as exc:
        print(f"Gateway service stopped: {exc}", file=sys.stderr)
        raise SystemExit(1)
