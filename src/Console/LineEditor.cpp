#include "pch.hpp"
#include "LineEditor.hpp"

namespace
{
    constexpr auto KEY_ESCAPE = '\x1B';
    constexpr auto KEY_BACKSPACE = '\b';
    constexpr auto KEY_DELETE = '\x7F';
    constexpr auto KEY_CTRL_A = '\x01';
    constexpr auto KEY_CTRL_E = '\x05';
    constexpr auto KEY_CTRL_K = '\x0B';
    constexpr auto KEY_CTRL_U = '\x15';
    constexpr auto CLEAR_LINE = "\r\x1B[2K"sv;
    // An incomplete escape sequence this long is dropped rather than waited on.
    constexpr std::size_t MAX_ESCAPE = 16;

    bool IsContinuation(char byte)
    {
        return (static_cast<unsigned char>(byte) & 0xC0) == 0x80;
    }

    // Zero for a byte that can't start a character.
    std::size_t GetCharacterLength(char lead)
    {
        const auto byte = static_cast<unsigned char>(lead);
        if (byte < 0x80)
        {
            return 1;
        }

        if ((byte & 0xE0) == 0xC0)
        {
            return 2;
        }

        if ((byte & 0xF0) == 0xE0)
        {
            return 3;
        }

        if ((byte & 0xF8) == 0xF0)
        {
            return 4;
        }

        return 0;
    }

    // Counts each character as one column.
    std::size_t CountColumns(std::string_view text)
    {
        return static_cast<std::size_t>(std::ranges::count_if(text, [](char byte)
        {
            return !IsContinuation(byte);
        }));
    }
}

std::vector<std::string> LineEditor::Feed(std::string_view bytes)
{
    m_pending += bytes;

    auto entered = std::vector<std::string>{};
    while (!m_pending.empty())
    {
        const auto taken = HandleNext(entered);
        if (taken == 0)
        {
            break;
        }

        m_pending.erase(0, taken);
    }

    return entered;
}

std::string LineEditor::Render() const
{
    auto text = std::string{CLEAR_LINE};
    text += PROMPT;
    text += m_line;

    const auto behind = CountColumns(std::string_view{m_line}.substr(m_cursor));
    if (behind > 0)
    {
        std::format_to(std::back_inserter(text), "\x1B[{}D", behind);
    }

    return text;
}

std::string LineEditor::RenderEntered(std::string_view line)
{
    auto text = std::string{CLEAR_LINE};
    text += PROMPT;
    text += line;
    text += "\r\n";
    return text;
}

std::string_view LineEditor::Erase()
{
    return CLEAR_LINE;
}

const std::string& LineEditor::GetLine() const
{
    return m_line;
}

std::size_t LineEditor::GetCursor() const
{
    return m_cursor;
}

std::size_t LineEditor::HandleNext(std::vector<std::string>& entered)
{
    const auto key = m_pending.front();
    const auto afterReturn = std::exchange(m_afterReturn, false);
    switch (key)
    {
    case '\r':
        Enter(entered);
        m_afterReturn = true;
        return 1;
    case '\n':
        if (!afterReturn)
        {
            Enter(entered);
        }

        return 1;
    case KEY_BACKSPACE:
    case KEY_DELETE:
        Backspace();
        return 1;
    case KEY_CTRL_A:
        m_cursor = 0;
        return 1;
    case KEY_CTRL_E:
        m_cursor = m_line.size();
        return 1;
    case KEY_CTRL_K:
        m_line.erase(m_cursor);
        return 1;
    case KEY_CTRL_U:
        m_line.erase(0, m_cursor);
        m_cursor = 0;
        return 1;
    case KEY_ESCAPE:
        return HandleEscape();
    default:
        break;
    }

    // Other control keys, and a stray byte from the middle of a character, are dropped.
    const auto length = GetCharacterLength(key);
    if (static_cast<unsigned char>(key) < 0x20 || length == 0)
    {
        return 1;
    }

    if (m_pending.size() < length)
    {
        return 0;
    }

    Insert(std::string_view{m_pending}.substr(0, length));
    return length;
}

// CSI (ESC [) and SS3 (ESC O) sequences, which end at their first byte from @ to ~. Any other byte after
// an escape is handled as a key of its own, so a lone Escape or Alt with a key does nothing.
std::size_t LineEditor::HandleEscape()
{
    if (m_pending.size() < 2)
    {
        return 0;
    }

    if (m_pending[1] != '[' && m_pending[1] != 'O')
    {
        return 1;
    }

    for (auto end = std::size_t{2}; end < m_pending.size(); ++end)
    {
        const auto last = m_pending[end];
        if (last < '@' || last > '~')
        {
            continue;
        }

        const auto parameters = std::string_view{m_pending}.substr(2, end - 2);
        if (parameters.empty() && last == 'A')
        {
            if (m_historyIndex > 0)
            {
                ShowHistory(m_historyIndex - 1);
            }
        }
        else if (parameters.empty() && last == 'B')
        {
            if (m_historyIndex < m_history.size())
            {
                ShowHistory(m_historyIndex + 1);
            }
        }
        else if (parameters.empty() && last == 'C')
        {
            MoveRight();
        }
        else if (parameters.empty() && last == 'D')
        {
            MoveLeft();
        }
        else if ((parameters.empty() && last == 'H') || (last == '~' && (parameters == "1" || parameters == "7")))
        {
            m_cursor = 0;
        }
        else if ((parameters.empty() && last == 'F') || (last == '~' && (parameters == "4" || parameters == "8")))
        {
            m_cursor = m_line.size();
        }
        else if (last == '~' && parameters == "3")
        {
            Delete();
        }

        return end + 1;
    }

    return m_pending.size() >= MAX_ESCAPE ? m_pending.size() : 0;
}

void LineEditor::Enter(std::vector<std::string>& entered)
{
    auto line = std::exchange(m_line, {});
    m_cursor = 0;
    m_draft.clear();

    if (!line.empty() && (m_history.empty() || m_history.back() != line))
    {
        m_history.push_back(line);
        if (m_history.size() > MAX_HISTORY)
        {
            m_history.pop_front();
        }
    }

    m_historyIndex = m_history.size();
    entered.push_back(std::move(line));
}

void LineEditor::Insert(std::string_view character)
{
    m_line.insert(m_cursor, character);
    m_cursor += character.size();
}

void LineEditor::Backspace()
{
    if (m_cursor == 0)
    {
        return;
    }

    const auto end = m_cursor;
    MoveLeft();
    m_line.erase(m_cursor, end - m_cursor);
}

void LineEditor::Delete()
{
    if (m_cursor == m_line.size())
    {
        return;
    }

    const auto start = m_cursor;
    MoveRight();
    m_line.erase(start, m_cursor - start);
    m_cursor = start;
}

void LineEditor::MoveLeft()
{
    while (m_cursor > 0)
    {
        --m_cursor;
        if (!IsContinuation(m_line[m_cursor]))
        {
            return;
        }
    }
}

void LineEditor::MoveRight()
{
    while (m_cursor < m_line.size())
    {
        ++m_cursor;
        if (m_cursor == m_line.size() || !IsContinuation(m_line[m_cursor]))
        {
            return;
        }
    }
}

// Leaving the line being typed for an older one keeps it as the draft, which coming back down restores.
void LineEditor::ShowHistory(std::size_t index)
{
    if (m_historyIndex == m_history.size())
    {
        m_draft = m_line;
    }

    m_historyIndex = index;
    m_line = index == m_history.size() ? m_draft : m_history[index];
    m_cursor = m_line.size();
}
