# Refactor Design

Plan for reorganizing `src/` and `tests/` so each file has one job, each folder holds one subsystem, and code used in several places is written once. Nothing a user or a script sees changes: the client connects, plays and logs as it does today, `client.jsonc` and account files read the same, and the Python API keeps every name. §11 lists the few things that do change: two message texts, and where a progress report falls within a step. Code style follows [CONVENTIONS.md](CONVENTIONS.md); this plan applies its file rules (§1, §5) to code written before they were followed everywhere. The work ships in eleven phases (§12). Each phase builds with zero warnings and passes every test before the next one starts.

What it fixes, by example:

- `Application.cpp` starts the program, and also parses the command line, counts Ctrl+C presses, finds and checks account files, puts together the log sink and holds a scope guard for the console.
- A lower-casing helper is written out eight times, a case-insensitive compare five times, and reading a whole file three times.
- The hitpoints stat index is defined three times, `MIN_OP` and `MAX_OP` twice, the number of levels three times, the zone size twice, and the game tick's 600 ms is defined only in the script host.
- `ScriptApi` (108 methods) answers queries about NPCs, items and locs, builds right-click menus, checks reachability, wraps every action and tracks the script's stop requests. The game knowledge in it can't be used, or tested, without the script layer.
- `ScriptBindings.cpp` (2,100 lines) holds all 140 bindings, and several do real work, such as filtering game messages or computing the HP percentage, even though `ScriptApi.hpp` says a binding only converts arguments and results.
- `Core/` holds a big-integer type, the config loader, a terminal line editor and the logger, which have nothing in common.

---

## 1. Decisions

| Topic | Decision |
|---|---|
| Behaviour | Unchanged, apart from what §11 lists. Every split moves code as it is; a phase that changes logic says so |
| `Core/` | Removed. Its files go to `Utils/`, `Console/` and `Config/` (§3) |
| Layers | Includes mostly run in this order: `Utils` → `Console` → `Io` → `Config` → `Cache` → `Game` → `Script` → `Accounts` → `Application`, with each folder including from the ones before it. This is a guide to where new code belongs, not a rule. A file may include from any folder when that gives the simpler design, as `ScriptHost.hpp` does with `Accounts/ProgressReport_s.hpp` (§10.1). Headers still can't include each other in a cycle: nothing is forward declared (CONVENTIONS §5), so the build would fail |
| `Application` | `Application.hpp` / `.cpp` move into a new `Application/` folder, beside the classes that take over what they used to do themselves. `pch.hpp` and `main.cpp` stay at the root of `src/`. CONVENTIONS §1 says `Application` stays at the root too, so that rule changes in the same phase (§13) |
| Game constants | A fact about the game moves to `Game/`, beside the type it describes. Constants about the bindings themselves, such as module names and argument limits, stay in `Script/` (§8.1) |
| Utilities | Static members of non-instantiable classes (CONVENTIONS §5), one class per kind: `StringUtils`, `FileUtils` |
| Errors | Each folder's exception types move to an `Error/` subfolder of that folder |
| Namespaces | `ChatDialog`, `SquareCollision` and `NavJson` become non-instantiable classes, as CONVENTIONS §5 asks of every `.cpp` |
| Game knowledge | Queries, menus and routes move from `ScriptApi` to `Game/`, as cheap views over the state like `InterfaceView`. `ScriptApi` is replaced by the script's actions, its control requests and a context that ties them together (§9.1) |
| Progress reports | Belong to the account: the schedule, the struct, the file and the formatting all live in `Accounts/`. The script host only runs `on_progress_report` when asked, and includes `Accounts/ProgressReport_s.hpp` for the report it hands back (§10.1) |
| History | A phase moves files with `git mv` in a commit of its own, before any commit that changes them, so `git log --follow` and blame keep working |
| Tests | Mirror the new tree. A test moves with the code it tests, and each new class gets its own test file. The helpers tests share live in `tests/Support/`, which mirrors `src/` too (§2) |

Rejected:

- **One CMake library per folder.** The linker would then enforce the order in Layers, which is meant as a guide, and every target would need its dependencies listed and kept current.
- **A single `GameConstants.hpp`.** Every file would include it, and it would change for unrelated reasons. Each constant goes beside the type it's about: `Stat_e::Hitpoints` beside `Stat_s`, `MenuOp::MAX` beside the menus.
- **Free functions in a namespace for the utilities.** CONVENTIONS §5 wants a class per `.cpp`.
- **Keeping `ScriptApi` as a facade** that forwards to the new `Game/` classes. That leaves around 70 one-line methods to keep in step with the classes they forward to. The bindings call the `Game/` classes directly, and the facade exists only during phase 7, to keep that phase small.

Not included:

- The Python standard library (`src/Script/Stdlib/`, 12,000 lines). It has its own layout and tests, and would get its own plan.
- Any name a script sees.
- The revision and proxy work. §13 lists the paths their plans need to change.

---

## 2. Target tree

New and moved files only; a folder marked "unchanged" keeps its files.

