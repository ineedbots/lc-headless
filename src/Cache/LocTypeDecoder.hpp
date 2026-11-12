#pragma once

#include "../Config/Type/Revision_e.hpp"
#include "Type/LocType_s.hpp"
#include "TextPool.hpp"

class LocTypeDecoder
{
public:
    LocTypeDecoder() = delete;

    // Interns the text it keeps into the pool and returns the types in id order.
    [[nodiscard]] static std::vector<LocType_s> Decode(std::span<const u8> dat, std::span<const u8> idx, TextPool& text, Revision_e revision);
};
