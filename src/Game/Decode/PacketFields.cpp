#include "pch.hpp"
#include "PacketFields.hpp"

#include "../../Io/Packet.hpp"

s32 PacketFields::ReadId(Packet& packet)
{
    const auto id = packet.G2();
    return id == NO_ID ? -1 : id;
}

u64 PacketFields::ReadName37(Packet& packet)
{
    return std::bit_cast<u64>(packet.G8());
}
