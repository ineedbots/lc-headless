#include "pch.hpp"
#include "FleetDatabase.hpp"

#include <SQLiteCpp/SQLiteCpp.h>
#include <nlohmann/json.hpp>

#include <charconv>

namespace
{
    constexpr auto SCHEMA_VERSION = 5;
    constexpr auto BUSY_TIMEOUT_MS = 25;
    constexpr auto BATCH_DELAY = 5ms;

    std::string PathToUtf8(const std::filesystem::path& path)
    {
        const auto text = path.u8string();
        return {reinterpret_cast<const char*>(text.data()), text.size()};
    }

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

    template <typename TRecord>
    void AppendAndWait(FleetDatabase& database, const TRecord& record)
    {
        auto completion = database.Enqueue(record);
        if (!completion)
        {
            throw std::runtime_error{"fleet database write queue is full"};
        }

        completion->get();
    }
}

FleetDatabase::FleetDatabase(std::filesystem::path path, Mode_e mode, FleetRetentionSettings_s retention)
    : m_path{std::move(path)}
    , m_mode{mode}
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

    if (m_mode == Mode_e::Background)
    {
        m_worker = std::thread{[this]
        {
            Run();
        }};
    }
}

FleetDatabase::~FleetDatabase()
{
    if (!m_worker.joinable())
    {
        return;
    }

    {
        const auto lock = std::lock_guard{m_mutex};
        m_stopping = true;
    }

    m_wake.notify_one();
    m_worker.join();
}

void FleetDatabase::Append(const FleetAccountDataLog_s& record)
{
    AppendAndWait(*this, record);
}

void FleetDatabase::Append(const FleetExperienceLog_s& record)
{
    AppendAndWait(*this, record);
}

void FleetDatabase::Append(const FleetBankLog_s& record)
{
    AppendAndWait(*this, record);
}

void FleetDatabase::Append(const FleetInventoryLog_s& record)
{
    AppendAndWait(*this, record);
}

void FleetDatabase::Append(const FleetEquipmentLog_s& record)
{
    AppendAndWait(*this, record);
}

std::optional<std::future<void>> FleetDatabase::Enqueue(const FleetAccountDataLog_s& record)
{
    return Enqueue(Record_t{record});
}

std::optional<std::future<void>> FleetDatabase::Enqueue(const FleetExperienceLog_s& record)
{
    return Enqueue(Record_t{record});
}

std::optional<std::future<void>> FleetDatabase::Enqueue(const FleetBankLog_s& record)
{
    return Enqueue(Record_t{record});
}

std::optional<std::future<void>> FleetDatabase::Enqueue(const FleetInventoryLog_s& record)
{
    return Enqueue(Record_t{record});
}

std::optional<std::future<void>> FleetDatabase::Enqueue(const FleetEquipmentLog_s& record)
{
    return Enqueue(Record_t{record});
}

std::optional<std::future<void>> FleetDatabase::Enqueue(Record_t record)
{
    auto write = PendingWrite_s{.record = std::move(record)};
    auto completion = write.completion.get_future();

    if (m_mode == Mode_e::Inline)
    {
        auto writes = std::vector<PendingWrite_s>{};
        writes.push_back(std::move(write));
        WriteBatch(std::move(writes));
        return std::optional{std::move(completion)};
    }

    {
        const auto lock = std::lock_guard{m_mutex};
        if (m_stopping || m_pendingWrites >= MAX_PENDING_WRITES)
        {
            return std::nullopt;
        }

        m_queue.push_back(std::move(write));
        ++m_pendingWrites;
    }

    m_wake.notify_one();
    return std::optional{std::move(completion)};
}

void FleetDatabase::Flush()
{
    auto lock = std::unique_lock{m_mutex};
    m_idle.wait(lock, [this]
    {
        return m_pendingWrites == 0;
    });
}

