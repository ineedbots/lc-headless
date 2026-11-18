#pragma once

#include "Database/Type/FleetAccountDataLog_s.hpp"
#include "Database/Type/FleetBankLog_s.hpp"
#include "Database/Type/FleetEquipmentLog_s.hpp"
#include "Database/Type/FleetExperienceLog_s.hpp"
#include "Database/Type/FleetInventoryLog_s.hpp"
#include "Database/Type/FleetStream_e.hpp"
#include "Config/Type/Config_s.hpp"

#include <SQLiteCpp/SQLiteCpp.h>

#include <unordered_map>

class FleetDatabase
{
public:
    enum class Mode_e
    {
        Inline, // Synchronous mode for direct callers and deterministic tests.
        Background,
    };

    static constexpr std::size_t MAX_PENDING_WRITES = 256;
    static constexpr std::size_t MAX_BATCH_WRITES = 64;

    explicit FleetDatabase(std::filesystem::path path, Mode_e mode = Mode_e::Background, FleetRetentionSettings_s retention = {});
    ~FleetDatabase();

    FleetDatabase(const FleetDatabase&) = delete;
    FleetDatabase& operator=(const FleetDatabase&) = delete;

    void Append(const FleetAccountDataLog_s& record);
    void Append(const FleetExperienceLog_s& record);
    void Append(const FleetBankLog_s& record);
    void Append(const FleetInventoryLog_s& record);
    void Append(const FleetEquipmentLog_s& record);

    [[nodiscard]] std::optional<std::future<void>> Enqueue(const FleetAccountDataLog_s& record);
    [[nodiscard]] std::optional<std::future<void>> Enqueue(const FleetExperienceLog_s& record);
    [[nodiscard]] std::optional<std::future<void>> Enqueue(const FleetBankLog_s& record);
    [[nodiscard]] std::optional<std::future<void>> Enqueue(const FleetInventoryLog_s& record);
    [[nodiscard]] std::optional<std::future<void>> Enqueue(const FleetEquipmentLog_s& record);

    void Flush();

    [[nodiscard]] u64 GetCommittedBatchCount() const
    {
        return m_committedBatchCount.load();
    }

    [[nodiscard]] const std::filesystem::path& GetPath() const
    {
        return m_path;
    }

private:
    using Record_t = std::variant<FleetAccountDataLog_s, FleetExperienceLog_s, FleetBankLog_s, FleetInventoryLog_s, FleetEquipmentLog_s>;

    struct PendingWrite_s
    {
        Record_t record;
        std::promise<void> completion;
    };

    [[nodiscard]] std::optional<std::future<void>> Enqueue(Record_t record);
    void Run();
    void WriteBatch(std::vector<PendingWrite_s> writes);
    void Write(const FleetAccountDataLog_s& record);
    void Write(const FleetExperienceLog_s& record);
    void Write(const FleetBankLog_s& record);
    void Write(const FleetInventoryLog_s& record);
    void Write(const FleetEquipmentLog_s& record);
    void Prune(std::string_view account, FleetStream_e stream);
    void EnsureOpen();

    std::filesystem::path m_path;
    Mode_e m_mode;
    FleetRetentionSettings_s m_retention;
    std::unique_ptr<SQLite::Database> m_database;
    std::unordered_map<std::string, s64> m_streamIds;
    std::unordered_map<std::string, s64> m_stateIds;
    std::unordered_map<std::string, s64> m_targetKindIds;
    std::unordered_map<std::string, s64> m_skillIds;
    std::unordered_map<std::string, s64> m_itemNameIds;
    std::mutex m_writeMutex;
    std::mutex m_mutex;
    std::condition_variable m_wake;
    std::condition_variable m_idle;
    std::deque<PendingWrite_s> m_queue;
    std::size_t m_pendingWrites = 0;
    bool m_stopping = false;
    std::atomic<u64> m_committedBatchCount = 0;
    std::thread m_worker;
};
