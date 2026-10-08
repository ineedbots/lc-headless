# Config Design

Design and test plan for `ConfigFile`, which loads the client's settings from a JSON file with comments, and writes a sample file when there is none. It replaces the reference client's INI config. The settings structs are converted in both directions with nlohmann/json's `NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_WITH_DEFAULT`, so a missing key takes its default, and a validation pass checks the rules their types don't carry. Code style follows [CONVENTIONS.md](CONVENTIONS.md). It builds on the project setup in [PacketDesign.md](PacketDesign.md) §7.5 and §8, parses RSA keys with `BigUInt` ([PacketDesign.md](PacketDesign.md) §5), checks the server URL the same way `WebSocketClient` does ([WebSocketDesign.md](WebSocketDesign.md) §3), and logs through `Logger` ([LoggerDesign.md](LoggerDesign.md)).

Reference sources:

- `rs2004-headless - Copy/headless-client/src/config.hpp` / `.cpp`: the previous INI config, `ClientConfig`
- `rs2004-headless - Copy/headless-client/tests/config_tests.cpp`: its tests
- `rs2004-headless - Copy/client.ini`: the settings file converted in §3
- `rs2004-headless - Copy/headless-client/src/main.cpp`, `protocol.cpp`: how the settings were used

---

## 1. Decisions

| Topic | Decision |
|---|---|
| Format | JSON with `//` and `/* */` comments, parsed by nlohmann/json with `ignore_comments = true`. Apart from comments it is strict JSON, so trailing commas, single quotes and `#` comments are syntax errors |
| File | `client.jsonc` in the working directory, or the path given as the first command-line argument. The `.jsonc` extension makes editors highlight comments instead of flagging them as errors. `client.jsonc` holds the password, so it's git-ignored |
| Sample | When the file doesn't exist, `Load` writes a sample there and throws a `ConfigError` asking for it to be filled in. The sample is `Config_s{}` serialized, so it always has exactly the keys and defaults the structs have |
| Shape | `ConfigFile` is a non-instantiable class with static `Load`, `Parse` and `Serialize`, like `StringUtils` in CONVENTIONS §5. `Load` and `Parse` return a `Config_s`: plain data, one struct per section. Values come out already converted to the types the client uses (`BigUInt`, `LogLevel_e`, `std::chrono::seconds`), so no code downstream parses or validates anything |
| Ownership | `Application` holds the loaded config in a `std::shared_ptr<const Config_s>` and passes it to any class that needs it. A class that keeps it stores its own copy of the pointer, so ownership is genuinely shared (CONVENTIONS §8) and no class can outlive the config it reads. The `const` keeps the settings read-only after loading, for every holder |
| Conversion | `NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_WITH_DEFAULT` generates `from_json` and `to_json` for `Config_s` and the four section structs. Each type nlohmann can't convert by itself (`BigUInt`, `LogLevel_e`, `std::chrono::seconds` and the CRC array) gets an `nlohmann::adl_serializer` specialization with both directions. All of it lives in `ConfigFile.cpp` |
| Macros | A deliberate exception to CONVENTIONS §6. The macros generate a `from_json` and a `to_json` per struct that would otherwise have to be written, and kept in step with the struct, by hand |
| Keys | The JSON keys are the C++ member names, because the macro uses each member's name as its key. They are camelCase (CONVENTIONS §6), and a key's path in the file is its path in code: `login.rsaModulus` in the file is `config.login.rsaModulus` |
| Key order | Reading uses `nlohmann::json`. Writing uses `nlohmann::ordered_json`, so a written file lists sections and keys in declaration order, the order of §3, instead of alphabetically |
| Defaults | Every key is optional. The macro reads each member with `value(name, default)`, so a missing key keeps the member's initializer. Five initializers break their own key's rule: the empty `url`, `username` and `password`, and the zero RSA modulus and exponent. Leaving out one of those keys fails in `Validate`, which names it. A missing `crcs` loads as nine zeros, which pass, and fails later, when a server that checks CRCs rejects the login |
| Rules | Rules that a type doesn't carry, such as the username's length or the range of the idle time, are checked by `Validate` after conversion |
| Numbers | Counts and IDs are JSON integers. CRCs and RSA values are strings holding a decimal or `0x`-hex number, because JSON has no hex literals and a 512-bit modulus doesn't fit in a JSON number. Hex is case-insensitive when read, so `0xDE5B3345` and `0xde5b3345` are the same value. `Serialize` writes lowercase |
| Strictness | `Validate` is the only check beyond what conversion does: a wrong type, or a value that breaks its rule, is an error. Unknown sections and keys are ignored without a warning, and a repeated key takes its last value, as nlohmann does by default |
| Errors | Everything `ConfigFile` throws for a missing, unreadable or invalid file is a `ConfigError`, the type in CONVENTIONS §8. Messages start with the dotted path of the key (`login.crcs: ...`), and `Load` puts the file path in front. `JSON_DIAGNOSTICS` makes nlohmann's own conversion errors carry the path |
| Secrets | No message or log line contains a value from the file. Syntax errors give a line and a column, but no excerpt. nlohmann's conversion errors name types and keys, never values |
| Logging | One warning, when TLS verification is turned off, logged through the `Logger&` that `Load` and `Parse` take. Loading logs nothing else |
| Dependency | nlohmann/json is used only in `ConfigFile.cpp`. No header exposes it |
| Threading | `ConfigFile` has no state. A loaded `Config_s` is `const` behind its `shared_ptr`, so any thread can read it, and copying or releasing the pointer is thread-safe |

Rejected:

- **A generic wrapper**, such as `config.Get<u16>("client.logoutComponent")`. Every consumer would then parse and range-check values itself, and a misspelled key would only surface when the code that reads it runs.
- **A `Config` class with private members and getters.** Validation happens once, at load, and after that the values are plain data, so CONVENTIONS §6 makes them a struct. Getters would only stop code from building a section by hand, which is exactly what tests of the classes that use it want to do.
- **A key table with one reader per key,** like the reference's field table. It could check integer ranges exactly and mark keys as required, but every key needed a row and a hand-written reader. The macros generate the reading and the writing, and `Validate` keeps the rules.
- **`NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE`, without defaults.** Every key would be required. Adding a setting would break every existing file until it gained the key, and files would have to spell out values that rarely change. The keys that can't do without a value fail anyway, in `Validate`.
- **`NLOHMANN_JSON_SERIALIZE_ENUM` for `LogLevel_e`.** An unknown string silently becomes the first enumerator, `Verbose`.
- **A hand-written sample text with a comment on each key.** It would explain more, but it would drift from the structs, and nlohmann can't write comments, so it couldn't be generated. The serialized sample can't drift, and §3's table explains the keys.
- **Passing nlohmann's syntax error message through.** Lexer errors quote the text they stopped in, as in `last read: '"hunter\q'`. A password with a stray backslash or quote would end up in the log.
- **CRCs as JSON numbers.** They could only be written in decimal, but CRCs are written and compared in hex.

---

## 2. Layout

```
rs2004-headless/
├── .gitignore
├── CMakeLists.txt
├── vcpkg.json
├── docs/
│   └── ConfigDesign.md
├── src/
│   ├── main.cpp
│   ├── Application.hpp
│   ├── Application.cpp
│   └── Core/
│       ├── ConfigError.hpp
│       ├── ConfigFile.hpp
│       └── ConfigFile.cpp
└── tests/
    └── Core/
        └── ConfigFileTests.cpp
```

