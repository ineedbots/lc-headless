#pragma once

#include "LocType_s.hpp"
#include "NpcType_s.hpp"
#include "ObjType_s.hpp"
#include "TextPool.hpp"
#include "VarpType_s.hpp"

class TypeDecoder
{
public:
    TypeDecoder() = delete;

    // Each interns the text it keeps into the pool and returns the types in id order.
    [[nodiscard]] static std::vector<LocType_s> DecodeLocs(std::span<const u8> dat, std::span<const u8> idx, TextPool& text);
    [[nodiscard]] static std::vector<NpcType_s> DecodeNpcs(std::span<const u8> dat, std::span<const u8> idx, TextPool& text);
    [[nodiscard]] static std::vector<ObjType_s> DecodeObjs(std::span<const u8> dat, std::span<const u8> idx, TextPool& text);
    [[nodiscard]] static std::vector<VarpType_s> DecodeVarps(std::span<const u8> dat, std::span<const u8> idx);
};
