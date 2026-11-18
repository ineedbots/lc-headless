#include "pch.hpp"
#include "FleetDatabase.hpp"

#include "FleetRecordStore.hpp"
#include "Type/FleetRecord.hpp"

namespace
{
    constexpr auto BATCH_DELAY = 5ms;

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
    : m_store{std::move(path), std::move(retention)}
    , m_mode{mode}
{
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
    return Enqueue(FleetRecord{record});
}

std::optional<std::future<void>> FleetDatabase::Enqueue(const FleetExperienceLog_s& record)
{
    return Enqueue(FleetRecord{record});
}

std::optional<std::future<void>> FleetDatabase::Enqueue(const FleetBankLog_s& record)
{
    return Enqueue(FleetRecord{record});
}

std::optional<std::future<void>> FleetDatabase::Enqueue(const FleetInventoryLog_s& record)
{
    return Enqueue(FleetRecord{record});
}

std::optional<std::future<void>> FleetDatabase::Enqueue(const FleetEquipmentLog_s& record)
{
    return Enqueue(FleetRecord{record});
}

std::optional<std::future<void>> FleetDatabase::Enqueue(FleetRecord record)
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
        auto records = std::vector<FleetRecord>{};
        records.reserve(writes.size());

        for (auto& write : writes)
        {
            records.push_back(std::move(write.record));
        }

        m_store.WriteBatch(records);
        ++m_committedBatchCount;
    }
    catch (...)
    {
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
