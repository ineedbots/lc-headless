#include "pch.hpp"

#include "Cache/SeqDecoder.hpp"
#include "Game/State/EntityStatus.hpp"
#include "Game/State/Entity_s.hpp"
#include "Io/Packet.hpp"

#include <catch2/catch_test_macros.hpp>

namespace
{
    SeqType_s Seq(std::vector<u16> frames, std::vector<u16> delays, s32 loops = -1, s32 maxLoops = 99)
    {
        return {.frames = std::move(frames), .delays = std::move(delays), .loops = loops, .maxLoops = maxLoops};
    }

    // A 274 or 289 anim file: a head of frame ids and group counts, empty transforms, and a delay byte each.
    std::vector<u8> AnimFile(std::span<const std::pair<u16, u8>> frames)
    {
        auto head = Packet{};
        head.P2(static_cast<s32>(frames.size()));
        auto del = Packet{};
        for (const auto& [id, delay] : frames)
        {
            head.P2(id);
            head.P1(0);
            del.P1(delay);
        }

        auto file = Packet{};
        file.PData(head.GetData());
        file.PData(del.GetData());
        file.P2(static_cast<s32>(head.GetLength() - 2));
        file.P2(0);
        file.P2(0);
        file.P2(static_cast<s32>(del.GetLength()));
        return {file.GetData().begin(), file.GetData().end()};
    }
}

TEST_CASE("A sequence plays its frames once, at their own delays when it gives none", "[SeqDecoder]")
{
    const auto delays = FrameDelays{{10, 4}, {11, 6}};
    CHECK(SeqDecoder::GetLength(Seq({10, 11}, {0, 0}), delays) == 10);
    CHECK(SeqDecoder::GetLength(Seq({10, 11}, {3, 0}), delays) == 9);
    // A frame with no delay anywhere shows for a cycle.
    CHECK(SeqDecoder::GetLength(Seq({10, 12}, {0, 0}), delays) == 5);
    CHECK(SeqDecoder::GetLength(Seq({}, {}), delays) == 0);
}

TEST_CASE("A looping sequence replays its last frames until its passes are done", "[SeqDecoder]")
{
    const auto delays = FrameDelays{};
    CHECK(SeqDecoder::GetLength(Seq({1, 2, 3}, {2, 3, 4}, 2, 4), delays) == 9 + 3 * 7);
    CHECK(SeqDecoder::GetLength(Seq({1, 2, 3}, {2, 3, 4}, 2, 1), delays) == 9);
    // Stepping back past the start ends it.
    CHECK(SeqDecoder::GetLength(Seq({1, 2, 3}, {2, 3, 4}, 5, 4), delays) == 9);
}

TEST_CASE("seq.dat and an anim file are read", "[SeqDecoder]")
{
    auto dat = Packet{};
    dat.P2(2);
    dat.P1(1);
    dat.P1(2);
    for (const auto frame : {7, 8})
    {
        dat.P2(frame);
        dat.P2(65535);
        dat.P2(0);
    }

    dat.P1(2);
    dat.P2(1);
    dat.P1(8);
    dat.P1(3);
    // A walk merge of two, which is skipped.
    dat.P1(3);
    dat.P1(2);
    dat.P1(4);
    dat.P1(5);
    dat.P1(0);
    // The second type is empty.
    dat.P1(0);
    const auto types = SeqDecoder::DecodeTypes(dat.GetData());
    REQUIRE(types.size() == 2);
    CHECK(types[0].frames == std::vector<u16>{7, 8});
    CHECK(types[0].loops == 1);
    CHECK(types[0].maxLoops == 3);
    CHECK(types[1].frames.empty());

    auto delays = FrameDelays{};
    const auto frames = std::to_array<std::pair<u16, u8>>({{7, 5}, {8, 6}});
    SeqDecoder::ReadFrameDelays(AnimFile(frames), delays);
    CHECK(delays.at(7) == 5);
    CHECK(delays.at(8) == 6);
    CHECK(SeqDecoder::GetLength(types[0], delays) == 11 + 2 * 6);
}

TEST_CASE("An animation counts as playing until its sequence has played out", "[SeqDecoder]")
{
    auto entity = Entity_s{};
    entity.animation = Animation_s{.id = 5, .delay = 0, .tick = 100};
    // 61 cycles end in the third tick.
    CHECK(EntityStatus::GetAnimation(entity, 100, 61) == 5);
    CHECK(EntityStatus::GetAnimation(entity, 102, 61) == 5);
    CHECK(EntityStatus::GetAnimation(entity, 103, 61) == -1);
    // A delay holds it back.
    entity.animation.delay = 30;
    CHECK(EntityStatus::GetAnimation(entity, 103, 61) == 5);
    // Without a length, it plays until another replaces it.
    CHECK(EntityStatus::GetAnimation(entity, 1000, std::nullopt) == 5);
    entity.animation.id = -1;
    CHECK(EntityStatus::GetAnimation(entity, 100, 61) == -1);
}
