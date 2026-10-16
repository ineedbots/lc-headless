#include "pch.hpp"

#include "Game/Decode/PacketFields.hpp"
#include "Io/Packet.hpp"

#include <catch2/catch_test_macros.hpp>

TEST_CASE("PacketFields reads an id, and none as -1", "[PacketFields]")
{
    auto written = Packet{};
    written.P2(0);
    written.P2(1234);
    written.P2(PacketFields::NO_ID);

    auto packet = Packet{written.GetData()};
    CHECK(PacketFields::ReadId(packet) == 0);
    CHECK(PacketFields::ReadId(packet) == 1234);
    CHECK(PacketFields::ReadId(packet) == -1);
    CHECK(packet.GetAvailable() == 0);
}

TEST_CASE("PacketFields reads a base-37 name from its 8 bytes", "[PacketFields]")
{
    auto written = Packet{};
    written.P8(0x0123456789ABCDEF);

    auto packet = Packet{written.GetData()};
    CHECK(PacketFields::ReadName37(packet) == u64{0x0123456789ABCDEF});
    CHECK(packet.GetAvailable() == 0);
}
