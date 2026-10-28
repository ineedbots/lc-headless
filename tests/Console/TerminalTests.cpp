#include "pch.hpp"
#include "Console/Terminal.hpp"
#include "Console/ConsoleInput.hpp"

#include <catch2/catch_test_macros.hpp>

#ifndef _WIN32
#include <fcntl.h>
#include <termios.h>
#include <unistd.h>

namespace
{
    class EnvironmentValue
    {
    public:
        EnvironmentValue(const char* name, const char* value) : m_name{name}
        {
            if (const auto* old = std::getenv(name)) m_old = old;
            if (value) setenv(name, value, 1);
            else unsetenv(name);
        }
        ~EnvironmentValue()
        {
            if (m_old) setenv(m_name, m_old->c_str(), 1);
            else unsetenv(m_name);
        }
    private:
        const char* m_name;
        std::optional<std::string> m_old;
    };

    // A private terminal, never the developer's controlling terminal. Restore both process streams
    // before assertions so Catch's output remains visible even when terminal behavior is wrong.
    class PseudoTerminal
    {
    public:
        PseudoTerminal()
        {
            std::fflush(stdout);
            try
            {
                master = posix_openpt(O_RDWR | O_NOCTTY);
                if (master < 0 || grantpt(master) != 0 || unlockpt(master) != 0) throw std::runtime_error{"Couldn't create pseudo-terminal"};
                m_slave = open(ptsname(master), O_RDWR | O_NOCTTY);
                m_input = dup(STDIN_FILENO);
                m_output = dup(STDOUT_FILENO);
                if (m_slave < 0 || m_input < 0 || m_output < 0 || dup2(m_slave, STDIN_FILENO) < 0 || dup2(m_slave, STDOUT_FILENO) < 0)
                    throw std::runtime_error{"Couldn't attach pseudo-terminal"};
            }
            catch (...)
            {
                Restore();
                throw;
            }
        }
        ~PseudoTerminal() { Restore(); }
        void CloseMaster()
        {
            close(master);
            master = -1;
        }
        int master = -1;
    private:
        void Restore()
        {
            std::fflush(stdout);
            if (m_input >= 0) { dup2(m_input, STDIN_FILENO); close(m_input); m_input = -1; }
            if (m_output >= 0) { dup2(m_output, STDOUT_FILENO); close(m_output); m_output = -1; }
            if (m_slave >= 0) { close(m_slave); m_slave = -1; }
            if (master >= 0) CloseMaster();
        }
        int m_slave = -1;
        int m_input = -1;
        int m_output = -1;
    };
}

TEST_CASE("Terminal raw mode reads keys and restores the original input settings", "[Terminal][TerminalCoverage]")
{
    const auto term = EnvironmentValue{"TERM", "xterm-256color"};
    auto original = termios{};
    auto raw = termios{};
    auto restored = termios{};
    auto attached = false;
    auto entered = false;
    auto success = false;
    auto written = ssize_t{0};
    auto received = std::optional<std::string>{};
    const auto keys = std::string{"hello \xc3\xa9\x1b[A"};
    {
        auto terminal = PseudoTerminal{};
        attached = Terminal::IsInputConsole();
        success = tcgetattr(STDIN_FILENO, &original) == 0;
        const auto restore = Terminal::EnterRawMode();
        entered = static_cast<bool>(restore);
        if (restore)
        {
            success = tcgetattr(STDIN_FILENO, &raw) == 0 && success;
            written = write(terminal.master, keys.data(), keys.size());
            if (written == static_cast<ssize_t>(keys.size())) received = Terminal::ReadKeys();
            restore();
            success = tcgetattr(STDIN_FILENO, &restored) == 0 && success;
        }
    }
    REQUIRE(attached);
    REQUIRE(entered);
    REQUIRE(success);
    CHECK((raw.c_lflag & (ICANON | ECHO)) == 0);
    CHECK(raw.c_cc[VMIN] == 1);
    CHECK(raw.c_cc[VTIME] == 0);
    CHECK(restored.c_lflag == original.c_lflag);
    CHECK(std::ranges::equal(restored.c_cc, original.c_cc));
    REQUIRE(written == static_cast<ssize_t>(keys.size()));
    CHECK(received == keys);
}

