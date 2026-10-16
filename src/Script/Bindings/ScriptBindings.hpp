#pragma once

#include "../ScriptContext.hpp"
#include "../ScriptVm.hpp"

// Functions find their ScriptContext by the VM they run in, so a VM must be unbound before its ScriptContext goes away.
class ScriptBindings
{
public:
    ScriptBindings() = delete;

    static void Bind(ScriptVm& vm, ScriptContext& context);
    static void Unbind(const ScriptVm& vm) noexcept;
    static void SetSettings(ScriptVm& vm, std::string_view settingsJson);
};
