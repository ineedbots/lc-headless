#pragma once

// pocketpy can be initialized and finalized only once per process, so exactly one ScriptRuntime may ever
// exist, and it must outlive every ScriptVm.
class ScriptRuntime
{
public:
    static constexpr s32 MAX_VMS = 16;

    ScriptRuntime();
    ~ScriptRuntime();

    ScriptRuntime(const ScriptRuntime&) = delete;
    ScriptRuntime& operator=(const ScriptRuntime&) = delete;

    [[nodiscard]] s32 AcquireSlot();
    void ReleaseSlot(s32 slot);
    [[nodiscard]] s32 GetFreeSlotCount() const;

private:
    std::array<bool, MAX_VMS> m_used{};
};
