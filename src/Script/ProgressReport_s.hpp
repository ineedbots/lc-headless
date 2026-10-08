#pragma once

// What a script's on_progress_report returned, as text in the script's order, and how long the script had
// been running.
struct ProgressReport_s
{
    std::chrono::seconds runTime{};
    std::vector<std::pair<std::string, std::string>> rows;
};
