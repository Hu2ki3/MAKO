## What's new in MAKO Renderer v4.0.0

<img src="https://raw.githubusercontent.com/eugeniosegala/MAKO/refs/heads/main/assets/inferno.png" alt="Inferno release artwork" width="100%">

### Release codename: Inferno

Inferno brings managed shaders to MAKO Renderer. Native and Flatpak builds bundle MAKO's vkBasalt fork for 64-bit and 32-bit games alongside Frame Generation and Scaling.

- **Shaders and effect stacks:** Build ordered per-profile stacks with sharpening, anti-aliasing, DLS denoise, and curated colour and cinematic effects. Managed changes apply live; advanced vkBasalt and ReShade-compatible chains load on the next launch.
- **Layer integration:** `mako-launch` places MAKO Renderer before vkBasalt, isolates unrelated implicit layers, and releases replaced effect graphs instead of retaining their GPU memory.
- **Steam Desktop FPS counter:** Native and Proton Steam launches preserve Steam's requested Vulkan overlay after MAKO's managed layers.
- **Display-aware pacing:** Gamescope VRR feedback selects qualified FIFO or target-clock pacing without resetting Adaptive. Fixed Smooth Cadence and validated Steady 2x can use FIFO; variable Fractional plans retain target-clock pacing.
- **Fractional Real Frame Priority:** Optional Low through Very High presets estimate real-frame caps from Target FPS. Automatic keeps prior behavior; explicit priorities preserve the saved Base FPS Cap. Delivered rates depend on the game and GPU.
- **Live Frame Generation pause:** The `0x` control pauses and resumes generation without reallocating resources. Scaling-only games skip unused Frame Generation initialization.
- **Adaptive and recovery:** Promotions compare adjacent measured workloads and stop when the current level already reaches 98% of target. Recovery responds to acquire timeouts or budget exhaustion, not ordinary slow frames.
- **Scaling and resolution:** Scaling with Frame Generation causes fewer presentation stalls in affected games. Eligible live resolution changes retry allocation once after retired resources are released; actual FPS still depends on the workload.
- **Arch Linux package:** `mako-renderer-bin` installs verified payloads system-wide without changing user-local MAKO installations.
