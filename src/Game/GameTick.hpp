#pragma once

class GameTick
{
public:
    static constexpr auto DURATION = std::chrono::milliseconds{600};

    GameTick() = delete;
};
