#include "pch.hpp"
#include "BankLogger.hpp"

#include "../Application/Events/ApplicationEventPublisher.hpp"

#include "../Game/State/GameStateQueries.hpp"
#include "../Utils/StringUtils.hpp"
#include "Type/FleetBankLog_s.hpp"

BankLogger::BankLogger(const GameCache_s& cache, std::shared_ptr<Logger> logger, std::string accountName, std::shared_ptr<FleetDatabase> database, std::shared_ptr<ApplicationEventPublisher> events)
    : m_cache{cache}
    , m_logger{std::move(logger)}
    , m_accountName{std::move(accountName)}
    , m_database{std::move(database)}
    , m_events{std::move(events)}
{
}

void BankLogger::Step(Clock::time_point now, const GameState_s& state)
{
    Poll(now);

    const auto open = GameStateQueries::IsBankOpen(m_cache, state);
    if (open && !m_wasOpen)
    {
        try
        {
            if (auto snapshot = Read(state))
            {
                if (m_pendingSnapshots.size() >= FleetDatabase::MAX_PENDING_WRITES)
                {
                    if (!m_writeFailed)
                    {
                        m_writeFailed = true;
                        m_logger->Warning("The bank's pending open-snapshot queue is full; this snapshot wasn't saved");
                    }
                }
                else
                {
                    m_pendingSnapshots.push_back(std::move(*snapshot));
                }
            }
        }
        catch (const std::exception& e)
        {
            if (!m_writeFailed)
            {
                m_writeFailed = true;
                m_logger->Warning("The bank wasn't saved to {}; it will retry: {}", m_database->GetPath().string(), e.what());
            }

            m_retryAt = now + 1s;
        }
    }

    if (!m_write && !m_pendingSnapshots.empty() && (!m_retryAt || now >= *m_retryAt))
    {
        auto snapshot = std::move(m_pendingSnapshots.front());
        m_pendingSnapshots.pop_front();
        if (!WriteSample(now, snapshot))
        {
            m_pendingSnapshots.push_front(std::move(snapshot));
        }
    }

    if (!open && m_pendingSnapshots.empty() && !m_write)
    {
        m_retryAt.reset();
    }

    m_wasOpen = open;
}

void BankLogger::Flush()
{
    if (m_write)
    {
        m_write->completion.wait();
        Poll(Clock::now());
    }

    const auto attempts = m_pendingSnapshots.size();
    for (auto i = std::size_t{}; i < attempts && !m_pendingSnapshots.empty(); ++i)
    {
        auto snapshot = std::move(m_pendingSnapshots.front());
        m_pendingSnapshots.pop_front();
        if (!WriteSample(Clock::now(), snapshot))
        {
            m_database->Flush();
            if (!WriteSample(Clock::now(), snapshot))
            {
                m_pendingSnapshots.push_front(std::move(snapshot));
                return;
            }
        }

        if (m_write)
        {
            m_write->completion.wait();
            Poll(Clock::now());
        }

        if (m_writeFailed)
        {
            return;
        }
    }
}

std::optional<BankLogger::Snapshot_s> BankLogger::Read(const GameState_s& state) const
{
    const auto* const bank = state.FindInventory(m_cache.bankComponent);
    if (bank == nullptr)
    {
        // Open, but the items haven't arrived: the next open records the bank instead.
        return std::nullopt;
    }

    // Grouped by id, in id order, so the same bank always reads the same way.
    auto quantities = std::map<s32, s32>{};
    for (const auto& slot : bank->slots)
    {
        if (slot.id < 0 || slot.count <= 0)
        {
            continue;
        }

        quantities[slot.id] += slot.count;
    }

    auto record = FleetBankLog_s{
        .time = std::format("{:%Y-%m-%dT%H:%M:%SZ}", std::chrono::floor<std::chrono::seconds>(std::chrono::system_clock::now())),
        .account = m_accountName};
    auto summary = std::vector<std::string>{};
    for (const auto& [id, qty] : quantities)
    {
        const auto name = m_cache.FindObjName(id);
        record.items.push_back({.id = id, .name = std::string{name}, .qty = qty});
        summary.push_back(std::format("{} x{}", name.empty() ? std::format("#{}", id) : std::string{name}, qty));
    }

    return Snapshot_s{
        .record = std::move(record),
        .summary = summary.empty() ? "empty" : StringUtils::Join(summary, ", ")};
}

bool BankLogger::WriteSample(Clock::time_point now, Snapshot_s snapshot)
{
    try
    {
        auto completion = m_database->Enqueue(snapshot.record);
        if (!completion)
        {
            throw std::runtime_error{"fleet database write queue is full"};
        }

        m_write.emplace(PendingWrite_s{std::move(snapshot), std::move(*completion)});
        m_retryAt.reset();
        Poll(now);
        return true;
    }
    catch (const std::exception& e)
    {
        if (!m_writeFailed)
        {
            m_writeFailed = true;
            m_logger->Warning("The bank wasn't saved to {}; it will retry: {}", m_database->GetPath().string(), e.what());
        }

        m_retryAt = now + 1s;
        return false;
    }
}

void BankLogger::Poll(Clock::time_point now)
{
    if (!m_write || m_write->completion.wait_for(0ms) != std::future_status::ready)
    {
        return;
    }

    auto write = std::move(*m_write);
    m_write.reset();

    try
    {
        write.completion.get();

        if (m_events)
        {
            m_events->Publish(m_accountName, write.snapshot.record);
        }

        if (m_writeFailed)
        {
            m_writeFailed = false;
            m_logger->Info("Writing the bank to {} again", m_database->GetPath().string());
        }
    }
    catch (const std::exception& e)
    {
        m_pendingSnapshots.push_front(std::move(write.snapshot));

        if (!m_writeFailed)
        {
            m_writeFailed = true;
            m_logger->Warning("The bank wasn't saved to {}; it will retry: {}", m_database->GetPath().string(), e.what());
        }

        m_retryAt = now + 1s;
        return;
    }

    m_logger->Info("Bank ({}): {}", write.snapshot.summary == "empty" ? "empty" : "open", write.snapshot.summary);
}
