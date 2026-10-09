#include "pch.hpp"
#include "TypeDecoder.hpp"

#include "../Io/Packet.hpp"
#include "CacheError.hpp"
#include "LocType_s.hpp"
#include "NpcType_s.hpp"
#include "ObjType_s.hpp"
#include "TextPool.hpp"
#include "VarpType_s.hpp"

namespace
{
    constexpr auto COUNT_SIZE = std::size_t{2};
    constexpr auto SIZE_ENTRY_SIZE = std::size_t{2};
    constexpr auto END_OPCODE = u8{0};
    constexpr auto STRING_TERMINATOR = u8{'\n'};
    constexpr auto HIDDEN_OPTION = "hidden"sv;
    constexpr auto CENTREPIECE_STRAIGHT = u8{10};
    constexpr auto ACTIVE_VALUE = u8{1};
    constexpr auto NO_COMBAT_LEVEL = u16{0};
    constexpr auto VOWELS = "aeiou"sv;

    constexpr auto NO_VALUE = std::size_t{0};
    // A source and a destination colour.
    constexpr auto RECOLOUR_SIZE = 2 * sizeof(u16);
    // A walk animation for each direction.
    constexpr auto WALK_ANIMS_SIZE = 4 * sizeof(u16);
    // A model and its offset.
    constexpr auto WEAR_SIZE = sizeof(u16) + sizeof(u8);
    // An obj and the count it's shown for.
    constexpr auto COUNT_OBJ_SIZE = 2 * sizeof(u16);

    // Opcodes are named after the fields they set in the webclient's LocType, NpcType, ObjType and
    // VarpType, or the engine's where the webclient has no name.
    constexpr auto NAME = u8{2};
    constexpr auto EXAMINE = u8{3};
    constexpr auto RECOLOUR = u8{40};

    constexpr auto LOC_MODELS_WITH_SHAPES = u8{1};
    constexpr auto LOC_MODELS = u8{5};
    constexpr auto LOC_WIDTH = u8{14};
    constexpr auto LOC_LENGTH = u8{15};
    constexpr auto LOC_NO_BLOCK_WALK = u8{17};
    constexpr auto LOC_NO_BLOCK_RANGE = u8{18};
    constexpr auto LOC_ACTIVE = u8{19};
    constexpr auto LOC_HILLSKEW = u8{21};
    constexpr auto LOC_SHARELIGHT = u8{22};
    constexpr auto LOC_OCCLUDE = u8{23};
    constexpr auto LOC_ANIM = u8{24};
    constexpr auto LOC_WALL_WIDTH = u8{28};
    constexpr auto LOC_AMBIENT = u8{29};
    constexpr auto LOC_FIRST_OP = u8{30};
    constexpr auto LOC_LAST_OP = u8{38};
    constexpr auto LOC_CONTRAST = u8{39};
    constexpr auto LOC_MAP_FUNCTION = u8{60};
    constexpr auto LOC_MIRROR = u8{62};
    constexpr auto LOC_NO_SHADOW = u8{64};
    constexpr auto LOC_RESIZE_X = u8{65};
    constexpr auto LOC_RESIZE_Y = u8{66};
    constexpr auto LOC_RESIZE_Z = u8{67};
    constexpr auto LOC_MAP_SCENE = u8{68};
    constexpr auto LOC_FORCE_APPROACH = u8{69};
    constexpr auto LOC_OFFSET_X = u8{70};
    constexpr auto LOC_OFFSET_Y = u8{71};
    constexpr auto LOC_OFFSET_Z = u8{72};
    constexpr auto LOC_FORCE_DECOR = u8{73};
    constexpr auto LOC_BREAK_ROUTE_FINDING = u8{74};
    constexpr auto LOC_RAISE_OBJECT = u8{75};
    constexpr auto LOC_MULTILOC = u8{77};

    constexpr auto NPC_MODELS = u8{1};
    constexpr auto NPC_SIZE = u8{12};
    constexpr auto NPC_READY_ANIM = u8{13};
    constexpr auto NPC_WALK_ANIM = u8{14};
    constexpr auto NPC_WALK_ANIMS = u8{17};
    constexpr auto NPC_FIRST_OP = u8{30};
    constexpr auto NPC_LAST_OP = u8{39};
    constexpr auto NPC_HEADS = u8{60};
    constexpr auto NPC_RESIZE_X = u8{90};
    constexpr auto NPC_RESIZE_Y = u8{91};
    constexpr auto NPC_RESIZE_Z = u8{92};
    constexpr auto NPC_NO_MINIMAP = u8{93};
    constexpr auto NPC_COMBAT_LEVEL = u8{95};
    constexpr auto NPC_RESIZE_H = u8{97};
    constexpr auto NPC_RESIZE_V = u8{98};
    constexpr auto NPC_ALWAYS_ON_TOP = u8{99};
    constexpr auto NPC_AMBIENT = u8{100};
    constexpr auto NPC_CONTRAST = u8{101};
    constexpr auto NPC_HEAD_ICON = u8{102};
    constexpr auto NPC_TURN_SPEED = u8{103};

