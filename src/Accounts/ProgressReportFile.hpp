#pragma once

#include "../Script/ProgressReport_s.hpp"

// One account's progress reports, appended to a file as tables. The first report of a run starts the file
// afresh, creating its folder if need be.
class ProgressReportFile
{
public:
    explicit ProgressReportFile(std::filesystem::path path);

    // Throws std::runtime_error when the file can't be written.
    void Write(const ProgressReport_s& report, std::chrono::system_clock::time_point time);
    [[nodiscard]] const std::filesystem::path& GetPath() const;

    [[nodiscard]] static std::string Format(const ProgressReport_s& report, std::chrono::system_clock::time_point time);
    // The rows on one line, for the log.
    [[nodiscard]] static std::string Summarize(const ProgressReport_s& report);

private:
    std::filesystem::path m_path;
    bool m_started = false;
};
