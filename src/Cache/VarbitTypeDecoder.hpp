#pragma once

#include "Type/VarbitType_s.hpp"

class VarbitTypeDecoder
{
public:
    VarbitTypeDecoder() = delete;

    [[nodiscard]] static std::vector<VarbitType_s> Decode(std::span<const u8> dat);
};
