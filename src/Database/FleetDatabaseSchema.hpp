#pragma once

#include <SQLiteCpp/SQLiteCpp.h>

class FleetDatabaseSchema
{
public:
    FleetDatabaseSchema() = delete;

    [[nodiscard]] static std::unique_ptr<SQLite::Database> Open(const std::filesystem::path& path);
};
