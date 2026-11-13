#include "pch.hpp"
#include "ItemLog.hpp"

#include "../Application/Events/ApplicationEventPublisher.hpp"

#include "../Game/State/GameStateQueries.hpp"

#include "../Utils/FileUtils.hpp"
#include "FleetLogJson.hpp"
#include "Type/FleetItem_s.hpp"
#include "Type/FleetItemRecord_s.hpp"

#include "Type/FleetInventoryLog_s.hpp"
#include "Type/FleetEquipmentLog_s.hpp"

#include <nlohmann/json.hpp>

namespace
{
    constexpr auto EXTENSION = ".jsonl"sv;
}

ItemLog::ItemLog(const GameCache_s& cache, std::shared_ptr<Logger> logger, std::string accountName, std::filesystem::path directory, Kind_e kind, std::chrono::seconds interval, std::shared_ptr<ApplicationEventPublisher> events)
    : m_cache{cache}
    , m_logger{std::move(logger)}
    , m_accountName{std::move(accountName)}
    , m_path{std::move(directory) / (m_accountName + std::string{EXTENSION})}
    , m_kind{kind}
    , m_interval{interval}
    , m_events{std::move(events)}
{
}

ItemLog::Contents_s ItemLog::Read(const GameState_s& state) const
{
    auto contents = Contents_s{};

    if (m_kind == Kind_e::Backpack)
    {
        contents.bankOpen = GameStateQueries::IsBankOpen(m_cache, state);
        // The bank swaps in its own backpack while open, and that is the one the player sees.
        contents.com = contents.bankOpen && m_cache.bankInventoryComponent != 0 ? m_cache.bankInventoryComponent : m_cache.inventoryComponent;
    }
    else
    {
        contents.com = m_cache.equipmentComponent;
    }

    const auto* const inventory = state.FindInventory(contents.com);
    if (inventory == nullptr)
    {
        return contents;
    }

    // Only the backpack has a meaningful "free", and the cache knows its size. An inventory packet can hold
    // just the filled slots, so counting those would report a full backpack whenever anything is carried.
    // The equipment interface's grid has decorative cells that can never hold anything, so it records only
    // what is worn.
    if (m_kind == Kind_e::Backpack)
    {
        contents.slots = static_cast<std::size_t>(m_cache.inventorySize);
    }
    else
    {
        contents.slots = inventory->slots.size();
    }

    // Grouped here, before writing: a backpack of 15 cakes is one entry with 15, not 15 entries.
    auto quantities = std::map<s32, s32>{};
    for (const auto& slot : inventory->slots)
    {
        if (slot.id < 0 || slot.count <= 0)
        {
            continue;
        }

        ++contents.used;
        quantities[slot.id] += slot.count;
    }

    for (const auto& [id, qty] : quantities)
    {
        contents.items.push_back({.id = id, .qty = qty});
    }

    return contents;
}

void ItemLog::Step(Clock::time_point now, const GameState_s& state)
{
    const auto contents = Read(state);
    // Before the container's contents have arrived there is nothing to say.
    if (contents.com == 0 || !state.FindInventory(contents.com))
    {
        return;
    }

    if (!m_lastSample)
    {
        WriteSample(now, contents);
        m_lastSample = contents;
        return;
    }

    if (contents == *m_lastSample && !m_pending)
    {
        return;
    }

    // A change the interval holds back waits for it, then is written once.
    const auto due = m_interval <= std::chrono::seconds::zero() || !m_nextSample || now >= *m_nextSample;
    if (!due)
    {
        m_pending = contents;
        return;
    }

    WriteSample(now, contents);
    m_lastSample = contents;
    m_pending.reset();
}

void ItemLog::WriteSample(Clock::time_point now, const Contents_s& contents)
{
    if (m_interval > std::chrono::seconds::zero())
    {
        m_nextSample = now + m_interval;
    }

    auto record = FleetItemRecord_s{
        .time = std::format("{:%Y-%m-%dT%H:%M:%SZ}", std::chrono::floor<std::chrono::seconds>(std::chrono::system_clock::now())),
        .account = m_accountName,
        .used = contents.used};
    if (m_kind == Kind_e::Backpack)
    {
        // bankOpen says which backpack these are: while a bank is open the game swaps in its own.
        record.bankOpen = contents.bankOpen;
        record.free = contents.slots - std::min(contents.slots, contents.used);
    }

    for (const auto& item : contents.items)
    {
        record.items.push_back({.id = item.id, .name = std::string{m_cache.FindObjName(item.id)}, .qty = item.qty});
    }

    try
    {
        const auto line = nlohmann::ordered_json(record).dump(-1, ' ', false, nlohmann::json::error_handler_t::replace) + '\n';
        FileUtils::AppendText(m_path, line);

        if (m_events)
        {
            if (m_kind == Kind_e::Backpack)
            {
                m_events->Publish(m_accountName, FleetInventoryLog_s{line});
            }
            else
            {
                m_events->Publish(m_accountName, FleetEquipmentLog_s{line});
            }
        }

        if (m_writeFailed)
        {
            m_writeFailed = false;
            m_logger->Info("Writing {} to {} again", m_kind == Kind_e::Backpack ? "the backpack" : "the worn equipment", m_path.string());
        }
    }
    catch (const std::exception& e)
    {
        // A convenience, like the other logs: never take the account down over it.
        if (!m_writeFailed)
        {
            m_writeFailed = true;
            m_logger->Warning("{} wasn't saved: {}", m_kind == Kind_e::Backpack ? "The backpack" : "The worn equipment", e.what());
        }
    }
}
