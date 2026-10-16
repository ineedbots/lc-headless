#include "pch.hpp"
#include "NpcTypeDecoder.hpp"

#include "../Io/Packet.hpp"
#include "DroppedOpcodes_s.hpp"
#include "NpcType_s.hpp"
#include "TextPool.hpp"
#include "TypeDecoder.hpp"

namespace
{
    using Dropped = DroppedOpcodes_s;

    constexpr auto NO_VALUE = DroppedOpcodes_s::NO_VALUE;
    constexpr auto NO_COMBAT_LEVEL = u16{0};
    // A walk animation for each direction.
    constexpr auto WALK_ANIMS_SIZE = 4 * sizeof(u16);

    constexpr auto MODELS = u8{1};
    constexpr auto SIZE = u8{12};
    constexpr auto READY_ANIM = u8{13};
    constexpr auto WALK_ANIM = u8{14};
    constexpr auto WALK_ANIMS = u8{17};
    constexpr auto FIRST_OP = u8{30};
    constexpr auto LAST_OP = u8{39};
    constexpr auto HEADS = u8{60};
    constexpr auto RESIZE_X = u8{90};
    constexpr auto RESIZE_Y = u8{91};
    constexpr auto RESIZE_Z = u8{92};
    constexpr auto NO_MINIMAP = u8{93};
    constexpr auto COMBAT_LEVEL = u8{95};
    constexpr auto RESIZE_H = u8{97};
    constexpr auto RESIZE_V = u8{98};
    constexpr auto ALWAYS_ON_TOP = u8{99};
    constexpr auto AMBIENT = u8{100};
    constexpr auto CONTRAST = u8{101};
    constexpr auto HEAD_ICON = u8{102};
    constexpr auto TURN_SPEED = u8{103};

    constexpr auto DROPPED = std::to_array({
        Dropped::DropCounted(MODELS, sizeof(u16)),
        Dropped::Drop(READY_ANIM, sizeof(u16)),
        Dropped::Drop(WALK_ANIM, sizeof(u16)),
        Dropped::Drop(WALK_ANIMS, WALK_ANIMS_SIZE),
        Dropped::DropCounted(TypeDecoder::RECOLOUR, TypeDecoder::RECOLOUR_SIZE),
        Dropped::DropCounted(HEADS, sizeof(u16)),
        Dropped::Drop(RESIZE_X, sizeof(u16)),
        Dropped::Drop(RESIZE_Y, sizeof(u16)),
        Dropped::Drop(RESIZE_Z, sizeof(u16)),
        Dropped::Drop(NO_MINIMAP, NO_VALUE),
        Dropped::Drop(RESIZE_H, sizeof(u16)),
        Dropped::Drop(RESIZE_V, sizeof(u16)),
        Dropped::Drop(ALWAYS_ON_TOP, NO_VALUE),
        Dropped::Drop(AMBIENT, sizeof(u8)),
        Dropped::Drop(CONTRAST, sizeof(u8)),
        Dropped::Drop(HEAD_ICON, sizeof(u16)),
        Dropped::Drop(TURN_SPEED, sizeof(u16)),
    });

    void DecodeNpc(Packet& packet, NpcType_s& type, TextPool& text)
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

            if (opcode >= FIRST_OP && opcode <= LAST_OP)
            {
                TypeDecoder::ReadOption(packet, opcode - FIRST_OP, type.ops, text, true);
                continue;
            }

            switch (opcode)
            {
            case TypeDecoder::NAME:
                type.name = text.Intern(TypeDecoder::ReadString(packet));
                break;
            case TypeDecoder::EXAMINE:
                type.examine = text.Intern(TypeDecoder::ReadString(packet));
                break;
            case SIZE:
                type.size = packet.G1();
                break;
            case COMBAT_LEVEL:
            {
                const auto level = packet.G2();
                type.combatLevel = level == NO_COMBAT_LEVEL ? std::nullopt : std::optional{level};
                break;
            }
            default:
                TypeDecoder::ThrowUnknown(opcode);
            }
        }
    }
}

std::vector<NpcType_s> NpcTypeDecoder::Decode(std::span<const u8> dat, std::span<const u8> idx, TextPool& text)
{
    return TypeDecoder::DecodeAll<NpcType_s>("npc", dat, idx, [&text](Packet& packet, NpcType_s& type)
    {
        DecodeNpc(packet, type, text);
    });
}
