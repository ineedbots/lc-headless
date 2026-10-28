#pragma once

struct ApplicationResult_s
{
    int exitCode;
    std::string output;
};

// Runs the shipped executable with isolated working files and closed stdin. A timeout kills and reaps
// the child before throwing, so a broken application cannot leave a background client behind.
[[nodiscard]] ApplicationResult_s RunApplication(const std::filesystem::path& directory, const std::vector<std::string>& arguments,
                                               std::string_view input = "");