- `Config_s` and the four section structs live in `ConfigFile.hpp`, the header of the class that reads and writes them.
- `ConfigFile.hpp` includes `BigUInt.hpp`, because `BigUInt` is a member of `LoginSettings_s`, and `Logger.hpp`, because `LogLevel_e` is a member of `ClientSettings_s` and `Logger` appears in `Load`'s and `Parse`'s prototypes.
- `ConfigError.hpp` is header-only, exactly as in CONVENTIONS §8. `ConfigFile.hpp` doesn't include it, because no prototype in it uses it. `ConfigFile.cpp` throws it, so it includes it, and so does any code that catches it.
- `ConfigFile.cpp` includes `BigUInt.hpp`, `ConfigError.hpp` and `Logger.hpp` itself, as CONVENTIONS §5 requires, then `<ixwebsocket/IXUrlParser.h>` and `<nlohmann/json.hpp>`. IXWebSocket is already a dependency ([WebSocketDesign.md](WebSocketDesign.md) §2).
- `vcpkg.json` gains `"nlohmann-json"`.
- CMake:
    - `find_package(nlohmann_json CONFIG REQUIRED)`. The library target links `nlohmann_json::nlohmann_json` privately, because no public header includes it. The test executable links it too, because the tests build their inputs with it (§6.1).
    - The library target gets `JSON_DIAGNOSTICS=1` as a private compile definition, so nlohmann's exceptions name the path of the value that failed. Since nlohmann 3.11 the setting is part of its ABI namespace, so the test executable, which doesn't set it, can't clash with the library.
- `pch.hpp` gains `<charconv>` for parsing CRCs and `<iterator>` for reading the file.
- `.gitignore` gains `client.jsonc`. No example file is committed: the first run writes one (§3).

---

## 3. File format

### Example

`client.ini`, converted:

```jsonc
{
    "server": {
        "url": "ws://localhost:80",
        // "url": "ws://127.0.0.1:80",
        // "origin": "http://localhost",
        // "url": "wss://w1.rs2b2t.com:443",
        "origin": "https://w1.rs2b2t.com",
        "tlsCaFile": "SYSTEM"
    },
    "login": {
        "crcs": ["0x00000000", "0xde5b3345", "0x6026f8fe", "0x07550309", "0x9a13636e", "0xca2717bd", "0x368f1792", "0x1b1fb6b2", "0xa7129379"],
        "rsaModulus": "0x88c38748a58228f7261cdc340b5691d7d0975dee0ecdb717609e6bf971eb3fe723ef9d130e4686813739768ad9472eb46d8bfcc042c1a5fcb05e931f632eea5d",
        "rsaExponent": "0x81f390b2cf8ca7039ee507975951d5a0b15a87bf8b3f99c966834118c50fd94d",
        /*
        "rsaModulus": "0xa7366d28aee360c6a5a49fadaac884826573f09870f3a031aece6d146277d85b6f79dae141769b16210046f6739d23b4b0d1160ef94c44771b9e6ecbd1917ba64eca7aab1c0265c8ef0205ab4f1033440fd9fe719f01554b9c50aa17cb8bd6cc5c7602831f94ae49121a8755ee9e76697b9af7848c85da834ca6ae9a1e33d32d",
        "rsaExponent": "0x10001",
        */
        "lowMemory": false,
        "revision": 289
    },
    "client": {
        "logoutComponent": 2458,
        "logLevel": "verbose",
        "idleSeconds": 5
    },
    "scripting": {
        "accountsDirectory": "accounts",
        "scriptsDirectory": "scripts",
        "callTimeoutMs": 1000,
        "pollIntervalMs": 10,
        "loginIntervalSeconds": 2,
        "killGraceSeconds": 30,
        "progressDirectory": "progress"
    }
}
```

`tlsCaFile`, `lowMemory`, `revision`, `logoutComponent`, `idleSeconds` and the whole `scripting` section hold their defaults here, so this file could leave them out and load the same. The account that `client.ini` held now goes in its own file (see Account files, below).

### Generated sample

What `Load` writes when the file doesn't exist. This is the exact text, byte for byte, with LF line endings and a final newline:

```jsonc
// Sample config, written because none was found.
// Set server.url and the login CRCs and RSA key, then run again.
// Each account goes in its own file in scripting.accountsDirectory.
{
    "server": {
        "url": "",
        "origin": "",
        "tlsCaFile": "SYSTEM"
    },
    "login": {
        "crcs": [
            "0x00000000",
            "0x00000000",
            "0x00000000",
            "0x00000000",
            "0x00000000",
            "0x00000000",
            "0x00000000",
            "0x00000000",
            "0x00000000"
        ],
        "rsaModulus": "0x0",
        "rsaExponent": "0x0",
        "lowMemory": false,
        "revision": 289
    },
    "client": {
        "logoutComponent": 2458,
        "logLevel": "info",
        "idleSeconds": 5
    },
    "scripting": {
        "accountsDirectory": "accounts",
        "scriptsDirectory": "scripts",
        "callTimeoutMs": 1000,
        "pollIntervalMs": 10,
        "loginIntervalSeconds": 2,
        "killGraceSeconds": 30,
        "progressDirectory": "progress"
    }
}
```

- The three comment lines are the fixed `SAMPLE_HEADER` constant. Everything after them is `Serialize(Config_s{})`.
- Every value is its key's default. A file that sets nothing behaves exactly like this one: it fails `Validate`, starting with `server.url`.

### Keys

| Key | Type | Default | Rule |
|---|---|---|---|
| `server.url` | string | `""` | A URL that `ix::UrlParser` accepts, with the scheme `ws` or `wss`: the check `WebSocketClient::Connect` makes ([WebSocketDesign.md](WebSocketDesign.md) §3, step 1) |
| `server.origin` | string | `""`: no `Origin` header | Empty, or printable ASCII |
| `server.tlsCaFile` | string | `"SYSTEM"` | Not empty: a PEM CA bundle path, `SYSTEM` for the platform trust store, or `NONE` for no verification. Only used for `wss` |
| `login.crcs` | array | Nine `"0x00000000"` | Exactly 9 strings, each a number from 0 to `0xFFFFFFFF`. Stored as `s32` with the same 32 bits, the type `Packet::P4` and `Packet::GetCrc` use |
| `login.rsaModulus` | string | `"0x0"` | A number that `BigUInt::Parse` accepts, greater than 1 |
| `login.rsaExponent` | string | `"0x0"` | A number that `BigUInt::Parse` accepts, greater than 0 |
| `login.lowMemory` | boolean | `false` | |
| `login.revision` | integer | `289` | `289`, the only revision the client speaks |
| `client.logoutComponent` | integer | `2458` | 0 to 65535 |
| `client.logLevel` | string | `"info"` | `verbose`, `info`, `warning` or `error` |
| `client.idleSeconds` | integer | `5` | 1 to 300. Stored as `std::chrono::seconds` |
| `scripting.accountsDirectory` | string | `"accounts"` | Not empty. The folder of account files, relative to the working directory |
| `scripting.scriptsDirectory` | string | `"scripts"` | Not empty. Where script files and their imports are found |
| `scripting.callTimeoutMs` | integer | `1000` | 10 to 60000. How long one call into a script may run. Stored as `std::chrono::milliseconds` |
| `scripting.pollIntervalMs` | integer | `10` | 1 to 1000. The longest the main loop waits between passes |
| `scripting.loginIntervalSeconds` | integer | `2` | 0 to 60. The gap between account logins |
| `scripting.killGraceSeconds` | integer | `30` | 0 to 600. How long a script that handles Ctrl+C has to stop its account |
| `scripting.progressDirectory` | string | `"progress"` | Not empty. Where progress reports are written, one file per account ([ScriptingDesign.md](ScriptingDesign.md) §12) |

