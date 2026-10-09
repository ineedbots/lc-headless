#pragma once

#include "LocType_s.hpp"
#include "NpcType_s.hpp"
#include "ObjType_s.hpp"
#include "TextPool.hpp"

class TypeDecoder
{
public:
    TypeDecoder() = delete;

    // Each takes a type's .dat and .idx entries from the config archive, interns the text into the
    // pool, and returns the types in id order. Throws CacheError, naming the type and id, for a
    // definition that doesn't decode to exactly its listed size.
    [[nodiscard]] static std::vector<LocType_s> DecodeLocs(std::span<const u8> dat, std::span<const u8> idx, TextPool& text);
    [[nodiscard]] static std::vector<NpcType_s> DecodeNpcs(std::span<const u8> dat, std::span<const u8> idx, TextPool& text);
    [[nodiscard]] static std::vector<ObjType_s> DecodeObjs(std::span<const u8> dat, std::span<const u8> idx, TextPool& text);
};