void FleetDatabase::Run()
{
    while (true)
    {
        auto batch = std::vector<PendingWrite_s>{};
        {
            auto lock = std::unique_lock{m_mutex};
            m_wake.wait(lock, [this]
            {
                return m_stopping || !m_queue.empty();
            });

            if (m_queue.empty() && m_stopping)
            {
                return;
            }

            if (!m_stopping && m_queue.size() < MAX_BATCH_WRITES)
            {
                m_wake.wait_for(lock, BATCH_DELAY, [this]
                {
                    return m_stopping || m_queue.size() >= MAX_BATCH_WRITES;
                });
            }

            const auto count = std::min(m_queue.size(), MAX_BATCH_WRITES);
            batch.reserve(count);
            for (auto i = std::size_t{}; i < count; ++i)
            {
                batch.push_back(std::move(m_queue.front()));
                m_queue.pop_front();
            }
        }

        WriteBatch(std::move(batch));
    }
}

void FleetDatabase::WriteBatch(std::vector<PendingWrite_s> writes)
{
    const auto writeLock = std::lock_guard{m_writeMutex};
    auto error = std::exception_ptr{};

    try
    {
        EnsureOpen();
        auto transaction = SQLite::Transaction{*m_database};

        auto touchedStreams = std::vector<std::pair<std::string, FleetStream_e>>{};
        for (const auto& write : writes)
        {
            std::visit([this, &touchedStreams](const auto& record)
            {
                Write(record);

                const auto touched = std::pair{record.account, StreamForRecord(record)};
                if (std::ranges::find(touchedStreams, touched) == touchedStreams.end())
                {
                    touchedStreams.push_back(touched);
                }
            }, write.record);
        }

        for (const auto& [account, stream] : touchedStreams)
        {
            Prune(account, stream);
        }

        transaction.commit();
        ++m_committedBatchCount;
    }
    catch (...)
    {
        // Cached IDs may refer to dictionary rows rolled back with this batch.
        m_streamIds.clear();
        m_stateIds.clear();
        m_targetKindIds.clear();
        m_skillIds.clear();
        m_itemNameIds.clear();
        error = std::current_exception();
    }

    for (auto& write : writes)
    {
        if (error)
        {
            write.completion.set_exception(error);
        }
        else
        {
            write.completion.set_value();
        }
    }

    if (m_mode == Mode_e::Background)
    {
        const auto lock = std::lock_guard{m_mutex};
        m_pendingWrites -= writes.size();
    }

    m_idle.notify_all();
}

void FleetDatabase::Write(const FleetAccountDataLog_s& record)
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

void FleetDatabase::Write(const FleetExperienceLog_s& record)
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

void FleetDatabase::Write(const FleetBankLog_s& record)
{
    const auto recordId = InsertRecord(*m_database, m_streamIds, record.account, FleetStream_e::Bank, record.time);
    {
        auto statement = SQLite::Statement{*m_database, "INSERT INTO fleet_bank (record_id) VALUES (?)"};
        statement.bind(1, recordId);
        statement.exec();
    }

    InsertItems(*m_database, m_itemNameIds, "fleet_bank_items", recordId, record.items);
}

void FleetDatabase::Write(const FleetInventoryLog_s& record)
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

void FleetDatabase::Write(const FleetEquipmentLog_s& record)
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

void FleetDatabase::Prune(std::string_view account, FleetStream_e stream)
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

