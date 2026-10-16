#include "pch.hpp"
#include "VarpTypeDecoder.hpp"

#include "../Io/Packet.hpp"
#include "DroppedOpcodes_s.hpp"
#include "TypeDecoder.hpp"
#include "VarpType_s.hpp"

namespace
{
    using Dropped = DroppedOpcodes_s;

    constexpr auto NO_VALUE = DroppedOpcodes_s::NO_VALUE;

    // The engine's VarPlayerType names 1, 2, 4, 5 and 6. The webclient reads the rest as server-side
    // fields without names, and the Java client's names are obfuscated, so they go by their numbers.
    constexpr auto SCOPE = u8{1};
    constexpr auto TYPE = u8{2};
    constexpr auto CODE3 = u8{3};
    constexpr auto NO_PROTECT = u8{4};
    constexpr auto CLIENT_CODE = u8{5};
    constexpr auto TRANSMIT = u8{6};
    constexpr auto CODE7 = u8{7};
    constexpr auto CODE8 = u8{8};
    constexpr auto CODE10 = u8{10};
    constexpr auto CODE11 = u8{11};
    constexpr auto CODE12 = u8{12};
    constexpr auto CODE13 = u8{13};

    constexpr auto DROPPED = std::to_array({
        Dropped::Drop(SCOPE, sizeof(u8)),
        Dropped::Drop(TYPE, sizeof(u8)),
        Dropped::Drop(CODE3, NO_VALUE),
        Dropped::Drop(NO_PROTECT, NO_VALUE),
        Dropped::Drop(TRANSMIT, NO_VALUE),
        Dropped::Drop(CODE7, sizeof(u32)),
        Dropped::Drop(CODE8, NO_VALUE),
        Dropped::Drop(CODE11, NO_VALUE),
        Dropped::Drop(CODE12, sizeof(u32)),
        Dropped::Drop(CODE13, NO_VALUE),
    });

    void DecodeVarp(Packet& packet, VarpType_s& type)
    {
        while (true)
        {
            const auto opcode = packet.G1();
            if (opcode == TypeDecoder::END_OPCODE)
            {
                break;
            }

            if (TypeDecoder::SkipDropped(packet, opcode, DROPPED))
            {
                continue;
            }

            switch (opcode)
            {
            case CLIENT_CODE:
                type.clientCode = packet.G2();
                break;
            case CODE10:
                static_cast<void>(TypeDecoder::ReadString(packet));
                break;
            default:
                TypeDecoder::ThrowUnknown(opcode);
            }
        }
    }
}

std::vector<VarpType_s> VarpTypeDecoder::Decode(std::span<const u8> dat, std::span<const u8> idx)
{
    return TypeDecoder::DecodeAll<VarpType_s>("varp", dat, idx, [](Packet& packet, VarpType_s& type)
    {
        DecodeVarp(packet, type);
    });
}
