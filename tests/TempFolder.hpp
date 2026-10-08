#pragma once

// A uniquely named folder under the system temp directory, removed with everything in it when destroyed.
class TempFolder
{
public:
    explicit TempFolder(std::string_view prefix);
    ~TempFolder();

    TempFolder(const TempFolder&) = delete;
    TempFolder& operator=(const TempFolder&) = delete;

    [[nodiscard]] const std::filesystem::path& GetPath() const;
    void WriteFile(const std::filesystem::path& relativePath, std::string_view text) const;
    // Replaces an existing file and moves its modification time a second on, so a file watcher sees the
    // change however coarse the file system's clock is.
    void RewriteFile(const std::filesystem::path& relativePath, std::string_view text) const;

private:
    std::filesystem::path m_path;
};
