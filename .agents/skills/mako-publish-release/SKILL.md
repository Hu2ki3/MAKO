---
name: mako-publish-release
description: Publish and verify a matched public MAKO Renderer and MAKO Decky release. Use for authorized publication; use mako-prepare-release for notes, artwork, and flavor-text preparation only.
---

# Publish MAKO

Locate the MAKO checkout and read its current `AGENTS.md` and [HOW_TO_RELEASE.md](../../../HOW_TO_RELEASE.md). The guide and owning scripts are authoritative; follow their current instructions rather than a copied procedure or a commit SHA stored in this skill.

Execution boundary: the host runs Git, release orchestration, Decky ZIP assembly, uploads, and published-asset checks. Docker or Podman compiles the portable native Renderer and Flatpak bundles; the Arch package uses a container only when host `makepkg` or `fakeroot` is unavailable. The containers build artifacts, not just caches.

Run host-dependent preflight, portable container builds, published-asset installation checks, and publication commands in the actual host context (`exec_command` with `sandbox_permissions: "require_escalated"` in Codex). The default isolated shell cannot establish the host's toolchain, running-game state, or installed-package state and may not access its container runtime or network. Do not treat a sandbox-only failure as evidence that SteamOS needs packages installed.

For each new paired release, choose one new `X.Y.Z` that advances both MAKO Renderer and MAKO Decky. Reuse a version only when resuming that exact incomplete release. Prepare and commit the two release-note files with the release changes. Push the candidate `main`, confirm the worktree is clean and `HEAD` matches `origin/main`, and record that commit's SHA. Follow the guide's complete local candidate ZIP check and applicable game matrix. Run MAKO Gym only when the changed boundary calls for targeted hardware evidence, and record what was not tested.

When the user explicitly authorizes publication, run the guide's top-level `./scripts/publish-release.sh X.Y.Z`. Let it publish the versioned Renderer host archive, Flatpak bundles, and verified Arch package first, then record the immutable Renderer checksums and source commit in Decky's pin, then version and publish the Decky ZIP. Use component commands only for a documented interrupted-release resume. Keep the pinned Vulkan-Headers and vkBasalt checks, release tests, and package verification active unless the guide's explicit maintainer exception applies. Never move a published tag, replace an asset, or manually edit script-owned pins and links.

Complete the guide's public-asset installation check. Verify Renderer and Decky release assets, pinned hashes, README links, the final GitHub Pages deployment, and live website download links before reporting the release complete. Report the published version, source and release commits, tags, artifact identities, validation evidence, and any unfinished checks. For a request limited to preparing release notes, artwork, and flavor text, use [Prepare Release](../mako-prepare-release/SKILL.md) instead. Its local materials can feed this workflow once publication is authorized.