- **Keys that must be set.** The defaults of `server.url`, `login.rsaModulus` and `login.rsaExponent` break their own rules. A file that leaves one of them out fails in `Validate`, which names the key.
- **`login.crcs`** defaults to nine zeros, which are valid numbers, so a file without it loads. A server that checks CRCs then rejects the login, and the login code reports that.

### Rules

- **Structure.** The top level is an object, and each section present is an object. Any section or key can be left out, and takes its default. Unknown sections and keys are ignored without a warning, so a misspelled key is ignored too, and its member keeps the default. The one exception is a leftover `account` section: it isn't read, and a warning says it belongs in an account file now.
- **Repeated keys.** A key set twice in the same object takes its last value. With alternatives kept as comments, as in the example, forgetting to comment one out means the later line wins.
- **Types.** Strings, booleans and arrays must have their JSON type, and a key set to `null` is a wrong type. To get a key's default, leave it out.
- **Integers.** nlohmann converts any JSON number, and a boolean, to an integer member with a `static_cast`:
    - A fraction is truncated: `5.5` reads as 5.
    - A 16-bit key wraps: `-1` reads as 65535, and `65536` as 0.
    - A boolean reads as 0 or 1.

    `Validate` then checks the converted value against the key's rule, where it has one. So `"idleSeconds": -5` still fails, but `"logoutComponent": -1` loads as 65535.
- **Numbers in strings** are decimal digits, or `0x` or `0X` followed by hex digits in either case. `"0xde5b3345"`, `"0XDE5B3345"` and `"0xDe5B3345"` are the same number. There's no sign, no whitespace and nothing after the digits. This is the rule `BigUInt::Parse` already uses.
- **Printable ASCII** is `0x20` to `0x7E`, so a username can contain spaces.
- **Case.** Section names, keys and other string values, such as `"info"` and `"SYSTEM"`, are case-sensitive. Hex numbers are the one exception (above).

### Account files

Each account has its own file in `scripting.accountsDirectory`, read by `ConfigFile::LoadAccount` with the same syntax rules, error paths and secret handling as `client.jsonc`. The file name without `.jsonc` is the account's name. A missing file is an error; no sample is written, and `accounts/example.jsonc.sample` is the template instead. Account files are git-ignored.

```jsonc
{
    "username": "bot1",
    "password": "s3cret-pw",
    "enabled": true,
    "script": {
        "file": "examples/chicken_killer.py",
        "progressReportMinutes": 20,
        "settings": {"npc_ids": [41], "loot_goal": 3}
    }
}
```

| Key | Type | Default | Rule |
|---|---|---|---|
| `username` | string | none | 1 to 12 printable ASCII characters |
| `password` | string | none | 1 to 20 printable ASCII characters |
| `enabled` | boolean | `true` | |
| `server` | object or `null` | none: `client.jsonc`'s | The same keys and rules as `client.jsonc`'s `server` section, with `url` required. Logs this account into another world |
| `script` | object or `null` | none: the account idles | |
| `script.file` | string | none | Not empty. Relative to `scripting.scriptsDirectory` |
| `script.progressReportMinutes` | integer | `0`: no reports | 0 to 1440. How often the script's `on_progress_report()` is called ([ScriptingDesign.md](ScriptingDesign.md) §12). Stored as `std::chrono::minutes` |
| `script.settings` | object | `{}` | Any object. It's kept as JSON text and becomes the script's `settings` ([ScriptingDesign.md](ScriptingDesign.md) §7) |

---

## 4. ConfigFile

### Interface

```cpp
#pragma once

#include "BigUInt.hpp"
#include "Logger.hpp"

struct ServerSettings_s
{
    std::string url;
    std::string origin;
    std::string tlsCaFile = "SYSTEM";
};

struct AccountSettings_s
{
    std::string username;
    std::string password;
};

struct LoginSettings_s
{
    static constexpr std::size_t CRC_COUNT = 9;
    static constexpr u16 SUPPORTED_REVISION = 289;

    std::array<s32, CRC_COUNT> crcs{};
    BigUInt rsaModulus;
    BigUInt rsaExponent;
    bool lowMemory = false;
    u16 revision = SUPPORTED_REVISION;
};

struct ClientSettings_s
{
    u16 logoutComponent = 2458;
    LogLevel_e logLevel = LogLevel_e::Info;
    std::chrono::seconds idleSeconds = 5s;
};

struct ScriptingSettings_s
{
    std::string accountsDirectory = "accounts";
    std::string scriptsDirectory = "scripts";
    std::chrono::milliseconds callTimeoutMs = 1000ms;
    std::chrono::milliseconds pollIntervalMs = 10ms;
    std::chrono::seconds loginIntervalSeconds = 2s;
    std::chrono::seconds killGraceSeconds = 30s;
    std::string progressDirectory = "progress";
};

struct Config_s
{
    ServerSettings_s server;
    LoginSettings_s login;
    ClientSettings_s client;
    ScriptingSettings_s scripting;
};

struct ScriptConfig_s
{
    std::string file;
    // The settings object as JSON text; the script reads it as its settings global.
    std::string settings = "{}";
    // How often on_progress_report is called; zero turns reports off.
    std::chrono::minutes progressReportMinutes{0};
};

// One account file. Without a script, the account logs in and idles.
struct AccountConfig_s
{
    std::string name;
    AccountSettings_s credentials;
    bool enabled = true;
    std::optional<ScriptConfig_s> script;
};

class ConfigFile
{
public:
    static constexpr auto DEFAULT_PATH = "client.jsonc";
    static constexpr auto ACCOUNT_EXTENSION = ".jsonc";

    ConfigFile() = delete;

    [[nodiscard]] static Config_s Load(const std::filesystem::path& path, Logger& logger = *Logger::GetDefault());
    [[nodiscard]] static Config_s Parse(std::string_view text, Logger& logger = *Logger::GetDefault());
    [[nodiscard]] static std::string Serialize(const Config_s& config);

    // The account's name is the file's name without its extension.
    [[nodiscard]] static AccountConfig_s LoadAccount(const std::filesystem::path& path);
    [[nodiscard]] static AccountConfig_s ParseAccount(std::string_view text, std::string name);
};
```

- `AccountSettings_s` (the username and password) is no longer part of `Config_s`. `GameClient` takes it as a constructor argument, from an `AccountConfig_s`.
- Account files are only read, and a script's settings can be any object, so `AccountConfig_s` and `ScriptConfig_s` have hand-written `from_json` functions instead of the macro. Neither has a `to_json`, and there's no account sample to serialize.

- The member names are the JSON keys, so renaming a member renames its key.
- `ServerSettings_s` uses the member names and the `tlsCaFile` default of `WebSocketOptions_s`, so building the options is a member-by-member copy (see Usage).
- **The member initializers are the defaults.**
    - A key missing from the file keeps its member's initializer, and the generated sample is made of them.
    - Values that differ for each server or account are left empty or zero: `url`, the credentials, the CRCs and the RSA key. All of them but the CRCs fail `Validate` until the file sets them.
    - Code that builds a struct in place starts from the same values.
