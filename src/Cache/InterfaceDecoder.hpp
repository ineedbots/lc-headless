#pragma once

#include "../Config/Type/Revision_e.hpp"
#include "Type/IfComponent_s.hpp"

class InterfaceDecoder
{
public:
    InterfaceDecoder() = delete;

    [[nodiscard]] static std::vector<IfComponent_s> Decode(std::span<const u8> data, Revision_e revision);
};