TEST_CASE("Terminal respects color opt outs and refuses raw mode for a dumb terminal", "[Terminal][TerminalCoverage]")
{
    auto colors = std::vector<bool>{};
    auto rawRejected = false;
    {
        auto terminal = PseudoTerminal{};
        const auto noColor = EnvironmentValue{"NO_COLOR", nullptr};
        const auto term = EnvironmentValue{"TERM", "xterm"};
        colors.push_back(Terminal::CanColor(stdout));
        {
            const auto empty = EnvironmentValue{"NO_COLOR", ""};
            colors.push_back(Terminal::CanColor(stdout));
        }
        {
            const auto disabled = EnvironmentValue{"NO_COLOR", "1"};
            colors.push_back(Terminal::CanColor(stdout));
        }
        {
            const auto dumb = EnvironmentValue{"TERM", "dumb"};
            colors.push_back(Terminal::CanColor(stdout));
            rawRejected = !Terminal::EnterRawMode();
        }
        {
            const auto absent = EnvironmentValue{"TERM", nullptr};
            colors.push_back(Terminal::CanColor(stdout));
        }
    }
    CHECK(colors == std::vector<bool>{true, true, false, false, true});
    CHECK(rawRejected);
}

TEST_CASE("Terminal reports the end of a closed pseudo-terminal", "[Terminal][TerminalCoverage]")
{
    const auto term = EnvironmentValue{"TERM", "xterm"};
    auto result = std::optional<std::string>{"unread"};
    auto entered = false;
    {
        auto terminal = PseudoTerminal{};
        const auto restore = Terminal::EnterRawMode();
        entered = static_cast<bool>(restore);
        terminal.CloseMaster();
        result = Terminal::ReadKeys();
        if (restore) restore();
    }
    CHECK(entered);
    CHECK_FALSE(result.has_value());
}

TEST_CASE("ConsoleInput edits terminal lines and releases its reader after closing", "[ConsoleInput][TerminalCoverage]")
{
    const auto term = EnvironmentValue{"TERM", "xterm"};
    auto interactive = false;
    auto released = false;
    auto lines = std::vector<std::string>{};
    auto original = termios{};
    auto restored = termios{};
    auto settingsRead = false;
    {
        auto terminal = PseudoTerminal{};
        settingsRead = tcgetattr(STDIN_FILENO, &original) == 0;
        auto input = ConsoleInput::ReadStdin();
        interactive = input->IsInteractive();
        const auto keys = std::string{"status\rhelx\x7fp\r"};
        const auto written = write(terminal.master, keys.data(), keys.size());
        if (written == static_cast<ssize_t>(keys.size()))
        {
            const auto deadline = std::chrono::steady_clock::now() + 5s;
            while (lines.size() < 2 && std::chrono::steady_clock::now() < deadline)
            {
                auto arrived = input->TakeLines();
                lines.insert(lines.end(), arrived.begin(), arrived.end());
                std::this_thread::sleep_for(1ms);
            }
        }
        input->Print(stdout, "above the prompt");
        input->Close();
        input->Close();
        input->Print(stdout, "after closing");
        settingsRead = tcgetattr(STDIN_FILENO, &restored) == 0 && settingsRead;
        const auto weak = std::weak_ptr<ConsoleInput>{input};
        input.reset();
        // Wakes the outstanding read, which sees m_closed before passing another key to the editor.
        const auto ignored = write(terminal.master, "ignored\n", 8);
        static_cast<void>(ignored);
        auto deadline = std::chrono::steady_clock::now() + 5s;
        while (!weak.expired() && std::chrono::steady_clock::now() < deadline) std::this_thread::sleep_for(1ms);
        if (!weak.expired())
        {
            terminal.CloseMaster();
            deadline = std::chrono::steady_clock::now() + 5s;
            while (!weak.expired() && std::chrono::steady_clock::now() < deadline) std::this_thread::sleep_for(1ms);
        }
        released = weak.expired();
    }
    CHECK(interactive);
    CHECK(lines == std::vector<std::string>{"status", "help"});
    CHECK(released);
    REQUIRE(settingsRead);
    CHECK(restored.c_lflag == original.c_lflag);
}
#endif