    constexpr auto OBJ_MODEL = u8{1};
    constexpr auto OBJ_ZOOM_2D = u8{4};
    constexpr auto OBJ_XAN_2D = u8{5};
    constexpr auto OBJ_YAN_2D = u8{6};
    constexpr auto OBJ_XOF_2D = u8{7};
    constexpr auto OBJ_YOF_2D = u8{8};
    // The webclient skips it without a name; the engine calls it code10.
    constexpr auto OBJ_CODE10 = u8{10};
    constexpr auto OBJ_STACKABLE = u8{11};
    constexpr auto OBJ_COST = u8{12};
    constexpr auto OBJ_MEMBERS = u8{16};
    constexpr auto OBJ_MAN_WEAR = u8{23};
    constexpr auto OBJ_MAN_WEAR_2 = u8{24};
    constexpr auto OBJ_WOMAN_WEAR = u8{25};
    constexpr auto OBJ_WOMAN_WEAR_2 = u8{26};
    constexpr auto OBJ_FIRST_OP = u8{30};
    constexpr auto OBJ_FIRST_INVENTORY_OP = u8{35};
    constexpr auto OBJ_LAST_INVENTORY_OP = u8{39};
    constexpr auto OBJ_MAN_WEAR_3 = u8{78};
    constexpr auto OBJ_WOMAN_WEAR_3 = u8{79};
    constexpr auto OBJ_MAN_HEAD = u8{90};
    constexpr auto OBJ_WOMAN_HEAD = u8{91};
    constexpr auto OBJ_MAN_HEAD_2 = u8{92};
    constexpr auto OBJ_WOMAN_HEAD_2 = u8{93};
    constexpr auto OBJ_ZAN_2D = u8{95};
    constexpr auto OBJ_CERTLINK = u8{97};
    constexpr auto OBJ_CERTTEMPLATE = u8{98};
    constexpr auto OBJ_FIRST_COUNT_OBJ = u8{100};
    constexpr auto OBJ_LAST_COUNT_OBJ = u8{109};
    constexpr auto OBJ_RESIZE_X = u8{110};
    constexpr auto OBJ_RESIZE_Y = u8{111};
    constexpr auto OBJ_RESIZE_Z = u8{112};
    constexpr auto OBJ_AMBIENT = u8{113};
    constexpr auto OBJ_CONTRAST = u8{114};
    constexpr auto OBJ_TEAM = u8{115};

    // The engine's VarPlayerType names 1, 2, 4, 5 and 6. The webclient reads the rest as server-side
    // fields without names, and the Java client's names are obfuscated, so they go by their numbers.
    constexpr auto VARP_SCOPE = u8{1};
    constexpr auto VARP_TYPE = u8{2};
    constexpr auto VARP_CODE3 = u8{3};
    constexpr auto VARP_NO_PROTECT = u8{4};
    constexpr auto VARP_CLIENT_CODE = u8{5};
    constexpr auto VARP_TRANSMIT = u8{6};
    constexpr auto VARP_CODE7 = u8{7};
    constexpr auto VARP_CODE8 = u8{8};
    constexpr auto VARP_CODE10 = u8{10};
    constexpr auto VARP_CODE11 = u8{11};
    constexpr auto VARP_CODE12 = u8{12};
    constexpr auto VARP_CODE13 = u8{13};

    // Opcodes first to last whose values are read and dropped: size bytes each, or with counted, a u8
    // count and then that many items of size bytes.
    struct DroppedOpcodes_s
    {
        u8 first;
        u8 last;
        std::size_t size;
        bool counted = false;
    };

    constexpr DroppedOpcodes_s Drop(u8 opcode, std::size_t size)
    {
        return {.first = opcode, .last = opcode, .size = size};
    }

    constexpr DroppedOpcodes_s DropCounted(u8 opcode, std::size_t itemSize)
    {
        return {.first = opcode, .last = opcode, .size = itemSize, .counted = true};
    }

