#include "pch.hpp"
#include "InterruptSignal.hpp"

namespace
{
    std::atomic<u32> interruptCount{0};

    void SignalHandler(int signalNum)
    {
        if (signalNum == SIGINT)
        {
            ++interruptCount;
        }
    }
}

void InterruptSignal::Install()
{
    std::signal(SIGINT, SignalHandler);
}

u32 InterruptSignal::GetCount()
{
    return interruptCount.load();
}
