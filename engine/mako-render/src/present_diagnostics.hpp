/* SPDX-License-Identifier: GPL-3.0-or-later */

#pragma once

#include "adaptive_scheduler.hpp"
#include "bridge_present_timing.hpp"

#include <chrono>
#include <cstddef>
#include <cstdint>
#include <optional>
#include <string_view>

#include <vulkan/vulkan_core.h>

namespace mako::layer::present_diagnostics {

    using Clock = std::chrono::steady_clock;

    [[nodiscard]] uint64_t allocateContextId();
    /// Return the process-start diagnostic policy shared by all layer paths.
    [[nodiscard]] bool enabled();
    /// Return the process-start slow-operation threshold in milliseconds.
    [[nodiscard]] double thresholdMilliseconds();
    [[nodiscard]] Clock::time_point start();

    void logBridgeTiming(uint64_t bridgeId, VkSwapchainKHR swapchain,
        const BridgePresentTiming::Window& window,
        size_t outstanding, uint64_t refreshCycleNs);

    enum class PresentWaitApi { Khr, Khr2 };

    struct ApplicationPresentMode {
        int64_t mode{-1};
        bool dynamic{};
        bool operator==(const ApplicationPresentMode&) const = default;
    };

    [[nodiscard]] inline ApplicationPresentMode applicationPresentMode(
            VkPresentModeKHR createdMode, const void* chain) {
        for (auto* node = static_cast<const VkBaseInStructure*>(chain);
                node; node = node->pNext) {
            if (node->sType == VK_STRUCTURE_TYPE_SWAPCHAIN_PRESENT_MODE_INFO_EXT) {
                const auto* modes = reinterpret_cast<const VkSwapchainPresentModeInfoEXT*>(node);
                // A multi-swapchain call has no per-context index here. Leave
                // it explicitly unknown rather than attributing index zero.
                return {modes->swapchainCount == 1 && modes->pPresentModes
                    ? static_cast<int64_t>(*modes->pPresentModes) : -1, true};
            }
        }
        return {static_cast<int64_t>(createdMode), false};
    }

    /// One bounded stream per calling thread. Switching device, swapchain or
    /// API drops an incomplete window instead of joining unrelated lifetimes.
    /// These observations never authorize completion or change a timeout.
    class ApplicationPresentWait {
    public:
        struct Window {
            size_t calls{};
            size_t successful{};
            size_t timeouts{};
            size_t errors{};
            size_t polls{};
            uint64_t firstPresentId{};
            uint64_t lastPresentId{};
            BridgePresentTiming::Samples duration;
        };

        [[nodiscard]] std::optional<Window> observe(VkDevice device,
                VkSwapchainKHR swapchain, PresentWaitApi api,
                uint64_t presentId, uint64_t timeout, VkResult result,
                Clock::time_point started, Clock::time_point finished) {
            if (!windowStarted || device != lastDevice ||
                    swapchain != lastSwapchain || api != lastApi) {
                windowStarted = started;
                lastDevice = device;
                lastSwapchain = swapchain;
                lastApi = api;
                window = {};
            }
            if (!window.calls)
                window.firstPresentId = presentId;
            ++window.calls;
            window.successful += result == VK_SUCCESS;
            window.timeouts += result == VK_TIMEOUT;
            window.errors += result < 0;
            window.polls += timeout == 0;
            window.lastPresentId = presentId;
            window.duration.add(std::chrono::duration<double, std::milli>(
                finished - started).count());
            if (finished - *windowStarted < std::chrono::seconds(1))
                return std::nullopt;
            windowStarted = finished;
            const auto completed = window;
            window = {};
            return completed;
        }
    private:
        std::optional<Clock::time_point> windowStarted;
        VkDevice lastDevice{};
        VkSwapchainKHR lastSwapchain{};
        PresentWaitApi lastApi{};
        Window window;
    };

    void recordApplicationPresentWait(VkDevice device, VkSwapchainKHR swapchain,
        PresentWaitApi api, uint64_t presentId, uint64_t timeout, VkResult result,
        Clock::time_point started, Clock::time_point finished);

    template<typename Wait>
    VkResult observeApplicationPresentWait(VkDevice device, VkSwapchainKHR swapchain,
            PresentWaitApi api, uint64_t presentId, uint64_t timeout, Wait&& wait) {
        if (!enabled())
            return wait();
        const auto started = Clock::now();
        const auto result = wait();
        const auto finished = Clock::now();
        recordApplicationPresentWait(device, swapchain, api, presentId, timeout,
            result, started, finished);
        return result;
    }

    class ContextScope {
    public:
        explicit ContextScope(uint64_t contextId);
        ~ContextScope();

        ContextScope(const ContextScope&) = delete;
        ContextScope& operator=(const ContextScope&) = delete;
    private:
        uint64_t previousContextId;
    };

    void logSlowOperation(std::string_view operation,
        size_t frameIndex, size_t sequenceIndex,
        Clock::time_point started,
        std::optional<VkResult> result = std::nullopt,
        std::optional<size_t> passIndex = std::nullopt,
        std::optional<uint32_t> imageIndex = std::nullopt);

    void logPresentFallback(size_t frameIndex, size_t sequenceIndex,
        size_t passIndex, size_t skippedFrames, uint64_t timelineValue,
        std::string_view acquireMode, std::string_view backendWork);

    void logHistoryWarmup(size_t frameIndex, size_t sequenceIndex,
        size_t remainingFrames, bool recovery,
        std::optional<uint32_t> acquiredImage);

    [[nodiscard]] AdaptiveSchedulerDiagnostics& adaptiveScheduler();

}
