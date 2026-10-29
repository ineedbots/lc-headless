#include "pch.hpp"
#include "../Support/TempFile.hpp"
#include "../Support/TempFolder.hpp"

#include "Console/ConsoleInput.hpp"
#include "Console/LogFile.hpp"
#include "Console/LogFormatter.hpp"
#include "Console/LogSinks.hpp"
#include "Utils/FileUtils.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/generators/catch_generators.hpp>
#include <catch2/matchers/catch_matchers_string.hpp>

#ifdef _WIN32
#include <io.h>
#else
#include <unistd.h>
#endif

namespace
{
#ifdef _WIN32
    constexpr auto Duplicate = &_dup;
    constexpr auto Replace = &_dup2;
    constexpr auto Close = &_close;
    constexpr auto Descriptor = &_fileno;
#else
    constexpr auto Duplicate = &dup;
    constexpr auto Replace = &dup2;
    constexpr auto Close = &close;
    constexpr auto Descriptor = &fileno;
#endif

    // Restore the process stream before making assertions, including when a test throws.
    class StreamCapture
    {
    public:
        explicit StreamCapture(std::FILE* stream)
            : m_stream{stream}
            , m_file{MakeTempFile()}
        {
            if (!m_file)
            {
                throw std::runtime_error{"Can't create the output capture file"};
            }
            std::fflush(m_stream);
            m_saved = Duplicate(Descriptor(m_stream));
            if (m_saved < 0)
            {
                throw std::runtime_error{"Can't save the output stream"};
            }
            if (Replace(Descriptor(m_file.get()), Descriptor(m_stream)) < 0)
            {
                Close(m_saved);
                m_saved = -1;
                throw std::runtime_error{"Can't redirect the output stream"};
            }
        }

        ~StreamCapture()
        {
            Restore();
        }

        StreamCapture(const StreamCapture&) = delete;
        StreamCapture& operator=(const StreamCapture&) = delete;

        std::string Read()
        {
            Restore();
            std::rewind(m_file.get());
            auto text = std::string{};
            auto buffer = std::array<char, 1024>{};
            while (const auto size = std::fread(buffer.data(), 1, buffer.size(), m_file.get()))
            {
                text.append(buffer.data(), size);
            }
            // The Windows CRT can translate console newlines to CRLF.
            for (auto pos = text.find("\r\n"); pos != std::string::npos; pos = text.find("\r\n", pos))
            {
                text.erase(pos, 1);
            }
            return text;
        }

    private:
        void Restore()
        {
            if (m_saved >= 0)
            {
                std::fflush(m_stream);
                Replace(m_saved, Descriptor(m_stream));
                Close(m_saved);
                m_saved = -1;
            }
        }

        std::FILE* m_stream;
        std::unique_ptr<std::FILE, decltype(&std::fclose)> m_file;
        int m_saved = -1;
    };

    LogEntry_s Entry(LogLevel_e level, std::string_view message = "message", std::string_view source = "bot")
    {
        return {.level = level, .time = std::chrono::sys_days{2026y / std::chrono::October / 13}, .message = message, .source = source};
    }
}

TEST_CASE("LogSinks routes each severity to its console stream and optionally to a plain log file", "[LogSinkCoverage]")
{
    const auto level = GENERATE(LogLevel_e::Verbose, LogLevel_e::Info, LogLevel_e::Warning, LogLevel_e::Error);
    const auto raw = GENERATE(false, true);
    const auto withFile = GENERATE(false, true);
    const auto folder = TempFolder{"rs2004-log-sink-tests"};
    const auto path = folder.GetPath() / "run.log";
    auto file = withFile ? std::make_shared<LogFile>(path) : nullptr;
    auto sink = LogSinks::Make(file, nullptr, raw);
    auto output = StreamCapture{stdout};
    auto error = StreamCapture{stderr};
    const auto entry = Entry(level);
    sink(entry);
    const auto standardOutput = output.Read();
    const auto standardError = error.Read();
    const auto expected = (raw ? LogFormatter::FormatLine(entry) : ConsoleOutput::FormatLine(entry)) + '\n';
    CHECK(standardOutput == (level < LogLevel_e::Warning ? expected : ""));
    CHECK(standardError == (level >= LogLevel_e::Warning ? expected : ""));
    if (withFile)
    {
        // Read while the sink still owns the file, verifying every write is flushed.
        CHECK(FileUtils::ReadText(path) == LogFormatter::FormatLine(entry) + '\n');
    }
    else
    {
        CHECK_FALSE(std::filesystem::exists(path));
    }
}

