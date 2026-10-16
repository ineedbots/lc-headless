#include "pch.hpp"
#include "PlayerQuery.hpp"

#include "../../Cache/GameCache_s.hpp"
#include "../State/EntityStatus.hpp"
#include "../State/GameState_s.hpp"
#include "../State/Stat_s.hpp"

PlayerQuery::PlayerQuery(const GameState_s& state, const GameCache_s& cache)
    : m_state{state}
    , m_cache{cache}
{
}

bool PlayerQuery::IsMoving() const
{
    return m_state.walkDestination.has_value() || EntityStatus::IsMoving(m_state.localPlayer, m_state.tick);
}

bool PlayerQuery::InCombat() const
{
    return EntityStatus::InCombat(m_state.localPlayer, m_state.tick);
}

bool PlayerQuery::IsRunning() const
{
    return m_state.GetVarp(m_cache.runVarp) == 1;
}

const Stat_s& PlayerQuery::GetStat(s32 stat) const
{
    if (stat < 0 || static_cast<std::size_t>(stat) >= m_state.stats.size())
    {
        throw std::invalid_argument{std::format("stat {} is not 0 to {}", stat, m_state.stats.size() - 1)};
    }

    return m_state.stats[static_cast<std::size_t>(stat)];
}

bool PlayerQuery::IsInterfaceOpen(s32 id) const
{
    const auto& interfaces = m_state.interfaces;
    return id >= 0 && (interfaces.mainModal == id || interfaces.sideModal == id || interfaces.chatModal == id);
}

std::optional<std::string> PlayerQuery::GetComponentText(u16 com) const
{
    const auto found = m_state.interfaces.components.find(com);
    if (found == m_state.interfaces.components.end())
    {
        return std::nullopt;
    }

    return found->second.text;
}
