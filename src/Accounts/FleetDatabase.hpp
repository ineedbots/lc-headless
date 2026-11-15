#pragma once

#include "Type/FleetAccountDataLog_s.hpp"
#include "Type/FleetBankLog_s.hpp"
#include "Type/FleetEquipmentLog_s.hpp"
#include "Type/FleetExperienceLog_s.hpp"
#include "Type/FleetInventoryLog_s.hpp"
#include "Type/FleetStream_e.hpp"

#include <SQLiteCpp/SQLiteCpp.h>

class FleetDatabase
{
public:
    explicit FleetDatabase(std::filesystem::path path);

    void Append(const FleetAccountDataLog_s& record);
    void Append(const FleetExperienceLog_s& record);
    void Append(const FleetBankLog_s& record);
    void Append(const FleetInventoryLog_s& record);
    void Append(const FleetEquipmentLog_s& record);

    [[nodiscard]] const std::filesystem::path& GetPath() const
    {
        return m_path;
    }

private:
    void EnsureOpen();

    std::filesystem::path m_path;
    std::unique_ptr<SQLite::Database> m_database;
};
