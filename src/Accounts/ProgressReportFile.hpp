#pragma once

#include "ProgressReport_s.hpp"

// The first report of a run starts the file afresh.
class ProgressReportFile
{
public:
    explicit ProgressReportFile(std::filesystem::path path);

    void Write(const ProgressReport_s& report, std::chrono::system_clock::time_point time);
    [[nodiscard]] const std::filesystem::path& GetPath() const;

    [[nodiscard]] static std::string Format(const ProgressReport_s& report, std::chrono::system_clock::time_point time);
    // On one line, for the log.
    [[nodiscard]] static std::string Summarize(const ProgressReport_s& report);

private:
    std::filesystem::path m_path;
    bool m_started = false;
};
