#pragma once

#include "../Cache/GameCache_s.hpp"
#include "../Console/Logger.hpp"
#include "../Game/State/GameState_s.hpp"

#include <filesystem>
#include <memory>
#include <string>

// Writes a bank's contents whenever one opens: <directory>/<account>.jsonl gains a line. Deliberately
// open-only: deposits and withdrawals made while the bank stays open aren't re-read, so each entry is the
// bank as it was when it opened. The last line is the bank's current contents.
class BankLogger
{
public:
    BankLogger(const GameCache_s& cache, std::shared_ptr<Logger> logger, std::string accountName, std::filesystem::path directory);

    // Called every step while in game. Records on the closed -> open edge only.
    void Step(const GameState_s& state);

    [[nodiscard]] const std::filesystem::path& GetDirectory() const { return m_directory; }

private:
    void Log(const GameState_s& state);

    const GameCache_s& m_cache;
    std::shared_ptr<Logger> m_logger;
    std::string m_accountName;
    std::filesystem::path m_directory;
    bool m_wasOpen = false;
    // So a folder that can't be written is reported once, not on every open.
    bool m_writeFailed = false;
};
