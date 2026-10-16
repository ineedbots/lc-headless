#pragma once

#include "../Config/Revision_e.hpp"
#include "ObjType_s.hpp"
#include "TextPool.hpp"

class ObjTypeDecoder
{
public:
    ObjTypeDecoder() = delete;

    // Interns the text it keeps into the pool and returns the types in id order, with each banknote
    // filled in from the obj it's a note of.
    [[nodiscard]] static std::vector<ObjType_s> Decode(std::span<const u8> dat, std::span<const u8> idx, TextPool& text, Revision_e revision);
};
