# Logger Design

Design and test plan for `Logger`, the log the client's classes write to. The application creates one at startup and shares it, through `std::shared_ptr`, with every class that logs. It has four levels, `Verbose`, `Info`, `Warning` and `Error`, and can be called from any thread, including IXWebSocket's I/O thread. Code style follows [CONVENTIONS.md](../CONVENTIONS.md). It builds on the project setup in [PacketDesign.md](PacketDesign.md) §7.5 and §8: the static library, Catch2, and the test presets. [PacketDesign.md](PacketDesign.md) and [WebSocketDesign.md](WebSocketDesign.md) log through it.

Reference sources:

- `rs2004-headless - Copy/headless-client/src/logger.hpp` / `.cpp`: the previous logger
- `rs2004-headless - Copy/headless-client/src/main.cpp`, `protocol.cpp`: how it was called

---

## 1. Decisions

| Topic | Decision |
|---|---|
| Shape | An ordinary class, `Logger`. Each instance has its own threshold and sink. `main` creates one console logger and passes it to every class that logs |
| Ownership | `std::shared_ptr<Logger>`. A class that logs takes one in its constructor and keeps it in `m_logger`. Ownership is genuinely shared (CONVENTIONS §8): the objects that log have unrelated lifetimes, and `WebSocketClient`'s I/O thread logs until the client's destructor joins it. The logger lives as long as its last user |
| Levels | `Verbose`, `Info`, `Warning` and `Error`, in increasing severity. A message is written when its level is at or above the logger's threshold. The threshold starts at `Info` unless the constructor is given another. `Error` is never filtered |
| Call style | `m_logger->Info("WebSocket connecting to {}", url)`. The format string converts to `LogFormat_s`, which holds a `std::format_string`, so it is checked at compile time as `std::format` checks its own |
| Source location | Debug builds record the call site with `std::source_location` and end the line with `[WebSocketClient.cpp:412]`. Release builds record nothing. The switch is `NDEBUG`, the same one `assert` uses, and the call syntax is the same in both |
| Cost when off | The level check is one relaxed atomic load, made before formatting. A filtered call formats nothing and allocates nothing |
| Threading | Callable from any thread. Each logger's mutex serializes its writes, so its lines never interleave and its sink doesn't have to be thread-safe |
| Failure | Logging never throws. Every logging function is `noexcept`, and a message that can't be formatted or written is dropped. That makes it safe in destructors, `noexcept` functions, `catch` blocks and I/O callbacks |
| Output | Each logger has one sink, a `std::function`. The default writes to the console: `Verbose` and `Info` to stdout, `Warning` and `Error` to stderr, flushed after every line. Tests give their logger a capture instead |
| Line format | `2026-10-05T18:34:12.345Z INFO    WebSocket open`: the UTC time to the millisecond, the level, then the message |

Rejected:

- **A process-wide logger with static functions.** No class would need a constructor parameter, but the threshold and sink would be global. Every test that checks logging would have to save and restore them, and two objects could never log to different places.
- **`Logger&` instead of `std::shared_ptr<Logger>`.** Every logger would have to outlive every object that uses it, by convention alone. `WebSocketClient`'s I/O thread logs until the client is destroyed, so getting that order wrong would be a use-after-free.
- **Wrapping spdlog.** It would fit behind the same interface, but four levels and a console sink don't justify a dependency.
- **Macros** (`LOG_INFO(...)`), which could add `__FILE__` and `__LINE__` or compile `Verbose` calls out of Release builds. CONVENTIONS §6 avoids macros, and `std::source_location` gives the call site without one. `Verbose` stays available in Release, which is the build run against the live server.
- **Source locations in Release builds too.** Every logging call would embed its source path, which is absolute and includes the user's home folder, in the shipped binary. Messages name their subsystem (§4), so Release logs stay readable without a location.
- **Local time.** It needs `std::chrono::current_zone`, which the minimum Linux standard libraries (libstdc++ 13, libc++ 17; see CONVENTIONS §4) don't provide. UTC times also compare directly with logs from another machine.

---

## 2. Layout

```
rs2004-headless/
├── docs/
│   └── LoggerDesign.md
├── src/
│   ├── main.cpp
│   └── Core/
│       ├── Logger.hpp
│       └── Logger.cpp
└── tests/
    ├── LogCapture.hpp
    ├── LogCapture.cpp
    └── Core/
        └── LoggerTests.cpp
```