```
src/
├── pch.hpp
├── main.cpp
├── Application/
│   ├── Application.hpp / .cpp       loads the config, cache and navigation, and runs the accounts  (from src/)
│   ├── CommandLine.hpp / .cpp       CommandLine_s, the options, Parse            (from Application)
│   └── InterruptSignal.hpp / .cpp   the SIGINT handler and its count              (from Application.cpp)
├── Utils/
│   ├── BigUInt.hpp / .cpp           + ToHexString                                 (from Core, ConfigFile.cpp)
│   ├── Endian.hpp                                                                 (from Core)
│   ├── FileUtils.hpp / .cpp         ReadText, ReplaceFile, IsInsideFolder
│   ├── FileWatcher.hpp / .cpp                                                     (from Core)
│   └── StringUtils.hpp / .cpp       ToLower, EqualsIgnoringCase, Trim, Split...
├── Console/
│   ├── ConsoleCommand_s.hpp                                                       (from Script)
│   ├── ConsoleCommandParser.hpp / .cpp  "@account name args" into a command      (from AccountRunner.cpp)
│   ├── ConsoleInput.hpp / .cpp      without its platform code                     (from Core)
│   ├── ConsoleLogScope.hpp / .cpp                                                 (from Application.cpp)
│   ├── ConsoleOutput.hpp / .cpp     writing entries to stdout and stderr          (from Logger)
│   ├── LineEditor.hpp / .cpp                                                      (from Core)
│   ├── LogEntry_s.hpp                                                             (from Logger.hpp)
│   ├── LogFile.hpp / .cpp                                                         (from Core)
│   ├── LogFormat_s.hpp                                                            (from Logger.hpp)
│   ├── LogFormatter.hpp / .cpp      FormatLine, FormatColoredLine                 (from Logger)
│   ├── LogLevel_e.hpp                                                             (from Logger.hpp)
│   ├── LogLevelNames.hpp / .cpp     "verbose" and the rest, both ways             (from ConfigFile.cpp, AccountRunner.cpp)
│   ├── LogSinks.hpp / .cpp          the file-and-console sink                      (from Application::InstallLogSink)
│   ├── Logger.hpp / .cpp            levels, sinks, named loggers, the default     (from Core)
│   └── Terminal.hpp / .cpp          every platform call for the terminal          (from Logger.cpp, ConsoleInput.cpp)
├── Io/
│   ├── Error/
│   │   ├── WebSocketClosedError.hpp
│   │   └── WebSocketError.hpp
│   ├── WebSocketUrl.hpp / .cpp      the ws/wss check both callers had             (from ConfigFile.cpp, WebSocketClient.cpp)
│   └── (Isaac, NetSystem, Packet, WebSocketClient unchanged)
├── Config/
│   ├── Error/ConfigError.hpp                                                      (from Core)
│   ├── AccountConfig_s.hpp          AccountConfig_s, AccountSettings_s, ScriptConfig_s
│   ├── AccountDirectory.hpp / .cpp  every enabled account in a folder            (from Application.cpp)
│   ├── AccountFile.hpp / .cpp       Load, Parse, AddScriptSettings                (from ConfigFile)
│   ├── Config_s.hpp                 Config_s and its Login, Client and Scripting sections
│   ├── ConfigFile.hpp / .cpp        Load, Parse, Serialize                         (from Core)
│   ├── ConfigJson.hpp / .cpp        every nlohmann conversion                      (from ConfigFile.cpp)
│   ├── ConfigOverrides.hpp / .cpp   an account's sections over client.jsonc's     (from Account.cpp)
│   ├── ConfigValidator.hpp / .cpp   every rule and limit                           (from ConfigFile.cpp)
│   ├── JsoncEditor.hpp / .cpp                                                     (from Core)
│   ├── JsoncScanner.hpp / .cpp      the scanner                                    (from JsoncEditor.cpp)
│   ├── JsoncValue_s.hpp             what the scanner finds                         (from JsoncEditor.cpp)
│   └── ServerSettings_s.hpp         shared by client.jsonc and account files
├── Cache/
│   ├── Error/CacheError.hpp
│   └── (otherwise unchanged; GameCache_s gains name lookups, §8.2)
├── Game/
│   ├── Error/
│   │   ├── ConnectionLostError.hpp
│   │   └── ProtocolError.hpp
│   ├── GameActions.hpp / .cpp       without the route finders
│   ├── GameClient.hpp / .cpp
│   ├── GameTick.hpp                 DURATION                                       (from ScriptHost.cpp)
│   ├── Tile_s.hpp                   + MAX_COORD                                    (from ScriptBindings.cpp)
│   ├── Interface/
│   │   ├── ChatDialog.hpp / .cpp    a class now                                    (from Game)
│   │   ├── DialogueTracker.hpp / .cpp  one continue, one answer per modal change   (from ScriptApi)
│   │   └── InterfaceView.hpp / .cpp + FindClientCode                               (from Game)
│   ├── Menu/
│   │   ├── MenuOp.hpp               MIN, MAX, COUNT, TALK, ATTACK, TAKE, DROP      (from ScriptApi, ClientPackets, PyConvert.cpp)
│   │   └── Menus.hpp / .cpp         each target's menu, and choosing from one      (from ScriptApi)
│   ├── Query/
│   │   ├── EntityQuery.hpp / .cpp   NPCs, players, ground items, locs              (from ScriptApi)
│   │   ├── InventoryItem_s.hpp                                                    (from ScriptApi.hpp)
│   │   ├── InventoryQuery.hpp / .cpp                                              (from ScriptApi)
│   │   └── SearchFilter_s.hpp / .cpp  + matching                                   (from ScriptApi)
│   ├── Map/
│   │   ├── InteractionRoutes.hpp / .cpp  the webclient's route rules              (from GameActions)
│   │   ├── SquareCollision.hpp / .cpp    a class now
│   │   └── (CollisionMap, LocShape, PathFinder, WalkMap, WorldMap unchanged)
│   ├── Nav/
│   │   ├── NavEdge_s.hpp, NavPoint_s.hpp, NavRect_s.hpp / .cpp, NavRequires_s.hpp / .cpp,
│   │   │   NavState_s.hpp, NavTeleport_s.hpp                                      (from NavGraph.hpp)
│   │   ├── NavGraph.hpp / .cpp
│   │   ├── NavJson.hpp / .cpp       a class now                                    (from Script)
│   │   ├── Navigation.hpp / .cpp    was Navigation_s                               (from NavGraph)
│   │   └── WorldPathFinder.hpp / .cpp
│   ├── Net/
│   │   ├── Error/LoginError.hpp / .cpp
│   │   └── (ClientPacketWriter, LoginHandshake, ServerPacketReader unchanged)
│   ├── State/
│   │   ├── BuildArea_s.hpp                                                        (from GameState_s.hpp)
│   │   ├── EntityStatus.hpp / .cpp  IsMoving, InCombat, TookDamage, COMBAT_TICKS  (from ScriptApi, ScriptBindings.cpp)
│   │   ├── Stat_e.hpp                                                             (from ScriptBindings.cpp)
│   │   └── (the rest unchanged)
│   ├── Decode/                      unchanged
│   └── Protocol/                    unchanged, apart from MIN_OP and MAX_OP going to MenuOp
├── Script/
│   ├── Error/
│   │   ├── ScriptError.hpp
│   │   ├── ScriptRaisedError.hpp                                                  (from PyConvert.hpp)
│   │   └── ScriptTypeError.hpp                                                    (from PyConvert.hpp)
│   ├── BotMessenger.hpp / .cpp
│   ├── ScriptActions.hpp / .cpp     the actions, checked against the state        (from ScriptApi)
│   ├── ScriptCommand_s.hpp                                                        (from ConsoleCommand_s.hpp)
│   ├── ScriptContext.hpp / .cpp     what one VM's bindings reach                   (replaces ScriptApi)
│   ├── ScriptControl.hpp / .cpp     stop, relog, step time, progress notes         (from ScriptApi)
│   ├── ScriptRuntime.hpp / .cpp
│   ├── ScriptVm.hpp / .cpp
│   ├── Stdlib.hpp / .cpp
│   ├── Stdlib/                      the Python files, unchanged
│   ├── Bindings/
│   │   ├── ActionBindings, ControlBindings, InterfaceBindings, InventoryBindings,
│   │   │   NavigationBindings, PlayerBindings, SocialBindings, WorldBindings .hpp / .cpp
│   │   ├── BindingSupport.hpp / .cpp  Guard, the Return helpers, the per-VM context
│   │   └── ScriptBindings.hpp / .cpp  Bind, Unbind, SetSettings
│   ├── Convert/
│   │   ├── PyArgs.hpp / .cpp        Python arguments to game values                (from PyConvert)
│   │   ├── PyObjects.hpp / .cpp     game values to the stdlib's classes            (from PyConvert)
│   │   └── PyValue.hpp / .cpp       ints, strings, lists, optionals                (from PyConvert)
│   └── Host/
│       ├── EventDispatcher.hpp / .cpp  game events, messages and the backpack to hooks  (from ScriptHost)
│       ├── LoopSchedule.hpp / .cpp     when loop() runs next                       (from ScriptHost)
│       ├── ScriptHooks.hpp / .cpp      finding and calling the runtime's hooks     (from ScriptHost)
│       └── ScriptHost.hpp / .cpp
└── Accounts/
    ├── Account.hpp / .cpp
    ├── AccountCommands.hpp / .cpp   help, status, loglevel, say, script commands   (from AccountRunner)
    ├── AccountRunner.hpp / .cpp
    ├── IdleSummary.hpp / .cpp       the summary an idle account logs               (from Account.cpp)
    ├── ProgressReport_s.hpp                                                       (from Script)
    ├── ProgressReportFile.hpp / .cpp
    └── ProgressReporter.hpp / .cpp  when a report is due, and where it goes       (from ScriptHost, Account.cpp)
```

`tests/` gets the same folders: `tests/Core/` splits into `tests/Utils/`, `tests/Console/` and `tests/Config/`, and `tests/ApplicationTests.cpp` becomes `tests/Application/CommandLineTests.cpp`. The helpers the tests share move out of the test folders into `tests/Support/`, which mirrors `src/` as well. Most of them are used from several test folders: `FakeGameServer` and `TestWorld` from `Accounts`, `Game` and `Script`, for example. Every other file under `tests/` is then a `...Tests.cpp`:

```
tests/Support/
├── DefaultLoggerScope, LogCapture, LoopbackPort, TempFolder .hpp / .cpp   (from tests/)
├── Cache/    CacheWriter, RealCache, TestCache .hpp / .cpp                (from tests/Cache/)
├── Game/     BitWriter, FakeGameServer, Fixtures, TestWorld .hpp / .cpp   (from tests/Game/)
└── Script/   HostFixture, ScriptTestRuntime .hpp / .cpp                   (from tests/Script/, and ScriptHostTests.cpp, §10.1)
```