- `Load` reads a file and calls `Parse`, or writes the sample when there's no file. `Parse` and `Serialize` work on text, which is what the tests call.
- `Load` and `Parse` take the `Logger&` their one warning goes through, and default to the default logger when it is left out. They log only during the call and don't keep the logger, so a reference is enough, as with a function that only reads the config ([LoggerDesign.md](LoggerDesign.md) §3 Usage). `Serialize` doesn't log, so it takes none.
- `Serialize` is the inverse of `Parse`: for a valid `Config_s`, `Parse(Serialize(config))` gives the same members back.
- All the structs follow the rule of zero, so a `Config_s` moves cheaply out of `Load` and into its `shared_ptr`.
- `Load` and `Parse` return a plain `Config_s`, not a `shared_ptr`. The caller decides how to store it, and the tests compare members without dereferencing anything.

### Usage

Loading at startup. `Application` takes the logger from `main`, holds the config in a `std::shared_ptr<const Config_s> m_config`, and applies the log level first:

```cpp
Application::Application(const std::filesystem::path& configPath, std::shared_ptr<Logger> logger)
    : m_logger{std::move(logger)}
{
    assert(m_logger && "Application needs a logger");
    m_config = std::make_shared<const Config_s>(ConfigFile::Load(configPath, *m_logger));
    m_logger->SetLevel(m_config->client.logLevel);
    m_logger->Info("Config loaded from {}", configPath.string());
}
```

- `std::make_shared` moves the loaded `Config_s` into its one allocation, so nothing is copied.
- The config is loaded in the body, after the `assert`, so `Load` never gets a null logger, and nothing depends on the order the members are declared in.
- `Application` passes `m_logger` on to every class it builds that logs, such as `WebSocketClient` ([LoggerDesign.md](LoggerDesign.md) §3 Usage).
- `Application.hpp` includes `Core/ConfigFile.hpp`, because `Config_s` appears in a member's type, and `Core/Logger.hpp`, because `Logger` appears in the constructor and a member.

`main.cpp` creates the logger, as in [LoggerDesign.md](LoggerDesign.md) §3 Usage, and passes it and the optional path to `Application`. A `ConfigError` reaches the last-resort catch like any other failure at startup, and the message says which file and key are wrong. On a first run, the message is the one that asks for the new sample to be filled in.

```
Fatal error: client.jsonc: not found, so a sample was written there; fill it in and run again
Fatal error: client.jsonc: login.crcs: must be an array of 9 strings
```

```cpp
int main(int argc, char** argv)
{
    const auto logger = std::make_shared<Logger>();
    Logger::SetDefault(logger);
    try
    {
        const auto args = std::span{argv, static_cast<std::size_t>(argc)};
        auto app = Application{args.size() > 1 ? args[1] : ConfigFile::DEFAULT_PATH, logger};
        return app.Run();
    }
    catch (const std::exception& e)
    {
        logger->Error("Fatal error: {}", e.what());
        return EXIT_FAILURE;
    }
}
```

Passing it to a class that keeps it. The constructor takes the `shared_ptr` by value and moves it into place, the sink-parameter rule of CONVENTIONS §8:

```cpp
class LoginSession
{
public:
    explicit LoginSession(std::shared_ptr<const Config_s> config);

private:
    std::shared_ptr<const Config_s> m_config;
};

LoginSession::LoginSession(std::shared_ptr<const Config_s> config)
    : m_config{std::move(config)}
{
    assert(m_config && "LoginSession needs a config");
}
```

```cpp
auto session = LoginSession{m_config};
```

Connecting:

```cpp
const auto& server = m_config->server;
m_socket.Connect({.url = server.url, .origin = server.origin, .tlsCaFile = server.tlsCaFile});
```

- A null config is a bug in the caller, not bad input, so classes `assert` on it rather than throw (CONVENTIONS §8).
- A function that only reads the config during the call, and doesn't keep it, takes `const Config_s&`, and the caller passes `*m_config`. Copying a `shared_ptr` costs an atomic increment and decrement, and only a class that keeps the config needs a share of it.
- Tests of a class that takes the config build a `Config_s` in place, set the members they need, and pass `std::make_shared<const Config_s>(std::move(config))`. No file and no JSON are involved.

### Behaviour

- **Loading.**
    1. If `std::filesystem::exists(path)` is false, write the sample there (see Sample below) and throw `ConfigError{std::format("{}: not found, so a sample was written there; fill it in and run again", path.string())}`. A filesystem error from the check itself, such as a parent folder that can't be read, is a `std::filesystem::filesystem_error` and passes through unchanged.
    2. Open the file with `std::ifstream{path, std::ios::binary}`. Binary mode keeps the text identical to the file's bytes on every platform, so the line and column of a syntax error match what an editor shows. If the file can't be opened, throw `ConfigError{std::format("Failed to open config file {}", path.string())}`.
    3. Read it whole with `std::istreambuf_iterator`. If the stream reports `bad()`, throw `ConfigError` the same way.
    4. Call `Parse(text, logger)`. Catch `ConfigError` and throw a new one with `{path}: ` in front of the message. This is the "add context" case in CONVENTIONS §8.
- **Sample.** `WriteSample(path)`, in the anonymous namespace:
    - It opens `std::ofstream{path, std::ios::binary}`. Binary mode keeps the LF line endings on Windows (CONVENTIONS §7).
    - It writes `SAMPLE_HEADER` followed by `ConfigFile::Serialize(Config_s{})`, then flushes.
    - If the file can't be opened or the write fails, it throws `ConfigError{std::format("{}: not found, and a sample couldn't be written there", path.string())}`. A folder that doesn't exist isn't created.
    - It never overwrites anything, because `Load` only calls it when nothing is at the path.
- **Parsing.**

    ```cpp
    Config_s ConfigFile::Parse(std::string_view text, Logger& logger)
    {
        const auto root = ParseJson(text);
        if (!root.is_object())
        {
            throw ConfigError{"the top level must be an object"};
        }

        auto config = Config_s{};
        try
        {
            root.get_to(config);
        }
        catch (const nlohmann::json::exception& e)
        {
            throw ConfigError{DescribeConversionError(e)};
        }

        Validate(config);
        WarnIfTlsVerificationDisabled(config, logger);
        return config;
    }
    ```

    - `ParseJson`, `DescribeConversionError`, `Validate` and `WarnIfTlsVerificationDisabled` are in the anonymous namespace of `ConfigFile.cpp`.
    - `get_to` runs the macro-generated `from_json` for `Config_s`, which reads each section, and each section reads each member, with `value(name, default)`. A missing key keeps the default; a present one is converted, and a wrong type throws. A missing section is a section of defaults.
    - The first wrong type throws, and `Validate` stops at the first broken rule, so a file with several problems reports them one at a time.
    - Converting nlohmann's exceptions into `ConfigError` where they leave the third-party code follows CONVENTIONS §8.
- **Unknown keys.**
    - The macros only look up the keys the structs have, so any other section or key is never read and is ignored, without a warning.
    - A misspelled key is ignored the same way, and its member keeps the default. If that default breaks a rule, `Validate` reports the key the misspelling was meant to be: `account.usrname` gives `account.username: must be 1 to 12 printable ASCII characters`.