- `LogLevel_e`, `LogEntry_s` and `LogFormat_s` live in `Logger.hpp`, the header of the class that owns them.
- `Logger` lives in `Core/`, because every subsystem uses it. A class that logs includes `../Core/Logger.hpp` in its header, because `Logger` appears in its constructor's prototype and its members, and again in its `.cpp` (CONVENTIONS §5).
- `pch.hpp` gains `<atomic>` and `<mutex>` for the logger's members, `<source_location>` and `<type_traits>` for `LogFormat_s`, and `<thread>` for the threading tests.
- `main.cpp` creates the logger and passes it to `Application`, which passes it on (see Usage).
- `LogCapture` is the test fixture every test file uses to check logging (§6.1). It sits at the root of `tests/` because it isn't tied to one subsystem.

---

## 3. Logger

### Interface

```cpp
#pragma once

enum class LogLevel_e : u8
{
    Verbose,
    Info,
    Warning,
    Error,
};

struct LogEntry_s
{
    LogLevel_e level;
    std::chrono::system_clock::time_point time;
    std::optional<std::source_location> location;
    std::string_view message;
};

template <typename... TArgs>
struct LogFormat_s
{
    // Implicit, so the format string converts at the call site, which is where
    // std::source_location::current() is evaluated. Only Debug builds take the location,
    // the same switch as assert, so a Release binary carries no source paths.
#ifdef NDEBUG
    template <typename T>
        requires std::convertible_to<const T&, std::string_view>
    consteval LogFormat_s(const T& formatText)
        : text{formatText}
    {
    }
#else
    template <typename T>
        requires std::convertible_to<const T&, std::string_view>
    consteval LogFormat_s(const T& formatText, std::source_location callSite = std::source_location::current())
        : text{formatText}
        , location{callSite}
    {
    }
#endif

    std::format_string<TArgs...> text;
    std::optional<std::source_location> location;
};

class Logger
{
public:
    using Sink = std::function<void(const LogEntry_s& entry)>;

    explicit Logger(LogLevel_e level = LogLevel_e::Info, Sink sink = WriteToConsole);

    template <typename... TArgs>
    void Verbose(LogFormat_s<std::type_identity_t<TArgs>...> format, TArgs&&... args) noexcept
    {
        Log(LogLevel_e::Verbose, format, std::forward<TArgs>(args)...);
    }

    template <typename... TArgs>
    void Info(LogFormat_s<std::type_identity_t<TArgs>...> format, TArgs&&... args) noexcept
    {
        Log(LogLevel_e::Info, format, std::forward<TArgs>(args)...);
    }

    template <typename... TArgs>
    void Warning(LogFormat_s<std::type_identity_t<TArgs>...> format, TArgs&&... args) noexcept
    {
        Log(LogLevel_e::Warning, format, std::forward<TArgs>(args)...);
    }

    template <typename... TArgs>
    void Error(LogFormat_s<std::type_identity_t<TArgs>...> format, TArgs&&... args) noexcept
    {
        Log(LogLevel_e::Error, format, std::forward<TArgs>(args)...);
    }

    template <typename... TArgs>
    void Log(LogLevel_e level, LogFormat_s<std::type_identity_t<TArgs>...> format, TArgs&&... args) noexcept
    {
        if (!IsEnabled(level))
        {
            return;
        }

        try
        {
            Write(level, format.location, std::format(format.text, std::forward<TArgs>(args)...));
        }
        catch (const std::exception&)
        {
            // Logging must never fail the caller, so a message that can't be formatted or written is dropped.
        }
    }

    void SetLevel(LogLevel_e level) noexcept;
    [[nodiscard]] LogLevel_e GetLevel() const noexcept;
    [[nodiscard]] bool IsEnabled(LogLevel_e level) const noexcept;

    Sink SetSink(Sink sink) noexcept;

    static void WriteToConsole(const LogEntry_s& entry);
    [[nodiscard]] static std::string FormatLine(const LogEntry_s& entry);

private:
    void Write(LogLevel_e level, std::optional<std::source_location> location, std::string_view message);

    std::atomic<LogLevel_e> m_level;
    std::mutex m_mutex;
    Sink m_sink;
};
```

