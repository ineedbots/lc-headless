#pragma once

// The input report a 225 server asks for. It turns tracking on with ENABLE_TRACKING and off with FINISH_TRACKING,
// and logs out a player that sent no report for the window as idle. While tracking is on, each action records the
// mouse events a click makes, encoded as the webclient's InputTracking encodes them, and a window with no actions
// still reports one mouse move.
class InputTracker
{
public:
    using Clock = std::chrono::steady_clock;

    // The webclient sets a report aside to send before it reaches this size.
    static constexpr std::size_t MAX_REPORT_SIZE = 500;
    static constexpr u8 LEFT_PRESS = 2;
    static constexpr u8 LEFT_RELEASE = 4;
    static constexpr u8 ABSOLUTE_MOVE = 7;
    // Each event's delta counts this long since the one before, up to MAX_DELTA.
    static constexpr auto DELTA_UNIT = 10ms;
    static constexpr u8 MAX_DELTA = 250;
    // The game view's corner and size in the client's frame, which clicks land inside.
    static constexpr s32 VIEW_X = 8;
    static constexpr s32 VIEW_Y = 11;
    static constexpr s32 VIEW_WIDTH = 512;
    static constexpr s32 VIEW_HEIGHT = 334;

    InputTracker();

    [[nodiscard]] bool IsActive() const;
    void Start(Clock::time_point now);
    // A move to a point in the game view, a left press and a release, a little apart.
    void RecordClick(Clock::time_point now);
    // Reports that filled up while tracking, oldest first.
    [[nodiscard]] std::vector<std::vector<u8>> TakeFullReports();
    // Stops tracking and returns what's left to report, after any reports that filled up.
    [[nodiscard]] std::vector<std::vector<u8>> Finish(Clock::time_point now);

private:
    [[nodiscard]] u8 TakeDelta(Clock::time_point at);
    [[nodiscard]] Clock::time_point After(s32 minDelta, s32 maxDelta);
    void Reserve(std::size_t size);
    void PutPositioned(u8 code, u8 delta, s32 x, s32 y);
    void PutEvent(u8 code, u8 delta);
    void RecordMove(Clock::time_point now);

    bool m_active = false;
    bool m_recordedAction = false;
    std::vector<u8> m_report;
    std::vector<std::vector<u8>> m_fullReports;
    Clock::time_point m_lastEvent;
    s32 m_x = 0;
    s32 m_y = 0;
    std::mt19937 m_random;
};
