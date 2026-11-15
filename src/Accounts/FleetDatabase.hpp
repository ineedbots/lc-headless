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
    enum class Mode_e
    {
        Inline, // Synchronous mode for direct callers and deterministic tests.
        Background,
    };

    static constexpr std::size_t MAX_PENDING_WRITES = 256;
    static constexpr std::size_t MAX_BATCH_WRITES = 64;

    explicit FleetDatabase(std::filesystem::path path, Mode_e mode = Mode_e::Background);
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
    void EnsureOpen();

    std::filesystem::path m_path;
    Mode_e m_mode;
    std::unique_ptr<SQLite::Database> m_database;
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