- The five logging functions are templates, so they're defined in the header. Everything else is in `Logger.cpp`.
- They take `LogFormat_s` through `std::type_identity_t`, which keeps it out of template argument deduction. `TArgs` then comes only from the arguments, as it does for `std::format_string` itself.
- `Write` is private. The templates are the only way to log, so every message passes the level check and the `catch`.
- The constructor takes the starting threshold and sink, so `Logger{}` is a console logger at `Info`. It moves `sink` into `m_sink` (CONVENTIONS §8, sink parameters).
- `std::mutex` and `std::atomic` make `Logger` neither copyable nor movable, by the rule of zero. That suits shared ownership: there is one instance, and every user points to it.
- `WriteToConsole` and `FormatLine` are static, because neither depends on a logger's state. `WriteToConsole` is the default sink.
- `SetSink` isn't `[[nodiscard]]`, because discarding the old sink, for example to silence a logger with `SetSink(nullptr)`, is legitimate.

### Usage

A class that logs takes the logger in its constructor:

```cpp
class WebSocketClient
{
public:
    explicit WebSocketClient(std::shared_ptr<Logger> logger);

private:
    std::shared_ptr<Logger> m_logger;
};
```

```cpp
WebSocketClient::WebSocketClient(std::shared_ptr<Logger> logger)
    : m_logger{std::move(logger)}
{
    assert(m_logger && "WebSocketClient needs a logger");
}
```

and logs through it:

```cpp
m_logger->Info("WebSocket connecting to {}", options.url);
m_logger->Verbose("WebSocket sending {} bytes", data.size());
m_logger->Warning("Packet string has no terminator (started at pos {})", start);
```

Logging a failure where it's handled:

```cpp
try
{
    Login();
}
catch (const WebSocketError& e)
{
    m_logger->Error("Login failed: {}", e.what());
    ScheduleReconnect();
}
```

`main.cpp` creates the logger. Its last-resort catch logs through it, replacing the `std::fprintf` in the CONVENTIONS §5 template:

```cpp
#include "pch.hpp"
#include "Application.hpp"

#include "Core/Logger.hpp"

int main()
{
    const auto logger = std::make_shared<Logger>();
    try
    {
        auto app = Application{logger};
        return app.Run();
    }
    catch (const std::exception& e)
    {
        logger->Error("Fatal error: {}", e.what());
        return EXIT_FAILURE;
    }
}
```

- **Passing it on.** Constructors take `std::shared_ptr<Logger>` by value and move it into `m_logger` (CONVENTIONS §8, sink parameters). A caller that keeps its own reference passes a copy, as `main` does; otherwise it moves its last use.
- **Never null.** A missing logger is a bug, so every constructor that takes one asserts it. Code that wants silence passes a logger with no sink: `std::make_shared<Logger>(LogLevel_e::Error, nullptr)`.
- **Only classes that log take one.** `Isaac` and `BigUInt` don't. A free function that logs only during a call takes `Logger&`, as `LogEvent` in `WebSocketClient.cpp` does.
- **`main` creates it before the `try`,** so the last-resort catch can still use it after `Application` is gone. `std::make_shared` can only fail there by running out of memory at startup, which ends in `std::terminate`.
- `Application` sets the threshold at startup with `SetLevel`, from the config file's `client.logLevel` key ([ConfigDesign.md](ConfigDesign.md) §4 Usage).
- A runtime string is logged through `"{}"`: `m_logger->Info("{}", text)`. Passing it as the format string doesn't compile, so braces in network data can never be read as format fields.
- `Log` takes the level as a value, for when it's only known at run time.

### Behaviour

- **Filtering.**
    - `IsEnabled(level)` is `level >= m_level`. The threshold is a `std::atomic<LogLevel_e>`, read and written with `std::memory_order_relaxed`.
    - The templates check it before formatting, so a filtered call costs one function call and one atomic load.
    - Arguments are still evaluated, as for any function call. An argument that is expensive to compute belongs behind `if (m_logger->IsEnabled(LogLevel_e::Verbose))`.
    - Other threads see a new threshold shortly after `SetLevel`, not necessarily at once. Nothing depends on the exact moment.
- **Formatting.**
    - The templates call `std::format` before `Write` takes the lock, so a slow formatter doesn't hold up other threads.
    - A bad format string or argument type is a compile error.
    - What `std::format` can still throw at run time, `std::bad_alloc` or a `std::format_error` from a formatter, is caught and the message is dropped. The empty `catch` gets a "why" comment.