    constexpr DroppedOpcodes_s DropRange(u8 first, u8 last, std::size_t size)
    {
        return {.first = first, .last = last, .size = size};
    }

    // we drop to save ram, as we do not need this info
    constexpr auto LOC_DROPPED = std::to_array({
        Drop(LOC_HILLSKEW, NO_VALUE),
        Drop(LOC_SHARELIGHT, NO_VALUE),
        Drop(LOC_OCCLUDE, NO_VALUE),
        Drop(LOC_ANIM, sizeof(u16)),
        Drop(LOC_WALL_WIDTH, sizeof(u8)),
        Drop(LOC_AMBIENT, sizeof(u8)),
        Drop(LOC_CONTRAST, sizeof(u8)),
        DropCounted(RECOLOUR, RECOLOUR_SIZE),
        Drop(LOC_MAP_FUNCTION, sizeof(u16)),
        Drop(LOC_MIRROR, NO_VALUE),
        Drop(LOC_NO_SHADOW, NO_VALUE),
        Drop(LOC_RESIZE_X, sizeof(u16)),
        Drop(LOC_RESIZE_Y, sizeof(u16)),
        Drop(LOC_RESIZE_Z, sizeof(u16)),
        Drop(LOC_MAP_SCENE, sizeof(u16)),
        Drop(LOC_OFFSET_X, sizeof(u16)),
        Drop(LOC_OFFSET_Y, sizeof(u16)),
        Drop(LOC_OFFSET_Z, sizeof(u16)),
        Drop(LOC_FORCE_DECOR, NO_VALUE),
        Drop(LOC_RAISE_OBJECT, sizeof(u8)),
    });

    constexpr auto NPC_DROPPED = std::to_array({
        DropCounted(NPC_MODELS, sizeof(u16)),
        Drop(NPC_READY_ANIM, sizeof(u16)),
        Drop(NPC_WALK_ANIM, sizeof(u16)),
        Drop(NPC_WALK_ANIMS, WALK_ANIMS_SIZE),
        DropCounted(RECOLOUR, RECOLOUR_SIZE),
        DropCounted(NPC_HEADS, sizeof(u16)),
        Drop(NPC_RESIZE_X, sizeof(u16)),
        Drop(NPC_RESIZE_Y, sizeof(u16)),
        Drop(NPC_RESIZE_Z, sizeof(u16)),
        Drop(NPC_NO_MINIMAP, NO_VALUE),
        Drop(NPC_RESIZE_H, sizeof(u16)),
        Drop(NPC_RESIZE_V, sizeof(u16)),
        Drop(NPC_ALWAYS_ON_TOP, NO_VALUE),
        Drop(NPC_AMBIENT, sizeof(u8)),
        Drop(NPC_CONTRAST, sizeof(u8)),
        Drop(NPC_HEAD_ICON, sizeof(u16)),
        Drop(NPC_TURN_SPEED, sizeof(u16)),
    });

    constexpr auto OBJ_DROPPED = std::to_array({
        Drop(OBJ_MODEL, sizeof(u16)),
        Drop(OBJ_ZOOM_2D, sizeof(u16)),
        Drop(OBJ_XAN_2D, sizeof(u16)),
        Drop(OBJ_YAN_2D, sizeof(u16)),
        Drop(OBJ_XOF_2D, sizeof(u16)),
        Drop(OBJ_YOF_2D, sizeof(u16)),
        Drop(OBJ_CODE10, sizeof(u16)),
        Drop(OBJ_MAN_WEAR, WEAR_SIZE),
        Drop(OBJ_MAN_WEAR_2, sizeof(u16)),
        Drop(OBJ_WOMAN_WEAR, WEAR_SIZE),
        Drop(OBJ_WOMAN_WEAR_2, sizeof(u16)),
        DropCounted(RECOLOUR, RECOLOUR_SIZE),
        Drop(OBJ_MAN_WEAR_3, sizeof(u16)),
        Drop(OBJ_WOMAN_WEAR_3, sizeof(u16)),
        Drop(OBJ_MAN_HEAD, sizeof(u16)),
        Drop(OBJ_WOMAN_HEAD, sizeof(u16)),
        Drop(OBJ_MAN_HEAD_2, sizeof(u16)),
        Drop(OBJ_WOMAN_HEAD_2, sizeof(u16)),
        Drop(OBJ_ZAN_2D, sizeof(u16)),
        DropRange(OBJ_FIRST_COUNT_OBJ, OBJ_LAST_COUNT_OBJ, COUNT_OBJ_SIZE),
        Drop(OBJ_RESIZE_X, sizeof(u16)),
        Drop(OBJ_RESIZE_Y, sizeof(u16)),
        Drop(OBJ_RESIZE_Z, sizeof(u16)),
        Drop(OBJ_AMBIENT, sizeof(u8)),
        Drop(OBJ_CONTRAST, sizeof(u8)),
        Drop(OBJ_TEAM, sizeof(u8)),
    });

