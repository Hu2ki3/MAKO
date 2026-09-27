#!/usr/bin/env python3
"""Portable safety tests for the game-scoped Gamescope VRR lease."""

from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
import io
import json
import os
import subprocess
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch


source = Path(__file__).with_name("mako-vrr-lease")
loader = SourceFileLoader("mako_vrr_lease", str(source))
spec = spec_from_loader(loader.name, loader)
module = module_from_spec(spec)
loader.exec_module(module)


class VrrLeaseTests(unittest.TestCase):
    def test_decision_log_emits_only_on_state_changes(self):
        output = io.StringIO()
        with patch.object(module.sys, "stderr", output):
            decisions = module.DecisionLog()
            decisions.record("no-matched-frame-generation-context")
            decisions.record("no-matched-frame-generation-context")
            decisions.record("write-confirmed-off")
        self.assertEqual(output.getvalue().splitlines(), [
            "MAKO Renderer: Gamescope VRR lease decision=no-matched-frame-generation-context",
            "MAKO Renderer: Gamescope VRR lease decision=write-confirmed-off",
        ])

    def test_only_a_vrr_capable_active_display_allows_an_override(self):
        with patch.object(module.subprocess, "run", return_value=
                          subprocess.CompletedProcess([], 0,
                              " - Display Flags: 0x3\n", "")):
            self.assertFalse(module.read_vrr_capability())
        with patch.object(module.subprocess, "run", return_value=
                          subprocess.CompletedProcess([], 0,
                              " - Display Flags: 0x7\n", "")):
            self.assertTrue(module.read_vrr_capability())
        with patch.object(module.subprocess, "run", return_value=
                          subprocess.CompletedProcess([], 0,
                              "gamescope_control info unavailable\n", "")):
            self.assertIsNone(module.read_vrr_capability())

    def test_display_identity_changes_when_gamescope_socket_is_replaced(self):
        with patch.dict(os.environ, {
            "XDG_RUNTIME_DIR": "/run/user/1000",
            "GAMESCOPE_WAYLAND_DISPLAY": "gamescope-test",
        }), patch.object(Path, "stat", side_effect=[
            SimpleNamespace(st_mode=0o140777, st_dev=12, st_ino=34),
            SimpleNamespace(st_mode=0o140777, st_dev=12, st_ino=35),
        ]):
            original = module.display_identity()
            self.assertEqual(original, (12, 34))
            self.assertNotEqual(module.display_identity(), original)

    def test_gamescope_vrr_read_uses_the_verified_x_root(self):
        with patch.object(module, "read_xroot_vrr", return_value=(True, "ok")):
            self.assertEqual(module.read_vrr(), (True, "ok"))
        with patch.object(module, "read_xroot_vrr", return_value=(None, "x-display-unavailable")):
            self.assertEqual(module.read_vrr(), (None, "x-display-unavailable"))

    def test_xroot_readback_matches_the_gamescope_pid_and_root_server(self):
        properties = {
            ":2": {"GAMESCOPE_PID": 123, "GAMESCOPE_XWAYLAND_SERVER_ID": 2},
            ":0": {"GAMESCOPE_PID": 123, "GAMESCOPE_XWAYLAND_SERVER_ID": 0,
                   "GAMESCOPE_VRR_ENABLED": 0},
        }
        with patch.dict(os.environ, {"DISPLAY": ":2"}), \
             patch.object(module, "xroot_properties",
                          side_effect=lambda display: properties.get(display)):
            self.assertEqual(module.read_xroot_vrr(), (False, "ok"))
            properties[":0"]["GAMESCOPE_PID"] = 999
            self.assertEqual(module.read_xroot_vrr(), (None, "x-root-unverified"))

    def test_xroot_query_parses_only_cardinal_properties(self):
        output = ("GAMESCOPE_PID(CARDINAL) = 123\n"
                  "GAMESCOPE_XWAYLAND_SERVER_ID(CARDINAL) = 0\n"
                  "GAMESCOPE_VRR_ENABLED(CARDINAL) = 1\n")
        with patch.object(module.subprocess, "run", return_value=
                          subprocess.CompletedProcess([], 0, output, "")):
            self.assertEqual(module.xroot_properties(":0"), {
                "GAMESCOPE_PID": 123,
                "GAMESCOPE_XWAYLAND_SERVER_ID": 0,
                "GAMESCOPE_VRR_ENABLED": 1,
            })

    def test_verified_x_session_without_vrr_feedback_fails_closed(self):
        with patch.object(module, "read_xroot_vrr", return_value=(None, "x-vrr-unavailable")):
            self.assertEqual(module.read_vrr(), (None, "x-vrr-unavailable"))

    def test_gamescope_vrr_write_uses_the_verified_root_property(self):
        with patch.object(module, "XROOT_CACHE", (":2", 123, ":0")), \
             patch.object(module, "read_xroot_vrr", return_value=(True, "ok")), \
             patch.object(module, "read_vrr", return_value=(False, "ok")), \
             patch.object(module.subprocess, "run", return_value=
                          subprocess.CompletedProcess([], 0, "", "")) as run:
            self.assertTrue(module.write_vrr(False, True))
            self.assertEqual(run.call_args.args[0], (
                "xprop", "-display", ":0", "-root", "-f",
                "GAMESCOPE_VRR_ENABLED", "32c", "-set", "GAMESCOPE_VRR_ENABLED", "0",
            ))
        with patch.object(module, "read_xroot_vrr", return_value=(None, "x-root-unverified")), \
             patch.object(module.subprocess, "run") as run:
            self.assertFalse(module.write_vrr(False, True))
            run.assert_not_called()
        with patch.object(module, "XROOT_CACHE", (":2", 123, ":0")), \
             patch.object(module, "read_xroot_vrr", return_value=(False, "ok")), \
             patch.object(module.subprocess, "run") as run:
            self.assertFalse(module.write_vrr(False, True))
            run.assert_not_called()

    def test_service_starts_outside_game_scope_with_session_environment(self):
        with patch.dict(os.environ, {
            "GAMESCOPE_WAYLAND_DISPLAY": "gamescope-test",
            "WAYLAND_DISPLAY": "gamescope-test",
            "DISPLAY": ":1",
            "XAUTHORITY": "/tmp/gamescope-test-xauthority",
            "XDG_RUNTIME_DIR": "/run/user/1000",
            "MAKO_CONFIG": "/tmp/mako-game.toml",
        }), patch.object(module.shutil, "which", return_value="/usr/bin/systemd-run"), \
             patch.object(Path, "stat", return_value=SimpleNamespace(
                 st_mode=0o140777, st_dev=12, st_ino=34)), \
             patch.object(module, "process_identity", return_value=(1, 9876)), \
             patch.object(module.subprocess, "run",
                          return_value=subprocess.CompletedProcess([], 0, "", "")) as run:
            self.assertEqual(module.start_service("123", "123-4-5"), 0)
            command = run.call_args.args[0]
            self.assertIn("--user", command)
            self.assertIn("--collect", command)
            self.assertIn("--setenv=GAMESCOPE_WAYLAND_DISPLAY=gamescope-test", command)
            self.assertIn("--setenv=DISPLAY=:1", command)
            self.assertIn("--setenv=XAUTHORITY=/tmp/gamescope-test-xauthority", command)
            self.assertIn("--setenv=MAKO_CONFIG=/tmp/mako-game.toml", command)
            self.assertEqual(command[-5:], ["123", "123-4-5", "9876", "12", "34"])

    def test_restore_only_while_value_is_still_ours(self):
        state = {"value": True}
        clock = {"now": 0.0}

        def write(value, expected):
            self.assertEqual(state["value"], expected)
            state["value"] = value
            return True

        with patch.object(module, "read_vrr", side_effect=lambda: (state["value"], "ok")), \
             patch.object(module, "write_vrr", side_effect=write), \
             patch.object(module.time, "monotonic", side_effect=lambda: clock["now"]):
            lease = module.VrrLease()
            self.assertEqual(lease.update("off"), "write-confirmed-off")
            self.assertFalse(state["value"])
            self.assertEqual(lease.update("off"), "holding-off")
            lease.restore()
            self.assertTrue(state["value"])

            lease.update("off")
            state["value"] = True  # Steam changed the live session.
            clock["now"] += module.HOLD_CHECK_SECONDS
            self.assertEqual(lease.update("off"), "yielded-to-external-change")
            self.assertTrue(lease.yielded)
            lease.restore()
            self.assertTrue(state["value"])

    def test_stable_hold_skips_subprocess_reads_but_restoration_reads_fresh(self):
        state = {"value": True}
        clock = {"now": 0.0}

        def write(value, expected):
            self.assertEqual(state["value"], expected)
            state["value"] = value
            return True

        with patch.object(module, "read_vrr", side_effect=lambda: (state["value"], "ok")) as read, \
             patch.object(module, "write_vrr", side_effect=write), \
             patch.object(module.time, "monotonic", side_effect=lambda: clock["now"]):
            lease = module.VrrLease()
            self.assertEqual(lease.update("off"), "write-confirmed-off")
            for second in range(1, int(module.HOLD_CHECK_SECONDS)):
                clock["now"] = float(second)
                self.assertEqual(lease.update("off"), "holding-off")
            self.assertEqual(read.call_count, 1)
            self.assertTrue(lease.restore())
            self.assertEqual(read.call_count, 2)
            self.assertTrue(state["value"])

    def test_stable_hold_detects_external_change_at_next_check(self):
        state = {"value": True}
        clock = {"now": 0.0}

        def write(value, expected):
            self.assertEqual(state["value"], expected)
            state["value"] = value
            return True

        with patch.object(module, "read_vrr", side_effect=lambda: (state["value"], "ok")) as read, \
             patch.object(module, "write_vrr", side_effect=write), \
             patch.object(module.time, "monotonic", side_effect=lambda: clock["now"]):
            lease = module.VrrLease()
            self.assertEqual(lease.update("off"), "write-confirmed-off")
            state["value"] = True  # Steam's live choice takes effect immediately.
            clock["now"] = module.HOLD_CHECK_SECONDS - 1
            self.assertEqual(lease.update("off"), "holding-off")
            self.assertEqual(read.call_count, 1)
            clock["now"] = module.HOLD_CHECK_SECONDS
            self.assertEqual(lease.update("off"), "yielded-to-external-change")
            self.assertTrue(lease.yielded)
            self.assertEqual(read.call_count, 2)
            self.assertTrue(lease.restore())
            self.assertTrue(state["value"])

    def test_noop_and_failures_have_distinct_decisions(self):
        with patch.object(module, "read_vrr", return_value=(False, "ok")), \
             patch.object(module, "write_vrr") as write:
            lease = module.VrrLease()
            self.assertEqual(lease.update("off"), "already-off")
            write.assert_not_called()

        with patch.object(module, "read_vrr", return_value=(None, "x-display-unavailable")):
            self.assertEqual(module.VrrLease().update("on"), "query-x-display-unavailable")

        with patch.object(module, "read_vrr", return_value=(True, "ok")), \
             patch.object(module, "write_vrr", return_value=False):
            lease = module.VrrLease()
            self.assertEqual(lease.update("off"), "write-not-verified")
            self.assertTrue(lease.baseline)
            self.assertFalse(lease.applied)

    def test_failed_restore_keeps_the_original_value_for_retry(self):
        with patch.object(module, "read_vrr", side_effect=[(True, "ok"), (None, "x-display-unavailable"), (False, "ok")]), \
             patch.object(module, "write_vrr", return_value=True) as write:
            lease = module.VrrLease()
            lease.update("off")
            self.assertFalse(lease.restore())
            self.assertEqual(lease.applied, False)
            self.assertTrue(lease.restore())
            self.assertIsNone(lease.applied)
            self.assertEqual(write.call_args_list[-1].args, (True, False))

    def test_exit_restoration_retries_transient_failure(self):
        lease = SimpleNamespace(restore=Mock(side_effect=[False, True]))
        with patch.object(module, "display_identity", return_value=(12, 34)), \
             patch.object(module.time, "sleep") as sleep:
            self.assertTrue(module.restore_on_exit(
                lease, module.DecisionLog(), (12, 34)))
        self.assertEqual(lease.restore.call_count, 2)
        sleep.assert_called_once_with(module.POLL_SECONDS)

    def test_exit_restoration_stops_after_bounded_failures(self):
        lease = SimpleNamespace(restore=Mock(return_value=False))
        output = io.StringIO()
        with patch.object(module, "display_identity", return_value=(12, 34)), \
             patch.object(module.time, "sleep") as sleep, \
             patch.object(module.sys, "stderr", output):
            self.assertFalse(module.restore_on_exit(
                lease, module.DecisionLog(), (12, 34)))
        self.assertEqual(lease.restore.call_count, module.RESTORE_ATTEMPTS)
        self.assertEqual(sleep.call_count, module.RESTORE_ATTEMPTS - 1)
        self.assertIn("decision=restore-unverified-at-exit", output.getvalue())

    def test_exit_restoration_skips_replacement_session(self):
        lease = SimpleNamespace(restore=Mock())
        with patch.object(module, "display_identity", return_value=(12, 35)):
            self.assertTrue(module.restore_on_exit(
                lease, module.DecisionLog(), (12, 34)))
        lease.restore.assert_not_called()

    def test_unverified_write_keeps_the_baseline_for_restoration(self):
        with patch.object(module, "read_vrr", side_effect=[(True, "ok"), (False, "ok")]), \
             patch.object(module, "write_vrr", side_effect=[False, True]) as write:
            lease = module.VrrLease()
            self.assertEqual(lease.update("off"), "write-not-verified")
            self.assertTrue(lease.restore())
            self.assertEqual(write.call_args_list[-1].args, (True, False))

    def test_delayed_readback_does_not_yield_or_lose_restoration(self):
        with patch.object(module, "read_vrr", side_effect=[
                (True, "ok"), (True, "ok"), (False, "ok"), (False, "ok")]), \
             patch.object(module, "write_vrr", side_effect=[False, True]) as write:
            lease = module.VrrLease()
            self.assertEqual(lease.update("off"), "write-not-verified")
            self.assertEqual(lease.update("off"), "awaiting-write-readback")
            self.assertFalse(lease.yielded)
            self.assertEqual(lease.update("off"), "write-confirmed-off")
            self.assertTrue(lease.restore())
            self.assertEqual(write.call_args_list[-1].args, (True, False))

    def test_live_profile_change_rearms_after_steam_change(self):
        state = {"value": True}
        clock = {"now": 0.0}

        def write(value, expected):
            self.assertEqual(state["value"], expected)
            state["value"] = value
            return True

        with patch.object(module, "read_vrr", side_effect=lambda: (state["value"], "ok")), \
             patch.object(module, "write_vrr", side_effect=write), \
             patch.object(module.time, "monotonic", side_effect=lambda: clock["now"]):
            lease = module.VrrLease()
            lease.update("off")
            state["value"] = True
            clock["now"] += module.HOLD_CHECK_SECONDS
            lease.update("off")
            lease.update("on")
            self.assertFalse(lease.yielded)
            lease.update("off")
            self.assertFalse(state["value"])

    def test_only_live_status_from_this_launch_selects_profile(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            status_dir = root / "runtime-state"
            status_dir.mkdir()
            pid = os.getpid()
            tick = module.process_identity(pid)[1]
            status = {"pid": pid, "process_start_ticks": tick,
                      "requested": {"name": "Game", "gamescope_vrr_mode": "off",
                                    "frame_generation_provisioned": True,
                                    "frame_generation_enabled": True}}
            (status_dir / f"{pid}-{tick}-frame-generation-1.json").write_text(json.dumps(status))
            observed = set()
            self.assertEqual(
                module.active_mode(status_dir, pid, tick, "123-456", observed),
                "off",
            )
            status["requested"]["frame_generation_enabled"] = False
            (status_dir / f"{pid}-{tick}-frame-generation-1.json").write_text(json.dumps(status))
            self.assertEqual(
                module.active_mode(status_dir, pid, tick, "123-456", observed),
                "follow-steam",
            )
            status["process_start_ticks"] += 1
            (status_dir / f"{pid}-{tick}-frame-generation-1.json").write_text(json.dumps(status))
            self.assertIsNone(module.active_mode(status_dir, pid, tick, "123-456", observed))


if __name__ == "__main__":
    unittest.main()
