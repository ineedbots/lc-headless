#pragma once

#include "../../Io/Packet.hpp"
#include "../State/GameState_s.hpp"
#include "../State/Zone_s.hpp"
#include "../Tile_s.hpp"

class ZoneDecoder
{
public:
    static constexpr s32 ACTIVE_ZONE_RADIUS = 3;
    static constexpr s32 BUILD_AREA_ZONES = 13;

    void SetZone(Packet& packet);
    void ResetZone(GameState_s& state) const;
    void DecodeSubPacket(u8 opcode, Packet& packet, GameState_s& state) const;
    void DecodeEnclosed(Packet& packet, GameState_s& state) const;

    [[nodiscard]] static LocLayer_e GetLayer(u8 shape);
    [[nodiscard]] static bool IsActive(const GameState_s& state, const Tile_s& tile);
    static void PruneInactive(GameState_s& state);

private:
    [[nodiscard]] Zone_s GetZone(const GameState_s& state) const;

    static void SetLoc(GameState_s& state, const Tile_s& tile, u8 info, s32 id);
    static void AddObj(GameState_s& state, const Tile_s& tile, u16 obj, s32 count);
    static void DeleteObj(GameState_s& state, const Tile_s& tile, u16 obj);
    static void CountObj(GameState_s& state, const Tile_s& tile, u16 obj, u16 oldCount, u16 newCount);

    s32 m_localX = 0;
    s32 m_localZ = 0;
};
