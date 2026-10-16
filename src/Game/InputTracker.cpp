#include "pch.hpp"
#include "InputTracker.hpp"

namespace
{
    constexpr auto POSITION_Y_SHIFT = 10;
    constexpr auto POSITION_EVENT_SIZE = std::size_t{5};
    constexpr auto PLAIN_EVENT_SIZE = std::size_t{2};
    // Clicks land in the middle half of the game view, as a player's mostly do.
    constexpr auto CLICK_MARGIN_X = InputTracker::VIEW_WIDTH / 4;
    constexpr auto CLICK_MARGIN_Y = InputTracker::VIEW_HEIGHT / 4;
    // In delta units: the press follows the move, and the release the press, after about a tenth of a second.
    constexpr auto MIN_PRESS_DELAY = 4;
    constexpr auto MAX_PRESS_DELAY = 12;
    constexpr auto MIN_RELEASE_DELAY = 6;
    constexpr auto MAX_RELEASE_DELAY = 14;
}

InputTracker::InputTracker()
    : m_random{std::random_device{}()}
{
}

bool InputTracker::IsActive() const
{
    return m_active;
}

void InputTracker::Start(Clock::time_point now)
{
    m_active = true;
    m_recordedAction = false;
    m_report.clear();
    m_fullReports.clear();
    m_lastEvent = now;
}

void InputTracker::RecordClick(Clock::time_point now)
{
    if (!m_active)
    {
        return;
    }

    m_recordedAction = true;
    RecordMove(now);

    const auto pressDelta = TakeDelta(After(MIN_PRESS_DELAY, MAX_PRESS_DELAY));
    PutPositioned(LEFT_PRESS, pressDelta, m_x, m_y);

    const auto releaseDelta = TakeDelta(After(MIN_RELEASE_DELAY, MAX_RELEASE_DELAY));
    PutEvent(LEFT_RELEASE, releaseDelta);
}

std::vector<std::vector<u8>> InputTracker::TakeFullReports()
{
    return std::exchange(m_fullReports, {});
}

std::vector<std::vector<u8>> InputTracker::Finish(Clock::time_point now)
{
    if (!m_active)
    {
        return {};
    }

    if (!m_recordedAction)
    {
        RecordMove(now);
    }

    auto reports = TakeFullReports();
    if (!m_report.empty())
    {
        reports.push_back(std::exchange(m_report, {}));
    }

    m_active = false;
    return reports;
}

// The time since the last event, in delta units, which then counts from here. An event the tracker places a
// little after the last one can be ahead of the clock, so a later one is never counted from before it.
u8 InputTracker::TakeDelta(Clock::time_point at)
{
    const auto elapsed = std::max(at - m_lastEvent, Clock::duration::zero());
    m_lastEvent = std::max(at, m_lastEvent);
    return static_cast<u8>(std::min<s64>(elapsed / DELTA_UNIT, MAX_DELTA));
}

InputTracker::Clock::time_point InputTracker::After(s32 minDelta, s32 maxDelta)
{
    auto distribution = std::uniform_int_distribution<s32>{minDelta, maxDelta};
    return m_lastEvent + distribution(m_random) * DELTA_UNIT;
}

// As the webclient's ensureCapacity: a report that an event would bring to MAX_REPORT_SIZE is set aside first.
void InputTracker::Reserve(std::size_t size)
{
    if (m_report.size() + size < MAX_REPORT_SIZE)
    {
        return;
    }

    m_fullReports.push_back(std::exchange(m_report, {}));
}

void InputTracker::PutPositioned(u8 code, u8 delta, s32 x, s32 y)
{
    Reserve(POSITION_EVENT_SIZE);

    const auto position = static_cast<u32>(x + (y << POSITION_Y_SHIFT));
    m_report.insert(m_report.end(), {code, delta, static_cast<u8>(position >> 16), static_cast<u8>(position >> 8), static_cast<u8>(position)});
}

void InputTracker::PutEvent(u8 code, u8 delta)
{
    Reserve(PLAIN_EVENT_SIZE);
    m_report.insert(m_report.end(), {code, delta});
}

void InputTracker::RecordMove(Clock::time_point now)
{
    auto xs = std::uniform_int_distribution<s32>{VIEW_X + CLICK_MARGIN_X, VIEW_X + VIEW_WIDTH - CLICK_MARGIN_X};
    auto ys = std::uniform_int_distribution<s32>{VIEW_Y + CLICK_MARGIN_Y, VIEW_Y + VIEW_HEIGHT - CLICK_MARGIN_Y};
    m_x = xs(m_random);
    m_y = ys(m_random);
    PutPositioned(ABSOLUTE_MOVE, TakeDelta(now), m_x, m_y);
}
