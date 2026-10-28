#include "pch.hpp"
#include "Game/Protocol/ProtTableBuilder.hpp"
#include <catch2/catch_test_macros.hpp>
#include <catch2/generators/catch_generators.hpp>

namespace
{
    enum class PacketKind : u8 { First, Second, Third };
    struct Row { PacketKind prot; u8 opcode; s32 size; };
    struct Table
    {
        std::array<std::optional<PacketKind>, 256> byOpcode{};
        std::array<std::optional<WireProt_s>, 3> byProt{};
    };
}

TEST_CASE("Protocol table builder preserves sparse wire opcodes and both lookup directions", "[Protocol][CompletionCoverage]")
{
    const auto opcode = GENERATE(u8{0}, u8{127}, u8{255});
    const auto rows = std::array{Row{PacketKind::Third, opcode, -2}, Row{PacketKind::First, 42, 6}};
    const auto table = ProtTableBuilder::Build<Table>(rows);
    CHECK(table.byOpcode[opcode] == PacketKind::Third);
    CHECK(table.byOpcode[42] == PacketKind::First);
    CHECK_FALSE(table.byOpcode[43].has_value());
    REQUIRE(table.byProt[0].has_value());
    CHECK(table.byProt[0]->opcode == 42);
    CHECK(table.byProt[0]->size == 6);
    CHECK_FALSE(table.byProt[1].has_value());
    REQUIRE(table.byProt[2].has_value());
    CHECK(table.byProt[2]->opcode == opcode);
    CHECK(table.byProt[2]->size == -2);
    const auto empty = ProtTableBuilder::Build<Table>(std::array<Row, 0>{});
    CHECK(std::ranges::none_of(empty.byOpcode, [](const auto& value) { return value.has_value(); }));
    CHECK(std::ranges::none_of(empty.byProt, [](const auto& value) { return value.has_value(); }));
}

TEST_CASE("Protocol table validation rejects duplicate packets and opcodes", "[Protocol][CompletionCoverage]")
{
    auto rows = std::array{Row{PacketKind::First, 10, 0}, Row{PacketKind::Second, 20, -1}, Row{PacketKind::Third, 30, -2}};
    REQUIRE(ProtTableBuilder::HasUniqueRows(rows));
    SECTION("duplicate wire opcode") { rows[2].opcode = rows[0].opcode; }
    SECTION("duplicate packet") { rows[2].prot = rows[1].prot; }
    CHECK_FALSE(ProtTableBuilder::HasUniqueRows(rows));
    CHECK(ProtTableBuilder::HasUniqueRows(std::array<Row, 0>{}));
    CHECK(ProtTableBuilder::HasUniqueRows(std::array{rows[0]}));
}

TEST_CASE("Protocol info validation requires each packet to occupy its own enum index", "[Protocol][CompletionCoverage]")
{
    auto rows = std::array{Row{PacketKind::First, 10, 0}, Row{PacketKind::Second, 20, -1}, Row{PacketKind::Third, 30, -2}};
    REQUIRE(ProtTableBuilder::IsInProtOrder(rows));
    const auto index = GENERATE(std::size_t{0}, std::size_t{1}, std::size_t{2});
    rows[index].prot = static_cast<PacketKind>((index + 1) % rows.size());
    CHECK_FALSE(ProtTableBuilder::IsInProtOrder(rows));
    CHECK(ProtTableBuilder::IsInProtOrder(std::array<Row, 0>{}));
}
