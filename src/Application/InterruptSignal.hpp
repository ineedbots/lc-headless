#pragma once

// Counts the SIGINTs, such as Ctrl+C, the process has had. A process has one handler, so this is static.
class InterruptSignal
{
public:
    InterruptSignal() = delete;

    static void Install();
    [[nodiscard]] static u32 GetCount();
};
