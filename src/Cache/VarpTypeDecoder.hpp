#pragma once

#include "../Config/Revision_e.hpp"
#include "VarpType_s.hpp"

class VarpTypeDecoder
{
public:
    VarpTypeDecoder() = delete;

    // Returns the types in id order.
    [[nodiscard]] static std::vector<VarpType_s> Decode(std::span<const u8> dat, std::span<const u8> idx, Revision_e revision);
};
