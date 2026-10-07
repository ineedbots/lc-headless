#include "pch.hpp"
#include "Fixtures.hpp"

#include "BitWriter.hpp"
#include "Game/Protocol/Base37.hpp"
#include "Game/State/GameState_s.hpp"
#include "Io/Packet.hpp"

namespace
{
    constexpr auto ANIMS = std::to_array<s32>({808, 823, 819, 820, 821, 822, 824});
    constexpr auto WEAR_SLOT_COUNT = 12;
    constexpr auto WEAPON_SLOT = 3;
    constexpr auto TORSO_SLOT = 4;
}

std::vector<u8> Fixtures::ToBytes(const Packet& packet)
{
    const auto data = packet.GetData();
    return {data.begin(), data.end()};
}

std::vector<u8> Fixtures::Concat(std::span<const u8> first, std::span<const u8> second)
{
    auto bytes = std::vector<u8>{first.begin(), first.end()};
    bytes.insert(bytes.end(), second.begin(), second.end());
    return bytes;
}

std::vector<u8> Fixtures::Appearance(std::string_view name, std::optional<u16> npcTransform)
{
    auto packet = Packet{};
    packet.P1(1);
    packet.P1(0);
    if (npcTransform)
    {
        packet.P2(0xFFFF);
        packet.P2(*npcTransform);
    }
    else
    {
        for (auto slot = 0; slot < WEAR_SLOT_COUNT; ++slot)
        {
            if (slot == WEAPON_SLOT)
            {
                packet.P2(0x200 + WEAPON);
            }
            else if (slot == TORSO_SLOT)
            {
                packet.P2(0x100 + TORSO_KIT);
            }
            else
            {
                packet.P1(0);
            }
        }
    }

    for (auto colour = 0; colour < 5; ++colour)
    {
        packet.P1(colour);
    }

    for (const auto anim : ANIMS)
    {
        packet.P2(anim);
    }

    packet.P8(std::bit_cast<s64>(Base37::Encode(name)));
    packet.P1(3);
    packet.P2(32);
    return ToBytes(packet);
}

std::vector<u8> Fixtures::Rebuild(s32 zoneX, s32 zoneZ)
{
    auto packet = Packet{};
    packet.P2(zoneX);
    packet.P2(zoneZ);
    return ToBytes(packet);
}

std::vector<u8> Fixtures::UpdatePid(u16 pid, bool members)
{
    auto packet = Packet{};
    packet.P2(pid);
    packet.P1(members ? 1 : 0);
    return ToBytes(packet);
}

std::vector<u8> Fixtures::PlaceLocalPlayer(s32 localX, s32 localZ, s32 level, std::span<const u8> appearance)
{
    const auto hasExtended = !appearance.empty();
    auto bits = BitWriter{};
    bits.Put(1, 1).Put(2, 3).Put(2, level).Put(7, localX).Put(7, localZ).Put(1, 1).Put(1, hasExtended ? 1 : 0);
    bits.Put(8, 0);
    if (!hasExtended)
    {
        return bits.GetBytes();
    }

    bits.Put(11, 2047);
    auto extended = Packet{};
    extended.P1(0x01);
    extended.P1(static_cast<s32>(appearance.size()));
    extended.PData(appearance);
    return Concat(bits.GetBytes(), ToBytes(extended));
}

std::vector<u8> Fixtures::AddNpc(u16 index, u16 type, s32 dx, s32 dz)
{
    auto bits = BitWriter{};
    bits.Put(8, 0).Put(14, index).Put(11, type).Put(5, dx).Put(5, dz).Put(1, 1).Put(1, 0);
    return bits.GetBytes();
}

std::vector<u8> Fixtures::Zone(s32 localX, s32 localZ)
{
    auto packet = Packet{};
    packet.P1(localX);
    packet.P1(localZ);
    return ToBytes(packet);
}

std::vector<u8> Fixtures::ObjAdd(u8 pos, u16 obj, u16 count)
{
    auto packet = Packet{};
    packet.P1(pos);
    packet.P2(obj);
    packet.P2(count);
    return ToBytes(packet);
}

std::vector<u8> Fixtures::MessageGame(std::string_view text)
{
    auto packet = Packet{};
    packet.PJStr(text);
    return ToBytes(packet);
}

GameState_s Fixtures::PlacedState()
{
    auto state = GameState_s{};
    state.buildArea = BuildArea_s{.loaded = true, .centreZoneX = CENTRE_ZONE, .centreZoneZ = CENTRE_ZONE, .baseX = BASE, .baseZ = BASE};
    state.pid = PID;
    state.placed = true;
    state.localPlayer.index = PID;
    state.localPlayer.tile = Tile_s{.x = HOME, .z = HOME, .level = 0};
    return state;
}
