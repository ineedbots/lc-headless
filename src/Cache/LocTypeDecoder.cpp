#include "pch.hpp"
#include "LocTypeDecoder.hpp"

#include "../Io/Packet.hpp"
#include "DroppedOpcodes_s.hpp"
#include "LocType_s.hpp"
#include "TextPool.hpp"
#include "TypeDecoder.hpp"

namespace
{
    using Dropped = DroppedOpcodes_s;

    constexpr auto NO_VALUE = DroppedOpcodes_s::NO_VALUE;
    constexpr auto CENTREPIECE_STRAIGHT = u8{10};
    constexpr auto ACTIVE_VALUE = u8{1};

    constexpr auto MODELS_WITH_SHAPES = u8{1};
    constexpr auto MODELS = u8{5};
    constexpr auto WIDTH = u8{14};
    constexpr auto LENGTH = u8{15};
    constexpr auto NO_BLOCK_WALK = u8{17};
    constexpr auto NO_BLOCK_RANGE = u8{18};
    constexpr auto ACTIVE = u8{19};
    constexpr auto HILLSKEW = u8{21};
    constexpr auto SHARELIGHT = u8{22};
    constexpr auto OCCLUDE = u8{23};
    constexpr auto ANIM = u8{24};
    constexpr auto WALL_WIDTH = u8{28};
    constexpr auto AMBIENT = u8{29};
    constexpr auto FIRST_OP = u8{30};
    constexpr auto LAST_OP = u8{38};
    constexpr auto CONTRAST = u8{39};
    constexpr auto MAP_FUNCTION = u8{60};
    constexpr auto MIRROR = u8{62};
    constexpr auto NO_SHADOW = u8{64};
    constexpr auto RESIZE_X = u8{65};
    constexpr auto RESIZE_Y = u8{66};
    constexpr auto RESIZE_Z = u8{67};
    constexpr auto MAP_SCENE = u8{68};
    constexpr auto FORCE_APPROACH = u8{69};
    constexpr auto OFFSET_X = u8{70};
    constexpr auto OFFSET_Y = u8{71};
    constexpr auto OFFSET_Z = u8{72};
    constexpr auto FORCE_DECOR = u8{73};
    constexpr auto BREAK_ROUTE_FINDING = u8{74};
    constexpr auto RAISE_OBJECT = u8{75};
    constexpr auto MULTILOC = u8{77};

    constexpr auto DROPPED = std::to_array({
        Dropped::Drop(HILLSKEW, NO_VALUE),
        Dropped::Drop(SHARELIGHT, NO_VALUE),
        Dropped::Drop(OCCLUDE, NO_VALUE),
        Dropped::Drop(ANIM, sizeof(u16)),
        Dropped::Drop(WALL_WIDTH, sizeof(u8)),
        Dropped::Drop(AMBIENT, sizeof(u8)),
        Dropped::Drop(CONTRAST, sizeof(u8)),
        Dropped::DropCounted(TypeDecoder::RECOLOUR, TypeDecoder::RECOLOUR_SIZE),
        Dropped::Drop(MAP_FUNCTION, sizeof(u16)),
        Dropped::Drop(MIRROR, NO_VALUE),
        Dropped::Drop(NO_SHADOW, NO_VALUE),
        Dropped::Drop(RESIZE_X, sizeof(u16)),
        Dropped::Drop(RESIZE_Y, sizeof(u16)),
        Dropped::Drop(RESIZE_Z, sizeof(u16)),
        Dropped::Drop(MAP_SCENE, sizeof(u16)),
        Dropped::Drop(OFFSET_X, sizeof(u16)),
        Dropped::Drop(OFFSET_Y, sizeof(u16)),
        Dropped::Drop(OFFSET_Z, sizeof(u16)),
        Dropped::Drop(FORCE_DECOR, NO_VALUE),
        Dropped::Drop(RAISE_OBJECT, sizeof(u8)),
    });

    // What a loc's model opcodes said, which decides whether it's active when opcode 19 doesn't.
    struct LocModels_s
    {
        bool present = false;
        bool shaped = false;
        u8 firstShape = 0;
    };

    void ReadModels(Packet& packet, bool withShapes, LocModels_s& models)
    {
        const auto count = packet.G1();
        if (count == 0)
        {
            return;
        }

        models.present = true;
        models.shaped = withShapes;
        for (auto i = 0; i < count; ++i)
        {
            static_cast<void>(packet.G2());

            if (!withShapes)
            {
                continue;
            }

            const auto shape = packet.G1();
            if (i == 0)
            {
                models.firstShape = shape;
            }
        }
    }

    void SkipMultiloc(Packet& packet)
    {
        static_cast<void>(packet.G2());

        const auto count = std::size_t{packet.G1()};
        TypeDecoder::Skip(packet, (count + 1) * sizeof(u16));
    }

    void DecodeLoc(Packet& packet, LocType_s& type, TextPool& text)
    {
        auto models = LocModels_s{};
        auto activeGiven = false;
        auto hasOptions = false;
        auto breaksRouteFinding = false;
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
                hasOptions = true;
                TypeDecoder::ReadOption(packet, opcode - FIRST_OP, type.ops, text, true);
                continue;
            }

            switch (opcode)
            {
            case MODELS_WITH_SHAPES:
                ReadModels(packet, true, models);
                break;
            case TypeDecoder::NAME:
                type.name = text.Intern(TypeDecoder::ReadString(packet));
                break;
            case TypeDecoder::EXAMINE:
                type.examine = text.Intern(TypeDecoder::ReadString(packet));
                break;
            case MODELS:
                ReadModels(packet, false, models);
                break;
            case WIDTH:
                type.width = packet.G1();
                break;
            case LENGTH:
                type.length = packet.G1();
                break;
            case NO_BLOCK_WALK:
                type.blockWalk = false;
                break;
            case NO_BLOCK_RANGE:
                type.blockRange = false;
                break;
            case ACTIVE:
                // As the webclient reads it: a 1 makes the loc active, and any value stops the default.
                activeGiven = true;

                if (packet.G1() == ACTIVE_VALUE)
                {
                    type.active = true;
                }
                break;
            case FORCE_APPROACH:
                type.forceApproach = packet.G1();
                break;
            case BREAK_ROUTE_FINDING:
                breaksRouteFinding = true;
                break;
            case MULTILOC:
                SkipMultiloc(packet);
                break;
            default:
                TypeDecoder::ThrowUnknown(opcode);
            }
        }

        if (!activeGiven)
        {
            const auto activeModels = models.present && (!models.shaped || models.firstShape == CENTREPIECE_STRAIGHT);
            type.active = activeModels || hasOptions;
        }

        if (breaksRouteFinding)
        {
            type.blockWalk = false;
            type.blockRange = false;
        }
    }
}

std::vector<LocType_s> LocTypeDecoder::Decode(std::span<const u8> dat, std::span<const u8> idx, TextPool& text)
{
    return TypeDecoder::DecodeAll<LocType_s>("loc", dat, idx, [&text](Packet& packet, LocType_s& type)
    {
        DecodeLoc(packet, type, text);
    });
}
