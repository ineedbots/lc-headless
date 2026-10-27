#pragma once

#include "Script/Stdlib.hpp"

#include <pocketpy.h>

// Test-only collection. Line numbers come from pocketpy's compiler, including nested declarations.
// Counts are line trace events, not statement counts (pocketpy can coalesce adjacent events).
class ScriptCoverage
{
public:
    explicit ScriptCoverage(std::span<const StdlibFile_s> files);
    ~ScriptCoverage();
    ScriptCoverage(const ScriptCoverage&) = delete;
    ScriptCoverage& operator=(const ScriptCoverage&) = delete;

    void AttachToCurrentVm();
    void Stop();
    [[nodiscard]] const std::map<std::string, std::vector<u64>, std::less<>>& GetHits() const;
    [[nodiscard]] bool Failed() const;
    [[nodiscard]] static std::chrono::milliseconds AdjustTimeout(std::chrono::milliseconds timeout);
    void Write(const std::filesystem::path& path) const;

    [[nodiscard]] static std::vector<int> ExecutableLines(std::string_view source, std::string_view filename);

private:
    static void OnVmCreated(int index);
    static void Trace(struct py_Frame* frame, enum py_TraceEvent event) noexcept;

    std::map<std::string, std::vector<u64>, std::less<>> m_hits;
    ScriptCoverage* m_previous = nullptr;
    void (*m_previousCtor)(int) = nullptr;
    std::string_view m_lastPath;
    std::vector<u64>* m_lastLines = nullptr;
    bool m_enabled = true;
    bool m_attached = false;
    bool m_failed = false;
};
