#pragma once

#include "Game/State/GameState_s.hpp"
#include "Io/Packet.hpp"

// Payload builders that encode server packets the way the engine's encoders do.
class Fixtures
{
public:
    static constexpr s32 CENTRE_ZONE = 400;
    static constexpr s32 BASE = (CENTRE_ZONE - 6) * 8;
    static constexpr s32 HOME_LOCAL = 48;
    static constexpr s32 HOME = BASE + HOME_LOCAL;
    static constexpr u16 PID = 5;
    static constexpr u16 WEAPON = 1277;
    static constexpr u16 TORSO_KIT = 18;

    Fixtures() = delete;

    [[nodiscard]] static std::vector<u8> ToBytes(const Packet& packet);
    [[nodiscard]] static std::vector<u8> Concat(std::span<const u8> first, std::span<const u8> second);

    [[nodiscard]] static std::vector<u8> Appearance(std::string_view name, std::optional<u16> npcTransform = std::nullopt);
    [[nodiscard]] static std::vector<u8> Rebuild(s32 zoneX = CENTRE_ZONE, s32 zoneZ = CENTRE_ZONE);
    [[nodiscard]] static std::vector<u8> UpdatePid(u16 pid = PID, bool members = true);
    [[nodiscard]] static std::vector<u8> PlaceLocalPlayer(s32 localX = HOME_LOCAL, s32 localZ = HOME_LOCAL, s32 level = 0, std::span<const u8> appearance = {});
    [[nodiscard]] static std::vector<u8> AddNpc(u16 index, u16 type, s32 dx, s32 dz);
    [[nodiscard]] static std::vector<u8> Zone(s32 localX, s32 localZ);
    [[nodiscard]] static std::vector<u8> ObjAdd(u8 pos, u16 obj, u16 count);
    [[nodiscard]] static std::vector<u8> MessageGame(std::string_view text);

    // A state that has had a rebuild, a PID and a placement at (HOME, HOME, 0).
    [[nodiscard]] static GameState_s PlacedState();
};
