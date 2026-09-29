## What's new in MAKO Decky v4.0.0

<img src="https://raw.githubusercontent.com/eugeniosegala/MAKO/refs/heads/main/assets/inferno.png" alt="Inferno release artwork" width="100%">

### Release codename: Inferno

> _“The flames painted the sea in colors no sailor had a name for.”_
>
> **Captain Matteo Veyr, _Chronicles of the Last Fleet_**

---

MAKO Decky 4.0 adds per-game shaders and ordered effect stacks through MAKO's managed vkBasalt fork. Install MAKO Renderer from the plugin to get the matching layer; a separate vkBasalt installation is unnecessary.

- **Shaders and effects:** Profiles offer sharpening, anti-aliasing, 20% default DLS denoise, and curated colour, contrast, cinematic, and retro effects, including new Clarity and Levels Plus shaders. Combine effects in your chosen order; each extra pass can increase GPU cost. Native 64-bit and 32-bit games and prepared Flatpak apps are supported.
- **Live controls and custom chains:** Supported shader settings update while you play. Default and saved profiles retain editable vkBasalt configuration files for custom chains and ReShade-compatible effects. Layer activation and manual configuration edits take effect after restarting the game.
- **Image Processing and Live Status:** Frame Generation, Scaling, and Shaders have separate tabs. Live Status shows active modes, limits, fallbacks, and input and display resolutions.
- **Frame Generation pause:** **Enable Frame-gen (Restart)** loads Frame Generation at launch; select `0x` to pause or resume it while playing. Steam and Decky menus pause generated frames automatically while real frames and scaling continue.
- **Fractional real-frame priority:** Choose **Automatic**, **Low**, **Medium**, **High**, or **Very High**. Automatic keeps the previous behavior; other levels estimate a real-frame cap from Target FPS without changing your saved manual Base FPS Cap. The displayed cap is an estimate, not a guaranteed frame rate.
- **VRR and pacing:** Follow Steam uses Gamescope's VRR state for eligible pacing modes without resetting the Adaptive level. Fixed Smooth Cadence and stable Steady 2x also gain ordered pacing without VRR.
- **Scaling with Frame Generation:** Improved frame delivery reduces stalls when the two features run together. The frame rate shown in-game may sit slightly below the selected target.
- **Adaptive and recovery:** Adaptive avoids raising the multiplier when it already reaches at least 98% of the target, and backs off after an unsustainable promotion. Recovery responds to frame-acquisition deadlines rather than ordinary slow rendering; eligible resolution changes can retry resource allocation once.
- **Steam Desktop FPS counter:** Native and Proton Steam launches retain Steam's Vulkan overlay with MAKO's managed layers in Desktop Mode.