    constexpr auto VARP_DROPPED = std::to_array({
        Drop(VARP_SCOPE, sizeof(u8)),
        Drop(VARP_TYPE, sizeof(u8)),
        Drop(VARP_CODE3, NO_VALUE),
        Drop(VARP_NO_PROTECT, NO_VALUE),
        Drop(VARP_TRANSMIT, NO_VALUE),
        Drop(VARP_CODE7, sizeof(u32)),
        Drop(VARP_CODE8, NO_VALUE),
        Drop(VARP_CODE11, NO_VALUE),
        Drop(VARP_CODE12, sizeof(u32)),
        Drop(VARP_CODE13, NO_VALUE),
    });

    // What a loc's model opcodes said, which decides whether it's active when opcode 19 doesn't.
    struct LocModels_s
    {
        bool present = false;
        bool shaped = false;
        u8 firstShape = 0;
    };

    // A banknote's links, resolved once every obj is decoded.
    struct CertLinks_s
    {
        std::optional<u16> link;
        std::optional<u16> templateId;
    };

    void Skip(Packet& packet, std::size_t count)
    {
        if (packet.GetAvailable() < count)
        {
            throw std::out_of_range{"value runs past the end"};
        }

        packet.SetPos(packet.GetPos() + count);
    }

    bool SkipDropped(Packet& packet, u8 opcode, std::span<const DroppedOpcodes_s> table)
    {
        const auto found = std::ranges::find_if(table, [opcode](const DroppedOpcodes_s& dropped)
        {
            return opcode >= dropped.first && opcode <= dropped.last;
        });

        if (found == table.end())
        {
            return false;
        }

        const auto count = found->counted ? std::size_t{packet.G1()} : std::size_t{1};
        Skip(packet, count * found->size);
        return true;
    }

    std::string ReadString(Packet& packet)
    {
        const auto unread = packet.GetData().subspan(packet.GetPos());
        if (std::ranges::find(unread, STRING_TERMINATOR) == unread.end())
        {
            throw CacheError{"a string runs past the end without its newline"};
        }

        return packet.GJStr();
    }

    bool EqualsIgnoringCase(std::string_view left, std::string_view right)
    {
        return std::ranges::equal(left, right, [](char a, char b)
        {
            return std::tolower(static_cast<unsigned char>(a)) == std::tolower(static_cast<unsigned char>(b));
        });
    }

    // Slots past the array's end are read and dropped, and "hidden", which the menu leaves out, can be
    // stored as NO_OPTION.
    void ReadOption(Packet& packet, std::size_t slot, std::span<u16> ops, TextPool& text, bool dropHidden)
    {
        const auto option = ReadString(packet);
        if (slot >= ops.size())
        {
            return;
        }

        if (dropHidden && EqualsIgnoringCase(option, HIDDEN_OPTION))
        {
            ops[slot] = TextPool::NO_OPTION;
            return;
        }

        ops[slot] = text.InternOption(option);
    }

    void ReadLocModels(Packet& packet, bool withShapes, LocModels_s& models)
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
        Skip(packet, (count + 1) * sizeof(u16));
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
            if (opcode == END_OPCODE)
            {
                break;
            }

            if (SkipDropped(packet, opcode, LOC_DROPPED))
            {
                continue;
            }

            if (opcode >= LOC_FIRST_OP && opcode <= LOC_LAST_OP)
            {
                hasOptions = true;
                ReadOption(packet, opcode - LOC_FIRST_OP, type.ops, text, true);
                continue;
            }

