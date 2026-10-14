#pragma once

#include "IfComponent_s.hpp"

class InterfaceDecoder
{
public:
    InterfaceDecoder() = delete;

    [[nodiscard]] static std::vector<IfComponent_s> Decode(std::span<const u8> data);
};
