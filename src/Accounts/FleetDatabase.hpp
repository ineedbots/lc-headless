#pragma once

#include "Type/FleetStream_e.hpp"

#include <SQLiteCpp/SQLiteCpp.h>

class FleetDatabase
{
public:
    explicit FleetDatabase(std::filesystem::path path);

    void Append(FleetStream_e stream, std::string_view account, std::string_view time, std::string_view payload);

    [[nodiscard]] const std::filesystem::path& GetPath() const
    {
        return m_path;
    }

private:
    void EnsureOpen();

    std::filesystem::path m_path;
    std::unique_ptr<SQLite::Database> m_database;
};
