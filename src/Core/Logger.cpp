#include "pch.hpp"
#include "Logger.hpp"

namespace
{
    std::string_view GetLevelName(LogLevel_e level)
    {
        switch (level)
        {
        case LogLevel_e::Verbose:
            return "VERBOSE";
        case LogLevel_e::Info:
            return "INFO";
        case LogLevel_e::Warning:
            return "WARNING";
        case LogLevel_e::Error:
            return "ERROR";
        }

        assert(false && "Unknown log level");
        return "UNKNOWN";
    }

    std::string_view GetFileName(std::string_view path)
    {
        const auto separator = path.find_last_of("/\\");
        if (separator == std::string_view::npos)
        {
            return path;
        }

        return path.substr(separator + 1);
    }
}

Logger::Logger(LogLevel_e level, Sink sink)
    : m_level{level}
    , m_sink{std::move(sink)}
{
}

void Logger::SetLevel(LogLevel_e level) noexcept
{
    m_level.store(level, std::memory_order_relaxed);
}

LogLevel_e Logger::GetLevel() const noexcept
{
    return m_level.load(std::memory_order_relaxed);
}

bool Logger::IsEnabled(LogLevel_e level) const noexcept
{
    return level >= GetLevel();
}

Logger::Sink Logger::SetSink(Sink sink) noexcept
{
    const auto lock = std::scoped_lock{m_mutex};
    m_sink.swap(sink);
    return sink;
}

void Logger::WriteToConsole(const LogEntry_s& entry)
{
    auto line = FormatLine(entry);
    line += '\n';

    auto* const stream = entry.level >= LogLevel_e::Warning ? stderr : stdout;
    std::fwrite(line.data(), 1, line.size(), stream);
    std::fflush(stream);
}

std::string Logger::FormatLine(const LogEntry_s& entry)
{
    const auto time = std::chrono::floor<std::chrono::milliseconds>(entry.time);
    auto line = std::format("{:%FT%T}Z {:<7} {}", time, GetLevelName(entry.level), entry.message);
    if (entry.location)
    {
        std::format_to(std::back_inserter(line), " [{}:{}]", GetFileName(entry.location->file_name()), entry.location->line());
    }

    return line;
}

void Logger::Write(LogLevel_e level, std::optional<std::source_location> location, std::string_view message)
{
    const auto lock = std::scoped_lock{m_mutex};
    if (!m_sink)
    {
        return;
    }

    // The time is read under the lock, so times in the output only go backwards if the wall clock does.
    m_sink(LogEntry_s{.level = level, .time = std::chrono::system_clock::now(), .location = location, .message = message});
}