- **Source location.**
    - `LogFormat_s`'s constructor is `consteval` and implicit. The string literal converts to `LogFormat_s` at the call site, so the default argument `std::source_location::current()` is evaluated there. It names the line that called `m_logger->Info`, not a line in `Logger.hpp`.
    - `explicit` would defeat that, so this is a deliberate exception to CONVENTIONS §8's `explicit` rule, explained in the "why" comment.
    - The constructor also checks the format string: it builds the `std::format_string` member, whose own constructor is `consteval`. A runtime string still doesn't compile.
    - `#ifdef NDEBUG` picks the constructor, the same switch `assert` uses. In a Debug build it records the call site. In a Release build it has no location parameter, so `current()` is never evaluated, `location` stays empty, and the binary carries no source paths or function names. This is the only `#ifdef` in `Logger`.
    - Everything after the constructor is the same in both builds: `Log` passes `format.location` to `Write`, and `FormatLine` prints it only when it holds a value.
    - The templates pass `format` along unchanged, so the hop from `Info` to `Log` keeps the caller's location. A helper that logs on its caller's behalf, such as `LogEvent` in `WebSocketClient.cpp`, reports its own line.
- **Writing.**

    ```cpp
    void Logger::Write(LogLevel_e level, std::optional<std::source_location> location, std::string_view message)
    {
        const auto lock = std::scoped_lock{m_mutex};
        if (!m_sink)
        {
            return;
        }

        m_sink(LogEntry_s{.level = level, .time = std::chrono::system_clock::now(), .location = location, .message = message});
    }
    ```

    - The time is read under the lock, so times in the output never go backwards unless the wall clock itself is adjusted. This gets a "why" comment in the code.
    - `entry.message` points into the formatted string and is valid only during the sink call. A sink that keeps the message copies it.
    - An exception from the sink leaves `Write` and is dropped by the template's `catch`.
- **Sinks.**
    - `SetSink` swaps `m_sink` under `m_mutex` and returns the previous one. Once it returns, no thread is inside the old sink or will call it again, so whatever the old sink captured can be destroyed.
    - `SetSink(nullptr)` discards every message. `SetSink(Logger::WriteToConsole)` restores the console.
    - A sink must not log through its own logger or call that logger's `SetSink`. The mutex isn't recursive, so either would deadlock.
- **Several loggers.**
    - Each logger has its own threshold, mutex and sink, and loggers share nothing. A program normally has one; tests make one per test (§6.1).
    - Two console loggers still never split a line, because each line is a single `std::fwrite`, and the C library locks the stream for each call.
- **Console.**
    - `WriteToConsole` writes `FormatLine(entry)` and a `\n` with one `std::fwrite`, then calls `std::fflush`. `Warning` and `Error` go to stderr, `Verbose` and `Info` to stdout.
    - Flushing every line means a crash loses nothing that was already logged, and stdout and stderr lines keep their order on a terminal.
    - Write failures, such as a closed stdout, are ignored.
    - The message is written as given: UTF-8 (MSVC builds with `/utf-8`), with any embedded newline left in place.
- **Line format.**
    - `FormatLine` returns `{time} {level} {message}`, followed by ` [{file}:{line}]` when the entry has a location, and without a newline.
    - The time is `entry.time` floored to milliseconds, formatted with `{:%FT%T}` and followed by `Z`: `2026-10-05T18:34:12.345Z`.
    - The level is `VERBOSE`, `INFO`, `WARNING` or `ERROR`, padded to 7 characters, the length of `VERBOSE` and `WARNING`, so the messages line up. `GetLevelName` in the anonymous namespace maps it.
    - The location is `file_name()` after its last `/` or `\`, then the line: `2026-10-05T18:34:12.345Z INFO    WebSocket open [WebSocketClient.cpp:412]`. Compilers report the full path that CMake passed in, and the file name alone is enough because file names match class names. `GetFileName` in the anonymous namespace strips the folders.
    - The location goes last, so the time, level and message columns are the same in Debug and Release.
- **Not included:**
    - A log file. TODO when the client runs unattended: a sink that writes `FormatLine(entry)` to a file and also calls `WriteToConsole`.
    - Thread ids. `std::thread::id` has no `std::formatter` until C++23.
    - Function names. `function_name()` is long and differs between compilers (MSVC gives the full signature), and the file and line already find the call.
    - Colours and asynchronous writing.

---

## 4. Choosing a level

| Level | For | Examples |
|---|---|---|
| `Error` | A failure, logged where it's handled and not rethrown: `main`, a thread entry point, a reconnect loop | `Login failed: WebSocket error: Connection refused`, `Fatal error: ...` |
| `Warning` | A problem the code noticed and carried on through: malformed input it tolerated, a timeout it recovered from, a risky setting it accepted | `Packet string has no terminator (started at pos 812)`, `Logout not confirmed within 5 s; closing the connection`, `Config disables TLS certificate verification (server.tlsCaFile is NONE)` |
| `Info` | Milestones that someone running the client wants to see by default | `WebSocket connecting to ws://localhost:43594/`, `WebSocket open`, `WebSocket closed (code 1000: Normal closure)` |
| `Verbose` | Detail for debugging: traffic, internal events | `WebSocket received 42 bytes`, `WebSocket error event: ...` |

