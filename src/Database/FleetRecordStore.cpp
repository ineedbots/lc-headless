#include "pch.hpp"
#include "FleetRecordStore.hpp"

#include "FleetDatabaseSchema.hpp"
#include "Type/FleetAccountDataLog_s.hpp"
#include "Type/FleetBankLog_s.hpp"
#include "Type/FleetEquipmentLog_s.hpp"
#include "Type/FleetExperienceLog_s.hpp"
#include "Type/FleetInventoryLog_s.hpp"
#include "Type/FleetItem_s.hpp"
#include "Type/FleetSkill_s.hpp"
#include "Type/FleetStream_e.hpp"
#include "Config/Type/Config_s.hpp"

#include <SQLiteCpp/SQLiteCpp.h>
#include <nlohmann/json.hpp>

#include <charconv>

namespace
{
    std::string_view StreamName(FleetStream_e stream)
    {
        switch (stream)
        {
        case FleetStream_e::AccountData:
            return "account-data";
        case FleetStream_e::Experience:
            return "experience";
        case FleetStream_e::Bank:
            return "bank";
        case FleetStream_e::Inventory:
            return "inventory";
        case FleetStream_e::Equipment:
            return "equipment";
        }

        throw std::invalid_argument{"unknown fleet stream"};
    }

    FleetStream_e StreamForRecord(const FleetAccountDataLog_s&)
    {
        return FleetStream_e::AccountData;
    }

    FleetStream_e StreamForRecord(const FleetExperienceLog_s&)
    {
        return FleetStream_e::Experience;
    }

    FleetStream_e StreamForRecord(const FleetBankLog_s&)
    {
        return FleetStream_e::Bank;
    }

    FleetStream_e StreamForRecord(const FleetInventoryLog_s&)
    {
        return FleetStream_e::Inventory;
    }

    FleetStream_e StreamForRecord(const FleetEquipmentLog_s&)
    {
        return FleetStream_e::Equipment;
    }

    std::string SanitizeUtf8(std::string_view text)
    {
        const auto encoded = nlohmann::json(std::string{text}).dump(-1, ' ', false, nlohmann::json::error_handler_t::replace);
        return nlohmann::json::parse(encoded).get<std::string>();
    }

    s64 StringId(
        SQLite::Database& database,
        std::unordered_map<std::string, s64>& ids,
        std::string_view table,
        std::string_view value)
    {
        auto name = std::string{value};
        const auto found = ids.find(name);
        if (found != ids.end())
        {
            return found->second;
        }

        const auto insertQuery = std::format("INSERT INTO {} (name) VALUES (?) ON CONFLICT (name) DO NOTHING", table);
        auto insertStatement = SQLite::Statement{database, insertQuery};
        insertStatement.bind(1, name);
        insertStatement.exec();

        const auto selectQuery = std::format("SELECT id FROM {} WHERE name = ?", table);
        auto selectStatement = SQLite::Statement{database, selectQuery};
        selectStatement.bind(1, name);
        if (!selectStatement.executeStep())
        {
            throw std::runtime_error{std::format("could not find value in {} after insert", table)};
        }

        const auto id = selectStatement.getColumn(0).getInt64();
        ids.emplace(std::move(name), id);
        return id;
    }

    s64 UnixTimestamp(std::string_view text)
    {
        if (text.size() != 20 || text[4] != '-' || text[7] != '-' || text[10] != 'T' || text[13] != ':' || text[16] != ':' || text[19] != 'Z')
        {
            throw std::invalid_argument{"fleet record time must use UTC format YYYY-MM-DDTHH:MM:SSZ"};
        }

        const auto parsePart = [text](std::size_t offset, std::size_t length)
        {
            for (const auto character : text.substr(offset, length))
            {
                if (character < '0' || character > '9')
                {
                    throw std::invalid_argument{"fleet record time contains a non-numeric date or time component"};
                }
            }

            auto value = int{};
            const auto first = text.data() + offset;
            const auto last = first + length;
            const auto [end, error] = std::from_chars(first, last, value);
            if (error != std::errc{} || end != last)
            {
                throw std::invalid_argument{"fleet record time contains a non-numeric date or time component"};
            }

            return value;
        };

        const auto date = std::chrono::year_month_day{
            std::chrono::year{parsePart(0, 4)},
            std::chrono::month{static_cast<unsigned int>(parsePart(5, 2))},
            std::chrono::day{static_cast<unsigned int>(parsePart(8, 2))}};
        const auto hours = parsePart(11, 2);
        const auto minutes = parsePart(14, 2);
        const auto seconds = parsePart(17, 2);
        if (!date.ok() || hours < 0 || hours > 23 || minutes < 0 || minutes > 59 || seconds < 0 || seconds > 59)
        {
            throw std::invalid_argument{"fleet record time contains an invalid date or time"};
        }

        const auto timestamp = std::chrono::sys_days{date} + std::chrono::hours{hours} + std::chrono::minutes{minutes} + std::chrono::seconds{seconds};
        return std::chrono::duration_cast<std::chrono::seconds>(timestamp.time_since_epoch()).count();
    }

