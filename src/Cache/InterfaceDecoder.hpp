#pragma once

#include "IfComponent_s.hpp"

class InterfaceDecoder
{
public:
    InterfaceDecoder() = delete;

    // Takes the interface archive's data entry and returns its components in the order it lists them.
    // Throws CacheError, naming the component, for data that doesn't decode.
    [[nodiscard]] static std::vector<IfComponent_s> Decode(std::span<const u8> data);
};
