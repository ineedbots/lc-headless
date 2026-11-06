#include "pch.hpp"
#include "BankLogger.hpp"

#include "../Game/State/GameStateQueries.hpp"
#include "../Utils/StringUtils.hpp"

#include <fstream>
#include <map>

namespace
{
    constexpr auto EXTENSION = ".jsonl"sv;

    std::string Escape(std::string_view text)
    {
        auto out = std::string{};
        out.reserve(text.size() + 2);
        for (const auto character : text)
        {
            switch (character)
            {
            case '"':
                out += "\\\"";
                break;
            case '\\':
                out += "\\\\";
                break;
            case '\n':
                out += "\\n";
                break;
            case '\t':
                out += "\\t";
                break;
            default:
                if (static_cast<unsigned char>(character) < 0x20)
                {
                    std::format_to(std::back_inserter(out), "\\u{:04x}", static_cast<unsigned>(character));
                }
                else
                {
                    out += character;
                }
                break;
            }
        }

        return out;
    }

    void Append(const std::filesystem::path& path, std::string_view text)
    {
        auto error = std::error_code{};
        if (!path.parent_path().empty())
        {
            std::filesystem::create_directories(path.parent_path(), error);
        }

        auto file = std::ofstream{path, std::ios::binary | std::ios::app};
        file << text;
        file.flush();
        if (!file)
        {
            throw std::runtime_error{std::format("can't write {}", path.string())};
        }
    }
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

    auto items = std::string{};
    auto summary = std::vector<std::string>{};
    for (const auto& [id, qty] : quantities)
    {
        const auto name = m_cache.FindObjName(id);
        if (!items.empty())
        {
            items += ",";
        }

        std::format_to(std::back_inserter(items), "{{\"id\":{},\"name\":\"{}\",\"qty\":{}}}", id, Escape(name), qty);
        summary.push_back(std::format("{} x{}", name.empty() ? std::format("#{}", id) : std::string{name}, qty));
    }

    const auto time = std::format("{:%Y-%m-%dT%H:%M:%SZ}", std::chrono::floor<std::chrono::seconds>(std::chrono::system_clock::now()));
    const auto record = std::format("{{\"time\":\"{}\",\"account\":\"{}\",\"items\":[{}]}}\n", time, Escape(m_accountName), items);

    try
    {
        Append(m_directory / (m_accountName + std::string{EXTENSION}), record);

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
