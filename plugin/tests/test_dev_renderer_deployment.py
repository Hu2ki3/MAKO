"""Exercise direct deployment against competing native installation layouts."""

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from py_modules.mako_plugin import constants as paths
from py_modules.mako_plugin.layer_manifests import manifest_library


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "dev_renderer_selection", PLUGIN_ROOT / "scripts/dev-renderer-selection.py")
selection = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(selection)


class DevRendererDeploymentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="mako dev deployment ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "home"
        self.plugin = self.root / "checkout/plugin"
        self.engine = self.root / "checkout/engine"
        self.installed_plugin = self.home / "homebrew/plugins/Mako"
        for relative in (
            "scripts/deploy-dev.sh", "scripts/dev-renderer-selection.py",
            "scripts/read_flatpak_runtime_contract.py", "shared_config.py",
            "py_modules/mako_plugin/__init__.py",
            "py_modules/mako_plugin/package_paths.py",
            "py_modules/mako_plugin/constants.py",
            "py_modules/mako_plugin/layer_manifests.py",
            "defaults/build_flavor.dev.py", "plugin.json",
        ):
            target = self.plugin / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(PLUGIN_ROOT / relative, target)
        self.write(self.plugin / "dist/index.js", "new frontend")
        self.write(self.plugin / "scripts/generate_ts_schema.py", "")
        self.write(self.installed_plugin / "plugin.json", (PLUGIN_ROOT / "plugin.json").read_text())
        self.write(self.installed_plugin / "dist/index.js", "old frontend")
        self.write(self.root / "bin/node", "#!/bin/sh\nexit 0\n", executable=True)
        self.write(self.engine / "scripts/build-steamos-dev.sh", "#!/bin/sh\nexit 0\n", executable=True)
        self.write(self.engine / "scripts/mako-vrr-lease", "#!/bin/sh\nexit 0\n", executable=True)
        self.write(self.engine / "scripts/manage-vkbasalt-release.py", """
import pathlib, shutil, sys
source = pathlib.Path(__file__).parents[1] / 'vkbasalt-fixture'
shutil.copytree(source, sys.argv[sys.argv.index('--stage-native') + 1], dirs_exist_ok=True)
""", executable=True)
        self.env = {**os.environ, "HOME": str(self.home),
                    "PATH": f"{self.root / 'bin'}:{os.environ['PATH']}"}
        for name in ("MAKO_BUILD_DIR", "MAKO_BUILD_32_DIR", "MAKO_ENGINE_REPO", "DECKY_PLUGIN_DIR"):
            self.env.pop(name, None)
        for bits in (64, 32):
            build = self.build_dir(bits)
            self.write(build / paths.LIB_FILENAME, f"new FG {bits}")
            self.write(build / paths.SPATIAL_SCALING_LIB_FILENAME, f"new spatial {bits}")
            spatial = paths.SPATIAL_SCALING_JSON_FILENAME if bits == 64 else paths.SPATIAL_SCALING_JSON32_FILENAME
            self.manifest(build / "private-scaling-manifest" / spatial,
                          self.library_dir("decky", bits) / paths.SPATIAL_SCALING_LIB_FILENAME,
                          paths.SPATIAL_SCALING_LAYER_NAME)
            libdir = "lib" if bits == 64 else "lib32"
            stage = self.engine / "vkbasalt-fixture"
            self.write(stage / libdir / "vkbasalt" / paths.VKBASALT_LIB_FILENAME, f"new vkBasalt {bits}")
            name = paths.VKBASALT_MANIFEST_FILENAME_64 if bits == 64 else paths.VKBASALT_MANIFEST_FILENAME_32
            self.manifest(stage / "share/mako-render/vulkan/vkbasalt.d" / name,
                          Path("unused-vkbasalt.so"), paths.VKBASALT_LAYER_NAME_64)

    @staticmethod
    def write(path, content, executable=False):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        if executable:
            path.chmod(0o755)

    def manifest(self, path, library, identity=paths.MAKO_LAYER_NAME):
        self.write(path, json.dumps({"layer": {"name": identity, "library_path": str(library)}}))

    def build_dir(self, bits):
        return self.engine / "build" / ("steamos-dev" if bits == 64 else "steamos-dev-32") / "mako-render"

    def library_dir(self, owner, bits):
        if owner == "decky":
            return self.home / (paths.LOCAL_LIB if bits == 64 else paths.LOCAL_LIB32)
        return self.home / ".local" / ("lib" if bits == 64 else "lib32")

    def prepare(self, owner):
        for bits in (64, 32):
            for installed_owner in ("decky", "standalone"):
                libdir = self.library_dir(installed_owner, bits)
                for filename in (paths.LIB_FILENAME, paths.SPATIAL_SCALING_LIB_FILENAME,
                                 f"vkbasalt/{paths.VKBASALT_LIB_FILENAME}"):
                    self.write(libdir / filename, f"old {installed_owner} {bits}")
            filename = paths.JSON_FILENAME if bits == 64 else paths.JSON32_FILENAME
            selected = self.library_dir(owner, bits) / paths.LIB_FILENAME
            for directory in (paths.VULKAN_LAYER_DIR, paths.USER_VULKAN_LAYER_DIR):
                manifest = self.home / directory / filename
                self.manifest(manifest, Path(os.path.relpath(selected, manifest.parent)))
        self.write(self.home / ".config/mako-render/conf.toml", "keep profiles")
        self.write(self.home / paths.MAKO_ROOT / paths.ACTIVE_RENDERER_STATE_FILENAME,
                   json.dumps({"schema_version": 1, "owner": owner, "version": "4.0.0"}))

    def deploy(self, bits):
        return subprocess.run(
            ["bash", str(self.plugin / "scripts/deploy-dev.sh"),
             "--engine" if bits == 64 else "--engine-32"],
            env=self.env, text=True, capture_output=True, timeout=30)

    def test_deploy_updates_selected_owner_and_only_requested_architecture(self):
        for owner in ("decky", "standalone"):
            for bits in (64, 32):
                with self.subTest(owner=owner, bits=bits):
                    self.prepare(owner)
                    state = self.home / paths.MAKO_ROOT / paths.ACTIVE_RENDERER_STATE_FILENAME
                    original_state = state.read_bytes()
                    original_manifest = (self.build_dir(bits) / "private-scaling-manifest" /
                        (paths.SPATIAL_SCALING_JSON_FILENAME if bits == 64 else paths.SPATIAL_SCALING_JSON32_FILENAME))
                    original_build_manifest = original_manifest.read_bytes()
                    result = self.deploy(bits)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn(f"verified active {bits}-bit {owner}", result.stdout)
                    _, libraries = selection.selected_libraries(self.home, bits)
                    for library, content in zip(libraries, (f"new FG {bits}", f"new spatial {bits}", f"new vkBasalt {bits}")):
                        self.assertEqual(library.read_text(), content)
                    other_owner = "decky" if owner == "standalone" else "standalone"
                    self.assertEqual((self.library_dir(other_owner, bits) / paths.LIB_FILENAME).read_text(), f"old {other_owner} {bits}")
                    other_bits = 32 if bits == 64 else 64
                    self.assertEqual((self.library_dir(owner, other_bits) / paths.LIB_FILENAME).read_text(), f"old {owner} {other_bits}")
                    self.assertEqual(state.read_bytes(), original_state)
                    self.assertEqual(original_manifest.read_bytes(), original_build_manifest)
                    self.assertEqual((self.home / ".config/mako-render/conf.toml").read_text(), "keep profiles")

    def test_ambiguous_or_missing_selection_fails_before_deploy(self):
        private = self.home / paths.VULKAN_LAYER_DIR / paths.JSON_FILENAME
        registered = self.home / paths.USER_VULKAN_LAYER_DIR / paths.JSON_FILENAME
        for case in ("unknown", "missing", "malformed", "identity", "disagreement"):
            with self.subTest(case=case):
                self.prepare("standalone")
                if case == "unknown":
                    self.manifest(private, self.home / "custom/libmako-render.so")
                elif case == "missing":
                    private.unlink()
                elif case == "malformed":
                    private.write_text("[]")
                elif case == "identity":
                    self.manifest(private, self.library_dir("standalone", 64) / paths.LIB_FILENAME, "wrong-layer")
                else:
                    self.manifest(registered, self.library_dir("decky", 64) / paths.LIB_FILENAME)
                result = self.deploy(64)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual((self.installed_plugin / "dist/index.js").read_text(), "old frontend")
                self.assertEqual((self.library_dir("standalone", 64) / paths.LIB_FILENAME).read_text(), "old standalone 64")

    def test_verification_rejects_stale_active_copy_and_wrong_secondary_selection(self):
        self.prepare("standalone")
        result = self.deploy(64)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        built = [self.build_dir(64) / paths.LIB_FILENAME,
                 self.build_dir(64) / paths.SPATIAL_SCALING_LIB_FILENAME,
                 self.engine / "vkbasalt-fixture/lib/vkbasalt" / paths.VKBASALT_LIB_FILENAME]
        active = self.library_dir("standalone", 64) / paths.LIB_FILENAME
        active.write_text("stale renderer")
        with self.assertRaisesRegex(ValueError, "differs from"):
            selection.verify(self.home, 64, built)
        shutil.copyfile(built[0], active)
        spatial = self.home / paths.SPATIAL_SCALING_LAYER_DIR / paths.SPATIAL_SCALING_JSON_FILENAME
        self.assertEqual(manifest_library(spatial), (self.library_dir("standalone", 64) / paths.SPATIAL_SCALING_LIB_FILENAME).resolve())
        self.manifest(spatial, self.library_dir("decky", 64) / paths.SPATIAL_SCALING_LIB_FILENAME, paths.SPATIAL_SCALING_LAYER_NAME)
        with self.assertRaisesRegex(ValueError, "another library"):
            selection.verify(self.home, 64, built)
