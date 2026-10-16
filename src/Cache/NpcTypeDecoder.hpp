#pragma once

#include "NpcType_s.hpp"
#include "TextPool.hpp"

class NpcTypeDecoder
{
public:
    NpcTypeDecoder() = delete;

    // Interns the text it keeps into the pool and returns the types in id order.
    [[nodiscard]] static std::vector<NpcType_s> Decode(std::span<const u8> dat, std::span<const u8> idx, TextPool& text);
};
