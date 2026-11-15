#pragma once

#include <SQLiteCpp/SQLiteCpp.h>
#include <nlohmann/json.hpp>

namespace FleetDatabaseReader
{
    inline nlohmann::ordered_json Tile(SQLite::Statement& statement, int xIndex)
    {
        const auto x = statement.getColumn(xIndex);
        if (x.isNull())
        {
            return nullptr;
        }

        return {
            {"x", x.getInt()},
            {"z", statement.getColumn(xIndex + 1).getInt()},
            {"level", statement.getColumn(xIndex + 2).getInt()}};
    }

    inline nlohmann::ordered_json Items(SQLite::Database& database, std::string_view table, s64 recordId)
    {
        const auto query = std::format(
            "SELECT items.item_id, names.name, items.quantity FROM {} AS items "
            "JOIN fleet_item_names AS names ON names.id = items.name_id "
            "WHERE items.record_id = ? ORDER BY items.item_id",
            table);
        auto statement = SQLite::Statement{database, query};
        statement.bind(1, recordId);

        auto items = nlohmann::ordered_json::array();
        while (statement.executeStep())
        {
            items.push_back({{"id", statement.getColumn(0).getInt()},
                             {"name", statement.getColumn(1).getString()},
                             {"qty", statement.getColumn(2).getInt()}});
        }

        return items;
    }

    inline nlohmann::ordered_json Read(SQLite::Database& database, std::string_view stream, s64 sequence, std::string_view account, std::string_view time)
    {
        auto record = nlohmann::ordered_json{{"time", time}, {"account", account}};

        if (stream == "account-data")
        {
            auto statement = SQLite::Statement{database,
                                               "SELECT state, settled, pid, tile_x, tile_z, tile_level, destination_x, destination_z, destination_level, "
                                               "target_kind, target_index, target_x, target_z, target_level, hp_current, hp_base, energy, "
                                               "prayer_current, prayer_base, special_attack_energy, special_attack_armed, running, moving, "
                                               "in_combat, weight, tick FROM fleet_account_data WHERE record_id = ?"};
            statement.bind(1, sequence);
            if (!statement.executeStep())
            {
                throw std::runtime_error{"account-data record has no typed data row"};
            }

            const auto optionalInteger = [&](int index)
            {
                const auto column = statement.getColumn(index);
                return column.isNull() ? nlohmann::ordered_json(nullptr) : nlohmann::ordered_json(column.getInt());
            };
            const auto optionalBoolean = [&](int index)
            {
                const auto column = statement.getColumn(index);
                return column.isNull() ? nlohmann::ordered_json(nullptr) : nlohmann::ordered_json(column.getInt() != 0);
            };
            const auto targetKind = statement.getColumn(9);
            auto target = nlohmann::ordered_json{};
            if (targetKind.isNull())
            {
                target = nullptr;
            }
            else if (targetKind.getString() == "tile")
            {
                target = {{"kind", "tile"}, {"tile", Tile(statement, 11)}};
            }
            else
            {
                target = {{"kind", targetKind.getString()}, {"index", statement.getColumn(10).getInt()}};
            }

            const auto hp = statement.getColumn(14);
            const auto prayer = statement.getColumn(17);
            const auto specialEnergy = statement.getColumn(19);
            record.update({{"state", statement.getColumn(0).getString()},
                           {"settled", statement.getColumn(1).getInt() != 0},
                           {"pid", optionalInteger(2)},
                           {"tile", Tile(statement, 3)},
                           {"destination", Tile(statement, 6)},
                           {"target", target},
                           {"hp", hp.isNull() ? nlohmann::ordered_json{} : nlohmann::ordered_json{{"current", hp.getInt()}, {"base", statement.getColumn(15).getInt()}}},
                           {"energy", optionalInteger(16)},
                           {"prayer", prayer.isNull() ? nlohmann::ordered_json{} : nlohmann::ordered_json{{"current", prayer.getInt()}, {"base", statement.getColumn(18).getInt()}}},
                           {"specialAttack", specialEnergy.isNull() ? nlohmann::ordered_json{} : nlohmann::ordered_json{{"energy", specialEnergy.getInt()}, {"armed", statement.getColumn(20).getInt() != 0}}},
                           {"running", optionalBoolean(21)},
                           {"moving", optionalBoolean(22)},
                           {"inCombat", optionalBoolean(23)},
                           {"weight", optionalInteger(24)},
                           {"tick", statement.getColumn(25).getInt64()}});
        }
        else if (stream == "experience")
        {
            auto header = SQLite::Statement{database, "SELECT state, settled FROM fleet_experience WHERE record_id = ?"};
            header.bind(1, sequence);
            if (!header.executeStep())
            {
                throw std::runtime_error{"experience record has no typed data row"};
            }

            auto skills = nlohmann::ordered_json::object();
            auto statement = SQLite::Statement{database, "SELECT skill, level, base, xp FROM fleet_experience_skills WHERE record_id = ? ORDER BY ordinal"};
            statement.bind(1, sequence);
            while (statement.executeStep())
            {
                skills[statement.getColumn(0).getString()] = {
                    {"level", statement.getColumn(1).getInt()},
                    {"base", statement.getColumn(2).getInt()},
                    {"xp", statement.getColumn(3).getInt()}};
            }

            record.update({{"state", header.getColumn(0).getString()},
                           {"settled", header.getColumn(1).getInt() != 0},
                           {"skills", std::move(skills)}});
        }
        else if (stream == "bank")
        {
            record["items"] = Items(database, "fleet_bank_items", sequence);
        }
        else if (stream == "inventory")
        {
            auto statement = SQLite::Statement{database, "SELECT bank_open, used, free FROM fleet_inventory WHERE record_id = ?"};
            statement.bind(1, sequence);
            if (!statement.executeStep())
            {
                throw std::runtime_error{"inventory record has no typed data row"};
            }

            record.update({{"bankOpen", statement.getColumn(0).getInt() != 0},
                           {"used", statement.getColumn(1).getInt64()},
                           {"free", statement.getColumn(2).getInt64()},
                           {"items", Items(database, "fleet_inventory_items", sequence)}});
        }
        else if (stream == "equipment")
        {
            auto statement = SQLite::Statement{database, "SELECT used FROM fleet_equipment WHERE record_id = ?"};
            statement.bind(1, sequence);
            if (!statement.executeStep())
            {
                throw std::runtime_error{"equipment record has no typed data row"};
            }

            record.update({{"used", statement.getColumn(0).getInt64()},
                           {"items", Items(database, "fleet_equipment_items", sequence)}});
        }
        else
        {
            throw std::invalid_argument{"unknown fleet stream"};
        }

        return record;
    }
}

