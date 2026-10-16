#include "pch.hpp"
#include "FileWatcher.hpp"

FileWatcher::FileWatcher(std::vector<std::filesystem::path> files)
    : m_files{std::move(files)}
    , m_seen{ReadTimes()}
{
}

bool FileWatcher::Check()
{
    auto times = ReadTimes();
    if (times == m_seen)
    {
        m_pending.reset();
        return false;
    }

    if (times != m_pending)
    {
        m_pending = std::move(times);
        return false;
    }

    m_seen = std::move(times);
    m_pending.reset();
    return true;
}

const std::vector<std::filesystem::path>& FileWatcher::GetFiles() const
{
    return m_files;
}

FileWatcher::Times FileWatcher::ReadTimes() const
{
    auto times = Times{};
    times.reserve(m_files.size());
    for (const auto& file : m_files)
    {
        auto error = std::error_code{};
        const auto time = std::filesystem::last_write_time(file, error);
        times.push_back(error ? std::nullopt : std::optional{time});
    }

    return times;
}
