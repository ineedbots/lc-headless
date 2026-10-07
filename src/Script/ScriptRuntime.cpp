#include "pch.hpp"
#include "ScriptRuntime.hpp"

#include "ScriptError.hpp"

#include <pocketpy.h>

namespace
{
    bool runtimeCreated = false;
}

ScriptRuntime::ScriptRuntime()
{
    assert(!runtimeCreated && "pocketpy can only be initialized once per process");
    runtimeCreated = true;
    py_initialize();
}

ScriptRuntime::~ScriptRuntime()
{
    assert(GetFreeSlotCount() == MAX_VMS && "A ScriptVm outlived the ScriptRuntime");
    py_finalize();
}

s32 ScriptRuntime::AcquireSlot()
{
    const auto freeSlot = std::ranges::find(m_used, false);
    if (freeSlot == m_used.end())
    {
        throw ScriptError{std::format("All {} script VMs are in use; run further accounts in another process", MAX_VMS)};
    }

    *freeSlot = true;
    return static_cast<s32>(freeSlot - m_used.begin());
}

void ScriptRuntime::ReleaseSlot(s32 slot)
{
    assert(slot >= 0 && slot < MAX_VMS && "VM slot out of range");
    const auto index = static_cast<std::size_t>(slot);
    assert(m_used[index] && "Releasing a VM slot that isn't in use");

    // A reset VM is rebuilt from scratch, so the next script to take the slot starts clean.
    py_switchvm(slot);
    py_resetvm();
    m_used[index] = false;
}

s32 ScriptRuntime::GetFreeSlotCount() const
{
    return static_cast<s32>(std::ranges::count(m_used, false));
}
