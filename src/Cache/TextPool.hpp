#pragma once

// The types' text, with each distinct string stored once. The views it hands out stay valid as long as
// the pool lives, after a move too, because the text sits in chunks that never move.
class TextPool
{
public:
    static constexpr u16 NO_OPTION = 0;
    static constexpr std::size_t CHUNK_SIZE = 64 * 1024;

    TextPool();

    TextPool(const TextPool&) = delete;
    TextPool& operator=(const TextPool&) = delete;
    TextPool(TextPool&&) noexcept = default;
    TextPool& operator=(TextPool&&) noexcept = default;

    [[nodiscard]] std::string_view Intern(std::string_view text);
    // The option's id in the option table. Empty text is NO_OPTION.
    [[nodiscard]] u16 InternOption(std::string_view text);
    [[nodiscard]] std::string_view GetOption(u16 id) const;
    // Counting NO_OPTION.
    [[nodiscard]] std::size_t GetOptionCount() const;
    // Frees the lookup tables that interning needs. Nothing can be interned afterward.
    void FinishInterning();

private:
    std::vector<std::unique_ptr<char[]>> m_chunks;
    std::size_t m_chunkUsed = 0;
    std::vector<std::string_view> m_options;
    std::unordered_set<std::string_view> m_strings;
    std::unordered_map<std::string_view, u16> m_optionIds;
    bool m_finished = false;
};
