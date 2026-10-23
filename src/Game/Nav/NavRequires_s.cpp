#include "pch.hpp"
#include "NavRequires_s.hpp"

#include "../../Utils/StringUtils.hpp"
#include "NavState_s.hpp"

namespace
{
    s32 QuestRank(std::string_view status)
    {
        if (status == "complete")
        {
            return 2;
        }

        return status == "started" ? 1 : 0;
    }

    s32 Count(const std::unordered_map<std::string, s32>& counts, std::string_view name)
    {
        const auto found = counts.find(StringUtils::ToLower(name));
        return found == counts.end() ? 0 : found->second;
    }
}

bool NavRequires_s::IsGated() const
{
    return members || freeSlots || !skills.empty() || !items.empty() || !worn.empty() || currency || !questWaivesItems.empty() || !quests.empty() || forbidEntranaRestricted || slashTool || !essenceExitReturn.empty();
}

std::optional<std::string> NavRequires_s::Check(const NavState_s& state) const
{
    if (members && !state.members)
    {
        return "members-only";
    }

    if (freeSlots && state.freeSlots < *freeSlots)
    {
        return std::format("need {} free inventory slots (have {})", *freeSlots, state.freeSlots);
    }

    for (const auto& skill : skills)
    {
        const auto have = Count(state.skills, skill.name);
        if (have < skill.count)
        {
            return std::format("need {} {} (have {})", skill.name, skill.count, have);
        }
    }

    const auto waived = !questWaivesItems.empty() && [&]
    {
        const auto found = state.quests.find(StringUtils::ToLower(questWaivesItems));
        return found != state.quests.end() && found->second == "complete";
    }();

    if (currency && !waived && Count(state.items, currency->name) < currency->count)
    {
        return std::format("need {} {} (have {})", currency->count, currency->name, Count(state.items, currency->name));
    }

    for (const auto& item : items)
    {
        if (!waived && Count(state.items, item.name) < item.count)
        {
            return std::format("need {} {} (have {})", item.count, item.name, Count(state.items, item.name));
        }
    }

    for (const auto& item : worn)
    {
        if (Count(state.worn, item.name) < item.count)
        {
            return std::format("need to wear {}", item.name);
        }
    }

    if (forbidEntranaRestricted && state.entranaRestrictedGear)
    {
        return "remove weapons and armour before Entrana";
    }

    if (slashTool && state.canSlashWeb == false)
    {
        return "need a knife or a bladed weapon to slash webs";
    }

    // Why: an unknown return passes, as rs2b0t's does, so a cheat-tele into the mine can still leave it.
    if (!essenceExitReturn.empty() && state.essenceExitReturn && *state.essenceExitReturn != essenceExitReturn)
    {
        return std::format("essence exit returns to {}, not {}", *state.essenceExitReturn, essenceExitReturn);
    }

    for (const auto& quest : quests)
    {
        const auto found = state.quests.find(StringUtils::ToLower(quest.quest));
        const auto status = found == state.quests.end() ? std::string{"unknown"} : found->second;
        if (status == "unknown" && !quest.maxStatus.empty())
        {
            return std::format("need to know where {} stands", quest.quest);
        }

        if (!quest.maxStatus.empty() && QuestRank(status) > QuestRank(quest.maxStatus))
        {
            return std::format("need {} at most {} (it's {})", quest.quest, quest.maxStatus, status);
        }

        if (!quest.minStatus.empty() && QuestRank(status) < QuestRank(quest.minStatus))
        {
            return std::format("need {} {} (it's {})", quest.quest, quest.minStatus, status);
        }
    }

    return std::nullopt;
}
