#pragma once

class JsonUtils
{
public:
    JsonUtils() = delete;

    // JSON string contents, without the surrounding quotes; preserves UTF-8 bytes.
    [[nodiscard]] static std::string EscapeString(std::string_view text);
};
