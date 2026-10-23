#pragma once

enum class StopRequest_e : u8
{
    None,
    Script,
    Account,
};

// settings_store.save(): a value for script.settings[name][key] in the account file.
struct SettingSave_s
{
    std::string name;
    std::string key;
    std::string valueJson;
};

// What a script asks of its host rather than of the game: to stop, to relog, to save a setting, and when it
// last made progress.
class ScriptControl
{
public:
    // The longest relog() a script may ask for.
    static constexpr auto MAX_RELOG = std::chrono::seconds{24 * 60 * 60};

    // The strongest request is kept until it's taken.
    void RequestStop(StopRequest_e request);
    [[nodiscard]] StopRequest_e TakeStopRequest();
    // relog(): log out, wait the delay, and log back in, with the script kept loaded.
    void RequestRelog(std::chrono::seconds delay);
    [[nodiscard]] std::optional<std::chrono::seconds> TakeRelogRequest();
    // Saves are kept in order until they're taken.
    void RequestSettingSave(SettingSave_s save);
    [[nodiscard]] std::vector<SettingSave_s> TakeSettingSaves();

    // The time of the host's current step, in milliseconds on its clock. Waits measure from it, so a test
    // that steps the host with made-up times controls them too.
    void SetStepTime(s64 milliseconds);
    [[nodiscard]] s64 GetStepTime() const;
    // The script reports progress the stall guard can't see, such as a finished trade.
    void NoteProgress();
    [[nodiscard]] std::optional<s64> GetLastProgress() const;

private:
    StopRequest_e m_stopRequest = StopRequest_e::None;
    std::optional<std::chrono::seconds> m_relogRequest;
    std::vector<SettingSave_s> m_settingSaves;
    s64 m_stepTime = 0;
    std::optional<s64> m_lastProgress;
};
