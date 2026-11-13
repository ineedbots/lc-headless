#include "pch.hpp"
#include "BankLogger.hpp"

#include "../Game/State/GameStateQueries.hpp"
#include "../Utils/FileUtils.hpp"
#include "../Utils/StringUtils.hpp"
#include "FleetLogJson.hpp"
#include "Type/FleetItem_s.hpp"
#include "Type/FleetItemRecord_s.hpp"

#include <nlohmann/json.hpp>

namespace
{
    constexpr auto EXTENSION = ".jsonl"sv;
}

BankLogger::BankLogger(const GameCache_s& cache, std::shared_ptr<Logger> logger, std::string accountName, std::filesystem::path directory)
    : m_cache{cache}
    , m_logger{std::move(logger)}
    , m_accountName{std::move(accountName)}
    , m_directory{std::move(directory)}
{
}

void BankLogger::Step(const GameState_s& state)
{
    const auto open = GameStateQueries::IsBankOpen(m_cache, state);
    if (open && !m_wasOpen)
    {
        Log(state);
    }

    m_wasOpen = open;
}

void BankLogger::Log(const GameState_s& state)
{
    const auto* const bank = state.FindInventory(m_cache.bankComponent);
    if (bank == nullptr)
    {
        // Open, but the items haven't arrived: the next open records the bank instead.
        return;
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
        const auto line = nlohmann::ordered_json(record).dump(-1, ' ', false, nlohmann::json::error_handler_t::replace) + '\n';
        FileUtils::AppendText(m_directory / (m_accountName + std::string{EXTENSION}), line);

        if (m_writeFailed)
        {
            m_writeFailed = false;
            m_logger->Info("Writing the bank to {} again", m_directory.string());
        }
    }
    catch (const std::exception& e)
    {
        // A convenience, like the experience log: never take the account down over it.
        if (!m_writeFailed)
        {
            m_writeFailed = true;
            m_logger->Warning("The bank wasn't saved: {}", e.what());
        }
    }

    m_logger->Info("Bank ({}): {}", summary.empty() ? "empty" : "open", summary.empty() ? "empty" : StringUtils::Join(summary, ", "));
}
