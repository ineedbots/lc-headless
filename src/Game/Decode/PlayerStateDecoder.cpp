#include "pch.hpp"
#include "PlayerStateDecoder.hpp"

#include "../../Config/Revision_e.hpp"
#include "../../Console/Logger.hpp"
#include "../../Io/Packet.hpp"
#include "../../Utils/StringUtils.hpp"
#include "../Protocol/Protocol.hpp"
#include "../Protocol/ServerProt.hpp"
#include "../State/GameEvent_s.hpp"
#include "../State/GameState_s.hpp"
#include "../State/Stat_s.hpp"
#include "StateLog.hpp"

namespace
{
    constexpr auto MAX_BASE_LEVEL_INDEX = std::size_t{98};
    constexpr auto REMOVED_PLAYER_OP = "null"sv;

    constexpr auto HINT_NPC = u8{1};
    constexpr auto HINT_FIRST_TILE = u8{2};
    constexpr auto HINT_LAST_TILE = u8{6};
    constexpr auto HINT_PLAYER = u8{10};

    const auto LEVEL_XP = []
    {
        constexpr auto MAX_LEVEL = 99;
        auto table = std::array<s32, MAX_LEVEL>{};
        auto total = 0.0;
        for (auto i = 0; i < MAX_LEVEL; ++i)
        {
            const auto level = i + 1;
            total += static_cast<s32>(level + std::pow(2.0, level / 7.0) * 300.0);
            table[static_cast<std::size_t>(i)] = static_cast<s32>(total / 4);
        }

        return table;
    }();

    u8 GetBaseLevel(s32 xp)
    {
        auto level = 1;
        for (auto i = std::size_t{0}; i < MAX_BASE_LEVEL_INDEX; ++i)
        {
            if (xp >= LEVEL_XP[i])
            {
                level = static_cast<s32>(i) + 2;
            }
        }

        return static_cast<u8>(level);
    }

    void SetVarp(GameState_s& state, u16 varp, s32 value)
    {
        const auto previous = state.GetVarp(varp);
        state.varps.insert_or_assign(varp, value);
        StateLog::AddEvent(state, VarpChanged_s{.varp = varp, .previous = previous, .value = value});
    }

    void DecodeStat(Packet& packet, GameState_s& state, Logger& logger)
    {
        const auto stat = packet.G1();
        const auto xp = packet.G4();
        const auto level = packet.G1();
        if (stat >= state.stats.size())
        {
            logger.Warning("UPDATE_STAT for stat {}, past the last of {}", stat, state.stats.size());
            return;
        }

        const auto previous = state.stats[stat];
        state.stats[stat] = Stat_s{.xp = xp, .level = level, .baseLevel = GetBaseLevel(xp)};
        StateLog::AddEvent(state, StatChanged_s{.stat = stat, .previous = previous, .current = state.stats[stat]});
    }

    void DecodeHintArrow(Packet& packet, GameState_s& state)
    {
        const auto type = packet.G1();
        if (type == HINT_NPC || type == HINT_PLAYER)
        {
            const auto kind = type == HINT_NPC ? HintArrowKind_e::Npc : HintArrowKind_e::Player;
            state.hintArrow = HintArrow_s{.kind = kind, .index = packet.G2()};
        }
        else if (type >= HINT_FIRST_TILE && type <= HINT_LAST_TILE)
        {
            auto arrow = HintArrow_s{.kind = HintArrowKind_e::Tile, .position = type};
            arrow.tile.x = packet.G2();
            arrow.tile.z = packet.G2();
            arrow.tile.level = state.localPlayer.tile.level;
            arrow.height = packet.G1();
            state.hintArrow = arrow;
        }
        else
        {
            state.hintArrow.reset();
        }

        // Every type pads its fields to the same fixed size.
        packet.SetPos(packet.GetLength());
    }

    void DecodeSetPlayerOp(Packet& packet, GameState_s& state)
    {
        const auto op = packet.G1();
        const auto priority = packet.G1();
        auto text = packet.GJStr();
        if (op < 1 || op > GameState_s::PLAYER_OP_COUNT)
        {
            return;
        }

        auto& slot = state.playerOps[op - 1];
        if (StringUtils::EqualsIgnoringCase(text, REMOVED_PLAYER_OP))
        {
            slot.reset();
            return;
        }

        slot = PlayerOp_s{.text = std::move(text), .deprioritised = priority == 0};
    }

    void DecodeLastLogin(Packet& packet, GameState_s& state, const Protocol& protocol)
    {
        auto lastLogin = LastLogin_s{};
        lastLogin.lastIp = std::bit_cast<u32>(packet.G4());
        lastLogin.daysSinceLogin = packet.G2();
        lastLogin.daysSinceRecoveryChange = packet.G1();
        lastLogin.unreadMessages = packet.G2();

        if (protocol.GetRevision() >= Revision_e::Rev289)
        {
            lastLogin.warnMembers = packet.G1() == 1;
        }

        state.lastLogin = lastLogin;
    }
}

void PlayerStateDecoder::Decode(ServerProt_e prot, Packet& packet, GameState_s& state, const Protocol& protocol, Logger& logger)
{
    switch (prot)
    {
    case ServerProt_e::VarpSmall:
    {
        const auto varp = packet.G2();
        SetVarp(state, varp, packet.G1B());
        return;
    }
    case ServerProt_e::VarpLarge:
    {
        const auto varp = packet.G2();
        SetVarp(state, varp, packet.G4());
        return;
    }

    case ServerProt_e::UpdateStat:
        DecodeStat(packet, state, logger);
        return;
    case ServerProt_e::UpdateRunEnergy:
        state.runEnergy = packet.G1();
        return;
    case ServerProt_e::UpdateRunWeight:
        state.runWeight = packet.G2B();
        return;
    case ServerProt_e::UpdatePid:
        state.pid = packet.G2();
        state.localPlayer.index = state.pid;

        if (protocol.GetRevision() >= Revision_e::Rev289)
        {
            state.members = packet.G1() == 1;
        }

        return;
    case ServerProt_e::UpdateRebootTimer:
        state.rebootTimer = RebootTimer_s{.ticks = packet.G2(), .tick = state.tick};
        StateLog::AddEvent(state, RebootStarted_s{.ticks = state.rebootTimer->ticks});
        return;
    case ServerProt_e::LastLoginInfo:
        DecodeLastLogin(packet, state, protocol);
        return;
    case ServerProt_e::HintArrow:
        DecodeHintArrow(packet, state);
        return;
    case ServerProt_e::SetPlayerOp:
        DecodeSetPlayerOp(packet, state);
        return;
    case ServerProt_e::SetMultiway:
        state.multiway = packet.G1() == 1;
        return;
    case ServerProt_e::MinimapToggle:
        state.minimapState = packet.G1();
        return;
    case ServerProt_e::UnsetMapFlag:
        state.walkDestination.reset();
        return;

    default:
        assert(false && "Not a player state packet");
        return;
    }
}