inline std::vector<nlohmann::ordered_json> ReadOrderedFleetRecords(const std::filesystem::path& path, std::string_view stream, std::string_view account)
{
    auto database = SQLite::Database{path.string(), SQLite::OPEN_READONLY};
    auto statement = SQLite::Statement{database,
                                       "SELECT records.sequence, accounts.name, records.recorded_at FROM fleet_records AS records "
                                       "JOIN fleet_accounts AS accounts ON accounts.id = records.account_id "
                                       "WHERE records.stream = ? AND accounts.name = ? ORDER BY records.sequence"};
    statement.bind(1, std::string{stream});
    statement.bind(2, std::string{account});

    auto records = std::vector<nlohmann::ordered_json>{};
    while (statement.executeStep())
    {
        records.push_back(FleetDatabaseReader::Read(
            database, stream, statement.getColumn(0).getInt64(), statement.getColumn(1).getString(), statement.getColumn(2).getString()));
    }

    return records;
}

inline std::vector<nlohmann::json> ReadFleetRecords(const std::filesystem::path& path, std::string_view stream, std::string_view account)
{
    auto records = std::vector<nlohmann::json>{};
    for (const auto& record : ReadOrderedFleetRecords(path, stream, account))
    {
        records.emplace_back(record);
    }

    return records;
}

inline std::vector<std::string> ReadFleetPayloads(const std::filesystem::path& path, std::string_view stream, std::string_view account)
{
    auto records = std::vector<std::string>{};
    for (const auto& record : ReadOrderedFleetRecords(path, stream, account))
    {
        records.push_back(record.dump(-1, ' ', false, nlohmann::json::error_handler_t::replace));
    }

    return records;
}
