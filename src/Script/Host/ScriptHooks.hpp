#pragma once

#include "../ScriptCommand_s.hpp"
#include "../ScriptVm.hpp"

#include <pocketpy.h>

// The stdlib runtime's hooks in one VM: which events the bot listens for, calling them, and the console
// commands it has added. The host decides whether the script is running, and what a hook that raises does.
class ScriptHooks
{
public:
    using IsRunningCheck = std::function<bool()>;
    // where names the code that failed, such as "on_tick()".
    using ErrorHandler = std::function<void(std::string_view where, std::string_view message)>;
    // After each call that returned, such as to act on a stop the hook asked for.
    using AfterCall = std::function<void()>;

    ScriptHooks(ScriptVm& vm, IsRunningCheck isRunning, ErrorHandler onError, AfterCall afterCall);

    [[nodiscard]] ScriptVm& GetVm() const;
    [[nodiscard]] bool IsRunning() const;
    // Another account's script can ask this from inside its own VM, through send_bot_message, so the VM that
    // was current is current again afterward.
    [[nodiscard]] bool Has(std::string_view name) const;
    // Calls the hook, while the script is running and has it.
    void Call(std::string_view name, std::span<const py_Ref> args = {});
    // Calls the runtime's dispatch for the event, which returns what its hook returned; nullopt when it raised.
    std::optional<py_GlobalRef> Dispatch(std::string_view name, std::span<const py_Ref> args = {});
    // By name. Like Has, this may be asked from inside another VM.
    [[nodiscard]] std::vector<ScriptCommand_s> GetCommands() const;

private:
    ScriptVm& m_vm;
    IsRunningCheck m_isRunning;
    ErrorHandler m_onError;
    AfterCall m_afterCall;
};
