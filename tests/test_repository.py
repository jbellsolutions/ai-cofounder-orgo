from __future__ import annotations

import json
import importlib.util
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_PROFILES = {
    "default",
    "head-of-ops",
    "revenue-partner",
    "affiliate-revenue-partner",
    "finance-risk",
    "research-analysis",
}


def load(relative: str):
    return json.loads((ROOT / relative).read_text())


class RepositoryContractTests(unittest.TestCase):
    def test_release_is_pinned_to_reviewed_hermes_version(self):
        deployment = load("orgo/deployment.json")
        self.assertEqual("v2026.8.31", deployment["runtime"]["hermes_release"])
        self.assertEqual("0.21.0", deployment["runtime"]["hermes_version"])
        self.assertEqual("29112bef099274229cadff79cdff7bf7b99c4b77", deployment["runtime"]["hermes_commit"])
        self.assertEqual("85ef536d455e51ab67aa74d79272efd49fe717597dbaadfd3cca179a905f4706", deployment["runtime"]["install_script_sha256"])
        setup = (ROOT / "orgo/setup.sh").read_text()
        self.assertIn(deployment["runtime"]["hermes_commit"], setup)
        self.assertIn(deployment["runtime"]["install_script_sha256"], setup)
        self.assertIn("sha256sum", setup)

    def test_org_registry_has_exact_initial_hierarchy(self):
        registry = load("org/registry.json")
        profiles = registry["profiles"]
        by_id = {profile["id"]: profile for profile in profiles}
        self.assertEqual(EXPECTED_PROFILES, set(by_id))
        self.assertEqual("human-owner", by_id["default"]["manager"])
        self.assertEqual("default", by_id["head-of-ops"]["manager"])
        self.assertEqual("default", by_id["revenue-partner"]["manager"])
        self.assertEqual("revenue-partner", by_id["affiliate-revenue-partner"]["manager"])
        self.assertEqual("default", by_id["finance-risk"]["manager"])
        self.assertEqual("default", by_id["research-analysis"]["manager"])
        self.assertEqual(len(profiles), len({profile["display_name"] for profile in profiles}))

    def test_all_profiles_have_unique_a2a_identity_and_safe_inbound_tools(self):
        profiles = load("org/registry.json")["profiles"]
        paths = set()
        tenants = set()
        for profile in profiles:
            self.assertTrue(profile["a2a"]["enabled"])
            self.assertIn("a2a", profile["toolsets"]["cli"])
            self.assertIn("kanban", profile["toolsets"]["cli"])
            self.assertNotIn("a2a", profile["toolsets"]["a2a"])
            self.assertNotIn("terminal", profile["toolsets"]["a2a"])
            self.assertNotIn("delegation", profile["toolsets"]["a2a"])
            self.assertNotIn(profile["a2a"]["path"], paths)
            self.assertNotIn(profile["a2a"]["tenant"], tenants)
            paths.add(profile["a2a"]["path"])
            tenants.add(profile["a2a"]["tenant"])

    def test_only_cofounder_owns_root_work_and_factory(self):
        profiles = load("org/registry.json")["profiles"]
        root_owners = [profile["id"] for profile in profiles if profile["kanban"]["may_own_root"]]
        factory_users = [profile["id"] for profile in profiles if "mcp-agent-factory" in profile["toolsets"]["cli"]]
        self.assertEqual(["default"], root_owners)
        self.assertEqual(["default"], factory_users)

    def test_every_profile_has_identity_and_triggerable_role_skill(self):
        for profile in load("org/registry.json")["profiles"]:
            role_name = profile["role_skill"].split("/")[-1]
            soul = ROOT / "profiles" / profile["id"] / "SOUL.md"
            skill = ROOT / "skills/roles" / role_name / "SKILL.md"
            self.assertTrue(soul.is_file(), soul)
            self.assertTrue(skill.is_file(), skill)
            self.assertIn(f"name: {role_name}", skill.read_text())

    def test_permissions_encode_approval_and_permanent_denials(self):
        policy = load("policies/permissions.json")
        self.assertEqual("allow", policy["actions"]["research.read"]["decision"])
        self.assertEqual("approval", policy["actions"]["financial.spend"]["decision"])
        self.assertEqual("approval-and-verify", policy["actions"]["data.delete"]["decision"])
        for action in (
            "credential.disclose",
            "permission.self_expand",
            "approval.fabricate",
            "audit.alter_or_delete",
            "profile.delete",
            "infrastructure.delete",
            "agent_identity.payment_method_change",
            "fleet.skip_canary",
        ):
            self.assertIn(action, policy["always_deny_to_agents"])

    def test_agent_factory_policy_has_no_dangerous_surface(self):
        policy = load("policies/agent-factory.json")
        self.assertTrue(policy["persistent_activation_requires_human_approval"])
        self.assertFalse(policy["activation_defaults"]["allow_terminal"])
        self.assertFalse(policy["activation_defaults"]["allow_external_write_tools"])
        for forbidden in ("delete-profile", "provision-computer", "change-billing", "grant-credential", "change-permissions", "arbitrary-command"):
            self.assertIn(forbidden, policy["never_exposed_as_factory_tools"])
        mcp = (ROOT / "services/agent_factory_mcp.py").read_text()
        self.assertNotIn("def agent_delete", mcp)
        self.assertNotIn("def agent_approve", mcp)

    def test_agent_factory_fails_closed_without_owner_approval(self):
        sys.path.insert(0, str(ROOT / "services"))
        import agent_factory

        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "home"
            state = home / ".hermes/cofounder"
            with mock.patch.object(Path, "home", return_value=home):
                factory = agent_factory.Factory(state_dir=state, assets_dir=ROOT)
                proposal = factory.propose("content-distribution", "Create a measured editorial workflow")
                self.assertEqual("proposed", proposal["status"])
                with self.assertRaisesRegex(ValueError, "approval"):
                    factory.activate(proposal["proposal_id"])
                with (
                    mock.patch.object(sys.stdin, "isatty", return_value=True),
                    mock.patch("builtins.input", return_value=f"APPROVE {proposal['proposal_id']}"),
                ):
                    approved = factory.approve(proposal["proposal_id"], "owner")
                self.assertEqual("approved", approved["status"])
                self.assertEqual(approved["proposal_hash"], approved["approval"]["proposal_hash"])

    def test_installer_enables_multiplex_kanban_a2a_and_hard_stops(self):
        source = (ROOT / "services/install_profiles.py").read_text()
        for required in (
            "gateway.multiplex_profiles",
            "gateway.multiplex_profile_allowlist",
            "gateway.platforms.a2a.extra.agents",
            "kanban.orchestrator_profile",
            "kanban.max_in_progress_per_profile",
            "tool_loop_guardrails.hard_stop_enabled",
            "approvals.mode",
            "mcp_servers.agent-factory",
            "mcp_servers.agent-cards",
            "mcp_servers.agentmail",
            "mcp_servers.agentphone",
            "mcp_servers.latitude",
        ):
            self.assertIn(required, source)
        self.assertIn('settings[f"platform_toolsets.{platform}"]', source)
        for required in (
            '"gateway.platforms.slack.enabled": False',
            '"gateway.platforms.telegram.enabled": False',
            '"gateway.platforms.a2a.enabled": False',
            '"mcp_servers.agent-factory.enabled": False',
        ):
            self.assertIn(required, source)

    def test_installer_assembles_six_isolated_profile_homes(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory)
            user_home = fixture / "user"
            hermes_home = user_home / ".hermes"
            bin_dir = fixture / "bin"
            bin_dir.mkdir(parents=True)
            hermes_home.mkdir(parents=True)
            (hermes_home / "config.yaml").write_text("model:\n  provider: openrouter\n")
            (hermes_home / "SOUL.md").write_text("Original generic agent.\n")
            (hermes_home / ".env").write_text(
                "OPENROUTER_API_KEY=model-only-fixture\n"
                "SLACK_BOT_TOKEN=channel-fixture\n"
            )
            fake = bin_dir / "hermes"
            fake.write_text(
                "#!/usr/bin/env bash\n"
                "set -euo pipefail\n"
                "printf '%s\\n' \"$*\" >> \"$TEST_HERMES_LOG\"\n"
                "if [ \"${1:-}\" = profile ] && [ \"${2:-}\" = create ]; then\n"
                "  name=$3\n"
                "  dest=\"$HOME/.hermes/profiles/$name\"\n"
                "  mkdir -p \"$dest\"\n"
                "  cp \"$HOME/.hermes/config.yaml\" \"$dest/config.yaml\"\n"
                "  cp \"$HOME/.hermes/.env\" \"$dest/.env\"\n"
                "  cp \"$HOME/.hermes/SOUL.md\" \"$dest/SOUL.md\"\n"
                "fi\n"
            )
            fake.chmod(0o755)
            log = fixture / "hermes.log"
            env = {
                **os.environ,
                "HOME": str(user_home),
                "PATH": f"{bin_dir}:{os.environ.get('PATH', '')}",
                "TEST_HERMES_LOG": str(log),
            }
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "services/install_profiles.py"),
                    "--root",
                    str(ROOT),
                    "--home",
                    str(hermes_home),
                    "--mode",
                    "all",
                ],
                env=env,
                text=True,
                capture_output=True,
            )
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertIn("# AI Co-Founder", (hermes_home / "SOUL.md").read_text())
            self.assertTrue((hermes_home / "cofounder/company/01-CONSTITUTION.md").is_file())
            self.assertTrue((hermes_home / "cofounder/services/agent_factory_mcp.py").is_file())
            self.assertTrue((hermes_home / "plugins/latitude-observer/plugin.yaml").is_file())
            for profile in EXPECTED_PROFILES - {"default"}:
                profile_home = hermes_home / "profiles" / profile
                self.assertTrue((profile_home / "SOUL.md").is_file(), profile)
                self.assertTrue((profile_home / "skills/shared/a2a-collaboration/SKILL.md").is_file(), profile)
                profile_env = (profile_home / ".env").read_text()
                self.assertIn("OPENROUTER_API_KEY", profile_env)
                self.assertNotIn("SLACK_BOT_TOKEN", profile_env)
            command_log = log.read_text()
            self.assertIn("gateway.platforms.a2a.enabled false", command_log)
            self.assertIn("mcp_servers.agent-factory.enabled false", command_log)
            self.assertIn("mcp_servers.agent-cards.enabled false", command_log)
            self.assertIn("mcp_servers.latitude.enabled false", command_log)

            existing = hermes_home / "profiles/head-of-ops/.env"
            existing.write_text(existing.read_text() + "CUSTOM_CONNECTOR_FIXTURE=preserved\n")
            second = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "services/install_profiles.py"),
                    "--root", str(ROOT),
                    "--home", str(hermes_home),
                    "--mode", "all",
                ],
                env=env,
                text=True,
                capture_output=True,
            )
            self.assertEqual(0, second.returncode, second.stdout + second.stderr)
            self.assertIn("CUSTOM_CONNECTOR_FIXTURE=preserved", existing.read_text())

    def test_managed_stack_versions_scopes_and_privacy_are_explicit(self):
        manifest = load("stack/manifest.json")
        self.assertEqual("2026.09.01.1", manifest["stack_version"])
        bundle = manifest["components"]["agent_bundle"]
        self.assertEqual("0.2.2", bundle["version"])
        self.assertEqual("default-profile-only-mediated-to-team-over-a2a", bundle["scope"])
        self.assertFalse(bundle["production_cards_default"])
        latitude = manifest["components"]["latitude"]
        self.assertEqual("metadata", latitude["default_capture_mode"])
        self.assertEqual("sanitized", latitude["semantic_capture_mode"])
        registry = {profile["id"]: profile for profile in load("org/registry.json")["profiles"]}
        for tool in ("mcp-agent-cards", "mcp-agentmail", "mcp-agentphone", "mcp-latitude"):
            self.assertIn(tool, registry["default"]["toolsets"]["cli"])
        for profile_id in EXPECTED_PROFILES - {"default"}:
            self.assertNotIn("mcp-agent-cards", registry[profile_id]["toolsets"]["cli"])

    def test_agent_bundle_import_is_atomic_and_never_prints_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory)
            home = fixture / ".hermes"
            config = fixture / "bundle.json"
            config.write_text(json.dumps({"mcpServers": {
                "agent-cards": {"url": "https://example.invalid/mcp"},
                "agentmail": {"headers": {"x-api-key": "mail-fixture"}},
                "agentphone": {"env": {"AGENTPHONE_API_KEY": "phone-fixture"}},
            }}))
            bin_dir = fixture / "bin"
            bin_dir.mkdir()
            fake = bin_dir / "hermes"
            fake.write_text("#!/usr/bin/env bash\nexit 0\n")
            fake.chmod(0o755)
            result = subprocess.run(
                [sys.executable, str(ROOT / "services/import_agent_bundle.py"), "--config", str(config), "--home", str(home), "--sandbox"],
                env={**os.environ, "PATH": f"{bin_dir}:{os.environ.get('PATH', '')}"},
                text=True,
                capture_output=True,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertNotIn("mail-fixture", result.stdout + result.stderr)
            self.assertNotIn("phone-fixture", result.stdout + result.stderr)
            self.assertEqual(0o600, (home / ".env").stat().st_mode & 0o777)

    def test_latitude_observer_defaults_to_metadata_and_registers_every_hook(self):
        path = ROOT / "plugins/latitude-observer/__init__.py"
        spec = importlib.util.spec_from_file_location("latitude_observer_test", path)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        with mock.patch.dict(os.environ, {"LATITUDE_CAPTURE_MODE": "metadata"}, clear=False):
            self.assertIsNone(module._content({"private": "fixture"}))
        with (
            mock.patch.dict(os.environ, {"LATITUDE_CAPTURE_MODE": "sanitized"}, clear=False),
            mock.patch.object(module, "_redact", return_value="[REDACTED]"),
        ):
            self.assertEqual("[REDACTED]", module._content({"private": "fixture"}))
        class Context:
            def __init__(self):
                self.hooks = []
            def register_hook(self, name, callback):
                self.hooks.append((name, callback))
        context = Context()
        module.register(context)
        self.assertIn("pre_tool_call", {name for name, _ in context.hooks})
        self.assertIn("on_session_finalize", {name for name, _ in context.hooks})

    def test_fleet_inventory_and_remote_commands_are_bounded(self):
        sys.path.insert(0, str(ROOT / "services"))
        import fleet_manager

        example = load("fleet/inventory.example.json")
        self.assertEqual(2, len(fleet_manager.validate_inventory(example)))
        active = json.loads(json.dumps(example))
        active["targets"] = [active["targets"][0]]
        active["targets"][0]["enabled"] = True
        targets = fleet_manager.validate_inventory(active, require_canary=True)
        script = fleet_manager.remote_script(targets[0], "a" * 40, "run-123", "deploy")
        self.assertIn("fleet_node.py", script)
        self.assertNotIn("eval", script)
        active["targets"][0]["repository"] = "https://github.com/untrusted/example.git"
        with self.assertRaisesRegex(ValueError, "allowlist"):
            fleet_manager.validate_inventory(active, require_canary=True)

    def test_fleet_node_snapshot_restores_managed_state_without_touching_env(self):
        sys.path.insert(0, str(ROOT / "services"))
        import fleet_node

        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "home"
            state = home / ".local/state/ai-guy-fleet"
            hermes = home / ".hermes"
            state.mkdir(parents=True)
            hermes.mkdir(parents=True)
            (hermes / "config.yaml").write_text("mode: before\n")
            (hermes / ".env").write_text("PRIVATE_FIXTURE=unchanged\n")
            backup = fleet_node.snapshot(home, state, "test-run")
            (hermes / "config.yaml").write_text("mode: after\n")
            (hermes / "SOUL.md").write_text("new file\n")
            fleet_node.restore(home, backup)
            self.assertEqual("mode: before\n", (hermes / "config.yaml").read_text())
            self.assertFalse((hermes / "SOUL.md").exists())
            self.assertEqual("PRIVATE_FIXTURE=unchanged\n", (hermes / ".env").read_text())

    def test_slack_manifest_is_ai_cofounder_and_owner_controllable(self):
        manifest = load("slack-manifest.json")
        self.assertEqual("AI Co-Founder", manifest["display_information"]["name"])
        self.assertIn("agent_view", manifest["features"])
        scopes = manifest["oauth_config"]["scopes"]["bot"]
        events = manifest["settings"]["event_subscriptions"]["bot_events"]
        self.assertIn("assistant:write", scopes)
        self.assertIn("app_context_changed", events)
        self.assertTrue(manifest["settings"]["socket_mode_enabled"])
        commands = {row["command"] for row in manifest["features"]["slash_commands"]}
        for command in ("/stop", "/approve", "/deny", "/agents", "/goal", "/kanban"):
            self.assertIn(command, commands)

    def test_public_files_contain_no_obvious_secret_values(self):
        excluded = {".git", "__pycache__"}
        patterns = (
            re.compile(r"sk-(?:live|proj|or-v1)-[A-Za-z0-9_-]{12,}"),
            re.compile(r"xox[baprs]-[A-Za-z0-9-]{12,}"),
            re.compile(r"(?i)(?:api[_ -]?key|token)\s*[:=]\s*['\"]?[A-Za-z0-9_-]{24,}"),
        )
        for path in ROOT.rglob("*"):
            if not path.is_file() or any(part in excluded for part in path.parts):
                continue
            body = path.read_text(errors="ignore")
            for pattern in patterns:
                self.assertIsNone(pattern.search(body), str(path))

    def test_all_local_markdown_links_resolve(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "tests/validate_links.py")],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
