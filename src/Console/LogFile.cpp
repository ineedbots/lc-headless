#include "pch.hpp"
#include "LogFile.hpp"

#include "LogEntry_s.hpp"
#include "LogFormatter.hpp"

LogFile::LogFile(std::filesystem::path path)
    : m_path{std::move(path)}
{
    const auto folder = m_path.parent_path();
    auto error = std::error_code{};
    if (!folder.empty())
    {
        std::filesystem::create_directories(folder, error);
    }

    m_stream.open(m_path, std::ios::out | std::ios::app | std::ios::binary);
    if (!m_stream)
    {
        throw std::runtime_error{std::format("{}: the log file can't be opened{}", m_path.string(), error ? ": " + error.message() : "")};
    }
}

void LogFile::Write(const LogEntry_s& entry)
{
    auto line = LogFormatter::FormatLine(entry);
    line += '\n';
    m_stream.write(line.data(), static_cast<std::streamsize>(line.size()));
    m_stream.flush();
    m_stream.clear();
}

const std::filesystem::path& LogFile::GetPath() const
{
    return m_path;
}
