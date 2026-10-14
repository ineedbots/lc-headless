#pragma once

// A change counts once modification times hold still between two checks, so a save made in several writes
// is seen once. A missing file counts as a state too, so deleting or creating one is a change.
class FileWatcher
{
public:
    explicit FileWatcher(std::vector<std::filesystem::path> files);

    // A change it reports counts as seen.
    [[nodiscard]] bool Check();
    [[nodiscard]] const std::vector<std::filesystem::path>& GetFiles() const;

private:
    using Times = std::vector<std::optional<std::filesystem::file_time_type>>;

    [[nodiscard]] Times ReadTimes() const;

    std::vector<std::filesystem::path> m_files;
    Times m_seen;
    std::optional<Times> m_pending;
};