TEST_CASE("LogSinks releases noninteractive input and falls back to ordinary console output", "[LogSinkCoverage]")
{
    const auto raw = GENERATE(false, true);
    auto console = std::make_shared<ConsoleInput>();
    REQUIRE_FALSE(console->IsInteractive());
    const auto weak = std::weak_ptr{console};
    auto sink = LogSinks::Make(nullptr, console, raw);
    console.reset();
    CHECK(weak.expired());

    auto output = StreamCapture{stdout};
    sink(Entry(LogLevel_e::Info));
    const auto text = output.Read();
    CHECK(text == "2026-10-13T00:00:00.000Z INFO    [bot] message\n");
}

TEST_CASE("LogSinks keeps its file alive until the sink is released", "[LogSinkCoverage]")
{
    const auto folder = TempFolder{"rs2004-log-sink-tests"};
    const auto path = folder.GetPath() / "run.log";
    auto file = std::make_shared<LogFile>(path);
    const auto weak = std::weak_ptr{file};
    auto sink = LogSinks::Make(file, nullptr, true);
    file.reset();
    CHECK_FALSE(weak.expired());

    auto output = StreamCapture{stdout};
    sink(Entry(LogLevel_e::Info, "still open"));
    const auto text = output.Read();
    CHECK(FileUtils::ReadText(path) == text);
    CHECK_THAT(text, Catch::Matchers::ContainsSubstring("[bot] still open\n"));
    sink = nullptr;
    CHECK(weak.expired());
}

TEST_CASE("LogSinks preserves file ordering while splitting console severities", "[LogSinkCoverage]")
{
    const auto folder = TempFolder{"rs2004-log-sink-tests"};
    const auto path = folder.GetPath() / "run.log";
    auto sink = LogSinks::Make(std::make_shared<LogFile>(path), nullptr, true);
    const auto entries = std::to_array<LogEntry_s>({Entry(LogLevel_e::Warning, "first"), Entry(LogLevel_e::Info, "second"), Entry(LogLevel_e::Error, "third")});
    auto output = StreamCapture{stdout};
    auto error = StreamCapture{stderr};
    for (const auto& entry : entries)
    {
        sink(entry);
    }
    const auto standardOutput = output.Read();
    const auto standardError = error.Read();
    const auto first = LogFormatter::FormatLine(entries[0]) + '\n';
    const auto second = LogFormatter::FormatLine(entries[1]) + '\n';
    const auto third = LogFormatter::FormatLine(entries[2]) + '\n';
    CHECK(standardOutput == second);
    CHECK(standardError == first + third);
    CHECK(FileUtils::ReadText(path) == first + second + third);
}

TEST_CASE("LogSinks integrates named loggers and applies filtering to both outputs", "[LogSinkCoverage]")
{
    const auto folder = TempFolder{"rs2004-log-sink-tests"};
    const auto path = folder.GetPath() / "run.log";
    auto logger = std::make_shared<Logger>(LogLevel_e::Warning, LogSinks::Make(std::make_shared<LogFile>(path), nullptr, true));
    auto named = Logger::CreateNamed(logger, "woodcutter");
    auto output = StreamCapture{stdout};
    auto error = StreamCapture{stderr};
    named->Info("filtered message");
    named->Warning("inventory full: {}", 28);
    named->Error("can't bank");
    const auto standardOutput = output.Read();
    const auto standardError = error.Read();
    CHECK(standardOutput.empty());
    CHECK_THAT(standardError, Catch::Matchers::ContainsSubstring("WARNING [woodcutter] inventory full: 28"));
    CHECK_THAT(standardError, Catch::Matchers::ContainsSubstring("ERROR   [woodcutter] can't bank"));
    CHECK_THAT(standardError, !Catch::Matchers::ContainsSubstring("filtered message"));
    CHECK(std::ranges::count(standardError, '\n') == 2);
    CHECK(FileUtils::ReadText(path) == standardError);
}