- **Serializing.**

    ```cpp
    std::string ConfigFile::Serialize(const Config_s& config)
    {
        // Parentheses, not braces: a braced ordered_json is an array holding the config.
        const auto json = nlohmann::ordered_json(config);
        return json.dump(INDENT) + '\n';
    }
    ```

    - `INDENT` is 4, the indentation of CONVENTIONS §7. `dump` writes `\n` between lines and nothing after the last one, so `Serialize` adds the final newline.
    - The parentheses are a deliberate exception to CONVENTIONS §8's `auto x = Type{...}`, explained in the "why" comment: `nlohmann::ordered_json{config}` would be an initializer list, which nlohmann turns into a one-element array.
    - `ordered_json` keeps keys in the order the macro-generated `to_json` writes them, which is the order the macros list the members.
    - No validation runs. Serializing an invalid config, such as `Config_s{}`, is how the sample is made.
- **Comments.** `ParseJson` calls `nlohmann::json::parse(text, nullptr, ALLOW_EXCEPTIONS, IGNORE_COMMENTS)`, with no parser callback and both flags as named `constexpr` constants set to `true`. nlohmann also skips a UTF-8 BOM, which some Windows editors write. A repeated key keeps its last value, so of two `url` lines the later one wins. Keys that are commented out never reach the parser, so they don't count.
- **Syntax errors.** `ParseJson` catches `nlohmann::json::parse_error` and throws `ConfigError{std::format("invalid JSON at line {}, column {}", line, column)}`:
    - The position comes from `e.byte`, nlohmann's 1-based offset of the byte where parsing stopped. The line is 1 plus the number of `\n` before that byte, and the column is the byte's 1-based offset within its line. Columns count bytes, not characters.
    - `e.what()` isn't used, because lexer errors quote the text they stopped in (§1, Rejected). The `catch` gets a "why" comment saying so.
- **Conversion.** After the anonymous namespace, `ConfigFile.cpp` specializes `nlohmann::adl_serializer` for the four types nlohmann can't convert, then applies the macros at global scope:

    ```cpp
    namespace nlohmann
    {
        template <>
        struct adl_serializer<BigUInt>
        {
            static void from_json(const json& value, BigUInt& result)
            {
                try
                {
                    result = BigUInt::Parse(value.get<std::string>());
                }
                catch (const std::invalid_argument&)
                {
                    throw json::type_error::create(302, "must be a decimal or 0x-hex number", &value);
                }
            }

            static void to_json(ordered_json& value, const BigUInt& source)
            {
                value = FormatHex(source);
            }
        };

        // adl_serializer<LogLevel_e>, adl_serializer<std::chrono::seconds> and
        // adl_serializer<std::array<s32, LoginSettings_s::CRC_COUNT>> follow the same pattern.
    }

    NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_WITH_DEFAULT(ServerSettings_s, url, origin, tlsCaFile)
    NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_WITH_DEFAULT(AccountSettings_s, username, password)
    NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_WITH_DEFAULT(LoginSettings_s, crcs, rsaModulus, rsaExponent, lowMemory, revision)
    NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_WITH_DEFAULT(ClientSettings_s, logoutComponent, logLevel, idleSeconds)
    NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_WITH_DEFAULT(ScriptingSettings_s, accountsDirectory, scriptsDirectory, callTimeoutMs, pollIntervalMs, loginIntervalSeconds, killGraceSeconds, progressDirectory)
    NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_WITH_DEFAULT(Config_s, server, login, client, scripting)
    ```

    (The comment inside the `nlohmann` namespace is there for this document only.)

    - **Placement.**
        - The macros sit in `ConfigFile.cpp`, not in the header, because only `Parse` and `Serialize` convert, and this keeps nlohmann out of every header.
        - They must be at global scope, the namespace of the structs, and not in the anonymous namespace. nlohmann finds the generated functions by argument-dependent lookup, which doesn't search the anonymous namespace.
    - **Generated functions.**
        - Since nlohmann 3.11 the macros generate `to_json` and `from_json` as templates over the JSON type, so the same macro serves `json` for reading and `ordered_json` for writing.
        - `from_json` default-constructs the struct and reads each member with `value(name, defaultObject.member)`. That returns the default when the key is missing, converts the value when it's present, and throws `type_error` 306 when the section itself isn't an object.
        - `to_json` writes each member with `json[name] = member`.
        - Both handle the members in the order the macro lists them.
    - **Directions.** Each serializer's `from_json` takes `const json&`, the type `Parse` reads, and its `to_json` takes `ordered_json&`, the type `Serialize` writes. Both specializations serve both JSON types, because `ordered_json` uses the same `adl_serializer`.
    - **Errors from the serializers.**
        - Each `from_json` reads its value with `get<...>()`, which throws nlohmann's own `type_error` for a wrong type.
        - It reports a bad value with `json::type_error::create(302, rule, &value)`, the same exception nlohmann's conversions throw.
        - With `JSON_DIAGNOSTICS`, both carry the value's path, and `DescribeConversionError` handles them like any other conversion error. A serializer never puts the value in its message.
    - **The serializers.**

        | Type | Reads | Writes |
        |---|---|---|
        | `BigUInt` | As shown. `Validate` checks the lower bounds, because they differ between the modulus and the exponent | `FormatHex`: `0x` and lowercase hex digits without leading zeros, `0x0` for zero. Built from `ToBytesBigEndian()`, so `BigUInt` itself doesn't change |
        | `LogLevel_e` | `verbose`, `info`, `warning` or `error`. Anything else throws `must be verbose, info, warning or error` | The same names |
        | `std::chrono::seconds` | `std::chrono::seconds{value.get<s64>()}`. `Validate` checks the range | `count()` |
        | `std::array<s32, CRC_COUNT>` | See below | Each item as `std::format("0x{:08x}", std::bit_cast<u32>(crc))`: `0x00000000`, `0xde5b3345` |

        - `LogLevel_e`'s names come from one `constexpr` table in the anonymous namespace, which both directions use.
        - Reading the CRC array:
            - The value must be an array of exactly `CRC_COUNT` items, or it throws `must be an array of 9 strings`.
            - Each item is read with `get<std::string>()` and parsed by `ParseU32`. That uses `std::from_chars`, with base 16 after a `0x` or `0X` prefix and base 10 otherwise, and requires a digit first and every character consumed. Base 16 accepts `a` to `f` and `A` to `F`, so case needs no handling of its own.
            - A bad item throws with `&value[i]` as the context, so its path ends with the index: `login.crcs.3`.
            - Each result is stored with `std::bit_cast<s32>`.
        - The array specialization applies to that exact array type, which only `LoginSettings_s` uses.
        - Every written value reads back to the same value: `FormatHex` and the CRC format are both forms `ParseU32` and `BigUInt::Parse` accept.
- **Conversion errors.** `DescribeConversionError` turns a nlohmann exception into the `{path}: {problem}` form the rest of `ConfigFile` uses:
    - It drops the `[json.exception.type_error.302] ` prefix up to the first `] `.
    - With `JSON_DIAGNOSTICS`, what remains starts with the JSON pointer in parentheses, `(/client/logLevel) type must be string, but is number`. That becomes `client.logLevel: type must be string, but is number`.
    - A section that isn't an object is reported against itself: `server: cannot use value() with array`.
    - nlohmann's conversion messages name JSON types and keys, never values, so passing their text through is safe, unlike syntax errors.
