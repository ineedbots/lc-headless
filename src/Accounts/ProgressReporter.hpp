#pragma once

#include "../Console/Logger.hpp"
#include "../Script/Host/ScriptHost.hpp"
#include "ProgressReportFile.hpp"
#include "ProgressReport_s.hpp"

// When the script's on_progress_report is due, and where the report goes: the log, and the account's
// progress file. The first is due an interval after the script first started, and each after it an interval
// after the last; one that falls due while the script isn't active waits until it is.
class ProgressReporter
{
public:
    using Clock = std::chrono::steady_clock;

    // A zero interval turns reports off.
    ProgressReporter(std::chrono::minutes interval, std::filesystem::path file, std::shared_ptr<Logger> logger);

    void Step(Clock::time_point now, ScriptHost& script);

private:
    void Write(const ProgressReport_s& report);

    std::chrono::minutes m_interval;
    ProgressReportFile m_file;
    std::shared_ptr<Logger> m_logger;
    std::optional<Clock::time_point> m_nextReport;
};
