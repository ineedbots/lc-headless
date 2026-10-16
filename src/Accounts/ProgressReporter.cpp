#include "pch.hpp"
#include "ProgressReporter.hpp"

#include "../Console/Logger.hpp"
#include "../Script/Host/ScriptHost.hpp"
#include "ProgressReportFile.hpp"
#include "ProgressReport_s.hpp"

ProgressReporter::ProgressReporter(std::chrono::minutes interval, std::filesystem::path file, std::shared_ptr<Logger> logger)
    : m_interval{interval}
    , m_file{std::move(file)}
    , m_logger{std::move(logger)}
{
}

void ProgressReporter::Step(Clock::time_point now, ScriptHost& script)
{
    if (m_interval <= std::chrono::minutes::zero() || !script.IsActive())
    {
        return;
    }

    if (!m_nextReport)
    {
        const auto started = script.GetStartTime();
        assert(started && "An active script has started");
        m_nextReport = *started + m_interval;
    }

    if (now < *m_nextReport)
    {
        return;
    }

    m_nextReport = now + m_interval;

    if (const auto report = script.RunProgressReport(now))
    {
        Write(*report);
    }
}

void ProgressReporter::Write(const ProgressReport_s& report)
{
    m_logger->Info("Progress: {}", ProgressReportFile::Summarize(report));

    try
    {
        m_file.Write(report, std::chrono::system_clock::now());
    }
    catch (const std::exception& e)
    {
        m_logger->Warning("The progress report wasn't saved: {}", e.what());
    }
}
