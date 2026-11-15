#include "pch.hpp"
#include "BankLogger.hpp"

#include "../Application/Events/ApplicationEventPublisher.hpp"

#include "../Game/State/GameStateQueries.hpp"
#include "../Utils/StringUtils.hpp"
#include "FleetLogJson.hpp"
#include "Type/FleetItem_s.hpp"
#include "Type/FleetItemRecord_s.hpp"

#include "Type/FleetBankLog_s.hpp"

#include <nlohmann/json.hpp>

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
    const auto open = GameStateQueries::IsBankOpen(m_cache, state);
    if (open && (!m_wasOpen || m_pending) && (!m_retryAt || now >= *m_retryAt))
    {
        Log(now, state);
    }

    if (!open)
    {
        m_pending = false;
        m_retryAt.reset();
    }

    m_wasOpen = open;
}

bool BankLogger::Log(Clock::time_point now, const GameState_s& state)
{
    const auto* const bank = state.FindInventory(m_cache.bankComponent);
    if (bank == nullptr)
    {
        // Open, but the items haven't arrived: the next open records the bank instead.
        return false;
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

    auto record = FleetItemRecord_s{
        .time = std::format("{:%Y-%m-%dT%H:%M:%SZ}", std::chrono::floor<std::chrono::seconds>(std::chrono::system_clock::now())),
        .account = m_accountName};
    auto summary = std::vector<std::string>{};
    for (const auto& [id, qty] : quantities)
    {
        const auto name = m_cache.FindObjName(id);
        record.items.push_back({.id = id, .name = std::string{name}, .qty = qty});
        summary.push_back(std::format("{} x{}", name.empty() ? std::format("#{}", id) : std::string{name}, qty));
    }

    try
    {
        const auto payload = nlohmann::ordered_json(record).dump(-1, ' ', false, nlohmann::json::error_handler_t::replace);
        m_database->Append(FleetStream_e::Bank, m_accountName, record.time, payload);
        m_pending = false;
        m_retryAt.reset();

        if (m_events)
        {
            m_events->Publish(m_accountName, FleetBankLog_s{payload});
        }

        if (m_writeFailed)
        {
            m_writeFailed = false;
            m_logger->Info("Writing the bank to {} again", m_database->GetPath().string());
        }
    }
    catch (const std::exception& e)
    {
        // A convenience, like the experience log: never take the account down over it.
        if (!m_writeFailed)
        {
            m_writeFailed = true;
            m_logger->Warning("The bank wasn't saved to {}; it will retry: {}", m_database->GetPath().string(), e.what());
        }

        m_pending = true;
        m_retryAt = now + 1s;

        return false;
    }

    m_logger->Info("Bank ({}): {}", summary.empty() ? "empty" : "open", summary.empty() ? "empty" : StringUtils::Join(summary, ", "));
    return true;
}
