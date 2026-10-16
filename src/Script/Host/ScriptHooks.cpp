#include "pch.hpp"
#include "ScriptHooks.hpp"

#include "../Convert/PyValue.hpp"
#include "../Error/ScriptError.hpp"
#include "../ScriptCommand_s.hpp"
#include "../ScriptVm.hpp"

#include <pocketpy.h>

namespace
{
    // The standard library's runtime (rs2004/_runtime.py), as the bootstrap names it in builtins.
    constexpr auto DISPATCH = "_rt_dispatch"sv;
    constexpr auto LISTENING = "_listening";
    constexpr auto COMMANDS = "_commands";
}

ScriptHooks::ScriptHooks(ScriptVm& vm, IsRunningCheck isRunning, ErrorHandler onError, AfterCall afterCall)
    : m_vm{vm}
    , m_isRunning{std::move(isRunning)}
    , m_onError{std::move(onError)}
    , m_afterCall{std::move(afterCall)}
{
}

ScriptVm& ScriptHooks::GetVm() const
{
    return m_vm;
}

bool ScriptHooks::IsRunning() const
{
    return m_isRunning();
}

// Another account's script can ask this from inside its own VM, through send_bot_message, so the VM that
// was current is current again afterward.
bool ScriptHooks::Has(std::string_view name) const
{
    const auto previous = py_currentvm();
    const auto listening = py_getdict(m_vm.GetBuiltins(), py_name(LISTENING));
    auto found = 0;
    if (listening != nullptr)
    {
        const auto key = std::string{name};
        found = py_dict_getitem_by_str(listening, key.c_str());
        if (found < 0)
        {
            py_clearexc(nullptr);
        }
    }

    py_switchvm(previous);
    return found == 1;
}

void ScriptHooks::Call(std::string_view name, std::span<const py_Ref> args)
{
    if (!IsRunning() || !Has(name))
    {
        return;
    }

    static_cast<void>(Dispatch(name, args));
}

std::optional<py_GlobalRef> ScriptHooks::Dispatch(std::string_view name, std::span<const py_Ref> args)
{
    // The event's name goes first, in a register the arguments don't use.
    m_vm.Activate();
    PyValue::FromString(py_r7(), name);

    auto all = std::vector<py_Ref>{py_r7()};
    all.insert(all.end(), args.begin(), args.end());
    try
    {
        const auto result = m_vm.CallBuiltin(DISPATCH, all);
        m_afterCall();
        return result;
    }
    catch (const ScriptError& e)
    {
        m_onError(std::format("on_{}()", name), e.what());
        return std::nullopt;
    }
}

std::vector<ScriptCommand_s> ScriptHooks::GetCommands() const
{
    auto commands = std::vector<ScriptCommand_s>{};
    // Like HasHook, this may be asked from inside another VM, which is current again afterward.
    const auto previous = py_currentvm();
    const auto found = py_getdict(m_vm.GetBuiltins(), py_name(COMMANDS));
    if (found != nullptr && py_isdict(found))
    {
        // The console module keeps every name and help a str.
        const auto added = py_dict_apply(found, [](py_Ref name, py_Ref help, void* context)
        {
            if (!py_isstr(name) || !py_isstr(help))
            {
                return true;
            }

            static_cast<std::vector<ScriptCommand_s>*>(context)->push_back(ScriptCommand_s{.name = py_tostr(name), .help = py_tostr(help)});
            return true;
        }, &commands);

        if (!added)
        {
            py_clearexc(nullptr);
        }
    }

    py_switchvm(previous);
    std::ranges::sort(commands, {}, &ScriptCommand_s::name);
    return commands;
}
