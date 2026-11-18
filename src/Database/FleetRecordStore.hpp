#pragma once

#include "Type/FleetRecord.hpp"
#include "Type/FleetStream_e.hpp"
#include "Config/Type/Config_s.hpp"

#include <SQLiteCpp/SQLiteCpp.h>

// The queue serializes access. Each batch owns one transaction, including pruning.
class FleetRecordStore
{
public:
    explicit FleetRecordStore(std::filesystem::path path, FleetRetentionSettings_s retention = {});

    void WriteBatch(std::span<const FleetRecord> records);

    [[nodiscard]] const std::filesystem::path& GetPath() const
    {
        return m_path;
    }

private:
    void Write(const FleetAccountDataLog_s& record);
    void Write(const FleetExperienceLog_s& record);
    void Write(const FleetBankLog_s& record);
    void Write(const FleetInventoryLog_s& record);
    void Write(const FleetEquipmentLog_s& record);
    void Prune(std::string_view account, FleetStream_e stream);
    void EnsureOpen();

    std::filesystem::path m_path;
    FleetRetentionSettings_s m_retention;
    std::unique_ptr<SQLite::Database> m_database;
    std::unordered_map<std::string, s64> m_streamIds;
    std::unordered_map<std::string, s64> m_stateIds;
    std::unordered_map<std::string, s64> m_targetKindIds;
    std::unordered_map<std::string, s64> m_skillIds;
    std::unordered_map<std::string, s64> m_itemNameIds;
};
