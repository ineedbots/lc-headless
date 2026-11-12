#pragma once

namespace ApplicationEntryPoint
{
    std::chrono::steady_clock::time_point GetStartTime();
    int Run(int argc, char** argv);
}
