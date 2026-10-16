#include "pch.hpp"
#include "TypeDecoder.hpp"

#include "../Io/Packet.hpp"
#include "../Utils/StringUtils.hpp"
#include "DroppedOpcodes_s.hpp"
#include "Error/CacheError.hpp"
#include "TextPool.hpp"

namespace
{
    constexpr auto STRING_TERMINATOR = u8{'\n'};
    constexpr auto HIDDEN_OPTION = "hidden"sv;
}

void TypeDecoder::Skip(Packet& packet, std::size_t count)
{
    if (packet.GetAvailable() < count)
    {
        throw std::out_of_range{"value runs past the end"};
    }

    packet.SetPos(packet.GetPos() + count);
}

bool TypeDecoder::SkipDropped(Packet& packet, u8 opcode, std::span<const DroppedOpcodes_s> table)
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

std::string TypeDecoder::ReadString(Packet& packet)
{
    const auto unread = packet.GetData().subspan(packet.GetPos());
    if (std::ranges::find(unread, STRING_TERMINATOR) == unread.end())
    {
        throw CacheError{"a string runs past the end without its newline"};
    }

    return packet.GJStr();
}

void TypeDecoder::ReadOption(Packet& packet, std::size_t slot, std::span<u16> ops, TextPool& text, bool dropHidden)
{
    const auto option = ReadString(packet);

    if (slot >= ops.size())
    {
        return;
    }

    if (dropHidden && StringUtils::EqualsIgnoringCase(option, HIDDEN_OPTION))
    {
        ops[slot] = TextPool::NO_OPTION;
        return;
    }

    ops[slot] = text.InternOption(option);
}

void TypeDecoder::ThrowUnknown(u8 opcode)
{
    throw CacheError{std::format("unknown opcode {}", opcode)};
}
