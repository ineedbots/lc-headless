#pragma once

// Case conversion and comparison operate on ASCII bytes.
class StringUtils
{
public:
    // The "C" locale's whitespace, as std::isspace has it.
    static constexpr auto WHITESPACE = " \t\n\v\f\r"sv;

    StringUtils() = delete;

    [[nodiscard]] static char ToLowerChar(char character);
    [[nodiscard]] static std::string ToLower(std::string_view text);
    [[nodiscard]] static bool EqualsIgnoringCase(std::string_view left, std::string_view right);
    [[nodiscard]] static std::string_view Trim(std::string_view text, std::string_view characters = WHITESPACE);
    [[nodiscard]] static std::string_view TrimEnd(std::string_view text, std::string_view characters = WHITESPACE);
    [[nodiscard]] static std::string TrimTrailingNewlines(std::string text);
    // The first word and the trimmed rest; both empty for blank text.
    [[nodiscard]] static std::pair<std::string_view, std::string_view> SplitFirstWord(std::string_view text);
    // Runs of whitespace separate words, so none is empty.
    [[nodiscard]] static std::vector<std::string_view> SplitWords(std::string_view text);
    [[nodiscard]] static std::string Join(std::span<const std::string> parts, std::string_view separator);
    // Returns -1 for a non-hexadecimal byte.
    [[nodiscard]] static int HexDigitValue(unsigned char digit);
    [[nodiscard]] static bool IsIdentifierAscii(std::string_view text);
    [[nodiscard]] static bool IsUtf8(std::string_view text);
    [[nodiscard]] static bool IsPrintableAscii(std::string_view text);
};
