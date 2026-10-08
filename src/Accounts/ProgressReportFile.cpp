#include "pch.hpp"
#include "ProgressReportFile.hpp"

#include "../Script/ProgressReport_s.hpp"

namespace
{
    constexpr auto NAME_HEADING = "Name"sv;
    constexpr auto VALUE_HEADING = "Value"sv;

    // A cell is one line of the table.
    std::string ToCell(std::string_view text)
    {
        auto cell = std::string{text};
        std::ranges::replace(cell, '\n', ' ');
        std::ranges::replace(cell, '\r', ' ');
        return cell;
    }

    std::string FormatRunTime(std::chrono::seconds runTime)
    {
        const auto hours = std::chrono::floor<std::chrono::hours>(runTime);
        const auto minutes = std::chrono::floor<std::chrono::minutes>(runTime - hours);
        if (hours.count() > 0)
        {
            return std::format("{}h {}m", hours.count(), minutes.count());
        }

        if (minutes.count() > 0)
        {
            return std::format("{}m", minutes.count());
        }

        return std::format("{}s", runTime.count());
    }

    std::string FormatBorder(std::size_t nameWidth, std::size_t valueWidth)
    {
        return std::format("+{}+{}+\n", std::string(nameWidth + 2, '-'), std::string(valueWidth + 2, '-'));
    }

    std::string FormatRow(std::string_view name, std::string_view value, std::size_t nameWidth, std::size_t valueWidth)
    {
        return std::format("| {:<{}} | {:<{}} |\n", name, nameWidth, value, valueWidth);
    }
}

ProgressReportFile::ProgressReportFile(std::filesystem::path path)
    : m_path{std::move(path)}
{
}

void ProgressReportFile::Write(const ProgressReport_s& report, std::chrono::system_clock::time_point time)
{
    const auto folder = m_path.parent_path();
    auto error = std::error_code{};
    if (!folder.empty())
    {
        std::filesystem::create_directories(folder, error);
    }

    // A stream that failed to open ignores the writes, so one check covers opening and writing.
    const auto mode = m_started ? std::ios::binary | std::ios::app : std::ios::binary | std::ios::trunc;
    auto file = std::ofstream{m_path, mode};
    file << (m_started ? "\n" : "") << Format(report, time);
    file.flush();
    if (!file)
    {
        throw std::runtime_error{std::format("can't write {}{}", m_path.string(), error ? std::format(" ({})", error.message()) : "")};
    }

    m_started = true;
}

const std::filesystem::path& ProgressReportFile::GetPath() const
{
    return m_path;
}

std::string ProgressReportFile::Format(const ProgressReport_s& report, std::chrono::system_clock::time_point time)
{
    auto rows = std::vector<std::pair<std::string, std::string>>{};
    auto nameWidth = NAME_HEADING.size();
    auto valueWidth = VALUE_HEADING.size();
    for (const auto& [name, value] : report.rows)
    {
        auto& row = rows.emplace_back(ToCell(name), ToCell(value));
        nameWidth = std::max(nameWidth, row.first.size());
        valueWidth = std::max(valueWidth, row.second.size());
    }

    const auto border = FormatBorder(nameWidth, valueWidth);
    auto text = std::format("Progress at {:%FT%T}Z, {} after the script started\n", std::chrono::floor<std::chrono::seconds>(time), FormatRunTime(report.runTime));
    text += border;
    text += FormatRow(NAME_HEADING, VALUE_HEADING, nameWidth, valueWidth);
    text += border;
    for (const auto& [name, value] : rows)
    {
        text += FormatRow(name, value, nameWidth, valueWidth);
    }

    text += border;
    return text;
}

std::string ProgressReportFile::Summarize(const ProgressReport_s& report)
{
    if (report.rows.empty())
    {
        return "nothing to report";
    }

    auto text = std::string{};
    for (const auto& [name, value] : report.rows)
    {
        if (!text.empty())
        {
            text += ", ";
        }

        std::format_to(std::back_inserter(text), "{}: {}", ToCell(name), ToCell(value));
    }

    return text;
}
