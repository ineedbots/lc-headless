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

private:
    std::filesystem::path m_path;
};