    s64 InsertRecord(
        SQLite::Database& database,
        std::unordered_map<std::string, s64>& streamIds,
        std::string_view account,
        FleetStream_e stream,
        std::string_view time)
    {
        {
            auto statement = SQLite::Statement{database, "INSERT INTO fleet_accounts (name) VALUES (?) ON CONFLICT (name) DO NOTHING"};
            statement.bind(1, std::string{account});
            statement.exec();
        }

        auto accountId = s64{};
        {
            auto statement = SQLite::Statement{database, "SELECT id FROM fleet_accounts WHERE name = ?"};
            statement.bind(1, std::string{account});
            if (!statement.executeStep())
            {
                throw std::runtime_error{"could not find fleet account after insert"};
            }

            accountId = statement.getColumn(0).getInt64();
        }

        auto statement = SQLite::Statement{database, "INSERT INTO fleet_records (account_id, stream_id, recorded_at) VALUES (?, ?, ?)"};
        statement.bind(1, accountId);
        statement.bind(2, StringId(database, streamIds, "fleet_streams", StreamName(stream)));
        statement.bind(3, UnixTimestamp(time));
        statement.exec();
        return database.getLastInsertRowid();
    }

    void BindOptionalInteger(SQLite::Statement& statement, int index, const std::optional<s32>& value)
    {
        if (value)
        {
            statement.bind(index, static_cast<s64>(*value));
        }
        else
        {
            statement.bind(index);
        }
    }

    void BindOptionalBool(SQLite::Statement& statement, int index, const std::optional<bool>& value)
    {
        if (value)
        {
            statement.bind(index, static_cast<s32>(*value));
        }
        else
        {
            statement.bind(index);
        }
    }

    void BindTile(SQLite::Statement& statement, int index, const std::optional<FleetLogTile_s>& tile)
    {
        if (tile)
        {
            statement.bind(index, static_cast<s64>(tile->x));
            statement.bind(index + 1, static_cast<s64>(tile->z));
            statement.bind(index + 2, static_cast<s64>(tile->level));
        }
        else
        {
            statement.bind(index);
            statement.bind(index + 1);
            statement.bind(index + 2);
        }
    }

    void BindStat(SQLite::Statement& statement, int index, const std::optional<FleetLogStat_s>& stat)
    {
        if (stat)
        {
            statement.bind(index, static_cast<s64>(stat->current));
            statement.bind(index + 1, static_cast<s64>(stat->base));
        }
        else
        {
            statement.bind(index);
            statement.bind(index + 1);
        }
    }

    void InsertItems(
        SQLite::Database& database,
        std::unordered_map<std::string, s64>& itemNameIds,
        std::string_view table,
        s64 recordId,
        const std::vector<FleetItem_s>& items)
    {
        const auto query = std::format("INSERT INTO {} (record_id, item_id, name_id, quantity) VALUES (?, ?, ?, ?)", table);
        auto itemStatement = SQLite::Statement{database, query};

        for (const auto& item : items)
        {
            itemStatement.bind(1, recordId);
            itemStatement.bind(2, static_cast<s64>(item.id));
            itemStatement.bind(3, StringId(database, itemNameIds, "fleet_item_names", SanitizeUtf8(item.name)));
            itemStatement.bind(4, static_cast<s64>(item.qty));
            itemStatement.exec();
            itemStatement.reset();
        }
    }
}

FleetRecordStore::FleetRecordStore(std::filesystem::path path, FleetRetentionSettings_s retention)
    : m_path{std::move(path)}
    , m_retention{std::move(retention)}
{
    const auto validateRetention = [](const FleetRecordRetention_s& retention)
    {
        return retention.maxRecords >= 0 && retention.pruneRecords >= 0 &&
            ((retention.maxRecords == 0 && retention.pruneRecords == 0) ||
             (retention.maxRecords > 0 && retention.pruneRecords > 0 && retention.pruneRecords < retention.maxRecords));
    };
    if (!validateRetention(m_retention.accountData) ||
        !validateRetention(m_retention.experience) ||
        !validateRetention(m_retention.bank) ||
        !validateRetention(m_retention.inventory) ||
        !validateRetention(m_retention.equipment))
    {
        throw std::invalid_argument{"fleet retention limits must both be zero to disable pruning, or pruneRecords must be less than a positive maxRecords"};
    }
}

