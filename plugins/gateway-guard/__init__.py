"""gateway-guard: keep the co-founder from taking its own gateway offline.

On 2026-10-21 a co-founder hit Hermes's built-in "refusing to restart the
gateway from inside the gateway" check, stripped _HERMES_GATEWAY to get past
it, and its restart helper was killed along with the gateway it was
restarting. The gateway stayed down until the owner restarted it by hand.

The gateway runs under supervisord as ``cofounder-gateway`` with autorestart,
so an agent-initiated restart could also become a restart loop. This hook
refuses any tool call that would stop, restart or signal the gateway or
supervisord, that references _HERMES_GATEWAY, that runs one of this
repository's gateway lifecycle scripts, or that would disable this plugin or
edit the supervisor config. Only the owner restarts the gateway, from a shell
outside it.

Hermes fails open when a hook raises, so the checks stay plain regexes and
the hook returns None on any internal error.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional

# Kept equal to services/gateway_service.py PROGRAM; a repository test checks.
PROGRAM = "cofounder-gateway"

_EXEC_TOOLS = {"terminal", "execute_code", "process"}
_FILE_TOOLS = {"write_file", "patch"}
# MCP tools are scanned like command tools: a desktop-control MCP can type a
# command into a desktop terminal, which has no _HERMES_GATEWAY at all. This
# prefix matches both mcp__server__tool (Hermes v2026.8.31) and mcp_server_tool.
_MCP_PREFIX = "mcp_"

_FLAGS = re.IGNORECASE | re.DOTALL

# Tokens may be separated by whitespace, quotes, commas or brackets, so the
# list-form argv used from execute_code (["hermes", "gateway", "restart"])
# matches the same rules as a shell command.
_SEP = r"[\s'\",\[\]]+"

# "hermes" as a program or path component, but not the ~/.hermes data dir.
_HERMES = r"(?<!\.)\bhermes\b"
# "gateway" as a process name, but not a log file being read.
_GATEWAY = r"\bgateway\b(?![-.\w]*\.log)"
_KILL = r"\b(?:pkill|killall|kill|killpg|send_signal)\b"
_WRITE = r"(?<![0-9&])>|\b(?:rm|mv|cp|sed|tee|truncate|unlink|chmod|chown|ln|install|rmtree|rename|replace|write|write_text|open)\b"

_EXEC_RULES = [
    (r"_HERMES_GATEWAY",
     "it references _HERMES_GATEWAY, the marker Hermes uses to refuse self-restarts"),
    (rf"\bgateway{_SEP}(?:stop|restart|uninstall)\b",
     "it would stop or restart the Hermes gateway"),
    (rf"\bgateway{_SEP}run\b.{{0,120}}?--replace\b",
     "`hermes gateway run --replace` would replace the running gateway"),
    (rf"{_HERMES}(?:_cli(?:\.main)?)?{_SEP}update\b",
     "`hermes update` restarts the gateway"),
    (r"\b(?:systemctl|service)\b.{0,80}?\b(?:stop|restart|kill)\b.{0,80}?hermes",
     "it would stop or restart a Hermes service"),
    (rf"\bsupervisorctl\b.{{0,120}}?\b(?:stop|restart|signal|remove)\b.{{0,120}}?\b(?:{PROGRAM}|all)\b",
     "it would stop or restart the supervised gateway"),
    (r"\bsupervisorctl\b.{0,120}?\b(?:shutdown|reload|update)\b",
     "it would restart supervisord and every program it runs"),
    (r"\bsupervisor\.(?:stop|restart|shutdown|signal|remove|reload)",
     "it would control supervisord over its RPC interface"),
    (rf"\bplugins{_SEP}(?:disable|remove|rm|uninstall){_SEP}(?:\S*/)?gateway-guard\b",
     "it would disable or remove the gateway-guard plugin"),
    (r"\bplugins\.(?:enabled|disabled)\b",
     "it would change which Hermes plugins load"),
    (rf"plugins/gateway-guard.*(?:{_WRITE})|(?:{_WRITE}).*plugins/gateway-guard",
     "it would modify the gateway-guard plugin"),
    (rf"/etc/supervisor\b.*(?:{_WRITE})|(?:{_WRITE}).*/etc/supervisor\b",
     "it would change the supervisord configuration"),
]
_EXEC_RULES = [(re.compile(p, _FLAGS), why) for p, why in _EXEC_RULES]

_KILL_RE = re.compile(_KILL, _FLAGS)
_KILL_TARGET_RE = re.compile(
    rf"{_HERMES}|{_GATEWAY}|\bsupervisord\b|\$PPID\b|\bgetppid\b", _FLAGS
)

# This repository's lifecycle entry points. Each stops or restarts the gateway
# through supervisord, so running one from a tool call is a self-restart too.
# Reading or grepping them stays allowed.
_LIFECYCLE_SCRIPT_RE = re.compile(
    r"(?<![\w.-])(?:emergency-stop|resume-team|create-team|connect-channels"
    r"|connect-tools|connect-a2a|connect-agent-stack)\.sh\b",
    re.IGNORECASE,
)
_LIFECYCLE_HELPER_RE = re.compile(
    r"\bgateway_service(?:\.py)?\b.*\b(?:install|restart|start|stop|pause)\b"
    r"|\bfleet_node(?:\.py)?\b.*\b(?:deploy|rollback)\b",
    re.IGNORECASE,
)
_PIPE_TO_SHELL_RE = re.compile(r"\|\s*(?:sudo\s+)?(?:ba|z|da)?sh\b|\|\s*python", re.IGNORECASE)
_SEGMENT_RE = re.compile(r"[;&|\n]+")
_WORD_RE = re.compile(r"[^\s'\"`$(){}\[\],]+")
_ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_WRAPPERS = {"sudo", "doas", "exec", "nohup", "time", "command", "builtin", "env", "nice"}
_READERS = {
    "cat", "less", "more", "head", "tail", "grep", "egrep", "fgrep", "rg", "sed",
    "awk", "wc", "ls", "stat", "file", "diff", "git", "nl", "cut", "sort",
    "md5sum", "sha256sum", "shasum", "readlink", "realpath", "test",
}


def _strings(value: Any) -> List[str]:
    """Every string inside a tool's arguments, at any depth."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for v in value.values() for s in _strings(v)]
    if isinstance(value, (list, tuple)):
        return [s for v in value for s in _strings(v)]
    return []


