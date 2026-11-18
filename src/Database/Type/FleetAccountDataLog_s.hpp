#pragma once

#include <nlohmann/json.hpp>

struct FleetLogTile_s
{
    s32 x = 0;
    s32 z = 0;
    s32 level = 0;

    [[nodiscard]] bool operator==(const FleetLogTile_s&) const = default;
};

NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_ONLY_SERIALIZE(FleetLogTile_s, x, z, level)

struct FleetLogStat_s
{
    s32 current = 0;
    s32 base = 0;

    [[nodiscard]] bool operator==(const FleetLogStat_s&) const = default;
};

NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_ONLY_SERIALIZE(FleetLogStat_s, current, base)

struct FleetLogSpecialAttack_s
{
    s32 energy = 0;
    bool armed = false;

    [[nodiscard]] bool operator==(const FleetLogSpecialAttack_s&) const = default;
};

NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_ONLY_SERIALIZE(FleetLogSpecialAttack_s, energy, armed)

struct FleetLogTarget_s
{
    std::string kind;
    std::optional<s32> index;
    std::optional<FleetLogTile_s> tile;

    [[nodiscard]] bool operator==(const FleetLogTarget_s&) const = default;
};

template <typename TJson>
void to_json(TJson& value, const FleetLogTarget_s& target)
{
    value = TJson{{"kind", target.kind}};
    if (target.index)
    {
        value["index"] = *target.index;
    }

    if (target.tile)
    {
        value["tile"] = *target.tile;
    }
}

template <typename TJson, typename TValue>
TJson FleetOptionalJson(const std::optional<TValue>& value)
{
    if (!value)
    {
        return TJson(nullptr);
    }

    return TJson(*value);
}

struct FleetAccountDataLog_s
{
    std::string time;
    std::string account;
    std::string state;
    bool settled = false;
    std::optional<s32> pid;
    std::optional<FleetLogTile_s> tile;
    std::optional<FleetLogTile_s> destination;
    std::optional<FleetLogTarget_s> target;
    std::optional<FleetLogStat_s> hp;
    std::optional<s32> energy;
    std::optional<FleetLogStat_s> prayer;
    std::optional<FleetLogSpecialAttack_s> specialAttack;
    std::optional<bool> running;
    std::optional<bool> moving;
    std::optional<bool> inCombat;
    std::optional<s32> weight;
    u64 tick = 0;

    [[nodiscard]] bool operator==(const FleetAccountDataLog_s& other) const
    {
        return state == other.state && settled == other.settled && pid == other.pid && tile == other.tile && destination == other.destination && target == other.target && hp == other.hp && energy == other.energy && prayer == other.prayer && specialAttack == other.specialAttack && running == other.running && moving == other.moving && inCombat == other.inCombat && weight == other.weight;
    }
};

template <typename TJson>
void to_json(TJson& value, const FleetAccountDataLog_s& record)
{
    value = TJson{
        {"time", record.time},
        {"account", record.account},
        {"state", record.state},
        {"settled", record.settled},
        {"pid", FleetOptionalJson<TJson>(record.pid)},
        {"tile", FleetOptionalJson<TJson>(record.tile)},
        {"destination", FleetOptionalJson<TJson>(record.destination)},
        {"target", FleetOptionalJson<TJson>(record.target)},
        {"hp", FleetOptionalJson<TJson>(record.hp)},
        {"energy", FleetOptionalJson<TJson>(record.energy)},
        {"prayer", FleetOptionalJson<TJson>(record.prayer)},
        {"specialAttack", FleetOptionalJson<TJson>(record.specialAttack)},
        {"running", FleetOptionalJson<TJson>(record.running)},
        {"moving", FleetOptionalJson<TJson>(record.moving)},
        {"inCombat", FleetOptionalJson<TJson>(record.inCombat)},
        {"weight", FleetOptionalJson<TJson>(record.weight)},
        {"tick", record.tick}};
}
