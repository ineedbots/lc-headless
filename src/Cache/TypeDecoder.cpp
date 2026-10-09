#include "pch.hpp"
#include "TypeDecoder.hpp"

#include "../Io/Packet.hpp"
#include "CacheError.hpp"
#include "LocType_s.hpp"
#include "NpcType_s.hpp"
#include "ObjType_s.hpp"
#include "TextPool.hpp"

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

    constexpr auto NAME = u8{2};
    constexpr auto EXAMINE = u8{3};

    constexpr auto LOC_MODELS_WITH_SHAPES = u8{1};
    constexpr auto LOC_MODELS = u8{5};
    constexpr auto LOC_WIDTH = u8{14};
    constexpr auto LOC_LENGTH = u8{15};
    constexpr auto LOC_NO_BLOCK_WALK = u8{17};
    constexpr auto LOC_NO_BLOCK_RANGE = u8{18};
    constexpr auto LOC_ACTIVE = u8{19};
    constexpr auto LOC_FIRST_OP = u8{30};
    constexpr auto LOC_LAST_OP = u8{38};
    constexpr auto LOC_FORCE_APPROACH = u8{69};
    constexpr auto LOC_BREAK_ROUTE_FINDING = u8{74};
    constexpr auto LOC_MULTILOC = u8{77};

    constexpr auto NPC_SIZE = u8{12};
    constexpr auto NPC_FIRST_OP = u8{30};
    constexpr auto NPC_LAST_OP = u8{39};
    constexpr auto NPC_COMBAT_LEVEL = u8{95};

    constexpr auto OBJ_STACKABLE = u8{11};
    constexpr auto OBJ_COST = u8{12};
    constexpr auto OBJ_MEMBERS = u8{16};
    constexpr auto OBJ_FIRST_OP = u8{30};
    constexpr auto OBJ_FIRST_INVENTORY_OP = u8{35};
    constexpr auto OBJ_LAST_INVENTORY_OP = u8{39};
    constexpr auto OBJ_CERTLINK = u8{97};
    constexpr auto OBJ_CERTTEMPLATE = u8{98};

    // Opcodes first to last whose values are read and dropped: size bytes each, or with counted, a u8
    // count and then that many items of size bytes.
    struct DroppedOpcodes_s
    {
        u8 first;
        u8 last;
        u8 size;
        bool counted = false;
    };

    constexpr auto LOC_DROPPED = std::to_array<DroppedOpcodes_s>({
        {21, 23, 0},
        {62, 62, 0},
        {64, 64, 0},
        {73, 73, 0},
        {28, 29, 1},
        {39, 39, 1},
        {75, 75, 1},
        {24, 24, 2},
        {60, 60, 2},
        {65, 68, 2},
        {70, 72, 2},
        {40, 40, 4, true},
    });

    constexpr auto NPC_DROPPED = std::to_array<DroppedOpcodes_s>({
        {93, 93, 0},
        {99, 99, 0},
        {100, 101, 1},
        {13, 14, 2},
        {90, 92, 2},
        {97, 98, 2},
        {102, 103, 2},
        {17, 17, 8},
        {1, 1, 2, true},
        {60, 60, 2, true},
        {40, 40, 4, true},
    });

    constexpr auto OBJ_DROPPED = std::to_array<DroppedOpcodes_s>({
        {113, 115, 1},
        {1, 1, 2},
        {4, 8, 2},
        {10, 10, 2},
        {24, 24, 2},
        {26, 26, 2},
        {78, 79, 2},
        {90, 93, 2},
        {95, 95, 2},
        {110, 112, 2},
        {23, 23, 3},
        {25, 25, 3},
        {100, 109, 4},
        {40, 40, 4, true},
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
