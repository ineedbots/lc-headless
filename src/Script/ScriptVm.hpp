#pragma once

#include "../Core/Logger.hpp"
#include "ScriptRuntime.hpp"

#include <pocketpy.h>

struct ScriptVmOptions_s
{
    std::filesystem::path scriptsDirectory;
    std::chrono::milliseconds callTimeout = 1000ms;
};

// One isolated interpreter in a runtime VM slot, handed back when destroyed. pocketpy runs one VM at a
// time, so every entry point switches to this one first, and values passed to Call must have been made
// after that switch. Python's print, log() and debug() write to the logger; imports resolve only in the
// scripts directory, then its lib folder; time.sleep raises, because it would stall every account.
class ScriptVm
{
public:
    static constexpr std::string_view LIBRARY_FOLDER = "lib";

    ScriptVm(ScriptRuntime& runtime, ScriptVmOptions_s options, std::shared_ptr<Logger> logger = Logger::GetDefault());
    ~ScriptVm();

    ScriptVm(const ScriptVm&) = delete;
    ScriptVm& operator=(const ScriptVm&) = delete;

    void RunFile(const std::filesystem::path& relativePath);
    void RunSource(std::string_view source, std::string_view filename);
    [[nodiscard]] bool HasFunction(std::string_view name);
    py_GlobalRef Call(std::string_view function, std::span<const py_Ref> args = {});

    void Activate() const;
    [[nodiscard]] py_GlobalRef GetBuiltins() const;
    [[nodiscard]] py_GlobalRef GetMain() const;
    [[nodiscard]] s32 GetSlot() const;
    [[nodiscard]] Logger& GetLogger() const;

    [[nodiscard]] static ScriptVm& GetCurrent();

private:
    void InstallBuiltins();
    void DisableSleep();
    template <typename TCall>
    void RunGuarded(TCall call);
    [[noreturn]] void ThrowPythonError(py_StackRef unwindPoint);
    [[nodiscard]] std::optional<std::filesystem::path> ResolveImport(std::string_view request) const;
    void AppendOutput(std::string_view text);
    void FlushOutput();

    static bool Log(int argc, py_StackRef argv) noexcept;
    static bool Debug(int argc, py_StackRef argv) noexcept;
    static bool WriteLog(LogLevel_e level, py_Ref args) noexcept;
    static bool Sleep(int argc, py_StackRef argv) noexcept;
    static char* ImportFile(const char* path, int* size) noexcept;
    static void Print(const char* text) noexcept;
    static void Flush() noexcept;

    ScriptRuntime& m_runtime;
    ScriptVmOptions_s m_options;
    std::shared_ptr<Logger> m_logger;
    s32 m_slot;
    std::string m_output;
};
