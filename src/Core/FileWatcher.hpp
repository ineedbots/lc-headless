#pragma once

// Notices when any of a set of files changes. A change counts once the files' modification times have
// held still from one check to the next, so a save made in several writes is seen once. A missing file
// counts as a state of its own, so deleting or creating one is a change too.
class FileWatcher
{
public:
    explicit FileWatcher(std::vector<std::filesystem::path> files);

    // True once a change has settled; that change then counts as seen.
    [[nodiscard]] bool Check();
    [[nodiscard]] const std::vector<std::filesystem::path>& GetFiles() const;

private:
    using Times = std::vector<std::optional<std::filesystem::file_time_type>>;

    [[nodiscard]] Times ReadTimes() const;

    std::vector<std::filesystem::path> m_files;
    Times m_seen;
    std::optional<Times> m_pending;
};