            switch (opcode)
            {
            case LOC_MODELS_WITH_SHAPES:
                ReadLocModels(packet, true, models);
                break;
            case NAME:
                type.name = text.Intern(ReadString(packet));
                break;
            case EXAMINE:
                type.examine = text.Intern(ReadString(packet));
                break;
            case LOC_MODELS:
                ReadLocModels(packet, false, models);
                break;
            case LOC_WIDTH:
                type.width = packet.G1();
                break;
            case LOC_LENGTH:
                type.length = packet.G1();
                break;
            case LOC_NO_BLOCK_WALK:
                type.blockWalk = false;
                break;
            case LOC_NO_BLOCK_RANGE:
                type.blockRange = false;
                break;
            case LOC_ACTIVE:
                // As the webclient reads it: a 1 makes the loc active, and any value stops the default.
                activeGiven = true;
                if (packet.G1() == ACTIVE_VALUE)
                {
                    type.active = true;
                }
                break;
            case LOC_FORCE_APPROACH:
                type.forceApproach = packet.G1();
                break;
            case LOC_BREAK_ROUTE_FINDING:
                breaksRouteFinding = true;
                break;
            case LOC_MULTILOC:
                SkipMultiloc(packet);
                break;
            default:
                throw CacheError{std::format("unknown opcode {}", opcode)};
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

    void DecodeNpc(Packet& packet, NpcType_s& type, TextPool& text)
    {
        while (true)
        {
            const auto opcode = packet.G1();
            if (opcode == END_OPCODE)
            {
                break;
            }

            if (SkipDropped(packet, opcode, NPC_DROPPED))
            {
                continue;
            }

            if (opcode >= NPC_FIRST_OP && opcode <= NPC_LAST_OP)
            {
                ReadOption(packet, opcode - NPC_FIRST_OP, type.ops, text, true);
                continue;
            }

            switch (opcode)
            {
            case NAME:
                type.name = text.Intern(ReadString(packet));
                break;
            case EXAMINE:
                type.examine = text.Intern(ReadString(packet));
                break;
            case NPC_SIZE:
                type.size = packet.G1();
                break;
            case NPC_COMBAT_LEVEL:
            {
                const auto level = packet.G2();
                type.combatLevel = level == NO_COMBAT_LEVEL ? std::nullopt : std::optional{level};
                break;
            }
            default:
                throw CacheError{std::format("unknown opcode {}", opcode)};
            }
        }
    }

    void DecodeObj(Packet& packet, ObjType_s& type, TextPool& text, CertLinks_s& cert)
    {
        while (true)
        {
            const auto opcode = packet.G1();
            if (opcode == END_OPCODE)
            {
                break;
            }

            if (SkipDropped(packet, opcode, OBJ_DROPPED))
            {
                continue;
            }

            if (opcode >= OBJ_FIRST_OP && opcode < OBJ_FIRST_INVENTORY_OP)
            {
                ReadOption(packet, opcode - OBJ_FIRST_OP, type.ops, text, true);
                continue;
            }

            if (opcode >= OBJ_FIRST_INVENTORY_OP && opcode <= OBJ_LAST_INVENTORY_OP)
            {
                ReadOption(packet, opcode - OBJ_FIRST_INVENTORY_OP, type.inventoryOps, text, false);
                continue;
            }

            switch (opcode)
            {
            case NAME:
                type.name = text.Intern(ReadString(packet));
                break;
            case EXAMINE:
                type.examine = text.Intern(ReadString(packet));
                break;
            case OBJ_STACKABLE:
                type.stackable = true;
                break;
            case OBJ_COST:
                type.cost = packet.G4();
                break;
            case OBJ_MEMBERS:
                type.members = true;
                break;
            case OBJ_CERTLINK:
                cert.link = packet.G2();
                break;
            case OBJ_CERTTEMPLATE:
                cert.templateId = packet.G2();
                break;
            default:
                throw CacheError{std::format("unknown opcode {}", opcode)};
            }
        }
    }

    void DecodeVarp(Packet& packet, VarpType_s& type)
    {
        while (true)
        {
            const auto opcode = packet.G1();
            if (opcode == END_OPCODE)
            {
                break;
            }

            if (SkipDropped(packet, opcode, VARP_DROPPED))
            {
                continue;
            }

            switch (opcode)
            {
            case VARP_CLIENT_CODE:
                type.clientCode = packet.G2();
                break;
            case VARP_CODE10:
                static_cast<void>(ReadString(packet));
                break;
            default:
                throw CacheError{std::format("unknown opcode {}", opcode)};
            }
        }
    }

    std::string_view GetArticle(std::string_view name)
    {
        if (name.empty())
        {
            return "a";
        }

        const auto initial = static_cast<char>(std::tolower(static_cast<unsigned char>(name.front())));
        return VOWELS.find(initial) == std::string_view::npos ? "a"sv : "an"sv;
    }

    // The webclient's ObjType.genCert: a note takes its name, members flag and value from the obj it's
    // a note of, stacks, and gets examine text that names that obj.
    void MakeNotes(std::vector<ObjType_s>& objs, std::span<const CertLinks_s> certs, TextPool& text)
    {
        for (auto& note : objs)
        {
            const auto& cert = certs[note.id];
            if (!cert.templateId)
            {
                continue;
            }

            if (!cert.link || *cert.link >= objs.size())
            {
                const auto link = cert.link ? s32{*cert.link} : -1;
                throw CacheError{std::format("obj {}: its certlink {} isn't an obj", note.id, link)};
            }

            const auto& linked = objs[*cert.link];
            note.name = linked.name;
            note.members = linked.members;
            note.cost = linked.cost;
            note.stackable = true;
            note.examine = text.Intern(std::format("Swap this note at any bank for {} {}.", GetArticle(linked.name), linked.name));
            note.noteOf = *cert.link;
        }
    }

    template <typename T, typename TDecode>
    std::vector<T> DecodeTypes(std::string_view kind, std::span<const u8> dat, std::span<const u8> idx, TDecode decode)
    {
        if (idx.size() < COUNT_SIZE || dat.size() < COUNT_SIZE)
        {
            throw CacheError{std::format("{0}.dat or {0}.idx is too short for its count", kind)};
        }

        auto index = Packet{idx};
        const auto count = std::size_t{index.G2()};
        const auto datCount = std::size_t{Packet{dat}.G2()};
        if (count != datCount)
        {
            throw CacheError{std::format("{0}.idx lists {1} definitions, but {0}.dat has {2}", kind, count, datCount)};
        }

        if (idx.size() < COUNT_SIZE + count * SIZE_ENTRY_SIZE)
        {
            throw CacheError{std::format("{}.idx is {} bytes, too short for {} sizes", kind, idx.size(), count)};
        }

        auto types = std::vector<T>(count);
        auto offset = COUNT_SIZE;
        for (std::size_t id = 0; id < count; ++id)
        {
            const auto size = std::size_t{index.G2()};
            if (offset + size > dat.size())
            {
                throw CacheError{std::format("{} {}: runs past the end of {}.dat", kind, id, kind)};
            }

            auto packet = Packet{dat.subspan(offset, size)};
            auto& type = types[id];
            type.id = static_cast<u16>(id);
            try
            {
                decode(packet, type);
            }
            catch (const CacheError& e)
            {
                throw CacheError{std::format("{} {}: {}", kind, id, e.what())};
            }
            catch (const std::out_of_range&)
            {
                throw CacheError{std::format("{} {}: runs past the end of its {} bytes", kind, id, size)};
            }

            if (packet.GetPos() != size)
            {
                throw CacheError{std::format("{} {}: ends at byte {} of its {}", kind, id, packet.GetPos(), size)};
            }

            offset += size;
        }

        if (offset != dat.size())
        {
            throw CacheError{std::format("{}.dat has {} bytes after its last definition", kind, dat.size() - offset)};
        }

        return types;
    }
}

std::vector<LocType_s> TypeDecoder::DecodeLocs(std::span<const u8> dat, std::span<const u8> idx, TextPool& text)
{
    return DecodeTypes<LocType_s>("loc", dat, idx, [&text](Packet& packet, LocType_s& type)
    {
        DecodeLoc(packet, type, text);
    });
}

std::vector<NpcType_s> TypeDecoder::DecodeNpcs(std::span<const u8> dat, std::span<const u8> idx, TextPool& text)
{
    return DecodeTypes<NpcType_s>("npc", dat, idx, [&text](Packet& packet, NpcType_s& type)
    {
        DecodeNpc(packet, type, text);
    });
}

std::vector<ObjType_s> TypeDecoder::DecodeObjs(std::span<const u8> dat, std::span<const u8> idx, TextPool& text)
{
    auto certs = std::vector<CertLinks_s>{};
    auto objs = DecodeTypes<ObjType_s>("obj", dat, idx, [&text, &certs](Packet& packet, ObjType_s& type)
    {
        DecodeObj(packet, type, text, certs.emplace_back());
    });

    MakeNotes(objs, certs, text);
    return objs;
}

std::vector<VarpType_s> TypeDecoder::DecodeVarps(std::span<const u8> dat, std::span<const u8> idx)
{
    return DecodeTypes<VarpType_s>("varp", dat, idx, [](Packet& packet, VarpType_s& type)
    {
        DecodeVarp(packet, type);
    });
}