void FleetDatabase::EnsureOpen()
{
    if (m_database)
    {
        return;
    }

    if (!m_path.parent_path().empty())
    {
        std::filesystem::create_directories(m_path.parent_path());
    }

    auto database = std::make_unique<SQLite::Database>(PathToUtf8(m_path), SQLite::OPEN_READWRITE | SQLite::OPEN_CREATE);
    database->exec(std::format("PRAGMA busy_timeout = {}", BUSY_TIMEOUT_MS));
    database->exec("PRAGMA foreign_keys = ON");

    auto version = 0;
    {
        auto versionStatement = SQLite::Statement{*database, "PRAGMA user_version"};
        if (!versionStatement.executeStep())
        {
            throw std::runtime_error{"could not read fleet database schema version"};
        }

        version = versionStatement.getColumn(0).getInt();
    }

    if (version > SCHEMA_VERSION)
    {
        throw std::runtime_error{std::format("fleet database schema version {} is newer than supported version {}", version, SCHEMA_VERSION)};
    }

    if (version != 0 && version != SCHEMA_VERSION)
    {
        throw std::runtime_error{std::format("fleet database schema version {} is unsupported; use a new database file", version)};
    }

    if (version == 0)
    {
        auto tables = SQLite::Statement{*database, "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"};
        if (!tables.executeStep())
        {
            throw std::runtime_error{"could not inspect fleet database schema"};
        }

        if (tables.getColumn(0).getInt() != 0)
        {
            throw std::runtime_error{"fleet database has an unversioned schema; use a new database file"};
        }
    }

    database->exec("PRAGMA journal_mode = WAL");
    database->exec("PRAGMA synchronous = NORMAL");
    database->exec("PRAGMA wal_autocheckpoint = 1000");

    if (version == 0)
    {
        auto transaction = SQLite::Transaction{*database};
        database->exec(
            "CREATE TABLE fleet_accounts ("
            "id INTEGER PRIMARY KEY, "
            "name TEXT NOT NULL UNIQUE)");
        database->exec("CREATE TABLE fleet_streams (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE)");
        database->exec(
            "CREATE TABLE fleet_records ("
            "sequence INTEGER PRIMARY KEY AUTOINCREMENT, "
            "account_id INTEGER NOT NULL REFERENCES fleet_accounts(id), "
            "stream_id INTEGER NOT NULL REFERENCES fleet_streams(id), "
            "recorded_at INTEGER NOT NULL)");
        database->exec("CREATE INDEX fleet_records_latest ON fleet_records (account_id, stream_id, sequence DESC)");
        database->exec("CREATE INDEX fleet_records_history ON fleet_records (account_id, stream_id, recorded_at, sequence)");
        database->exec("CREATE INDEX fleet_records_stream_latest ON fleet_records (stream_id, account_id, sequence DESC)");
        database->exec("CREATE TABLE fleet_item_names (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE)");
        database->exec("CREATE TABLE fleet_states (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE)");
        database->exec("CREATE TABLE fleet_target_kinds (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE)");
        database->exec("INSERT INTO fleet_target_kinds (id, name) VALUES (1, 'npc'), (2, 'player'), (3, 'tile')");
        database->exec("CREATE TABLE fleet_skills (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE)");
        database->exec(
            "CREATE TABLE fleet_account_data ("
            "record_id INTEGER PRIMARY KEY REFERENCES fleet_records(sequence) ON DELETE CASCADE, "
            "state_id INTEGER NOT NULL REFERENCES fleet_states(id), "
            "settled INTEGER NOT NULL CHECK (settled IN (0, 1)), "
            "pid INTEGER, "
            "tile_x INTEGER, tile_z INTEGER, tile_level INTEGER, "
            "destination_x INTEGER, destination_z INTEGER, destination_level INTEGER, "
            "target_kind_id INTEGER REFERENCES fleet_target_kinds(id), target_index INTEGER, target_x INTEGER, target_z INTEGER, target_level INTEGER, "
            "hp_current INTEGER, hp_base INTEGER, "
            "energy INTEGER CHECK (energy BETWEEN 0 AND 100), "
            "prayer_current INTEGER, prayer_base INTEGER, "
            "special_attack_energy INTEGER CHECK (special_attack_energy BETWEEN 0 AND 1000), "
            "special_attack_armed INTEGER CHECK (special_attack_armed IN (0, 1)), "
            "running INTEGER CHECK (running IN (0, 1)), "
            "moving INTEGER CHECK (moving IN (0, 1)), "
            "in_combat INTEGER CHECK (in_combat IN (0, 1)), "
            "weight INTEGER, "
            "tick INTEGER NOT NULL CHECK (tick >= 0), "
            "CHECK ((tile_x IS NULL AND tile_z IS NULL AND tile_level IS NULL) OR (tile_x IS NOT NULL AND tile_z IS NOT NULL AND tile_level IS NOT NULL)), "
            "CHECK ((destination_x IS NULL AND destination_z IS NULL AND destination_level IS NULL) OR (destination_x IS NOT NULL AND destination_z IS NOT NULL AND destination_level IS NOT NULL)), "
            "CHECK ((hp_current IS NULL AND hp_base IS NULL) OR (hp_current IS NOT NULL AND hp_base IS NOT NULL)), "
            "CHECK ((prayer_current IS NULL AND prayer_base IS NULL) OR (prayer_current IS NOT NULL AND prayer_base IS NOT NULL)), "
            "CHECK ((special_attack_energy IS NULL AND special_attack_armed IS NULL) OR "
            "(special_attack_energy IS NOT NULL AND special_attack_armed IS NOT NULL)), "
            "CHECK ((target_kind_id IS NULL AND target_index IS NULL AND target_x IS NULL AND target_z IS NULL AND target_level IS NULL) OR "
            "(target_kind_id IS NOT NULL AND target_kind_id IN (1, 2) AND target_index IS NOT NULL AND target_x IS NULL AND target_z IS NULL AND target_level IS NULL) OR "
            "(target_kind_id IS NOT NULL AND target_kind_id = 3 AND target_index IS NULL AND target_x IS NOT NULL AND target_z IS NOT NULL AND target_level IS NOT NULL)))");
        database->exec(
            "CREATE TABLE fleet_experience ("
            "record_id INTEGER PRIMARY KEY REFERENCES fleet_records(sequence) ON DELETE CASCADE, "
            "state_id INTEGER NOT NULL REFERENCES fleet_states(id), "
            "settled INTEGER NOT NULL CHECK (settled IN (0, 1)))");
        database->exec(
            "CREATE TABLE fleet_experience_skills ("
            "record_id INTEGER NOT NULL REFERENCES fleet_experience(record_id) ON DELETE CASCADE, "
            "skill_id INTEGER NOT NULL REFERENCES fleet_skills(id), "
            "ordinal INTEGER NOT NULL CHECK (ordinal >= 0), "
            "level INTEGER NOT NULL, "
            "base INTEGER NOT NULL, "
            "xp INTEGER NOT NULL CHECK (xp >= 0), "
            "PRIMARY KEY (record_id, skill_id), "
            "UNIQUE (record_id, ordinal)) WITHOUT ROWID");
        database->exec(
            "CREATE TABLE fleet_bank ("
            "record_id INTEGER PRIMARY KEY REFERENCES fleet_records(sequence) ON DELETE CASCADE)");
        database->exec(
            "CREATE TABLE fleet_bank_items ("
            "record_id INTEGER NOT NULL REFERENCES fleet_bank(record_id) ON DELETE CASCADE, "
            "item_id INTEGER NOT NULL, "
            "name_id INTEGER NOT NULL REFERENCES fleet_item_names(id), "
            "quantity INTEGER NOT NULL CHECK (quantity > 0), "
            "PRIMARY KEY (record_id, item_id)) WITHOUT ROWID");
        database->exec(
            "CREATE TABLE fleet_inventory ("
            "record_id INTEGER PRIMARY KEY REFERENCES fleet_records(sequence) ON DELETE CASCADE, "
            "bank_open INTEGER NOT NULL CHECK (bank_open IN (0, 1)), "
            "used INTEGER NOT NULL CHECK (used >= 0), "
            "free INTEGER NOT NULL CHECK (free >= 0))");
        database->exec(
            "CREATE TABLE fleet_inventory_items ("
            "record_id INTEGER NOT NULL REFERENCES fleet_inventory(record_id) ON DELETE CASCADE, "
            "item_id INTEGER NOT NULL, "
            "name_id INTEGER NOT NULL REFERENCES fleet_item_names(id), "
            "quantity INTEGER NOT NULL CHECK (quantity > 0), "
            "PRIMARY KEY (record_id, item_id)) WITHOUT ROWID");
        database->exec(
            "CREATE TABLE fleet_equipment ("
            "record_id INTEGER PRIMARY KEY REFERENCES fleet_records(sequence) ON DELETE CASCADE, "
            "used INTEGER NOT NULL CHECK (used >= 0))");
        database->exec(
            "CREATE TABLE fleet_equipment_items ("
            "record_id INTEGER NOT NULL REFERENCES fleet_equipment(record_id) ON DELETE CASCADE, "
            "item_id INTEGER NOT NULL, "
            "name_id INTEGER NOT NULL REFERENCES fleet_item_names(id), "
            "quantity INTEGER NOT NULL CHECK (quantity > 0), "
            "PRIMARY KEY (record_id, item_id)) WITHOUT ROWID");
        database->exec(std::format("PRAGMA user_version = {}", SCHEMA_VERSION));
        transaction.commit();
    }
    m_database = std::move(database);
}