- **Each failure is logged once, at `Error`, by the code that handles it.** Code that throws doesn't also log at `Error`, and code that catches only to rethrow doesn't log at all (CONVENTIONS §8). A class may log what led up to a failure at `Verbose`.
- **A warning means the code carried on.** It is logged once, by the code that noticed the problem and worked around it. If the problem stops the operation, it is a failure instead: throw, and the handler logs it at `Error`.
- **Never log secrets:** the password, the plaintext login block, ISAAC seeds. Log the size of network data, not its bytes.
- **Messages from a subsystem start with its name** (`WebSocket ...`, `Packet ...`), so they can be told apart without a source location. They read like exception messages, without a trailing period.
- **Don't log while holding a mutex that another thread waits on.** A console write is slow; log after releasing it.

---

## 5. Differences from the reference logger

| Reference | Here | Why |
|---|---|---|
| Free functions in `namespace logger` over global state | A `Logger` instance, shared through `std::shared_ptr` with each class that logs | Requested. A test hands the object under test its own logger instead of redirecting a global one |
| Four levels: `error`, `warn`, `info`, `verbose` | The same four: `Verbose`, `Info`, `Warning`, `Error` | `warn` is spelled out, like the other names |
| `LogLevel` ordered most severe first, filtered on `level > current` | `LogLevel_e` ordered least severe first, filtered on `level >= threshold` | Reads in order of severity |
| Takes a finished `std::string_view`; callers build it with `+` and `std::to_string` | Takes a format string and arguments | Checked at compile time, and a filtered call builds no string. The reference built `"Smoke idle duration: " + std::to_string(...)` even with `verbose` off |
| Level read and written under the mutex | `std::atomic` | The check before formatting takes no lock |
| `[INFO] message` | `2026-10-05T18:34:12.345Z INFO    message` | Times make the WebSocket timing (the handshake, the 300 ms close) visible |
| No source locations | Debug builds end each line with `[file:line]` | Finds the call site without a macro |
| `set_streams(std::ostream*, std::ostream*)` to redirect output | `SetSink` | A capture sees the level and message without parsing text, and a file sink fits the same slot |
| `std::cout` and `std::cerr`, with no flush | `std::fwrite` and `std::fflush` per line | Nothing already logged is lost in a crash |
| Not `noexcept`, and callers build the message, which can throw | `noexcept`, with formatting inside | Safe in `WebSocketClient::OnMessage`, `Close`, `Stop` and destructors |
| `log_level` config key: `error`, `warn`, `info` or `verbose` | `client.logLevel`: `verbose`, `info`, `warning` or `error` | The names of `LogLevel_e`. No `warn` alias: every config file is rewritten for the new keys anyway ([ConfigDesign.md](ConfigDesign.md) §5) |

---

## 6. Test plan

### 6.1 Strategy

- Every test builds its own loggers, so tests share no logging state and nothing has to be restored. `[Logger]` tests give theirs a capture or their own sink, so nothing reaches the console.
- The `Logger` tests check whole messages. Tests of other classes check a captured entry's level, its order among the others, and a fragment of its message, such as a URL or a byte count. As with exceptions, the rest of the text isn't checked.

Out of scope:

