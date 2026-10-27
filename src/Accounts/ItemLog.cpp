#include "pch.hpp"
#include "ItemLog.hpp"

#include "../Game/State/GameStateQueries.hpp"

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

ItemLog::ItemLog(const GameCache_s& cache, std::shared_ptr<Logger> logger, std::string accountName, std::filesystem::path directory, Kind_e kind, std::chrono::seconds interval)
    : m_cache{cache}
    , m_logger{std::move(logger)}
    , m_accountName{std::move(accountName)}
    , m_path{std::move(directory) / (m_accountName + std::string{EXTENSION})}
    , m_kind{kind}
    , m_interval{interval}
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

    auto items = std::string{};
    for (std::size_t i = 0; i < contents.items.size(); ++i)
    {
        const auto& item = contents.items[i];
        std::format_to(std::back_inserter(items), "{}{{\"id\":{},\"name\":\"{}\",\"qty\":{}}}",
                       i == 0 ? "" : ",", item.id, Escape(m_cache.FindObjName(item.id)), item.qty);
    }

    const auto time = std::format("{:%Y-%m-%dT%H:%M:%SZ}", std::chrono::floor<std::chrono::seconds>(std::chrono::system_clock::now()));
    const auto free = contents.slots - std::min(contents.slots, contents.used);

    auto line = std::string{};
    if (m_kind == Kind_e::Backpack)
    {
        // bankOpen says which backpack these are: while a bank is open the game swaps in its own.
        line = std::format("{{\"time\":\"{}\",\"account\":\"{}\",\"bankOpen\":{},\"used\":{},\"free\":{},\"items\":[{}]}}\n",
                           time, Escape(m_accountName), contents.bankOpen, contents.used, free, items);
    }
    else
    {
        line = std::format("{{\"time\":\"{}\",\"account\":\"{}\",\"used\":{},\"items\":[{}]}}\n",
                           time, Escape(m_accountName), contents.used, items);
    }

    try
    {
        Append(m_path, line);

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
