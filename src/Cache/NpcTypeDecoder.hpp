#pragma once

#include "../Config/Type/Revision_e.hpp"
#include "Type/NpcType_s.hpp"
#include "TextPool.hpp"

class NpcTypeDecoder
{
public:
    NpcTypeDecoder() = delete;

    // Interns the text it keeps into the pool and returns the types in id order.
    [[nodiscard]] static std::vector<NpcType_s> Decode(std::span<const u8> dat, std::span<const u8> idx, TextPool& text, Revision_e revision);
};
