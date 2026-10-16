#include "pch.hpp"
#include "ConsoleInput.hpp"

#include "LineEditor.hpp"
#include "Terminal.hpp"

#include <iostream>

namespace
{
    // How long the line reader waits after a console read that ended without a line, so one that keeps
    // ending at once doesn't spin.
    constexpr auto READ_RETRY = 250ms;
    // Some writers, such as PowerShell's pipes, start UTF-8 input with one.
    constexpr auto BYTE_ORDER_MARK = "\xEF\xBB\xBF"sv;
    constexpr auto CTRL_C = '\x03';

    void Write(std::FILE* stream, std::string_view text)
    {
        std::fwrite(text.data(), 1, text.size(), stream);
        std::fflush(stream);
    }
}

std::shared_ptr<ConsoleInput> ConsoleInput::ReadStdin()
{
    auto input = std::make_shared<ConsoleInput>();
    if (auto restore = Terminal::EnterRawMode())
    {
        input->m_restoreTerminal = std::move(restore);
        input->m_editor.emplace();
        Write(stdout, input->m_editor->Render());
        std::thread{[input]
        {
            input->ReadKeys();
        }}.detach();

        return input;
    }

    std::thread{[input]
    {
        input->ReadLines();
    }}.detach();

    return input;
}

void ConsoleInput::Push(std::string line)
{
    {
        const auto lock = std::lock_guard{m_mutex};
        m_lines.push_back(std::move(line));
    }

    m_arrived.notify_all();
}

std::vector<std::string> ConsoleInput::TakeLines()
{
    const auto lock = std::lock_guard{m_mutex};
    return std::exchange(m_lines, {});
}

void ConsoleInput::WaitUntil(Clock::time_point time)
{
    auto lock = std::unique_lock{m_mutex};
    m_arrived.wait_until(lock, time, [this]
    {
        return !m_lines.empty();
    });
}

bool ConsoleInput::IsInteractive() const
{
    return m_editor.has_value();
}

void ConsoleInput::Print(std::FILE* stream, std::string_view text)
{
    const auto lock = std::lock_guard{m_outputMutex};
    const auto prompting = m_editor && !m_closed;
    if (prompting)
    {
        Write(stdout, LineEditor::Erase());
    }

    auto line = std::string{text};
    line += '\n';
    Write(stream, line);

    if (prompting)
    {
        Write(stdout, m_editor->Render());
    }
}

void ConsoleInput::Close()
{
    const auto lock = std::lock_guard{m_outputMutex};

    if (!m_editor || m_closed)
    {
        return;
    }

    m_closed = true;
    Write(stdout, LineEditor::Erase());
    m_restoreTerminal();
}

void ConsoleInput::ReadLines()
{
    const auto console = Terminal::IsInputConsole();
    auto line = std::string{};
    auto first = true;
    while (true)
    {
        if (std::getline(std::cin, line))
        {
            if (std::exchange(first, false) && line.starts_with(BYTE_ORDER_MARK))
            {
                line.erase(0, BYTE_ORDER_MARK.size());
            }

            if (line.ends_with('\r'))
            {
                line.pop_back();
            }

            Push(std::move(line));
            continue;
        }

        // Piped input has ended for good. At the console, Ctrl+C and Ctrl+Z end a read as the end of the
        // input does, and the next read waits for a line again.
        if (!console)
        {
            return;
        }

        std::cin.clear();
        std::clearerr(stdin);
        std::this_thread::sleep_for(READ_RETRY);
    }
}

void ConsoleInput::ReadKeys()
{
    while (true)
    {
        const auto bytes = Terminal::ReadKeys();
        if (!bytes)
        {
            return;
        }

        auto entered = std::vector<std::string>{};
        {
            const auto lock = std::lock_guard{m_outputMutex};

            if (m_closed)
            {
                return;
            }

            entered = m_editor->Feed(*bytes);

            auto text = std::string{};
            for (const auto& line : entered)
            {
                text += LineEditor::RenderEntered(line);
            }

            text += m_editor->Render();
            Write(stdout, text);
        }

        for (auto& line : entered)
        {
            Push(std::move(line));
        }

        // A terminal normally turns Ctrl+C into a signal before it's read, but one that passes it on as
        // a key still interrupts. Escape sequences and UTF-8 never hold the byte.
        for (auto count = std::ranges::count(*bytes, CTRL_C); count > 0; --count)
        {
            std::raise(SIGINT);
        }
    }
}
