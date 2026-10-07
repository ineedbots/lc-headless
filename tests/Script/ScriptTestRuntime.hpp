#pragma once

#include "Script/ScriptRuntime.hpp"

// pocketpy can be initialized only once per process, so every test shares this runtime. It's created on
// first use and finalized when the test executable exits.
class ScriptTestRuntime
{
public:
    ScriptTestRuntime() = delete;

    [[nodiscard]] static ScriptRuntime& Get();
};
