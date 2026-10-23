#include "pch.hpp"
#include "SeqDecoder.hpp"

#include "../Io/Packet.hpp"
#include "Error/CacheError.hpp"

namespace
{
    // The webclient's SeqType opcodes, which 225 to 289 share.
    constexpr auto FRAMES = u8{1};
    constexpr auto LOOPS = u8{2};
    constexpr auto WALK_MERGE = u8{3};
    constexpr auto REACH_FORWARD = u8{4};
    constexpr auto PRIORITY = u8{5};
    constexpr auto REPLACE_HELD_LEFT = u8{6};
    constexpr auto REPLACE_HELD_RIGHT = u8{7};
    constexpr auto MAX_LOOPS = u8{8};
    constexpr auto PREANIM_MOVE = u8{9};
    constexpr auto POSTANIM_MOVE = u8{10};
    constexpr auto DUPLICATE_BEHAVIOUR = u8{11};
    constexpr auto END = u8{0};
    constexpr auto NO_FRAME = u16{65535};
    constexpr auto SECTION_LENGTHS_SIZE = std::size_t{8};

    SeqType_s DecodeType(Packet& packet)
    {
        auto type = SeqType_s{};
        while (true)
        {
            const auto opcode = packet.G1();
            switch (opcode)
            {
            case END:
                return type;
            case FRAMES:
            {
                const auto count = packet.G1();
                for (auto i = 0; i < count; ++i)
                {
                    type.frames.push_back(packet.G2());
                    static_cast<void>(packet.G2());
                    type.delays.push_back(packet.G2());
                }

                break;
            }
            case LOOPS:
                type.loops = packet.G2();
                break;
            case WALK_MERGE:
            {
                const auto count = packet.G1();
                packet.SetPos(packet.GetPos() + count);
                break;
            }
            case REACH_FORWARD:
                break;
            case PRIORITY:
            case PREANIM_MOVE:
            case POSTANIM_MOVE:
            case DUPLICATE_BEHAVIOUR:
                static_cast<void>(packet.G1());
                break;
            case REPLACE_HELD_LEFT:
            case REPLACE_HELD_RIGHT:
                static_cast<void>(packet.G2());
                break;
            case MAX_LOOPS:
                type.maxLoops = packet.G1();
                break;
            default:
                throw CacheError{std::format("seq: unknown opcode {}", opcode)};
            }
        }
    }

    // The frames of one head section: each frame's id and group count, as many as its first two bytes say, with a
    // delay byte each in del. 225's heads also give the highest frame id after the count, and each frame's base.
    void ReadHeads(Packet& head, Packet& del, bool is225, FrameDelays& delays)
    {
        const auto total = head.G2();
        if (is225)
        {
            static_cast<void>(head.G2());
        }

        for (auto i = 0; i < total; ++i)
        {
            const auto id = head.G2();
            delays.insert_or_assign(id, del.G1());
            if (is225)
            {
                static_cast<void>(head.G2());
            }

            static_cast<void>(head.G1());
        }
    }
}

std::vector<SeqType_s> SeqDecoder::DecodeTypes(std::span<const u8> dat)
{
    auto packet = Packet{dat};
    const auto count = packet.G2();
    auto types = std::vector<SeqType_s>{};
    types.reserve(count);
    for (auto id = 0; id < count; ++id)
    {
        types.push_back(DecodeType(packet));
    }

    return types;
}

void SeqDecoder::ReadFrameDelays(std::span<const u8> file, FrameDelays& delays)
{
    if (file.size() < SECTION_LENGTHS_SIZE)
    {
        throw CacheError{std::format("anim file is {} bytes, too short for its section lengths", file.size())};
    }

    auto lengths = Packet{file.last(SECTION_LENGTHS_SIZE)};
    const auto headLength = lengths.G2();
    const auto tran1Length = lengths.G2();
    const auto tran2Length = lengths.G2();
    const auto delLength = lengths.G2();

    // The head's frame count comes before the length that counts it.
    const auto headSize = std::size_t{headLength} + 2;
    const auto delStart = headSize + tran1Length + tran2Length;
    if (delStart + delLength > file.size())
    {
        throw CacheError{std::format("anim file is {} bytes, shorter than its sections", file.size())};
    }

    auto head = Packet{file.first(headSize)};
    auto del = Packet{file.subspan(delStart, delLength)};
    ReadHeads(head, del, false, delays);
}

void SeqDecoder::ReadFrameDelays225(std::span<const u8> head, std::span<const u8> del, FrameDelays& delays)
{
    auto headPacket = Packet{head};
    auto delPacket = Packet{del};
    ReadHeads(headPacket, delPacket, true, delays);
}

u32 SeqDecoder::GetLength(const SeqType_s& type, const FrameDelays& delays)
{
    const auto count = type.frames.size();
    if (count == 0)
    {
        return 0;
    }

    const auto delayOf = [&type, &delays](std::size_t frame)
    {
        auto delay = u32{type.delays[frame]};
        if (delay == 0 && type.frames[frame] != NO_FRAME)
        {
            const auto found = delays.find(type.frames[frame]);
            delay = found == delays.end() ? 0 : found->second;
        }

        return delay == 0 ? u32{1} : delay;
    };

    auto first = u32{0};
    for (auto frame = std::size_t{0}; frame < count; ++frame)
    {
        first += delayOf(frame);
    }

    // After each pass the client steps back loops frames, until maxLoops passes have played; a sequence that
    // doesn't loop, or would step back past its start, plays once.
    if (type.loops <= 0 || static_cast<std::size_t>(type.loops) > count || type.maxLoops <= 1)
    {
        return first;
    }

    auto replay = u32{0};
    for (auto frame = count - static_cast<std::size_t>(type.loops); frame < count; ++frame)
    {
        replay += delayOf(frame);
    }

    return first + replay * static_cast<u32>(type.maxLoops - 1);
}
