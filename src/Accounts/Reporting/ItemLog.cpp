#include "pch.hpp"
#include "ItemLog.hpp"

#include "ReportWriteCompletion.hpp"

#include "Websockets/Events/ApplicationEventPublisher.hpp"

#include "Game/State/GameStateQueries.hpp"

#include "Database/Type/FleetInventoryLog_s.hpp"
#include "Database/Type/FleetEquipmentLog_s.hpp"

ItemLog::ItemLog(const GameCache_s& cache, std::shared_ptr<Logger> logger, std::string accountName, std::shared_ptr<FleetDatabase> database, Kind_e kind, std::chrono::seconds interval, std::shared_ptr<ApplicationEventPublisher> events)
    : m_cache{cache}
    , m_logger{std::move(logger)}
    , m_accountName{std::move(accountName)}
    , m_database{std::move(database)}
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
    Poll(now);

    const auto contents = Read(state);
    // Before the container's contents have arrived there is nothing to say.
    if (contents.com == 0 || !state.FindInventory(contents.com))
    {
        return;
    }

    if (m_write)
    {
        if (contents == m_write->contents)
        {
            m_pending.reset();
        }
        else
        {
            m_pending = contents;
        }

        return;
    }

    if (m_retryAt && now < *m_retryAt)
    {
        if (m_lastSample && contents == *m_lastSample)
        {
            m_pending.reset();
        }
        else
        {
            m_pending = contents;
        }

        return;
    }

    if (!m_lastSample)
    {
        if (!WriteSample(now, contents))
        {
            m_pending = contents;
        }

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

    if (WriteSample(now, contents))
    {
        m_pending.reset();
    }
    else
    {
        m_pending = contents;
    }
}

void ItemLog::Flush()
{
    if (!m_write)
    {
        return;
    }

    m_write->completion.wait();
    Poll(Clock::now());
}

bool ItemLog::WriteSample(Clock::time_point now, const Contents_s& contents)
{
    try
    {
        const auto time = std::format("{:%Y-%m-%dT%H:%M:%SZ}", std::chrono::floor<std::chrono::seconds>(std::chrono::system_clock::now()));

        if (m_kind == Kind_e::Backpack)
        {
            auto record = FleetInventoryLog_s{
                .time = time,
                .account = m_accountName,
                .bankOpen = contents.bankOpen,
                .used = contents.used,
                .free = contents.slots - std::min(contents.slots, contents.used)};
            for (const auto& item : contents.items)
            {
                record.items.push_back({.id = item.id, .name = std::string{m_cache.FindObjName(item.id)}, .qty = item.qty});
            }

            auto completion = m_database->Enqueue(record);
            if (!completion)
            {
                throw std::runtime_error{"fleet database write queue is full"};
            }

            m_write.emplace(PendingWrite_s{
                .record = std::move(record),
                .completion = std::move(*completion),
                .contents = contents,
                .sampledAt = now});
            Poll(now);
        }
        else
        {
            auto record = FleetEquipmentLog_s{
                .time = time,
                .account = m_accountName,
                .used = contents.used};
            for (const auto& item : contents.items)
            {
                record.items.push_back({.id = item.id, .name = std::string{m_cache.FindObjName(item.id)}, .qty = item.qty});
            }

            auto completion = m_database->Enqueue(record);
            if (!completion)
            {
                throw std::runtime_error{"fleet database write queue is full"};
            }

            m_write.emplace(PendingWrite_s{
                .record = std::move(record),
                .completion = std::move(*completion),
                .contents = contents,
                .sampledAt = now});
            Poll(now);
        }

        return true;
    }
    catch (const std::exception& e)
    {
        // A convenience, like the other logs: never take the account down over it.
        if (!m_writeFailed)
        {
            m_writeFailed = true;
            m_logger->Warning("{} wasn't saved to {}; it will retry: {}", m_kind == Kind_e::Backpack ? "The backpack" : "The worn equipment", m_database->GetPath().string(), e.what());
        }

        m_retryAt = now + (m_interval > std::chrono::seconds::zero() ? m_interval : 1s);
        return false;
    }
}

void ItemLog::Poll(Clock::time_point now)
{
    ReportWriteCompletion::Poll(m_write, [this](auto& write)
    {
        m_lastSample = write.contents;
        m_retryAt.reset();

        if (m_interval > std::chrono::seconds::zero())
        {
            m_nextSample = write.sampledAt + m_interval;
        }

        std::visit([this](const auto& record)
        {
            ReportWriteCompletion::Publish(m_events, *m_logger, m_accountName, record);
        }, write.record);

        if (m_writeFailed)
        {
            m_writeFailed = false;
            m_logger->Info("Writing {} to {} again", m_kind == Kind_e::Backpack ? "the backpack" : "the worn equipment", m_database->GetPath().string());
        }
    }, [this, now](auto& write, const std::exception& e)
    {
        if (!m_writeFailed)
        {
            m_writeFailed = true;
            m_logger->Warning("{} wasn't saved to {}; it will retry: {}", m_kind == Kind_e::Backpack ? "The backpack" : "The worn equipment", m_database->GetPath().string(), e.what());
        }

        if (!m_pending)
        {
            m_pending = write.contents;
        }

        m_retryAt = now + (m_interval > std::chrono::seconds::zero() ? m_interval : 1s);
    });
}
