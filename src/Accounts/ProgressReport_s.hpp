#pragma once

// What on_progress_report returned, as text in the script's order.
struct ProgressReport_s
{
    std::chrono::seconds runTime{};
    std::vector<std::pair<std::string, std::string>> rows;
};
