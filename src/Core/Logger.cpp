#include "pch.hpp"
#include "Logger.hpp"

#ifdef _WIN32
#include <Windows.h>
#else
#include <unistd.h>
#endif

namespace
{
    constexpr auto COLOR_RESET = "\x1B[0m"sv;

    // Empty for the terminal's own color.
    std::string_view GetLevelColor(LogLevel_e level)
    {
        switch (level)
        {
        case LogLevel_e::Verbose:
            return "\x1B[36m";
        case LogLevel_e::Info:
            return {};
        case LogLevel_e::Warning:
            return "\x1B[33m";
        case LogLevel_e::Error:
            return "\x1B[31m";
        }

        return {};
    }

#ifdef _WIN32
    bool CanColor(std::FILE* stream)
    {
        // https://no-color.org: set and not empty. The size counts the terminating null.
        if (GetEnvironmentVariableA("NO_COLOR", nullptr, 0) > 1)
        {
            return false;
        }

        const auto handle = GetStdHandle(stream == stderr ? STD_ERROR_HANDLE : STD_OUTPUT_HANDLE);
        auto mode = DWORD{0};
        if (!GetConsoleMode(handle, &mode))
        {
            return false;
        }

        return (mode & ENABLE_VIRTUAL_TERMINAL_PROCESSING) != 0 || SetConsoleMode(handle, mode | ENABLE_VIRTUAL_TERMINAL_PROCESSING) != 0;
    }
#else
    bool CanColor(std::FILE* stream)
    {
        const auto* const noColor = std::getenv("NO_COLOR");
        const auto* const term = std::getenv("TERM");
        return (noColor == nullptr || *noColor == '\0') && isatty(fileno(stream)) != 0 && (term == nullptr || std::string_view{term} != "dumb");
    }
#endif

    void WriteConsoleLine(std::FILE* stream, std::string line)
    {
        line += '\n';
        std::fwrite(line.data(), 1, line.size(), stream);
        std::fflush(stream);
    }

    // Checked once per stream, the first time something is written to the console.
    bool CanColorStream(std::FILE* stream)
    {
        static const auto output = CanColor(stdout);
        static const auto error = CanColor(stderr);
        return stream == stderr ? error : output;
    }
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

    struct DefaultLogger_s
    {
        std::mutex mutex;
        std::shared_ptr<Logger> logger = std::make_shared<Logger>();
    };

    // A function-local static, so the default exists even when another file's static
    // initializer asks for it before this file's globals would have been initialized.
    DefaultLogger_s& GetDefaultLogger()
    {
        static auto defaultLogger = DefaultLogger_s{};
        return defaultLogger;
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
    return level >= GetLevel() && (m_parent == nullptr || m_parent->IsEnabled(level));
}

Logger::Sink Logger::SetSink(Sink sink) noexcept
{
    const auto lock = std::scoped_lock{m_mutex};
    m_sink.swap(sink);
    return sink;
}

const std::string& Logger::GetSource() const noexcept
{
    return m_source;
}

std::shared_ptr<Logger> Logger::CreateNamed(std::shared_ptr<Logger> parent, std::string source)
{
    assert(parent && "A named logger needs a parent");
    auto named = std::make_shared<Logger>(LogLevel_e::Verbose, nullptr);
    named->m_parent = std::move(parent);
    named->m_source = std::move(source);
    return named;
}

std::shared_ptr<Logger> Logger::GetDefault() noexcept
{
    auto& defaultLogger = GetDefaultLogger();
    const auto lock = std::scoped_lock{defaultLogger.mutex};
    return defaultLogger.logger;
}

std::shared_ptr<Logger> Logger::SetDefault(std::shared_ptr<Logger> logger) noexcept
{
    assert(logger && "The default logger can't be null");

    auto& defaultLogger = GetDefaultLogger();
    const auto lock = std::scoped_lock{defaultLogger.mutex};
    defaultLogger.logger.swap(logger);
    return logger;
}

void Logger::WriteToConsole(const LogEntry_s& entry)
{
    WriteConsoleLine(GetConsoleStream(entry.level), FormatConsoleLine(entry));
}

void Logger::WritePlainToConsole(const LogEntry_s& entry)
{
    WriteConsoleLine(GetConsoleStream(entry.level), FormatLine(entry));
}

std::string Logger::FormatColoredLine(const LogEntry_s& entry)
{
    const auto color = GetLevelColor(entry.level);
    if (color.empty())
    {
        return FormatLine(entry);
    }

    auto line = std::string{color};
    line += FormatLine(entry);
    line += COLOR_RESET;
    return line;
}

std::string Logger::FormatConsoleLine(const LogEntry_s& entry)
{
    return CanColorStream(GetConsoleStream(entry.level)) ? FormatColoredLine(entry) : FormatLine(entry);
}

std::FILE* Logger::GetConsoleStream(LogLevel_e level)
{
    return level >= LogLevel_e::Warning ? stderr : stdout;
}

std::string Logger::FormatLine(const LogEntry_s& entry)
{
    const auto time = std::chrono::floor<std::chrono::milliseconds>(entry.time);
    auto line = std::format("{:%FT%T}Z {:<7} ", time, GetLevelName(entry.level));
    if (!entry.source.empty())
    {
        std::format_to(std::back_inserter(line), "[{}] ", entry.source);
    }

    line += entry.message;
    if (entry.location)
    {
        std::format_to(std::back_inserter(line), " [{}:{}]", GetFileName(entry.location->file_name()), entry.location->line());
    }

    return line;
}

void Logger::Write(LogLevel_e level, std::optional<std::source_location> location, std::string_view message)
{
    Deliver(level, location, message, m_source);
}

void Logger::Deliver(LogLevel_e level, std::optional<std::source_location> location, std::string_view message, std::string_view source)
{
    if (m_parent)
    {
        m_parent->Deliver(level, location, message, source);
        return;
    }

    const auto lock = std::scoped_lock{m_mutex};
    if (!m_sink)
    {
        return;
    }

    // The time is read under the lock, so times in the output only go backwards if the wall clock does.
    m_sink(LogEntry_s{.level = level, .time = std::chrono::system_clock::now(), .location = location, .message = message, .source = source});
}