- What `WriteToConsole` prints. It is `FormatLine` (§6.6) plus one `std::fwrite`, and is checked by hand.
- A sink that logs through its own logger, which deadlocks.
- A null logger passed to a constructor. That is an `assert`, so it's a bug, not an input.

**`LogCapture`** (`tests/LogCapture.hpp` / `.cpp`) is shared by every test file that checks logging:

```cpp
#pragma once

#include "Core/Logger.hpp"

struct CapturedLog_s
{
    LogLevel_e level;
    std::chrono::system_clock::time_point time;
    std::optional<std::source_location> location;
    std::string message;
};

class LogCapture
{
public:
    explicit LogCapture(LogLevel_e level = LogLevel_e::Verbose);
    ~LogCapture();

    LogCapture(const LogCapture&) = delete;
    LogCapture& operator=(const LogCapture&) = delete;

    [[nodiscard]] std::shared_ptr<Logger> GetLogger() const;
    [[nodiscard]] std::vector<CapturedLog_s> GetEntries() const;

private:
    void Append(const LogEntry_s& entry);

    mutable std::mutex m_mutex;
    std::vector<CapturedLog_s> m_entries;
    std::shared_ptr<Logger> m_logger;
};
```

- The constructor creates a `Logger` at the requested threshold, with a sink that calls `Append`, which copies the message.
- `GetLogger` returns that logger, to hand to the object under test: `auto client = WebSocketClient{capture.GetLogger()};`.
- The destructor calls `m_logger->SetSink(nullptr)`. The object under test may still hold the logger, and a `WebSocketClient`'s I/O thread may still be logging. Once `SetSink` returns, no thread is inside the capture's sink (§3 Sinks), so destroying the capture is safe, and later calls through the logger reach nothing.
- Its own mutex guards the entries, because the test thread reads them while other threads may still be logging. `GetEntries` returns a copy.
- Its sink captures `this`, so it can be neither copied nor moved.

### 6.2 Filtering

For each threshold, a `LogCapture` at that threshold, then one call at each level:

| Threshold | `Verbose` | `Info` | `Warning` | `Error` |
|---|---|---|---|---|
| `Verbose` | Captured | Captured | Captured | Captured |
| `Info` | | Captured | Captured | Captured |
| `Warning` | | | Captured | Captured |
| `Error` | | | | Captured |

- `IsEnabled` matches the table. `GetLevel` returns the threshold given to the constructor, and after `SetLevel`, the new one.
- `Log(level, ...)` behaves as the function for that level.
- `Logger{}` starts at `Info`, and its `SetSink(nullptr)` returns a non-empty sink: the console.
- **Filtered calls don't format.** A test type's `std::formatter` counts its calls. At threshold `Info`, `Verbose("{}", counted)` leaves the count at 0 and `Info("{}", counted)` makes it 1.

### 6.3 Messages

| Call | Captured level | Captured message |
|---|---|---|
| `Info("plain")` | `Info` | `plain` |
| `Info("{} + {} = {}", 1, 2, 3)` | `Info` | `1 + 2 = 3` |
| `Error("{{}} {}", "x")` | `Error` | `{} x` |
| `Verbose("{:>4}", 7)` | `Verbose` | `   7` |
| `Warning("{} left", 3)` | `Warning` | `3 left` |
| `Info("{}", "{}")` | `Info` | `{}`: an argument is never read as a format |
| `Info("{}", std::string(100'000, 'a'))` | `Info` | All 100 000 characters |
| `Log(LogLevel_e::Error, "{}", 5)` | `Error` | `5` |

- Entries arrive in call order.
- An entry's time lies between `std::chrono::system_clock::now()` read just before the call and just after it.
- `static_assert(noexcept(std::declval<Logger&>().Info("x")))`, and the same for `Verbose`, `Warning`, `Error` and `Log`.

**Source location.** On the line before each call, the test reads `std::source_location::current().line() + 1` as the expected line. It then branches on `NDEBUG`, as `LogFormat_s` does:

| Call | Debug build | Release build |
|---|---|---|
| `Info("x")` | Location's `file_name()` ends with `LoggerTests.cpp`; its line is the expected one | No location |
| `Warning("{}", 1)` | The same | No location |
| `Log(LogLevel_e::Error, "x")` | The same | No location |

The file is the test file, not `Logger.hpp`: the location survives the hop from `Info` to `Log`.

### 6.4 Failures

