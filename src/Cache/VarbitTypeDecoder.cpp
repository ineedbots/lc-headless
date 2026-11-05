#include "pch.hpp"
#include "VarbitTypeDecoder.hpp"

#include "../Io/Packet.hpp"
#include "Error/CacheError.hpp"
#include "TypeDecoder.hpp"
#include "VarbitType_s.hpp"

namespace
{
    constexpr auto END = u8{0};
    constexpr auto SELECTOR = u8{1};
    constexpr auto DEBUG_NAME = u8{10};
    constexpr auto VARP_BITS = 32;
}

std::vector<VarbitType_s> VarbitTypeDecoder::Decode(std::span<const u8> dat)
{
    try
    {
        auto packet = Packet{dat};
        auto types = std::vector<VarbitType_s>(packet.G2());
        for (auto& type : types)
        {
            while (true)
            {
                const auto opcode = packet.G1();
                if (opcode == END)
                {
                    break;
                }

                if (opcode == SELECTOR)
                {
                    type.baseVar = packet.G2();
                    type.startBit = packet.G1();
                    type.endBit = packet.G1();
                    if (type.startBit > type.endBit || type.endBit >= VARP_BITS)
                    {
                        throw CacheError{"varbit: invalid bit range"};
                    }
                }
                else if (opcode == DEBUG_NAME)
                {
                    static_cast<void>(TypeDecoder::ReadString(packet));
                }
                else
                {
                    TypeDecoder::ThrowUnknown(opcode);
                }
            }
        }

        if (packet.GetPos() != dat.size())
        {
            throw CacheError{"varbit.dat has trailing bytes"};
        }

        return types;
    }
    catch (const std::out_of_range&)
    {
        throw CacheError{"varbit.dat is truncated"};
    }
}
