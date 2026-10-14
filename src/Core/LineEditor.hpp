#pragma once

// Takes a VT100 terminal's keys in raw mode and gives the escape codes that redraw the prompt line.
// A line wider than the terminal isn't redrawn cleanly.
class LineEditor
{
public:
    static constexpr auto PROMPT = "> "sv;
    static constexpr std::size_t MAX_HISTORY = 100;

    // An escape sequence or character split between calls waits for the rest.
    [[nodiscard]] std::vector<std::string> Feed(std::string_view bytes);
    [[nodiscard]] std::string Render() const;
    [[nodiscard]] static std::string RenderEntered(std::string_view line);
    [[nodiscard]] static std::string_view Erase();

    [[nodiscard]] const std::string& GetLine() const;
    // In bytes.
    [[nodiscard]] std::size_t GetCursor() const;

private:
    // Zero when it needs more bytes first.
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