def _protected_pids() -> List[int]:
    """The gateway (this process), its parent, and supervisord."""
    pids = [os.getpid(), os.getppid()]
    try:
        with open("/var/run/supervisord.pid") as f:
            pids.append(int(f.read().strip()))
    except (OSError, ValueError):
        pass
    return [pid for pid in pids if pid > 1]


def _first_command(segment: str) -> str:
    """The program a shell segment runs, skipping assignments and wrappers."""
    for word in _WORD_RE.findall(segment):
        if word.startswith("-") or _ASSIGNMENT_RE.match(word):
            continue
        base = word.rsplit("/", 1)[-1].lower()
        if base in _WRAPPERS:
            continue
        return base
    return ""


def _runs_lifecycle_entry_point(text: str) -> bool:
    for segment in _SEGMENT_RE.split(text):
        if _LIFECYCLE_SCRIPT_RE.search(segment) or _LIFECYCLE_HELPER_RE.search(segment):
            if _first_command(segment) not in _READERS:
                return True
    return bool(_LIFECYCLE_SCRIPT_RE.search(text) and _PIPE_TO_SHELL_RE.search(text))


def _check_exec(text: str) -> Optional[str]:
    for rule, why in _EXEC_RULES:
        if rule.search(text):
            return why
    if _runs_lifecycle_entry_point(text):
        return "it would run a co-founder script that stops or restarts the gateway"
    if _KILL_RE.search(text):
        if _KILL_TARGET_RE.search(text):
            return "it would signal the gateway, a Hermes process or supervisord"
        for pid in _protected_pids():
            if re.search(rf"\b{pid}\b", text):
                return f"it would signal pid {pid}, the gateway or supervisord"
    return None


def _is_guarded_path(path: str) -> bool:
    path = os.path.expanduser(path)
    return "plugins/gateway-guard" in path or path.startswith("/etc/supervisor")


def _is_hermes_config(path: str) -> bool:
    path = os.path.expanduser(path)
    return os.path.basename(path) == "config.yaml" and ".hermes" in path


def _check_file(tool_name: str, args: Dict[str, Any]) -> Optional[str]:
    path = args.get("path") if isinstance(args.get("path"), str) else ""
    if path and _is_guarded_path(path):
        return "it would modify the gateway-guard plugin or the supervisord configuration"
    if tool_name == "write_file" and path and _is_hermes_config(path):
        if "gateway-guard" not in str(args.get("content") or ""):
            return "rewriting config.yaml without gateway-guard would disable this guard"
    if tool_name == "patch":
        if path and _is_hermes_config(path) and "gateway-guard" in str(args.get("old_string") or ""):
            return "it would remove gateway-guard from config.yaml"
        patch_text = str(args.get("patch") or "")
        if "gateway-guard" in patch_text or "/etc/supervisor" in patch_text:
            return "it would modify the gateway-guard plugin or the supervisord configuration"
    return None


def _block(reason: str) -> Dict[str, str]:
    return {
        "action": "block",
        "message": (
            f"BLOCKED by gateway-guard: {reason}. You run inside the Hermes gateway and "
            "may not stop, restart or signal it, touch _HERMES_GATEWAY, or change this "
            "guard or the supervisor config. Do not look for another way around this. "
            "If a restart is needed (for example to load a config change), say so and ask "
            f"the owner to run `supervisorctl restart {PROGRAM}` from a shell on this "
            "computer, or to send /restart in Slack or Telegram."
        ),
    }


def _on_pre_tool_call(tool_name: str = "", args: Any = None, **_: Any) -> Optional[Dict[str, str]]:
    try:
        if tool_name in _EXEC_TOOLS or tool_name.startswith(_MCP_PREFIX):
            reason = _check_exec("\n".join(_strings(args)))
        elif tool_name in _FILE_TOOLS:
            reason = _check_file(tool_name, args if isinstance(args, dict) else {})
        else:
            return None
    except Exception:
        return None
    return _block(reason) if reason else None


def register(ctx) -> None:
    ctx.register_hook("pre_tool_call", _on_pre_tool_call)
