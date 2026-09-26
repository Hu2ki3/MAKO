---
name: mako-deploy-local
description: Quickly build, deploy, and reload MAKO Decky plus the native 64-bit MAKO Renderer in the installed Decky test environment. Use for local development iteration.
---

# Deploy MAKO locally

This workflow updates the installed MAKO Decky development instance and replaces the native 64-bit MAKO Renderer. Announce that local deployment is starting. Games using MAKO must be closed before the Renderer is replaced; stop if there is evidence that one is still running.

Execution boundary: build, installation, and reload run directly on the SteamOS host. This workflow does not start Docker or Podman; Codex's isolated command shell is not the SteamOS host.

## Workflow

1. Locate the MAKO repository root and confirm it contains `AGENTS.md`, `plugin/package.json`, and `plugin/scripts/deploy-dev.sh`. Read the current `AGENTS.md` and the **Direct SteamOS iteration** section of `plugin/docs/PACKAGING.md`; they remain authoritative if this skill becomes stale.
2. Inspect the branch and worktree and preserve all user changes. Check running games, the build toolchain, and X11/XCB headers on the actual SteamOS host, not inside Codex's default isolated command environment. The Renderer builder fetches the shared Vulkan-Headers pin into its local cache and enforces the package header check. In Codex, use host execution (`exec_command` with `sandbox_permissions: "require_escalated"`) for the process check and deployment. A sandbox process list cannot establish that host games are closed, and Pacman can report a header package installed after a SteamOS image update even when its files are missing. The plugin must already be installed in Decky; let the deployment script fail closed if the configured installation cannot be found.
3. For a local Decky plus 64-bit Renderer deploy, run this from the repository root:

   ```bash
   pnpm --dir plugin run dev:all --reload
   ```

   This incrementally builds and deploys the Decky frontend, Python backend, and native 64-bit Renderer, refreshes development identity, and reloads MAKO Decky. It does not build the 32-bit Renderer, Qt UI archive, or Flatpak bundles. Do not expand the deployment scope based on the changed files; use a different command only when the user explicitly requests that scope. If a host prerequisite is missing, use the SteamOS build-tool installer linked from `plugin/docs/PACKAGING.md`; do not infer host availability from the sandbox or silently switch to a container/package build.
4. Check the command's final deployment and reload status. Report exactly which scopes were deployed and whether reload succeeded. If the script says a protected manifest was retained, surface that warning rather than replacing it manually.

This workflow creates no ZIP and performs no publication. Do not commit, push, tag, publish, or run a full release build unless separately requested.