void FleetRecordStore::WriteBatch(std::span<const FleetRecord> records)
{
    try
    {
        EnsureOpen();
        auto transaction = SQLite::Transaction{*m_database};

        auto touchedStreams = std::vector<std::pair<std::string, FleetStream_e>>{};
        for (const auto& entry : records)
        {
            std::visit([this, &touchedStreams](const auto& record)
            {
                Write(record);

                const auto touched = std::pair{record.account, StreamForRecord(record)};
                if (std::ranges::find(touchedStreams, touched) == touchedStreams.end())
                {
                    touchedStreams.push_back(touched);
                }
            }, entry);
        }

        for (const auto& [account, stream] : touchedStreams)
        {
            Prune(account, stream);
        }

        transaction.commit();
    }
    catch (...)
    {
        // Cached IDs may refer to dictionary rows rolled back with this batch.
        m_streamIds.clear();
        m_stateIds.clear();
        m_targetKindIds.clear();
        m_skillIds.clear();
        m_itemNameIds.clear();
        throw;
    }
}

void FleetRecordStore::Write(const FleetAccountDataLog_s& record)
{
    const auto recordId = InsertRecord(*m_database, m_streamIds, record.account, FleetStream_e::AccountData, record.time);
    auto statement = SQLite::Statement{*m_database,
                                       "INSERT INTO fleet_account_data ("
                                       "record_id, state_id, settled, pid, tile_x, tile_z, tile_level, destination_x, destination_z, destination_level, "
                                       "target_kind_id, target_index, target_x, target_z, target_level, hp_current, hp_base, energy, prayer_current, prayer_base, "
                                       "special_attack_energy, special_attack_armed, running, moving, in_combat, weight, tick) "
                                       "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"};
    statement.bind(1, recordId);
    statement.bind(2, StringId(*m_database, m_stateIds, "fleet_states", record.state));
    statement.bind(3, static_cast<s32>(record.settled));
    BindOptionalInteger(statement, 4, record.pid);
    BindTile(statement, 5, record.tile);
    BindTile(statement, 8, record.destination);

    if (record.target)
    {
        statement.bind(11, StringId(*m_database, m_targetKindIds, "fleet_target_kinds", record.target->kind));
        BindOptionalInteger(statement, 12, record.target->index);
        BindTile(statement, 13, record.target->tile);
    }
    else
    {
        statement.bind(11);
        statement.bind(12);
        statement.bind(13);
        statement.bind(14);
        statement.bind(15);
    }

    BindStat(statement, 16, record.hp);
    BindOptionalInteger(statement, 18, record.energy);
    BindStat(statement, 19, record.prayer);

    if (record.specialAttack)
    {
        statement.bind(21, static_cast<s64>(record.specialAttack->energy));
        statement.bind(22, static_cast<s32>(record.specialAttack->armed));
    }
    else
    {
        statement.bind(21);
        statement.bind(22);
    }

    BindOptionalBool(statement, 23, record.running);
    BindOptionalBool(statement, 24, record.moving);
    BindOptionalBool(statement, 25, record.inCombat);
    BindOptionalInteger(statement, 26, record.weight);
    statement.bind(27, static_cast<s64>(record.tick));
    statement.exec();
}

void FleetRecordStore::Write(const FleetExperienceLog_s& record)
{
    const auto recordId = InsertRecord(*m_database, m_streamIds, record.account, FleetStream_e::Experience, record.time);
    {
        auto statement = SQLite::Statement{*m_database, "INSERT INTO fleet_experience (record_id, state_id, settled) VALUES (?, ?, ?)"};
        statement.bind(1, recordId);
        statement.bind(2, StringId(*m_database, m_stateIds, "fleet_states", record.state));
        statement.bind(3, static_cast<s32>(record.settled));
        statement.exec();
    }

    auto statement = SQLite::Statement{*m_database, "INSERT INTO fleet_experience_skills (record_id, skill_id, ordinal, level, base, xp) VALUES (?, ?, ?, ?, ?, ?)"};
    for (std::size_t i = 0; i < record.skills.size(); ++i)
    {
        const auto& [name, skill] = record.skills[i];
        statement.bind(1, recordId);
        statement.bind(2, StringId(*m_database, m_skillIds, "fleet_skills", name));
        statement.bind(3, static_cast<s64>(i));
        statement.bind(4, static_cast<s32>(skill.level));
        statement.bind(5, static_cast<s32>(skill.base));
        statement.bind(6, static_cast<s64>(skill.xp));
        statement.exec();
        statement.reset();
    }
}