- **Validation.** `Validate` checks the rules from §3 that conversion doesn't:

    ```cpp
    void Validate(const Config_s& config)
    {
        Check(IsWebSocketUrl(config.server.url), "server.url", "must be a ws:// or wss:// URL");
        Check(config.server.origin.empty() || IsPrintableAscii(config.server.origin), "server.origin", "must be empty or printable ASCII");
        Check(!config.server.tlsCaFile.empty(), "server.tlsCaFile", "must be a PEM file path, SYSTEM or NONE");
        // ...one Check per remaining rule in §3, in the order of the table
    }
    ```

    (The comment is there for this document only.)

    - `Check(valid, path, rule)` throws `ConfigError{std::format("{}: {}", path, rule)}` when `valid` is false.
    - `Validate` is also where a key that can't do without a value fails when it's missing: its default breaks the rule. It can't tell a missing key from one set to the same value, so the message gives the rule, not "missing".
    - `IsWebSocketUrl` calls `ix::UrlParser::parse` and requires the protocol it returns to be `ws` or `wss`.
    - The limits are named `constexpr` constants in the anonymous namespace (`MAX_USERNAME_LENGTH`, `MIN_IDLE_SECONDS`, `MAX_IDLE_SECONDS`, ...). The revision check uses `LoginSettings_s::SUPPORTED_REVISION`.
    - `logoutComponent`, `lowMemory` and `crcs` have no rule beyond their type.
    - The paths in `Validate` are written out by hand. A test for each rule (§6.5) catches a path that no longer matches its member after a rename.
- **TLS.** `tlsCaFile` matters only for `wss`. With a `ws` URL it's stored as written and unused, without a warning, so switching `url` between a local `ws` server and a remote `wss` one stays a one-line edit, as in `client.ini`. With a `wss` URL and `NONE`, `Parse` logs `Warning` through the logger it was given: `Config disables TLS certificate verification (server.tlsCaFile is NONE)`.
- **Error messages.**
    - Every message from `Parse` but a syntax error reads `{path}: {problem}`, such as `client.idleSeconds: must be from 1 to 300`.
    - Messages never contain a value from the file.
    - They read like other exception messages: no trailing period, and lowercase, so that `client.jsonc: login.crcs: must be an array of 9 strings` reads as one line.
- **Logging.**
    - The TLS warning is logged while the file loads, before `Application` calls `SetLevel` with `logLevel`. It therefore shows at the threshold the logger was created with, `Info` from `main`, even when the file sets `"error"`. That is deliberate: a problem in the file that sets the level should still be visible.
    - Writing the sample isn't logged separately. The `ConfigError` that follows says what happened, and `main` logs it once ([LoggerDesign.md](LoggerDesign.md) §4).
- **Adding a setting.**
    1. Add the member, with its default as the initializer, to its section struct, and its name to that struct's macro, in the same position.
    2. If it has a rule, add a `Check` to `Validate`. If its type is new to the config, add an `adl_serializer` specialization with both directions.
    3. Add a row to the §3 table, update the §3 generated sample, and add the §6.4, §6.5 and §6.7 cases.

    Existing files keep loading: the new key takes its default until a file sets it. The generated sample picks it up by itself.
- **Not included:**
    - Saving a loaded config back. `Serialize` could do it, but the file's comments would be lost.
    - Reloading the config while the client runs.
    - Overriding individual keys from the command line or the environment.
    - Resolving a relative `tlsCaFile` against the config file's folder. It's passed to IXWebSocket as written and resolves against the working directory, as in the reference.
    - A JSON Schema for editor completion. TODO if the file grows.
    - Trailing commas. nlohmann 3.12 can accept them, but then the file would no longer be JSON plus comments.
    - More than one account per file.
    - Wiping the password from memory after login.

---

## 5. Differences from the reference config

| Reference | Here | Why |
|---|---|---|
| INI, parsed with SimpleIni | JSON with comments, parsed with nlohmann/json | Nested sections map directly onto JSON objects, and nlohmann already handles the syntax |
| A field table with a hand-written reader per key | `NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_WITH_DEFAULT`, four `adl_serializer` specializations, and `Validate` | The macros generate the reading and the writing |
| A missing file is an error; `client.ini.example` is committed by hand | A missing file is replaced by a generated sample, then an error | The sample can't drift from the structs |
| snake_case keys: `connect`, `ws_origin`, `tls_ca_file`, `rsa_modulus`, `log_level`, ... | The member names: `url`, `origin`, `tlsCaFile`, `rsaModulus`, `logLevel`, ... | The macro uses each member's name as its key |
| Keys marked required in the field table, including `crcs` | Every key optional. A key whose default breaks its rule fails in `Validate`; a missing `crcs` loads as zeros and fails at login | The macro has no notion of required, and the defaults already show which keys can't be left out |
| Every missing required key reported together | One at a time | `Validate` stops at the first broken rule |
| `[section] key` in messages | `section.key: ...` | A key's path in the file is its path in code |
| Unknown sections and keys are errors | Ignored, without a warning | The macros never read a key the structs don't have |
| Duplicate keys are errors | The last value is used, without a warning | nlohmann's default behaviour |
| Every number in decimal or `0x` hex | Integers are JSON numbers; CRCs and RSA values are strings in decimal or `0x` hex | JSON has no hex literals |
| `low_memory`: `0`, `1`, `true` or `false` | A JSON boolean | JSON has a boolean type |
| Integers range-checked as they're parsed | Converted by nlohmann, then checked against each key's rule by `Validate`. Fractions truncate and 16-bit keys can wrap (§3) | The cost of nlohmann's integer conversion |
| `parse` returns warnings in an out-parameter for `main` to log | `Parse` logs its one warning itself, through the `Logger&` it takes | `Logger` exists now, and [LoggerDesign.md](LoggerDesign.md) §4 has warnings logged by the code that noticed the problem |
| An `Endpoint` struct, a hand-written URL parser, and an explicit port required | The URL as a string, checked with `ix::UrlParser` | One parser: a URL that loads always passes `WebSocketClient::Connect`'s check |
| `tls_ca_file` with a `ws` URL: a warning, and the value reset to `SYSTEM` | Kept, unused, no warning | Switching between `ws` and `wss` stays a one-line edit |
| CRCs as `std::array<u32, 9>` | `std::array<s32, 9>`, the same bits | `Packet::P4` and `Packet::GetCrc` use `s32` |
| `parse_u32`, `parse_u16`, `parse_bool`, `parse_u32_list` and `trim`: public, returning `bool` | Helpers in the anonymous namespace, and serializers that throw | Only `ConfigFile` uses them, and CONVENTIONS §8 reports failures by throwing |
| `log_level`: `error`, `warn`, `info` or `verbose` | `logLevel`: `verbose`, `info`, `warning` or `error` | The names of `LogLevel_e`. The `warn` alias from [LoggerDesign.md](LoggerDesign.md) §5 isn't needed: every file is rewritten for the new keys anyway |
| `std::runtime_error` | `ConfigError` | Callers can catch config failures specifically, and the tests can require that type |
| Flat accessors: `config.username()` | Section structs: `config.account.username` | The structs mirror the file's sections |
| `main` holds the config in a `std::optional`, and `Protocol` keeps a `const ClientConfig&` to it | `Application` holds a `std::shared_ptr<const Config_s>`, and each class that keeps the config stores a copy of the pointer | A class can't outlive the config it reads, which a reference member doesn't guarantee |
| `load(const std::string&)` | `Load(const std::filesystem::path&)` | CONVENTIONS §9 |

