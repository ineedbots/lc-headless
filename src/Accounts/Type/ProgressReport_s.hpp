#pragma once

#include <nlohmann/json.hpp>

// What on_progress_report returned, as text in the script's order.
struct ProgressReport_s
{
    std::chrono::seconds runTime{};
    std::vector<std::pair<std::string, std::string>> rows;
};

inline void to_json(nlohmann::json& value, const ProgressReport_s& report)
{
    value = {{"runTimeSeconds", report.runTime.count()}, {"rows", report.rows}};
}