void FleetRecordStore::Write(const FleetBankLog_s& record)
{
    const auto recordId = InsertRecord(*m_database, m_streamIds, record.account, FleetStream_e::Bank, record.time);
    {
        auto statement = SQLite::Statement{*m_database, "INSERT INTO fleet_bank (record_id) VALUES (?)"};
        statement.bind(1, recordId);
        statement.exec();
    }

    InsertItems(*m_database, m_itemNameIds, "fleet_bank_items", recordId, record.items);
}

void FleetRecordStore::Write(const FleetInventoryLog_s& record)
{
    const auto recordId = InsertRecord(*m_database, m_streamIds, record.account, FleetStream_e::Inventory, record.time);
    {
        auto statement = SQLite::Statement{*m_database, "INSERT INTO fleet_inventory (record_id, bank_open, used, free) VALUES (?, ?, ?, ?)"};
        statement.bind(1, recordId);
        statement.bind(2, static_cast<s32>(record.bankOpen));
        statement.bind(3, static_cast<s64>(record.used));
        statement.bind(4, static_cast<s64>(record.free));
        statement.exec();
    }

    InsertItems(*m_database, m_itemNameIds, "fleet_inventory_items", recordId, record.items);
}

void FleetRecordStore::Write(const FleetEquipmentLog_s& record)
{
    const auto recordId = InsertRecord(*m_database, m_streamIds, record.account, FleetStream_e::Equipment, record.time);
    {
        auto statement = SQLite::Statement{*m_database, "INSERT INTO fleet_equipment (record_id, used) VALUES (?, ?)"};
        statement.bind(1, recordId);
        statement.bind(2, static_cast<s64>(record.used));
        statement.exec();
    }

    InsertItems(*m_database, m_itemNameIds, "fleet_equipment_items", recordId, record.items);
}

void FleetRecordStore::Prune(std::string_view account, FleetStream_e stream)
{
    const auto& retention = [&]() -> const FleetRecordRetention_s&
    {
        switch (stream)
        {
        case FleetStream_e::AccountData:
            return m_retention.accountData;
        case FleetStream_e::Experience:
            return m_retention.experience;
        case FleetStream_e::Bank:
            return m_retention.bank;
        case FleetStream_e::Inventory:
            return m_retention.inventory;
        case FleetStream_e::Equipment:
            return m_retention.equipment;
        }

        throw std::invalid_argument{"unknown fleet stream"};
    }();
    if (retention.maxRecords == 0)
    {
        return;
    }

    auto accountId = s64{};
    {
        auto statement = SQLite::Statement{*m_database, "SELECT id FROM fleet_accounts WHERE name = ?"};
        statement.bind(1, std::string{account});
        if (!statement.executeStep())
        {
            throw std::runtime_error{"could not find fleet account while pruning records"};
        }

        accountId = statement.getColumn(0).getInt64();
    }

    const auto streamId = StringId(*m_database, m_streamIds, "fleet_streams", StreamName(stream));
    auto count = s64{};
    {
        auto statement = SQLite::Statement{*m_database, "SELECT COUNT(*) FROM fleet_records WHERE account_id = ? AND stream_id = ?"};
        statement.bind(1, accountId);
        statement.bind(2, streamId);
        if (!statement.executeStep())
        {
            throw std::runtime_error{"could not count fleet records while pruning"};
        }

        count = statement.getColumn(0).getInt64();
    }

    if (count < retention.maxRecords)
    {
        return;
    }

    const auto pruneRounds = (count - retention.maxRecords) / retention.pruneRecords + 1;
    const auto deleteCount = pruneRounds * retention.pruneRecords;
    auto deleteStatement = SQLite::Statement{
        *m_database,
        "DELETE FROM fleet_records WHERE sequence IN ("
        "SELECT sequence FROM fleet_records WHERE account_id = ? AND stream_id = ? "
        "ORDER BY sequence ASC LIMIT ?)"};
    deleteStatement.bind(1, accountId);
    deleteStatement.bind(2, streamId);
    deleteStatement.bind(3, deleteCount);
    deleteStatement.exec();
}

void FleetRecordStore::EnsureOpen()
{
    if (m_database)
    {
        return;
    }

    m_database = FleetDatabaseSchema::Open(m_path);
}