`tests/Stdlib/helpers.py` belongs to the Python tests, which this plan leaves alone. CMake needs no change: the sources are globbed (CONVENTIONS §2), and the Python stdlib's path, `src/Script/Stdlib`, doesn't move.

---

## 3. `Core/`, file by file

| Today | Goes to | Split |
|---|---|---|
| `BigUInt` | `Utils/BigUInt` | Gains `ToHexString()`, which is `FormatHex` from `ConfigFile.cpp` |
| `ConfigError.hpp` | `Config/Error/ConfigError.hpp` | |
| `ConfigFile` | `Config/` | Into `Config_s.hpp`, `ServerSettings_s.hpp`, `AccountConfig_s.hpp`, `ConfigFile`, `AccountFile`, `ConfigJson` and `ConfigValidator` (§6) |
| `ConsoleInput` | `Console/ConsoleInput` | Its platform code goes to `Console/Terminal` (§5.2) |
| `Endian.hpp` | `Utils/Endian.hpp` | |
| `FileWatcher` | `Utils/FileWatcher` | |
| `JsoncEditor` | `Config/JsoncEditor` | The scanner goes to `JsoncScanner`, its structs to `JsoncValue_s.hpp` (§6.6) |
| `LineEditor` | `Console/LineEditor` | |
| `LogFile` | `Console/LogFile` | |
| `Logger` | `Console/Logger` | Into `LogLevel_e.hpp`, `LogEntry_s.hpp`, `LogFormat_s.hpp`, `Logger`, `LogFormatter`, `ConsoleOutput` and `Terminal` (§5.1) |

---

## 4. Utils

### 4.1 `StringUtils`

```cpp
class StringUtils
{
public:
    // The "C" locale's whitespace, as std::isspace has it.
    static constexpr auto WHITESPACE = " \t\n\v\f\r"sv;

    StringUtils() = delete;

    [[nodiscard]] static std::string ToLower(std::string_view text);
    [[nodiscard]] static bool EqualsIgnoringCase(std::string_view left, std::string_view right);
    [[nodiscard]] static std::string_view Trim(std::string_view text);
    [[nodiscard]] static std::string TrimTrailingNewlines(std::string text);
    // The first word and the trimmed rest; both empty for blank text.
    [[nodiscard]] static std::pair<std::string_view, std::string_view> SplitFirstWord(std::string_view text);
    // Runs of whitespace separate words, so none is empty.
    [[nodiscard]] static std::vector<std::string_view> SplitWords(std::string_view text);
    [[nodiscard]] static std::string Join(std::span<const std::string> parts, std::string_view separator);
    [[nodiscard]] static bool IsPrintableAscii(std::string_view text);
};
```

Every function lower-cases through `unsigned char`, as each copy does today. The copies it replaces:

| Function | Copies today |
|---|---|
| `ToLower` | `Application.cpp`, `AccountRunner.cpp`, `BotMessenger.cpp`, `ChatDialog.cpp` (`Lower`), `NavGraph.cpp` (`Lower`), `WorldPathFinder.cpp` (`Lower`), `NavJson.cpp` (`Lower`), the `lower` lambda in `ScriptBindings.cpp`'s `FindComponents` |
| `EqualsIgnoringCase` | `TypeDecoder.cpp`, `ServerPacketDecoder.cpp`, `InterfaceView.cpp`, `ScriptApi.cpp`, `ScriptBindings.cpp` (`SameText`) |
| `Trim` | `AccountRunner.cpp` (space and tab), `Base37.cpp` (all of `WHITESPACE`) |
| `SplitFirstWord`, `SplitWords` | `AccountRunner.cpp`; `ChatDialog.cpp` has its own `SplitWords`, on spaces only |
| `TrimTrailingNewlines` | `ScriptVm.cpp` |
| `Join` | `JsoncEditor.cpp` (`JoinPath`); the hand-written `", "` loops in `Account::AddSettingDefaults` and `AccountRunner::HandleCommand` |
| `IsPrintableAscii` | `ConfigFile.cpp` |

`WordPack.cpp`'s `ToLower(char)` works on one character for its lookup table and stays.

The two copies of `Trim` and `SplitWords` disagree on what counts as whitespace. The shared one uses all of `WHITESPACE`, which changes nothing anyone can see: a console line never holds `\n`, `ConsoleInput` strips a trailing `\r`, `LineEditor` treats Ctrl+K (`\v`) and Ctrl+L (`\f`) as keys rather than inserting them, and the interface text `ChatDialog` splits has had its line breaks replaced with spaces by `CleanText` and holds no tabs. `StringUtilsTests` covers each character anyway.

### 4.2 `FileUtils`

```cpp
class FileUtils
{
public:
    FileUtils() = delete;

    // Nullopt when the file can't be opened or read; each caller words its own error.
    [[nodiscard]] static std::optional<std::string> ReadText(const std::filesystem::path& path);
    // Through a temporary file beside it, so the file is never left half written. Throws std::runtime_error.
    static void ReplaceFile(const std::filesystem::path& path, std::string_view text);
    // A relative path with no root and no "..", so joining it to a folder stays inside that folder.
    [[nodiscard]] static bool IsInsideFolder(const std::filesystem::path& relative);
};
```

`ReadText` replaces `ConfigFile.cpp`'s `ReadFile`, `NavGraph.cpp`'s `ReadFile` and `ScriptVm.cpp`'s `ReadText`. `ReplaceFile` and `IsInsideFolder` are moved from `ConfigFile.cpp` and `ScriptVm.cpp` unchanged, except that `ReplaceFile` throws `std::runtime_error` rather than `ConfigError`, with the same messages. Its only caller is `AccountFile::AddScriptSettings`. `Account::AddSettingDefaults` catches any `std::exception` and logs its text, so what the log shows doesn't change, and no test expects a `ConfigError` from a failed write.

### 4.3 Moved without change

`Endian.hpp`, `FileWatcher` and `BigUInt`, apart from `BigUInt::ToHexString()`, which `ConfigJson` uses where `FormatHex` was.

---

## 5. Console

### 5.1 `Logger`, split by job

