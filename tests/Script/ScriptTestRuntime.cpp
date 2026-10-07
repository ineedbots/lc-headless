#include "pch.hpp"
#include "ScriptTestRuntime.hpp"

#include "Script/ScriptRuntime.hpp"

ScriptRuntime& ScriptTestRuntime::Get()
{
    static auto runtime = ScriptRuntime{};
    return runtime;
}
