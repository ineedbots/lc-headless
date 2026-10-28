#include "pch.hpp"

#include "Cache/SeqDecoder.hpp"
#include "Cache/Error/CacheError.hpp"
#include "Game/State/EntityStatus.hpp"
#include "Game/State/Entity_s.hpp"
#include "Io/Packet.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/generators/catch_generators.hpp>
#include <catch2/matchers/catch_matchers_string.hpp>

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

TEST_CASE("Sequence metadata does not consume the next sequence", "[SeqDecoder]")
{
    // Every metadata opcode the client ignores, with distinct payloads and an empty second sequence.
    const auto dat = std::to_array<u8>({0, 2, 4, 5, 80, 6, 1, 2, 7, 3, 4, 9, 70, 10, 60, 11, 50, 0, 0});
    const auto types = SeqDecoder::DecodeTypes(dat);
    REQUIRE(types.size() == 2);
    CHECK(types[0].frames.empty());
    CHECK(types[1].frames.empty());
    CHECK(SeqDecoder::DecodeTypes(std::to_array<u8>({0, 0})).empty());
}

TEST_CASE("Sequence decoding rejects unknown opcodes and truncated frames", "[SeqDecoder]")
{
    CHECK_THROWS_WITH(SeqDecoder::DecodeTypes(std::to_array<u8>({0, 1, 12})),
                      Catch::Matchers::ContainsSubstring("seq: unknown opcode 12"));
    CHECK_THROWS_AS(SeqDecoder::DecodeTypes(std::to_array<u8>({0, 1, 12})), CacheError);

    const auto complete = std::to_array<u8>({0, 1, 1, 1, 0, 7, 255, 255, 0, 5, 0});
    for (auto size = std::size_t{0}; size < complete.size(); ++size)
    {
        CAPTURE(size);
        CHECK_THROWS_AS(SeqDecoder::DecodeTypes(std::span{complete}.first(size)), std::out_of_range);
    }
    REQUIRE(SeqDecoder::DecodeTypes(complete).size() == 1);
}

TEST_CASE("Animation files need a complete section table and declared sections", "[SeqDecoder]")
{
    auto delays = FrameDelays{};
    const auto shortFile = std::array<u8, 7>{};
    for (auto size = std::size_t{0}; size <= shortFile.size(); ++size)
    {
        CAPTURE(size);
        CHECK_THROWS_AS(SeqDecoder::ReadFrameDelays(std::span{shortFile}.first(size), delays), CacheError);
    }

    // Declaring a transform or delay section beyond the end must fail before reading frames.
    const auto offset = GENERATE(0, 2, 4, 6);
    auto file = std::array<u8, 10>{};
    file[2 + offset] = 255;
    CHECK_THROWS_WITH(SeqDecoder::ReadFrameDelays(file, delays),
                      Catch::Matchers::ContainsSubstring("shorter than its sections"));
    CHECK(delays.empty());
}

TEST_CASE("Animation frame counts cannot read past their head or delay section", "[SeqDecoder]")
{
    // A valid empty head, followed by lengths for no transforms or delays.
    auto file = std::array<u8, 10>{};
    file[1] = 1; // Claims one frame, but neither its id nor its delay is present.
    auto delays = FrameDelays{};
    CHECK_THROWS_AS(SeqDecoder::ReadFrameDelays(file, delays), std::out_of_range);

    const auto frames = std::to_array<std::pair<u16, u8>>({{7, 5}});
    auto missingDelay = AnimFile(frames);
    // Remove only the declared delay length; the frame head still claims one frame.
    missingDelay.back() = 0;
    CHECK_THROWS_AS(SeqDecoder::ReadFrameDelays(missingDelay, delays), std::out_of_range);
}

TEST_CASE("225 animation heads include a maximum id and each frame's base", "[SeqDecoder]")
{
    const auto head = std::to_array<u8>({0, 2, 0, 20, 0, 7, 0, 30, 2, 0, 20, 0, 40, 3});
    const auto del = std::to_array<u8>({5, 9});
    auto delays = FrameDelays{{7, 1}, {99, 12}};
    SeqDecoder::ReadFrameDelays225(head, del, delays);
    CHECK(delays.at(7) == 5);
    CHECK(delays.at(20) == 9);
    CHECK(delays.at(99) == 12);
    CHECK(delays.size() == 3);
    CHECK(SeqDecoder::GetLength(Seq({7, 20}, {0, 0}), delays) == 14);
}

TEST_CASE("225 animation decoding rejects incomplete headers and delay lists", "[SeqDecoder]")
{
    const auto head = std::to_array<u8>({0, 1, 0, 7, 0, 7, 0, 30, 0});
    const auto del = std::to_array<u8>({5});
    for (auto size = std::size_t{0}; size < head.size(); ++size)
    {
        CAPTURE(size);
        auto delays = FrameDelays{};
        CHECK_THROWS_AS(SeqDecoder::ReadFrameDelays225(std::span{head}.first(size), del, delays), std::out_of_range);
    }
    auto delays = FrameDelays{};
    CHECK_THROWS_AS(SeqDecoder::ReadFrameDelays225(head, {}, delays), std::out_of_range);
}

TEST_CASE("Sequence sentinel frames and zero delays last at least one cycle", "[SeqDecoder]")
{
    const auto delays = FrameDelays{{65535, 50}, {7, 0}};
    CHECK(SeqDecoder::GetLength(Seq({65535, 7, 8}, {0, 0, 0}), delays) == 3);
    CHECK(SeqDecoder::GetLength(Seq({7}, {4}, 0, 99), delays) == 4);
    CHECK(SeqDecoder::GetLength(Seq({7}, {4}, 1, 0), delays) == 4);
    CHECK(SeqDecoder::GetLength(Seq({7}, {4}, 1, 3), delays) == 12);
}