---

## 6. Test plan

The plan below was written while `client.jsonc` held the account. Since the account moved to its own file ([ScriptingDesign.md](ScriptingDesign.md) Phase 3), its cases have moved with it. The username and password rules, and the checks that no message quotes a credential, now run against `ConfigFile::ParseAccount`, in the `[AccountFile]` cases of `ConfigFileTests.cpp`. Those cases also cover `enabled`, `script`, `script.file`, `script.settings`, `script.progressReportMinutes` and `LoadAccount`. The config file's cases cover the `scripting` section's defaults, limits and wrong types instead, and a leftover `account` section's warning. Where the plan below mentions `account.*`, read it as the account file.

### 6.1 Strategy

- **Inputs.**
    - Most cases change one key of the §3 example and leave the rest valid. The test parses the example with nlohmann (`nlohmann::json::parse(EXAMPLE, nullptr, true, true)`), edits it (`json["login"]["crcs"].erase(0)`, `json["account"].erase("password")`), and passes `json.dump()` to `ConfigFile::Parse`.
    - Cases that need exact text, such as syntax errors and duplicate keys, are raw string literals with a delimiter that JSON can't end early: `R"json(...)json"`.
- **Logging.** Every test holds a `LogCapture` ([LoggerDesign.md](LoggerDesign.md) §6.1) and passes `*capture.GetLogger()` to `Parse` and `Load`, so warnings never reach the console. The tables write `Parse(text)` and `Load(path)` and leave that argument out. Where a row says "no log entries" or names a warning, the test checks the capture.
- **Failures.** A failure must be a `ConfigError` (`REQUIRE_THROWS_AS`), and its message must contain the key's dotted path (`REQUIRE_THROWS_WITH` with `ContainsSubstring`). The rest of the message isn't checked, except for §6.3's line and column, §6.6's secrets and §6.8's first-run message.

Out of scope:

- The exact wording of messages.
- What `ix::UrlParser` accepts beyond the cases in §6.5. `WebSocketClient`'s tests own that.
- How nlohmann converts numbers to integer members (§3 Rules), beyond the cases `Validate` rejects. That's nlohmann's behaviour, not a rule of the format.
- What the macro does with a section set to `null`.
- A filesystem error from `std::filesystem::exists`. It can't be caused reliably from a test.
- What a server does with zero CRCs. That belongs to the login code's tests.
- Running the client against a server with the loaded settings.

### 6.2 Complete and minimal files

The §3 example parses with no log entries, and every member holds:

| Member | Value |
|---|---|
| `server.url` | `"ws://localhost:80"` |
| `server.origin` | `"https://w1.rs2b2t.com"` |
| `server.tlsCaFile` | `"SYSTEM"` |
| `account.username`, `account.password` | `"test"`, `"test"` |
| `login.crcs` | `0`, then `std::bit_cast<s32>(0xde5b3345u)` and so on for the eight hex values in order |
| `login.rsaModulus`, `login.rsaExponent` | `BigUInt::Parse` of the §3 strings |
| `login.lowMemory` | `false` |
| `login.revision` | `289` |
| `client.logoutComponent` | `2458` |
| `client.logLevel` | `LogLevel_e::Verbose` |
| `client.idleSeconds` | `5s` |

A file with only the five keys that must be set (`server.url`, `account.username`, `account.password`, `login.rsaModulus` and `login.rsaExponent`) parses with no log entries. Every other member holds its §3 default, and `login.crcs` is nine zeros.

### 6.3 Syntax

| Input | Result |
|---|---|
| `//` comments on their own lines and after values, and a `/* */` comment spanning several lines | Parses |
| A `//` comment on the last line with no newline after it | Parses |
| A UTF-8 BOM before the `{` | Parses |
| CRLF line endings throughout | Parses |
| A `# comment` line | `ConfigError`: only `//` and `/* */` are comments |
| `{'a': 1}`, `{a: 1}`, an unclosed `/*` | `ConfigError` |
| Empty text | `ConfigError` containing `line 1, column 1` |
| `"{\n\"a\": 1,\n}"`: a trailing comma | `ConfigError` containing `line 3, column 1` |
| `"// first\n{\n\"a\": 1,\n}"` | `ConfigError` containing `line 4, column 1`: comment lines count |
| `"{\r\n\"a\": 1,\r\n}"` | `ConfigError` containing `line 3, column 1` |
| The top level is `[]`, `5`, `"x"` or `null` | `ConfigError` |

### 6.4 Structure

| Change to the §3 example | Result |
|---|---|
| Each of `server.url`, `account.username`, `account.password`, `login.rsaModulus` and `login.rsaExponent` removed on its own | `ConfigError` containing its path, from `Validate` |
| Each of the other eight keys removed on its own | Parses with no log entries; that member holds its §3 default (`login.crcs`: nine zeros) |
| `server`, `account` or `login` removed | `ConfigError` containing `server.url`, `account.username` or `login.rsaModulus`, the first rule each one's defaults break |
| `client` removed | Parses with no log entries; `client` holds its defaults |
| `{}` instead of the whole file | `ConfigError` containing `server.url` |
| `"server": []`, `"login": "x"` | `ConfigError` containing the section's name |
| Each key set to `null` | `ConfigError` containing its path |
| An extra section `"extra": {"url": "x"}` | Parses with no log entries; every member is as in §6.2 |
| `idleSeconds` renamed to `idleSecond`, set to `30` | Parses with no log entries; `client.idleSeconds` is the default `5s` |
| `username` renamed to `usrname` | `ConfigError` containing `account.username`, with no log entries |
| `"Server"` instead of `"server"` | `ConfigError` containing `server.url`, with no log entries |
| A second `"url"` in `server`, after the first, set to `"ws://other:80"` (raw text) | Parses with no log entries; `server.url` is `"ws://other:80"` |
| A `wss://` URL with `tlsCaFile` `"NONE"` | Parses; one `Warning`, containing `server.tlsCaFile` |
| A `wss://` URL with `tlsCaFile` `"SYSTEM"` | Parses with no log entries |
| A `ws://` URL with `tlsCaFile` `"NONE"` or `"certs/ca.pem"` | Parses with no log entries; stored as written |

### 6.5 Values

Each rejection is a `ConfigError` containing the key's path. A CRC item's path ends with its index, as in `login.crcs.3`.

