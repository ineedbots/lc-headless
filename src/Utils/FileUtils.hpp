#pragma once

class FileUtils
{
public:
    FileUtils() = delete;

    // Nullopt when the file can't be opened or read; each caller words its own error.
    [[nodiscard]] static std::optional<std::string> ReadText(const std::filesystem::path& path);
    // Through a temporary file beside it, so the file is never left half written.
    static void ReplaceFile(const std::filesystem::path& path, std::string_view text);
    // A relative path with no root and no "..", so joining it to a folder stays inside that folder.
    [[nodiscard]] static bool IsInsideFolder(const std::filesystem::path& relative);
};