- A test type whose formatter throws `std::runtime_error`: `Info("{}", throwing)` returns normally and nothing is captured. The next `Info("ok")` is captured.
- A logger whose sink throws `std::runtime_error`: `Info("x")` returns normally, and `Info("y")` then reaches the sink again.
- Both throws happen inside a `noexcept` call, so an exception that escaped would end the test run in `std::terminate`.

### 6.5 Sinks and instances

- After installing sink `a`, `SetSink(b)` returns a function that reaches `a`.
- After `SetSink(nullptr)`, `Info("x")` returns normally and reaches no sink. A sink installed afterwards works again.
- **Independent loggers.** Two loggers with different thresholds and sinks: a call on one never reaches the other's sink, and `SetLevel` on one leaves the other's threshold unchanged.
- **Outliving the capture.** After a `LogCapture` is destroyed, logging through a copy of its logger returns normally and is captured nowhere.

### 6.6 Line format

Times are built as `std::chrono::sys_days{2026y / std::chrono::October / 5} + 18h + 34min + 12s + 345ms`. The test builds each entry itself, so these cases behave the same in Debug and Release. Entries have no location unless the row says so.

| Entry | `FormatLine` |
|---|---|
| `Info`, 2026-10-05 18:34:12.345, `hello` | `2026-10-05T18:34:12.345Z INFO    hello` |
| `Verbose`, same time, `hello` | `2026-10-05T18:34:12.345Z VERBOSE hello` |
| `Warning`, same time, `hello` | `2026-10-05T18:34:12.345Z WARNING hello` |
| `Error`, same time, `hello` | `2026-10-05T18:34:12.345Z ERROR   hello` |
| `Info`, 2026-01-02 03:04:05 exactly, `hello` | `2026-01-02T03:04:05.000Z INFO    hello` |
| `Info`, 2026-10-05 18:34:12.345999, `hello` | `2026-10-05T18:34:12.345Z INFO    hello`: truncated, not rounded |
| `Info`, 2026-10-05 18:34:12.345, `hello`, location `std::source_location::current()` read in the test at line `L` | `2026-10-05T18:34:12.345Z INFO    hello [LoggerTests.cpp:L]`: folders stripped |

### 6.7 Threads

- **No interleaving.** 8 threads share one logger, through copies of its `std::shared_ptr`, and each logs 1000 `Info` entries, `"{thread} {index}"`. The sink records each message. It sets an atomic flag on entry and clears it on exit, and fails the test if it finds the flag already set.
    - All 8000 entries arrive, each message intact.
    - Each thread's indices arrive in increasing order.
    - No two sink calls overlapped.
- **Swapping sinks under load.** 4 threads log continuously through one logger while the test thread installs a fresh counting sink on it 100 times. Each time, it records the replaced sink's count right after `SetSink` returns.
    - After the threads join, every replaced sink's count still equals the count recorded when it was replaced: no call reached it after `SetSink` returned.
    - The counts of all the sinks add up to the number of calls the threads made: nothing was lost or delivered twice.

### 6.8 Tooling

- Tag: `[Logger]`.
- `LogCapture.cpp` builds into the test executable through the existing `tests/**/*.cpp` glob.

### 6.9 Done when

- All tests pass on `windows-debug` and `windows-release` (and on the `linux-*` presets once available), with zero warnings. Both configurations matter here, because the source location tests take a different branch in each.
- The §6.7 cases pass 50 times in a row (`ctest --preset windows-debug --repeat until-fail:50`).

---

## 7. Implementation order

This comes right after the project setup (PacketDesign §8 step 1), so `Packet` and `WebSocketClient` can log from the start.

1. **`pch.hpp`:** add `<atomic>`, `<mutex>`, `<source_location>`, `<thread>` and `<type_traits>`.
2. **`LogFormat_s` on its own:** build one `logger.Info("{}", 1)` call on every preset, Debug and Release, before writing the rest. The wrapper relies on a `consteval` constructor that calls `std::format_string`'s, with `std::source_location::current()` as a default argument. If a toolchain rejects that pattern, it's best found here.
3. **`Logger` and `LogCapture`,** plus the §6.2 to §6.6 tests.
4. **Threads:** the §6.7 tests.
5. **`main.cpp` and `Application`:** `main` creates the logger and passes it to `Application`, and the last-resort catch logs through it.
