#pragma once

#include <SQLiteCpp/SQLiteCpp.h>
#include <nlohmann/json.hpp>

inline std::vector<std::string> ReadFleetPayloads(const std::filesystem::path& path, std::string_view stream, std::string_view account)
{
    auto database = SQLite::Database{path.string(), SQLite::OPEN_READONLY};
    auto statement = SQLite::Statement{database, "SELECT payload FROM fleet_records WHERE stream = ? AND account = ? ORDER BY sequence"};
    statement.bind(1, std::string{stream});
    statement.bind(2, std::string{account});

    auto records = std::vector<std::string>{};
    while (statement.executeStep())
    {
        records.emplace_back(statement.getColumn(0).getString());
    }

    return records;
}

inline std::vector<nlohmann::json> ReadFleetRecords(const std::filesystem::path& path, std::string_view stream, std::string_view account)
{
    auto records = std::vector<nlohmann::json>{};
    for (const auto& payload : ReadFleetPayloads(path, stream, account))
    {
        records.push_back(nlohmann::json::parse(payload));
    }

    return records;
}
