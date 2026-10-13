#pragma once

// The line being typed at the console's prompt. It takes the keys as a VT100 terminal sends them, in raw
// mode, and gives the escape codes that draw the prompt line again. It handles UTF-8, the arrow keys, Home,
// End, Delete, Backspace, Ctrl+A, Ctrl+E, Ctrl+U and Ctrl+K, and Up and Down through the lines entered
// before. A line wider than the terminal isn't redrawn cleanly.
class LineEditor
{
public:
    static constexpr auto PROMPT = "> "sv;
    static constexpr std::size_t MAX_HISTORY = 100;

    // Takes what the terminal sent; an escape sequence or a character split between calls is kept until
    // the rest arrives. Returns the lines entered with Enter, oldest first.
    [[nodiscard]] std::vector<std::string> Feed(std::string_view bytes);
    // Draws the prompt and the line over the terminal's current line, leaving the cursor where it's editing.
    [[nodiscard]] std::string Render() const;
    // Draws a line that has been entered, and moves to the next terminal line, so it stays on screen.
    [[nodiscard]] static std::string RenderEntered(std::string_view line);
    // Erases the terminal's current line, leaving the cursor at its start.
    [[nodiscard]] static std::string_view Erase();

    [[nodiscard]] const std::string& GetLine() const;
    // The cursor's position in the line, in bytes.
    [[nodiscard]] std::size_t GetCursor() const;

private:
    // Handles the key or sequence at the start of m_pending, and returns how many bytes it took; zero when
    // it needs more bytes first.
    [[nodiscard]] std::size_t HandleNext(std::vector<std::string>& entered);
    [[nodiscard]] std::size_t HandleEscape();
    void Enter(std::vector<std::string>& entered);
    void Insert(std::string_view character);
    void Backspace();
    void Delete();
    void MoveLeft();
    void MoveRight();
    void ShowHistory(std::size_t index);

    std::string m_line;
    std::size_t m_cursor = 0;
    std::string m_pending;
    // A \r was the last key, so a \n straight after it is the same Enter.
    bool m_afterReturn = false;
    std::deque<std::string> m_history;
    // m_history.size() is the line being typed, which m_draft keeps while Up shows older ones.
    std::size_t m_historyIndex = 0;
    std::string m_draft;
};
