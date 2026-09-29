/* SPDX-License-Identifier: GPL-3.0-or-later */

#pragma once

#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <cmath>
#include <optional>
#include <utility>

namespace mako::layer::present_diagnostics {

    /// Observation only: no result from this accumulator feeds presentation policy.
    class BridgePresentTiming {
    public:
        struct Samples {
            size_t count{};
            double sum{};
            double squaredSum{};
            double maximum{};
            void add(double value) {
                ++count;
                sum += value;
                squaredSum += value * value;
                maximum = count == 1 ? value : std::max(maximum, value);
            }
            [[nodiscard]] double mean() const { return count ? sum / static_cast<double>(count) : 0; }
            [[nodiscard]] double deviation() const {
                return count ? std::sqrt(std::max(0.0,
                    squaredSum / static_cast<double>(count) - mean() * mean())) : 0;
            }
        };
        struct Window {
            size_t requests{};
            size_t feedbacks{};
            size_t unmatched{};
            size_t overwritten{};
            size_t discontinuities{};
            Samples requestedInterval;
            Samples reportedInterval;
            Samples lateness;
            Samples submitLateness;
        };

        void request(uint32_t id, uint64_t desired, uint64_t wake, uint64_t submit) {
            if (!started)
                started = wake;
            auto& entry = pending[id % pending.size()];
            if (entry.valid)
                ++window.overwritten;
            entry = {id, desired, true};
            ++window.requests;
            if (previousDesired && desired > previousDesired)
                window.requestedInterval.add(milliseconds(desired - previousDesired));
            previousDesired = desired;
            window.submitLateness.add(wake > submit ? milliseconds(wake - submit) : 0);
        }

        void feedback(uint32_t id, uint64_t desired, uint64_t actual) {
            auto& entry = pending[id % pending.size()];
            if (!entry.valid || entry.id != id || entry.desired != desired || !actual) {
                ++window.unmatched;
                return;
            }
            entry.valid = false;
            ++window.feedbacks;
            // Gamescope may report a target vblank slightly before the request.
            window.lateness.add(actual >= desired ? milliseconds(actual - desired)
                                                  : -milliseconds(desired - actual));
            if (previousActual) {
                if (id == previousId + uint32_t{1} && actual > previousActual)
                    window.reportedInterval.add(milliseconds(actual - previousActual));
                else
                    ++window.discontinuities;
            }
            previousActual = actual;
            previousId = id;
        }

        [[nodiscard]] std::optional<Window> take(uint64_t now) {
            if (!started || now < started || now - started < 1000000000)
                return std::nullopt;
            started = now;
            return std::exchange(window, {});
        }

        [[nodiscard]] size_t outstanding() const {
            return static_cast<size_t>(std::count_if(pending.begin(), pending.end(),
                [](const auto& entry) { return entry.valid; }));
        }

    private:
        struct Pending { uint32_t id{}; uint64_t desired{}; bool valid{}; };
        std::array<Pending, 128> pending{};
        uint64_t started{};
        uint64_t previousDesired{};
        uint64_t previousActual{};
        uint32_t previousId{};
        Window window;
        static double milliseconds(uint64_t ns) { return static_cast<double>(ns) / 1000000.0; }
    };
}
