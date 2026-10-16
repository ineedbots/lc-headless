#include "pch.hpp"
#include "ObjTypeDecoder.hpp"

#include "../Io/Packet.hpp"
#include "DroppedOpcodes_s.hpp"
#include "Error/CacheError.hpp"
#include "ObjType_s.hpp"
#include "TextPool.hpp"
#include "TypeDecoder.hpp"

namespace
{
    using Dropped = DroppedOpcodes_s;

    constexpr auto VOWELS = "aeiou"sv;
    // A model and its offset.
    constexpr auto WEAR_SIZE = sizeof(u16) + sizeof(u8);
    // An obj and the count it's shown for.
    constexpr auto COUNT_OBJ_SIZE = 2 * sizeof(u16);

    constexpr auto MODEL = u8{1};
    constexpr auto ZOOM_2D = u8{4};
    constexpr auto XAN_2D = u8{5};
    constexpr auto YAN_2D = u8{6};
    constexpr auto XOF_2D = u8{7};
    constexpr auto YOF_2D = u8{8};
    // The webclient skips it without a name; the engine calls it code10.
    constexpr auto CODE10 = u8{10};
    constexpr auto STACKABLE = u8{11};
    constexpr auto COST = u8{12};
    constexpr auto MEMBERS = u8{16};
    constexpr auto MAN_WEAR = u8{23};
    constexpr auto MAN_WEAR_2 = u8{24};
    constexpr auto WOMAN_WEAR = u8{25};
    constexpr auto WOMAN_WEAR_2 = u8{26};
    constexpr auto FIRST_OP = u8{30};
    constexpr auto FIRST_INVENTORY_OP = u8{35};
    constexpr auto LAST_INVENTORY_OP = u8{39};
    constexpr auto MAN_WEAR_3 = u8{78};
    constexpr auto WOMAN_WEAR_3 = u8{79};
    constexpr auto MAN_HEAD = u8{90};
    constexpr auto WOMAN_HEAD = u8{91};
    constexpr auto MAN_HEAD_2 = u8{92};
    constexpr auto WOMAN_HEAD_2 = u8{93};
    constexpr auto ZAN_2D = u8{95};
    constexpr auto CERTLINK = u8{97};
    constexpr auto CERTTEMPLATE = u8{98};
    constexpr auto FIRST_COUNT_OBJ = u8{100};
    constexpr auto LAST_COUNT_OBJ = u8{109};
    constexpr auto RESIZE_X = u8{110};
    constexpr auto RESIZE_Y = u8{111};
    constexpr auto RESIZE_Z = u8{112};
    constexpr auto AMBIENT = u8{113};
    constexpr auto CONTRAST = u8{114};
    constexpr auto TEAM = u8{115};

    constexpr auto DROPPED = std::to_array({
        Dropped::Drop(MODEL, sizeof(u16)),
        Dropped::Drop(ZOOM_2D, sizeof(u16)),
        Dropped::Drop(XAN_2D, sizeof(u16)),
        Dropped::Drop(YAN_2D, sizeof(u16)),
        Dropped::Drop(XOF_2D, sizeof(u16)),
        Dropped::Drop(YOF_2D, sizeof(u16)),
        Dropped::Drop(CODE10, sizeof(u16)),
        Dropped::Drop(MAN_WEAR, WEAR_SIZE),
        Dropped::Drop(MAN_WEAR_2, sizeof(u16)),
        Dropped::Drop(WOMAN_WEAR, WEAR_SIZE),
        Dropped::Drop(WOMAN_WEAR_2, sizeof(u16)),
        Dropped::DropCounted(TypeDecoder::RECOLOUR, TypeDecoder::RECOLOUR_SIZE),
        Dropped::Drop(MAN_WEAR_3, sizeof(u16)),
        Dropped::Drop(WOMAN_WEAR_3, sizeof(u16)),
        Dropped::Drop(MAN_HEAD, sizeof(u16)),
        Dropped::Drop(WOMAN_HEAD, sizeof(u16)),
        Dropped::Drop(MAN_HEAD_2, sizeof(u16)),
        Dropped::Drop(WOMAN_HEAD_2, sizeof(u16)),
        Dropped::Drop(ZAN_2D, sizeof(u16)),
        Dropped::DropRange(FIRST_COUNT_OBJ, LAST_COUNT_OBJ, COUNT_OBJ_SIZE),
        Dropped::Drop(RESIZE_X, sizeof(u16)),
        Dropped::Drop(RESIZE_Y, sizeof(u16)),
        Dropped::Drop(RESIZE_Z, sizeof(u16)),
        Dropped::Drop(AMBIENT, sizeof(u8)),
        Dropped::Drop(CONTRAST, sizeof(u8)),
        Dropped::Drop(TEAM, sizeof(u8)),
    });

    // A banknote's links, resolved once every obj is decoded.
    struct CertLinks_s
    {
        std::optional<u16> link;
        std::optional<u16> templateId;
    };

    void DecodeObj(Packet& packet, ObjType_s& type, TextPool& text, CertLinks_s& cert)
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

            if (opcode >= FIRST_OP && opcode < FIRST_INVENTORY_OP)
            {
                TypeDecoder::ReadOption(packet, opcode - FIRST_OP, type.ops, text, true);
                continue;
            }

            if (opcode >= FIRST_INVENTORY_OP && opcode <= LAST_INVENTORY_OP)
            {
                TypeDecoder::ReadOption(packet, opcode - FIRST_INVENTORY_OP, type.inventoryOps, text, false);
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
            case STACKABLE:
                type.stackable = true;
                break;
            case COST:
                type.cost = packet.G4();
                break;
            case MEMBERS:
                type.members = true;
                break;
            case CERTLINK:
                cert.link = packet.G2();
                break;
            case CERTTEMPLATE:
                cert.templateId = packet.G2();
                break;
            default:
                TypeDecoder::ThrowUnknown(opcode);
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
}

std::vector<ObjType_s> ObjTypeDecoder::Decode(std::span<const u8> dat, std::span<const u8> idx, TextPool& text)
{
    auto certs = std::vector<CertLinks_s>{};
    auto objs = TypeDecoder::DecodeAll<ObjType_s>("obj", dat, idx, [&text, &certs](Packet& packet, ObjType_s& type)
    {
        DecodeObj(packet, type, text, certs.emplace_back());
    });

    MakeNotes(objs, certs, text);
    return objs;
}