| Key | Accepted | Rejected |
|---|---|---|
| `server.url` | `"ws://localhost:80"`, `"wss://w1.example.com:443/path"`, stored as written | `"http://localhost:80"`, `"localhost:80"`, `""`, `80` |
| `server.origin` | `""`, `"http://localhost"` | `"http://exämple"`, `"a\tb"`, `true` |
| `server.tlsCaFile` | `"SYSTEM"`, `"NONE"`, `"certs/ca.pem"` | `""`, `5` |
| `account.username` | 1 and 12 characters, `"a b"` | `""`, 13 characters, `"tab\there"`, `"é"`, `5` |
| `account.password` | 1 and 20 characters | `""`, 21 characters, `"nul\u0000x"`, `"é"`, `5` |
| `login.crcs` | 9 items mixing `"0"`, `"0xde5b3345"`, `"0xDE5B3345"`, `"0Xde5b3345"`, `"0xDe5B3345"` and `"4294967295"`. The four spellings of `0xde5b3345` give the same value, and `"4294967295"` is stored as `-1` | 8 or 10 items; one string `"0, 0, 0, ..."`; an item `"0x100000000"`, `"4294967296"`, `"-1"`, `"+1"`, `" 1"`, `"0x"`, `""`, `"0x0x1"`, `"1.5"` or `5` |
| `login.rsaModulus` | `"3233"`, `"0xca1"`, `"0xCA1"` and `"0XcA1"`, all equal to `BigUInt::Parse("3233")` | `"0"`, `"1"`, `""`, `"0xzz"`, `3233` |
| `login.rsaExponent` | `"1"`, `"0x10001"` | `"0"`, `""`, `65537` |
| `login.lowMemory` | `true`, `false` | `0`, `1`, `"true"` |
| `login.revision` | `289` | `288`, `290`, `"289"`, `true` |
| `client.logoutComponent` | `0`, `65535` | `"2458"`, `null` |
| `client.logLevel` | `"verbose"`, `"info"`, `"warning"` and `"error"` give the four levels | `"warn"`, `"Info"`, `"debug"`, `""`, `2` |
| `client.idleSeconds` | `1` gives `1s`, `300` gives `300s` | `0`, `301`, `-5`, `"5"` |

### 6.6 Secrets

- For each rejected `account.username` and `account.password` string in §6.5 that isn't empty, the message doesn't contain the value.
- `"password": "hunter\q2"`, an invalid escape: `ConfigError` whose message doesn't contain `hunter`.
- `"password": "hunter2` and then the end of the text: the same.
- The edited example that §6.4 and §6.5 start from sets the password to a distinctive value, `"s3cret-pw"`. No message thrown and no entry captured in those cases contains it.

### 6.7 Serializing

- **The sample.** `Serialize(Config_s{})` equals the §3 generated sample without its two header lines, exactly. That one comparison covers the key order, the 4-space indentation, the LF line endings, the final newline and the written form of every type.
- **Round trip.** `Parse(Serialize(Parse(EXAMPLE)))` gives the members in §6.2, and `Serialize` of that equals `Serialize(Parse(EXAMPLE))`.
- **Written forms.** Each row sets one member of the parsed §3 example and serializes it. The value appears in the output as shown and parses back to the same member:

| Member | Value | Written as |
|---|---|---|
| `login.rsaModulus` | `BigUInt::Parse("0")` | `"0x0"` |
| `login.rsaModulus` | `BigUInt::Parse("3233")` | `"0xca1"` |
| `login.rsaModulus` | `BigUInt::Parse("0x0000ff")` | `"0xff"`: no leading zeros |
| `login.rsaModulus` | `BigUInt::Parse("0x80")` | `"0x80"`: the sign-padding byte from `ToBytesBigEndian` isn't written |
| `login.rsaModulus` | The §3 modulus | Its §3 string |
| `login.crcs[0]` | `0` | `"0x00000000"` |
| `login.crcs[0]` | `-1` | `"0xffffffff"` |
| `login.crcs[0]` | `std::bit_cast<s32>(0xde5b3345u)` | `"0xde5b3345"` |
| `client.logLevel` | Each of the four levels | `"verbose"`, `"info"`, `"warning"`, `"error"` |
| `client.idleSeconds` | `300s` | `300` |

- **Case on the way back.** A file whose CRCs and RSA values are written in upper case parses, and `Serialize` writes them back in lower case: `"0XDE5B3345"` comes back as `"0xde5b3345"`. Both are the same value.
- **Filling in the sample.** The test parses the generated sample with nlohmann and sets `server.url`, `account.username`, `account.password`, `login.rsaModulus` (`"3233"`) and `login.rsaExponent` (`"17"`). `Parse` then succeeds with no log entries, and gives the same members as the minimal file in §6.2 with the same five values.

### 6.8 Load

The tests work in a fresh folder under `std::filesystem::temp_directory_path()`, which a small RAII helper in the test file's anonymous namespace creates and removes. Files are written in binary mode.

- The §3 example, written to a file: `Load` returns the same members as §6.2.
- The same file with CRLF line endings and a BOM: loads.
- A file whose `login.crcs` has 8 items: `ConfigError` whose message starts with the path and `: `, and contains `login.crcs`.
- **First run.**
    - A path that doesn't exist throws a `ConfigError` whose message contains the path and `sample`.
    - The file now exists, and its bytes are exactly the §3 generated sample.
    - A second `Load` of the same path throws a `ConfigError` containing `server.url`, the first rule the sample breaks. The sample isn't rewritten.
- **First run, nowhere to write.** A path inside a folder that doesn't exist: `ConfigError` whose message contains the path, and neither the folder nor the file is created.

### 6.9 Tooling

- Tag: `[ConfigFile]`.
- The test executable links `nlohmann_json::nlohmann_json` to build its inputs (§2).
- The path checks in §6.4 and §6.5 depend on `JSON_DIAGNOSTICS` on the library target. Without it, nlohmann's conversion errors carry no path, and those checks fail.

### 6.10 Done when

- All tests pass on `windows-debug` and `windows-release` (and on the `linux-*` presets once available), with zero warnings.
- The client starts with the converted `client.jsonc` from §3, logs `Config loaded from client.jsonc`, and connects.
- Started in an empty folder, the client writes `client.jsonc`, exits with the first-run message, and the file opens in an editor with no errors flagged.

---

## 7. Implementation order

This comes after `BigUInt` ([PacketDesign.md](PacketDesign.md) §8 step 3) and the IXWebSocket dependency ([WebSocketDesign.md](WebSocketDesign.md) §7 step 1).

1. **Dependencies:**
    - Add `nlohmann-json` to `vcpkg.json` and `find_package` it.
    - Link it privately to the library and to the test executable, and give the library `JSON_DIAGNOSTICS=1`.
    - Add `<charconv>` and `<iterator>` to `pch.hpp`.
2. **Syntax first:** `ConfigError`, and `ParseJson` with comments and the line and column message, plus the §6.3 tests. This checks nlohmann's comment handling on every preset before anything depends on it.
3. **Conversion:** the settings structs, the `adl_serializer` specializations in both directions, the macros, `DescribeConversionError` and `Serialize`, plus the §6.2, §6.4 and §6.7 tests. The first build on each preset confirms three things:
    - The macro-generated functions work with both `json` and `ordered_json`, and `value()` reaches the custom serializers.
    - The messages carry dotted paths.
    - `Serialize(Config_s{})` matches the §3 sample byte for byte.
4. **`Validate`:** plus the §6.5 and §6.6 tests.
5. **`Load` and the sample:** plus the §6.8 tests.
6. **Wiring:**
    - `main` creates the logger and passes it and the optional path to `Application`. `Application` loads the config into its `std::shared_ptr<const Config_s>`, sets the logger's level, builds `WebSocketOptions_s`, and passes the logger to the classes it builds.
    - Git-ignore `client.jsonc`.
    - Update [LoggerDesign.md](LoggerDesign.md):
        - The `log_level` TODOs in §3 and §5: the key is now `client.logLevel`, with no `warn` alias.
        - The "unknown config key" example of a `Warning` in §4: nothing warns about one now.
