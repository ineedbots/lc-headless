#pragma once

#include "ScriptApi.hpp"
#include "ScriptVm.hpp"

// Installs the script API into a VM's builtins: the constants, the prelude's classes, and a function for
// each ScriptApi call. Functions find their ScriptApi by the VM they run in, so a VM must be unbound
// before its ScriptApi goes away.
class ScriptBindings
{
public:
    ScriptBindings() = delete;

    static void Bind(ScriptVm& vm, ScriptApi& api);
    static void Unbind(const ScriptVm& vm) noexcept;
    static void SetSettings(ScriptVm& vm, std::string_view settingsJson);
};