| File | Holds |
|---|---|
| `LogLevel_e.hpp` | The enum |
| `LogEntry_s.hpp` | The entry a sink gets |
| `LogFormat_s.hpp` | The format string that carries the call site |
| `Logger.hpp` / `.cpp` | Levels, `SetSink`, `CreateNamed`, `GetDefault`, `SetDefault`, `Log` and its four wrappers. Nothing about how an entry looks or where it's written |
| `LogFormatter.hpp` / `.cpp` | `FormatLine` and `FormatColoredLine`, with the level names and colours they use |
| `ConsoleOutput.hpp` / `.cpp` | `Write` (coloured where the terminal shows colour), `WritePlain`, `FormatLine` (the console's choice of the two) and `GetStream` (stderr for warnings and errors) |
| `Terminal.hpp` / `.cpp` | §5.2 |

The default sink in `Logger`'s constructor becomes `ConsoleOutput::Write`. The tests that call `Logger::FormatLine` and `Logger::FormatColoredLine` move to `tests/Console/LogFormatterTests.cpp`.

### 5.2 `Terminal`

All the terminal's platform code, so `<Windows.h>` and `<termios.h>` are included in one file only (CONVENTIONS §4, §9):

```cpp
class Terminal
{
public:
    Terminal() = delete;

    // On a terminal that shows VT100 colours, and only when NO_COLOR isn't set.
    [[nodiscard]] static bool CanColor(std::FILE* stream);
    [[nodiscard]] static bool IsInputConsole();
    // Returns how to undo it, or nothing when either side isn't a terminal that takes VT100 codes.
    [[nodiscard]] static std::function<void()> EnterRawMode();
    // Empty after a Ctrl+C on Windows; nullopt once the terminal is gone.
    [[nodiscard]] static std::optional<std::string> ReadKeys();
};
```

`CanColor` comes from `Logger.cpp`; the rest from `ConsoleInput.cpp`. `ConsoleOutput` keeps the once-per-stream cache of `CanColor`'s answer that `Logger.cpp` has today.

### 5.3 `LogLevelNames`

`ConfigFile.cpp` and `AccountRunner.cpp` each have their own copy of the `LOG_LEVEL_NAMES` table. One class replaces both:

```cpp
class LogLevelNames
{
public:
    static constexpr auto CHOICES = "verbose, info, warning or error"sv;

    LogLevelNames() = delete;

    // Exactly as written; the console lower-cases what was typed first.
    [[nodiscard]] static std::optional<LogLevel_e> Find(std::string_view name);
    [[nodiscard]] static std::string_view GetName(LogLevel_e level);
};
```

### 5.4 `LogSinks` and `ConsoleLogScope`

`Application::InstallLogSink` builds a sink that writes each entry to the log file, if there is one, and then to the console. It writes above the prompt when the console is interactive, plain when the console is raw, and coloured otherwise. That becomes `LogSinks::Make(std::shared_ptr<LogFile> file, std::shared_ptr<ConsoleInput> console, bool rawConsole)`, which returns a `Logger::Sink`, and Application passes it to `SetSink`. The check that drops a console that isn't interactive moves into `Make`.

`ConsoleLogScope` moves from `Application.cpp`'s anonymous namespace to its own file, unchanged.

### 5.5 Console commands

`ConsoleCommand_s` moves from `Script/` to `Console/`, since it's what the console produces. `ScriptCommand_s`, a command a script added together with its help text, moves to its own header, `Script/ScriptCommand_s.hpp`. Today it shares a file named after the other struct.

The parsing at the top of `AccountRunner::HandleCommand` becomes `ConsoleCommandParser`:

```cpp
struct ConsoleLine_s
{
    // Without the prefix; nullopt when the line wasn't sent to one account.
    std::optional<std::string> target;
    // Its name is empty when the line held only the target.
    ConsoleCommand_s command;
};

class ConsoleCommandParser
{
public:
    static constexpr auto TARGET_PREFIX = '@';

    ConsoleCommandParser() = delete;

    // Nullopt for a blank line.
    [[nodiscard]] static std::optional<ConsoleLine_s> Parse(std::string_view line);
};
```

`AccountRunner` keeps the order of its warnings: it checks the target is an account before it checks a command follows.

---

## 6. Config

### 6.1 The structs

| Header | Holds |
|---|---|
| `ServerSettings_s.hpp` | `ServerSettings_s`, used by both files |
| `Config_s.hpp` | `Config_s` and its sections: `LoginSettings_s`, `ClientSettings_s`, `ScriptingSettings_s` |
| `AccountConfig_s.hpp` | `AccountConfig_s`, `AccountSettings_s`, `ScriptConfig_s` |

A section lives in the header of the struct that owns it (CONVENTIONS §6). `ServerSettings_s` gets a header of its own because both files use it. `GameClient` includes `AccountConfig_s.hpp` for `AccountSettings_s`, and no longer needs `ConfigFile.hpp`.

### 6.2 `ConfigJson`

The only file that includes `<nlohmann/json.hpp>` for the config. It holds every `adl_serializer`, the `NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_WITH_DEFAULT` lines, the hand-written `from_json` for accounts, and the error text that never quotes the input (`GetTextPosition`, `DescribeConversionError`). Its header names only the project's own types:

```cpp
class ConfigJson
{
public:
    ConfigJson() = delete;

    // Throws ConfigError naming the key, and never quoting the text, which can hold the password.
    [[nodiscard]] static Config_s ParseConfig(std::string_view text);
    [[nodiscard]] static AccountConfig_s ParseAccount(std::string_view text);
    [[nodiscard]] static std::string SerializeConfig(const Config_s& config);
    // For the parser's error, which says where the text is wrong.
    static void CheckObject(std::string_view text);
};
```

The `from_json` overloads for `ScriptConfig_s` and `AccountConfig_s` stay at global scope in `ConfigJson.cpp`, because nlohmann finds them by argument-dependent lookup in the structs' own namespace.

### 6.3 `ConfigValidator`

`Validate`, `ValidateAccount`, `ValidateServer`, every `MAX_` and `MIN_` constant, and the TLS warning (`WarnIfTlsVerificationDisabled` becomes `ConfigValidator::Warn(const Config_s&, Logger&)`). `ValidateServer` calls `WebSocketUrl::IsValid` (§6.7).

### 6.4 `ConfigFile`, `AccountFile`, `AccountDirectory`

- `ConfigFile`: `DEFAULT_PATH`, `Load`, `Parse`, `Serialize`. Each reads through `FileUtils`, then `ConfigJson`, then `ConfigValidator`, and adds the path to any error, as today.
- `AccountFile`: `EXTENSION` (was `ConfigFile::ACCOUNT_EXTENSION`), `Load`, `Parse`, `AddScriptSettings`.
- `AccountDirectory::LoadEnabled(const std::filesystem::path& directory)`: `FindAccountFiles`, the enabled filter, the "no enabled account files" error and `CheckUsernamesAreUnique`, all from `Application.cpp`. The check that the folder exists stays in `Application::LoadAccounts`, because its message names the `--account` option. The option belongs to the command line, and account files know nothing about it.

### 6.5 `ConfigOverrides`

`Account.cpp`'s `WithServer` becomes `ConfigOverrides::ForAccount(std::shared_ptr<const Config_s> config, const AccountConfig_s& account)`, which returns the config unchanged when the account replaces nothing. This is the function [ProxyDesign.md](ProxyDesign.md) §3 calls `WithAccountOverrides`, so the proxy work adds its `proxy` case here.

### 6.6 `JsoncScanner`

`JsoncEditor.cpp` holds a scanner of about 150 lines, and the editing on top of it. The scanner and its structs move out:

- `JsoncValue_s.hpp`: what the scanner finds. Today `Member_s` is forward declared so `Value_s` can hold a vector of them, which CONVENTIONS §5 forbids. Nest the member inside the value instead (`JsoncValue_s::Member_s`, holding a key, where it starts, and the index of its value in a `std::vector<JsoncValue_s>` the outer value owns), or another shape that needs no forward declaration.
- `JsoncScanner`: `ScanDocument`, throwing `ConfigError` on anything it doesn't expect, as today.
- `JsoncEditor`: layout detection, formatting and `AddMissing`.

### 6.7 `Io/WebSocketUrl`

`ConfigFile.cpp` and `WebSocketClient.cpp` each check for a `ws://` or `wss://` URL with `ix::UrlParser`. `WebSocketUrl::GetScheme(url)` and `WebSocketUrl::IsValid(url)` replace both. `ConfigValidator::Warn` uses `GetScheme` to spot `wss`. The class lives in `Io/` because the URL is the WebSocket's, and `WebSocketClient` is its main user.

---

## 7. Application

What's left in `Application` is its job as the program's entry point: load the config, set the level, open the log file, load the cache and build the navigation in the constructor; then in `Run`, make the runtime and the runner, install the interrupt handler and the console, and run.

| New class | From | Holds |
|---|---|---|
| `Application/CommandLine` | `Application::ParseCommandLine` and its constants | `CommandLine_s` (in the class's header, CONVENTIONS §6), the four option names, `USAGE`, and `Parse(std::span<char* const> args)` with its two combination rules |
| `Application/InterruptSignal` | `Application.cpp`'s `interruptCount` and `SignalHandler` | `Install()` and `GetCount()`. Static, since a process has one handler |
| `Config/AccountDirectory` | `FindAccountFiles`, `CheckUsernamesAreUnique` and the loop in `LoadAccounts` | §6.4 |
| `Console/LogSinks` | `InstallLogSink` | §5.4 |
| `Console/ConsoleLogScope` | `Application.cpp` | §5.4 |

`Application::LoadAccounts` keeps the `--account` branch and its `--debugger` rule, and the check that the accounts folder exists. Everything else it does moves to `AccountDirectory::LoadEnabled`. `main.cpp` stays at the root of `src/`. It includes `Application/Application.hpp` and `Application/CommandLine.hpp`, and calls `CommandLine::Parse`.

---

## 8. Game

### 8.1 Constants

| Constant | Today | Goes to |
|---|---|---|
| Hitpoints is stat 3 | `ScriptBindings.cpp` `HITPOINTS`, `ScriptHost.cpp` `HITPOINTS`, `Account.cpp` `HITPOINTS_STAT` | `Stat_e::Hitpoints` |
| The other stat indices, 0 to 20 | `ScriptBindings.cpp`'s `CONSTANTS`, as bare numbers | `Stat_e`. The bindings' table names its values |
| 600 ms per tick | `ScriptHost.cpp` `MILLISECONDS_PER_TICK`, with `MILLISECONDS_PER_SECOND` | `GameTick::DURATION`, a `std::chrono::milliseconds`. `system_update`'s seconds become `std::chrono::duration_cast<std::chrono::seconds>(ticks * GameTick::DURATION)`, which truncates exactly as the integer division does |
| In combat for 8 ticks after a hit | `ScriptApi::COMBAT_TICKS` | `EntityStatus::COMBAT_TICKS` |
| Ops 1 to 5 | `ClientPackets::MIN_OP` / `MAX_OP`, and `PyConvert.cpp`'s own `MIN_OP` / `MAX_OP` | `MenuOp::MIN`, `MenuOp::MAX`. `ClientPackets` and `PyArgs` both use them |
| A menu has 5 slots | `ScriptApi::MENU_SIZE` | `MenuOp::COUNT` |
| Talk-to is op 1, Attack 2, Take 3, Drop 5 | `ScriptApi::OP_TALK`, `OP_ATTACK`, `OP_TAKE`, `OP_DROP` | `MenuOp::TALK`, `ATTACK`, `TAKE`, `DROP` |
| "Take" and "Drop" | `ScriptApi::TAKE_OPTION`, `DROP_OPTION`, with `ScriptApi.cpp`'s `TAKE_SLOT`, `DROP_SLOT` | `MenuOp::TAKE_OPTION`, `DROP_OPTION`. Each slot is its op minus one, so the slot constants go |
| Four levels | `WorldMap::LEVELS`, `WalkMap::LEVELS`, and `0, 3` written out in three bindings | `MapSquare::LEVELS`, which the cache already defines; `Game/` uses it. The bindings check against `MapSquare::LEVELS - 1` |
| Map squares 0 to 255 | written out in `square_locs` | `MapSquare::MAX_SQUARE`, which `ID_SHIFT` implies |
| The build area is 104 tiles | `BuildArea_s::SIZE` and `CollisionMap::SIZE` | `BuildArea_s::SIZE` in its own `State/BuildArea_s.hpp`, so `CollisionMap` can define `SIZE = BuildArea_s::SIZE` without including all of `GameState_s` |
| A zone is 8 tiles | `ServerPacketDecoder.cpp` `ZONE_SIZE` and `Zone_s::SIZE` | `Zone_s::SIZE` |
| The four loc layers in order | the same `LAYERS` array in `GameActions.cpp` and `ScriptApi.cpp` | `WorldMap::LOC_LAYERS`, beside `GetLoc(tile, layer)`, which both loops call |
| Script coordinates up to 32767 | `ScriptBindings.cpp` `MAX_COORD` | `Tile_s::MAX_COORD`. `ClientPackets.cpp`'s own `MAX_COORD` is the packet field's limit, 0xFFFF; rename it `MAX_WIRE_COORD` so the two can't be confused |
| HP as a percentage | `ScriptBindings.cpp` `PERCENT` and the sum in `get_hp_percent` | `Stat_s::GetPercent()` |

These stay in `Script/` because they're about the bindings, not the game: `PRELUDE_FILE`, `LOAD_STDLIB_FILE`, `LOAD_SETTINGS`, `CORE_MODULE`, `BUILTIN_FUNCTIONS`, `SETTINGS_JSON`, the `_rt_` names and hook names in `ScriptHost.cpp`, and `MAX_RELOG_SECONDS`, which goes to `ScriptControl`.

`Stat_e` lists the stats this revision has:

```cpp
enum class Stat_e : u8
{
    Attack = 0,
    Defence = 1,
    Strength = 2,
    Hitpoints = 3,
    Ranged = 4,
    Prayer = 5,
    Magic = 6,
    Cooking = 7,
    Woodcutting = 8,
    Fletching = 9,
    Fishing = 10,
    Firemaking = 11,
    Crafting = 12,
    Smithing = 13,
    Mining = 14,
    Herblore = 15,
    Agility = 16,
    Thieving = 17,
    Runecraft = 20,
};
```

`GameState_s::STAT_COUNT` stays at 25, the number of slots the server sends. `GameState_s` gains `GetStat(Stat_e)`, so code reads `state.GetStat(Stat_e::Hitpoints)` rather than indexing `stats` with a cast.

### 8.2 Game knowledge out of `ScriptApi`

Each of these needs only the state, the map and the cache, so each is a small view or a static class in `Game/`, made where it's needed, as `InterfaceView` is today:

| Class | From `ScriptApi` | Notes |
|---|---|---|
| `Menu/Menus` | `GetNpcMenu`, `GetLocMenu`, `GetGroundItemMenu`, `GetItemMenu`, `GetInventoryMenu`, `GetPlayerMenu`, the `Find...Op` functions, and `MakeMenu`, `DescribeMenu`, `ChooseOption`, `RequireType`, `DescribeType` | `using Menu = std::array<std::string_view, MenuOp::COUNT>`. `FindGroundItemOp` and `FindItemOp` build their menus with `GetGroundItemMenu` and `GetItemMenu`, so the code that fills in "Take" and "Drop" exists once. `FindInventoryOption` keeps its own check: unlike `GetInventoryMenu`, it doesn't reject an inventory whose items have their own options |
| `Query/SearchFilter_s` | `SearchFilter_s`, `Matches`, `MatchesId`, `MatchesName` | Matching becomes methods on the struct |
| `Query/EntityQuery` | `GetNpcs`, `GetNearestNpc`, `GetNpc`, `GetPlayers`, `GetPlayerByName`, `GetGroundItems`, `GetNearestGroundItem`, `GetLocAt`, `GetLocs`, `GetNearestLoc`, and the `SortByDistance` and `FindNearest` templates | Built from the state and the map |
| `Query/InventoryQuery` | `InventoryItem_s`, `GetInventory`, `CountItems`, `FindItem`, `GetEmptySlots`, `HasItem` | |
| `Map/InteractionRoutes` | `GameActions::FindWalkRoute`, `FindEntityRoute`, `FindGroundItemRoute`, `FindLocRoute`, with `FindRoute`, `GetLocTarget`, `MakeAreaTarget`, `MakeLocTarget` | `GameActions` sends packets; these work out routes, and both `GameActions` and the scripts' `can_reach_*` use them |
| `State/EntityStatus` | `IsMoving(entity, tick)`, `InCombat(entity, tick)`, and `took_damage`'s loop from `ScriptBindings.cpp` | |
| `Interface/DialogueTracker` | `m_continuedAt`, `m_answeredAt`, and the halves of `FindContinue`, `IsCountDialogOpen`, `ContinueDialogue` and `AnswerCountDialog` that use them | The webclient sends one resume per dialogue and one answer per count dialog; this remembers which modal change each was sent in |
| `InterfaceView::FindClientCode(u16 root, ClientCode_e code)` | `ScriptApi.cpp`'s second anonymous namespace, `FindAcceptDesign` | Also fixes that namespace sitting halfway down the file (CONVENTIONS §5) |
| `GameCache_s::FindNpcName`, `FindObjName`, `FindLocName`, `FindTypeIds` | `ScriptApi::GetNpcName` and the rest; the matching loop in `ScriptBindings.cpp`'s `FindTypeIds` | Names come from the cache, so they're found there |

### 8.3 Files that hold more than one class, and namespaces

- `NavGraph.cpp` implements `NavRect_s::Contains`, `NavRequires_s::IsGated` and `Check`, `NavGraph` and `Navigation_s`. Each struct gets its own header in `Nav/`, with a `.cpp` where it has methods. `Navigation_s` has constructors that load files and a `GetData` lookup, so it's a class (CONVENTIONS §6): `Navigation`, with public `map` and `graph` replaced by `GetMap()` and `GetGraph()`.
- `ChatDialog`, `SquareCollision` and `NavJson` are namespaces; each becomes a class of static members with a deleted constructor.
- `tests/Cache/RealCache.hpp` forward declares `GameCache_s`. It includes the header instead.

### 8.4 Folders

`ChatDialog` and `InterfaceView` move to `Game/Interface/`, the errors to `Game/Error/` and `Game/Net/Error/`, and `NavJson` from `Script/` to `Game/Nav/`. `GameClient`, `GameActions` and `Tile_s` stay at `Game/`'s root, which keeps the tree shallow (CONVENTIONS §1).

---

## 9. Script

### 9.1 `ScriptApi` is replaced

Once §8.2 has moved its queries out, `ScriptApi` still does three jobs. Each becomes its own class:

| Class | Holds |
|---|---|
| `ScriptActions` | Every action, with the checks that make one return false when its target is no longer tracked (`HasItem`, `HasGroundItem`, the `FindNpc` and `FindPlayer` checks), plus a `DialogueTracker`, `SetRun`, `CanSetRun`, `SetAppearance` and `IsAppearanceScreenOpen` |
| `ScriptControl` | `RequestStop` / `TakeStopRequest`, `RequestRelog` / `TakeRelogRequest`, `SetStepTime` / `GetStepTime`, `NoteProgress` / `GetLastProgress`, and `StopRequest_e` |
| `ScriptContext` | What one VM's bindings reach: the state, the map, the cache, the `ScriptActions`, the `ScriptControl`, the navigation, the messenger and the username. `ToTile(x, z)` puts a tile on the player's level, and `GetEntities()`, `GetInventories()` and `GetInterfaces()` make the views. `SendBotMessage` moves here from `ScriptApi` as it is |

`ScriptHost` owns all three, as it owns `ScriptApi` today, so a stop request or a continued dialogue still outlasts a reload. `ScriptHost` still clears the stop request when it reloads. `FindWorldPath` and `GetNavigation` don't move: the binding calls `WorldPathFinder::FindPath` with the context's navigation.

### 9.2 `ScriptBindings`, split by area

| Class | Bindings |
|---|---|
| `ControlBindings` | `step_time`, `note_progress`, `last_progress`, `relog`, `stop_script`, `stop_account`, `send_bot_message` |
| `PlayerBindings` | `tick` and `get_tick`, `is_placed`, `is_members`, the position and distance bindings, `get_pid`, `get_name`, `get_combat_level`, `get_run_energy`, `get_weight`, `is_moving`, `get_walk_destination`, `in_combat`, `is_running`, `took_damage`, `get_local_player`, the stat and HP bindings, `get_varp` |
| `WorldBindings` | NPCs, players, ground items, locs, `get_npc_type`, `get_item_type`, `get_loc_type`, `find_type_ids`, `in_scene`, `square_locs` |
| `InventoryBindings` | `get_inventory`, `get_equipment`, the count and item lookups, `get_empty_slots`, `is_inventory_full`, `has_inventory`, `get_inventories` |
| `InterfaceBindings` | The modals, components, open interfaces and tabs, `get_texts`, `modal_changes`, `find_continue`, the chat and make bindings, `is_count_dialog_open`, `get_player_menu`, `can_set_run`, `is_appearance_screen_open` |
| `ActionBindings` | Walking, interacting, using, casting, clicking, `continue_dialogue`, `answer_count`, `close_interfaces`, `set_run`, `set_appearance` |
| `NavigationBindings` | `can_reach_*`, `is_reachable`, `find_path`, `can_step`, `find_world_path`, `nav_data`, `walk_tile` |
| `SocialBindings` | `say`, `send_pm`, `command`, friends and ignores, `message_mark`, `game_messages_since` |

Each class has one public member, `static void Add(std::vector<BoundFunction_s>& functions, const GameCache_s& cache)`. `ScriptBindings::Bind` collects every class's functions, binds them in `_core`, and binds `BUILTIN_FUNCTIONS` into builtins as well, as today. `BindingSupport` holds `Guard`, the `Return...` helpers, `BoundFunction_s`, and the per-VM table of contexts that `Bind` and `Unbind` fill and `GetContext()` reads. Today that table is `boundApis` in `ScriptBindings.cpp`'s anonymous namespace.

A binding only converts arguments and results. The bindings that do more today hand it to `Game/` (§8): `took_damage` to `EntityStatus`, `get_hp_percent` to `Stat_s::GetPercent`, `find_type_ids` to `GameCache_s::FindTypeIds`, and `in_rect` to a `Tile_s` check. Two filtering loops stay as they are, `game_messages_since` and `get_inventories`, because what they return is shaped for the stdlib.

### 9.3 `PyConvert`, split by direction

| Class | Holds |
|---|---|
| `PyValue` | Plain values both ways: `FromString`, `FromPoint`, `FromList`, `FromOptional`, `ToInt`, `ToBool`, `ToString`, `ToOptionalInt`, `ToOptionalBool`, `ToU16`; and `IsInstance`, `GetField`, and the type name for error messages |
| `PyObjects` | Game values into the stdlib's classes: the class and field names, `FromNpc` to `FromComponent`, the component and button type names, and the `Set...` helpers |
| `PyArgs` | Script arguments into game values: `ToOp`, `ToOpChoice`, `ToIds`, `ToNames`, `ToIndex`, `ToItem`, `ToGroundItem`, `IsLoc`, `ToLoc`, `ToPoints`, with `GroundItemRef_s`, `LocRef_s` and `OpChoice`; and from `ScriptBindings.cpp`, `ToCoord`, `ToRadius`, the three filter builders, `ToLayer`, `ToBytes`, `ToRoot` |

`ScriptTypeError` and `ScriptRaisedError` move from `PyConvert.hpp` to `Script/Error/`.

### 9.4 `ScriptHost`

| Class | Holds |
|---|---|
| `LoopSchedule` | `LoopWait_e`, the five wait members, `IsLoopDue`, `ScheduleLoop` and the timing half of `GetNextLoop`. Plain C++: `ScriptHost` reads the `(kind, value)` tuple and passes it in, so the class can be tested without a VM |
| `ScriptHooks` | `HasHook`, `CallHook`, `Dispatch`, and the read of `_commands` that `GetCommands` does. It's made with the VM, a function that reports a failed hook (`ScriptHost::Fail`), one called after each call (`ApplyStopRequest`) and one that says whether the script is still running. `ScriptHost` remakes it on every load |
| `EventDispatcher` | `DispatchEvents`, `DispatchEvent`, `DispatchBackpack`, `DispatchMessages` and `DescribeChatType`; the `m_lastEvent`, `m_lastMessage` and `m_backpack` they keep; and their part of `SkipToPresent`. It stops at the same points as today: before each event, each message and each backpack slot, once the script isn't running |
| `ScriptHost` | Loading, reloading and watching files, the login sync, starting, the tick hook, upkeep, the loop, the bot message and console command queues, running `on_progress_report` when `Account` asks (§10.1), and the status |

`DispatchEvent`'s long `if` chain over `std::get_if` is moved as it is. Converting it to `std::visit` is possible, but it would be a behaviour-neutral rewrite, not a move, so it waits until the split has landed.

---

## 10. Accounts

### 10.1 Progress reports

`progressReportMinutes` is an account setting, and the report goes to the account's file, so the account decides when one is due. `ProgressReport_s` moves from `Script/` to `Accounts/` in phase 1, as a plain move. The schedule follows in phase 9.

`ScriptHost` gives up `ScriptHostOptions_s::progressInterval`, `onProgressReport` and `m_nextReport`, and gains:

```cpp
// Started and running, with the player placed and settled: when the loop and the hooks run.
[[nodiscard]] bool IsActive() const;
// When on_start first ran; a reload doesn't reset it.
[[nodiscard]] std::optional<Clock::time_point> GetStartTime() const;
[[nodiscard]] bool HasProgressReport() const;
// Nullopt without on_progress_report, or when it raised, which fails the script as it does today.
[[nodiscard]] std::optional<ProgressReport_s> RunProgressReport(Clock::time_point now);
```

`RunProgressReport` is today's private `RunProgressReport`, returning the report instead of calling back with it. Its run time still counts from `GetStartTime()`.

The schedule moves to a new class:

```cpp
// When the script's on_progress_report is due, and where the report goes: the log, and the account's progress file.
class ProgressReporter
{
public:
    using Clock = std::chrono::steady_clock;

    // A zero interval turns reports off.
    ProgressReporter(std::chrono::minutes interval, std::filesystem::path file, std::shared_ptr<Logger> logger);

    void Step(Clock::time_point now, ScriptHost& script);
};
```

`Step` keeps today's rules. It does nothing while the script isn't `IsActive()`. The first report falls due one interval after `GetStartTime()`. Once a report is due and the script is active, the next one is due an interval after now, whether or not the script has `on_progress_report`. A due report waits while the account is out of game, and runs once the script is active again.

`Account` owns a `ProgressReporter` in place of `m_progressFile`, and gives it today's file path. `Account::StepScript` calls `Step` straight after `m_script->Step(now)`, and before `Flush`, so anything the report sends goes out in the same pass. `Account::WriteProgressReport` moves into `ProgressReporter` with its log line and its warning when the file can't be written. The warning that a script without `on_progress_report` makes `progressReportMinutes` pointless moves from `ScriptHost`'s constructor to `Account`'s, which checks `HasProgressReport()` once the script has loaded.

Tests:

- The timing cases in `ScriptHostTests` ("asks for progress reports") move to `tests/Accounts/ProgressReporterTests.cpp`. It needs a `ScriptHost`, so `ScriptHostTests`'s `HostFixture` moves to `tests/Support/Script/HostFixture.hpp` / `.cpp`.
- The hook's cases (a report that isn't a dict fails the script; the rows and their text) stay in `ScriptHostTests` and call `RunProgressReport` directly.
- The warning's case moves to `AccountTests`.
- New: a report that falls due while the account is out of game runs once it's back, and the next one counts from then.

### 10.2 `AccountRunner`

`AccountRunner` keeps the run loop, the login schedule, interrupts, `Quit` (because it changes who logs in) and the `HandleCommand` entry point. The rest of the command handling moves to `AccountCommands`:

```cpp
// The console's commands other than quit, and the script commands it passes on.
class AccountCommands
{
public:
    static constexpr auto HELP = "help"sv;
    static constexpr auto STATUS = "status"sv;
    static constexpr auto QUIT = "quit"sv;
    static constexpr auto EXIT = "exit"sv;
    static constexpr auto LOG_LEVEL = "loglevel"sv;
    static constexpr auto SAY = "say"sv;

    AccountCommands(const std::vector<std::unique_ptr<Account>>& accounts, Logger& logger);

    // By its file's name or its username, in any case.
    [[nodiscard]] Account* FindAccount(std::string_view name) const;
    void ShowHelp(const Account* target) const;
    void ShowStatus(const Account* target) const;
    void SetLogLevel(const Account* target, std::span<const std::string> args) const;
    void Say(Account* target, std::string_view text) const;
    void SendToScripts(Account* target, const ConsoleCommand_s& command) const;
};
```

`HandleCommand` becomes: parse the line with `ConsoleCommandParser`, find the target, then dispatch on the name. `Application` prints `AccountCommands::HELP` where it printed `AccountRunner::COMMAND_HELP`.

### 10.3 `Account`

- `LogSummary` and `DescribeNearestNpcs` become `IdleSummary::Log(Logger&, const GameState_s&)`, which reads hitpoints through `Stat_e::Hitpoints`.
- `WithServer` becomes `ConfigOverrides::ForAccount` (§6.5).
- `AddSettingDefaults` calls `AccountFile::AddScriptSettings` and joins the keys with `StringUtils::Join`.

The relog and relogin state machine stays in `Account`. It touches every other member, and it's what the class is for.

---

## 11. Behaviour that changes

| Where | Today | After |
|---|---|---|
| A `client.jsonc` that can't be opened | `Failed to open config file <path>` | `Failed to read config file <path>`. The second message, for a read that fails after the file opened, was already `Failed to read config file` |
| An account file that can't be opened or read | `Failed to open config file <path>` | `Failed to read account file <path>` |
| A progress report that falls due in a step | Runs after that step's events, tick hook and upkeep, and before its `loop()` | Runs after the whole of `ScriptHost::Step`, `loop()` included (§10.1). A report's counters can include one more pass of `loop()` than they would today. The interval, the first report's delay and the run time are unchanged |
| A script without `on_progress_report` on an account with `progressReportMinutes` | The warning is logged before `Loaded script <file>` | The same warning, logged after it |

No test checks either message text today. `StringUtilsTests` pins the whitespace rules of §4.1, which change nothing anyone can see.

Code API changes, all internal: `Logger`'s static formatting functions move to `LogFormatter` and `ConsoleOutput`, `ConfigFile::LoadAccount` becomes `AccountFile::Load`, `Application::ParseCommandLine` becomes `CommandLine::Parse`, `AccountRunner::COMMAND_*` become `AccountCommands::*`, `Navigation_s` becomes `Navigation` with getters, `ScriptHostOptions_s` loses `progressInterval` and `onProgressReport` (§10.1), and `ScriptApi` is gone (§9.1).

---

## 12. Phases

Each phase:

- Moves files in a commit of its own, made with `git mv` and only the include paths changed, before the commits that change those files.
- Builds `windows-debug` and `windows-release`, with zero warnings. Release is where warnings are errors (`/WX`, `-Werror`), and Release is also where `NDEBUG` takes the call site off log lines.
- Runs the whole test suite with `ctest --preset windows-debug` and `--preset windows-release`.
- Runs clang-format on the files it touched.
- Updates every doc that names a file it moved (§13).

| # | Phase | Contents | Done when |
|---|---|---|---|
| 1 | Moves | `Core/` emptied into `Utils/`, `Console/` and `Config/`; `Application.hpp` / `.cpp` into `Application/`, with CONVENTIONS §1 and §11 changed to match (§13); every `Error/` folder; `NavJson` to `Game/Nav/`; `ChatDialog` and `InterfaceView` to `Game/Interface/`; `ConsoleCommand_s` to `Console/`; `ProgressReport_s` to `Accounts/`; the tests to match, and every test helper to `tests/Support/` (§2); CONVENTIONS.md (§13). Include paths only, apart from CONVENTIONS.md | `src/Core/` and `tests/Core/` are gone, every file in `tests/` outside `Support/` is a `...Tests.cpp`, everything builds and passes, and `git log --follow` traces each file |
| 2 | Utils | `StringUtils`, `FileUtils`, `BigUInt::ToHexString`, `Io/WebSocketUrl`; every copy in §4.1 and §4.2 replaced; `StringUtilsTests`, `FileUtilsTests` | No anonymous namespace defines a copy of a `StringUtils` or `FileUtils` function |
| 3 | Console | The `Logger` split, `LogFormatter`, `ConsoleOutput`, `Terminal`, `LogLevelNames`, `LogSinks`, `ConsoleLogScope`, `ScriptCommand_s` in its own header, `ConsoleCommandParser`; tests for the parser and the names | `<Windows.h>` appears only in `Terminal.cpp`. Today `ConsoleInput.cpp` and `Logger.cpp` both include it |
| 4 | Config | The struct headers, `ConfigJson`, `ConfigValidator`, `ConfigFile` and `AccountFile`, `AccountDirectory`, `ConfigOverrides`, `JsoncScanner`; `ConfigFileTests` split into `ConfigFileTests` and `AccountFileTests` | `<nlohmann/json.hpp>` appears in `Config/` only in `ConfigJson.cpp` and `JsoncEditor.cpp` |
| 5 | Application | `CommandLine`, `InterruptSignal`; `ApplicationTests` becomes `CommandLineTests`. A live run, with a scratch `client.jsonc` and `--account`, logs as it did before phase 1 | `Application.cpp`'s anonymous namespace is empty and gone |
| 6 | Game constants and types | Everything in §8.1 and §8.3: `Stat_e`, `GameTick`, `MenuOp`, `BuildArea_s.hpp`, `WorldMap::LOC_LAYERS`, `Stat_s::GetPercent`, `GameState_s::GetStat`, the namespaces made classes, the `Nav/` structs, `Navigation` | `grep` finds no `HITPOINTS`, `MILLISECONDS_PER_TICK`, `MIN_OP` or `LEVELS = 4` outside the one definition each |
| 7 | Game knowledge | Everything in §8.2. `ScriptApi` forwards to the new classes for this phase only, so the bindings don't change yet. New tests: `MenusTests`, `EntityQueryTests`, `InventoryQueryTests`, `InteractionRoutesTests`, with the matching cases moved from `ScriptApiTests` | Each new class has tests that don't make a VM |
| 8 | Script | §9: `ScriptContext`, `ScriptActions` and `ScriptControl` replace `ScriptApi`; the bindings split and call `Game/` directly; `PyConvert` split; `ScriptHost` split; `LoopScheduleTests`. A live run with an example script, such as `scripts/examples/walker.py`, behaves as it did before | `ScriptApi.hpp` is gone; no file in `Script/Bindings/` is over 500 lines |
| 9 | Accounts | §10: `ProgressReporter` and the schedule out of `ScriptHost`, `AccountCommands`, `IdleSummary`; `ProgressReporterTests`, and `HostFixture` shared | `ScriptHostOptions_s` has no progress fields; `AccountRunner.cpp` holds no command bodies other than `Quit` |
| 10 | Optional | `GameClient`'s retry backoff (`GetRetryDelay`, `ScheduleRetry`) as a `RetrySchedule` class with its own tests; `ServerPacketDecoder`'s `DecodePacket` switch split by area, as the entity and zone decoders already are; `TypeDecoder` split into one decoder per type | Each is its own commit, and can be dropped |
| 11 | Docs | A last pass over `docs/` for anything the phases missed | No doc names a path that doesn't exist |

Phases 1 to 6 are low risk: they move code and replace exact copies. Phases 7 and 8 change the most code. Phase 7 is complete on its own, because `ScriptApi` keeps forwarding, so it can land and be reviewed before phase 8 removes `ScriptApi`.

---

## 13. Effect on the docs and the other plans

[CONVENTIONS.md](CONVENTIONS.md) changes in phase 1, so the guide matches this project:

- §1: only `pch.hpp` and `main.cpp` must stay at the root of `src/`, and `Application.hpp` / `.cpp` live in `src/Application/` with the code that supports them. The example tree and §11's checklist follow.
- The examples' `Core/` paths become this project's folders:
  - `Core/ConfigFile` becomes `Config/ConfigFile`, in §1's tree, §5's include examples and §10.
  - `Core/StringUtils` becomes `Utils/StringUtils`, in §1 and §5.
  - `Core/StringHash_s` becomes `Utils/StringHash_s`, in §1 and §10.
  - `Core/Endian` becomes `Utils/Endian`, in §1 and §9.
  - `Core/Platform` becomes `Utils/Platform`, in §8.
  - `Core/ConfigError` becomes `Config/Error/ConfigError`, in §8.
  - §1's sample subsystems, `Core/` and `Graphics/`, become `Utils/` and `Graphics/`.
- Two rules this plan follows are written down where those examples are:
  - §1: helpers that several subsystems share go in `Utils/`, as static members of a class per kind.
  - §8: a project exception type lives in an `Error/` subfolder of its subsystem's folder.

Docs that name a moved file, to update in the phase that moves it:

| Doc | Names |
|---|---|
| [PacketDesign.md](PacketDesign.md) | `src/Core/Endian.hpp`, `src/Core/BigUInt.hpp`, `src/Core/Logger.hpp` |
| [LoggerDesign.md](LoggerDesign.md), [WebSocketDesign.md](WebSocketDesign.md), [CacheDesign.md](CacheDesign.md), [ConfigDesign.md](ConfigDesign.md) | `Core/Logger`, `Core/ConfigFile` |
| [ScriptingDesign.md](ScriptingDesign.md), [BotApiDesign.md](BotApiDesign.md) | `ScriptApi`, `ScriptBindings`, `PyConvert` |

[RevisionDesign.md](RevisionDesign.md):

- `Revision_e` goes in `Config/Revision_e.hpp`, not `Core/`. The revision is a setting, read with the rest of `login`, and the cache loader and `Protocol` include it from there.
- The `login.revision` rule goes in `ConfigValidator`. Its tests go in `tests/Config/ConfigFileTests.cpp`.
- `Protocol` can use `MenuOp::MIN` and `MAX` where it checks ops.

[ProxyDesign.md](ProxyDesign.md):

- `ProxySettings_s` goes in `Config/ProxySettings_s.hpp`, since both `Config_s` and `AccountConfig_s` hold one, as `ServerSettings_s` does (§6.1).
- `ValidateProxy` goes in `ConfigValidator`, and the `proxy` override in `ConfigOverrides::ForAccount`, which is that plan's `WithAccountOverrides` (§6.5).
- Its config tests go in `tests/Config/`.

Whichever lands first, the other's plan gets these paths before its work starts.

---

## 14. As built

Phases 1 to 9 and 11 are done. Phase 10 is not started. Where the code differs from the plan above:

| Plan | As built |
|---|---|
| §8.2's query classes | Two more: `PlayerQuery` (moving, in combat, running, a stat, an open interface, a component's text) and `ReachQuery` (`CanReachEntity`, `CanReachGroundItem`, `CanReachLoc`, `IsReachable`, `CanStep`, `FindPath`). `ScriptContext` makes each query on demand with `GetEntities`, `GetInventories`, `GetPlayer`, `GetReach` and `GetInterfaces` |
| §6.4: `<nlohmann/json.hpp>` only in `ConfigJson.cpp` and `JsoncEditor.cpp` | `JsoncScanner.cpp` includes it too, to decode the escapes in a member's key |
| §8.3: `Navigation` | It reads every nav file itself, and `NavGraph` takes the JSON text rather than a path |
| §9.3: the argument helpers | `ToRoot` is in `PyArgs`, since both `InterfaceBindings` and `ActionBindings` use it |
| §8.1: constants | Three more: `Tile_s::MAX_COORD` with `Tile_s::IsInRect`, `MapSquare::MAX_SQUARE`, and the name and id lookups on `GameCache_s` (`FindLocName`, `FindLocIds` and the NPC and object ones) that several bindings had written out |
| §2's test helpers | `tests/Support/Game/QueryWorld` builds the state the `Game/Query` tests search, and `tests/Support/Script/HostFixture` is shared by the host, progress and account tests |
| §12: docs in the phase that moves a file | Every doc was updated in phase 11. The plans not yet built, [RevisionDesign.md](RevisionDesign.md) and [ProxyDesign.md](ProxyDesign.md), now use §13's paths. The other designs' change records keep the names they had at the time, under a note that points here |
