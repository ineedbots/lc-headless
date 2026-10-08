# C++ Project Conventions

How every new C++ codebase is set up and written. When something isn't covered here, match the surrounding code.

## Quick reference

| Topic | Convention |
|---|---|
| Language | C++20, no compiler extensions |
| Build | CMake with presets |
| Toolchains | MSVC on Windows, Clang on Linux |
| Dependencies | vcpkg, manifest mode |
| File extensions | `.hpp` / `.cpp` |
| Includes | Include the needed header; never forward declare |
| Braces | Allman |
| Indentation | 4 spaces, never tabs |
| Line endings | LF only, never CR or CRLF |
| Classes, functions | `PascalCase` |
| Structs | `PascalCase_s` |
| Enums | `PascalCase_e` (`enum class`) |
| Locals, parameters | `camelCase` |
| Private members | `m_camelCase` |
| Constants | `constexpr ALL_CAPS` |
| Preprocessor | Allowed; prefer `constexpr` when possible |
| Pointers | `Type* name` |
| Ownership | RAII, `std::unique_ptr` |
| Copies | Minimize; move semantics, `emplace` where it fits |
| Errors | Exceptions |
| Control flow | Return early; `continue` in loops |
| Bugs, invariants | `assert` |
| Comments | Sparingly: TODOs and necessary explanations only |
| Null | `nullptr` only |

---

## 1. Project layout

```
ProjectName/
├── .clang-format
├── .editorconfig
├── .gitattributes
├── .gitignore
├── CMakeLists.txt
├── CMakePresets.json
├── CONVENTIONS.md
├── vcpkg.json
└── src/
    ├── pch.hpp
    ├── main.cpp
    ├── Application.hpp
    ├── Application.cpp
    ├── Core/
    │   ├── ConfigFile.hpp
    │   ├── ConfigFile.cpp
    │   ├── Endian.hpp
    │   ├── StringHash_s.hpp
    │   ├── StringUtils.hpp
    │   └── StringUtils.cpp
    └── Graphics/
        ├── BlendMode_e.hpp
        ├── Renderer.hpp
        ├── Renderer.cpp
        ├── TextureCache.hpp
        ├── TextureCache.cpp
        └── Vertex_s.hpp
```

- File names match class names exactly: `class TextureCache` lives in `TextureCache.hpp` / `TextureCache.cpp`.
- `pch.hpp` and `main.cpp` are the only files that don't follow the class-name rule.
- `pch.hpp`, `main.cpp`, and `Application.hpp` / `Application.cpp` always stay at the root of `src/`. They are the entry points to the codebase and should be found instantly.
- Everything else may live in subfolders of `src/` that group related files by feature or subsystem (`Core/`, `Graphics/`). Nothing is required to sit at the root. Nest folders when it helps, but keep the tree shallow.
- Folder names are PascalCase.
- A header and its `.cpp` always sit side by side in the same folder.
- Build output goes in `build/`, which is git-ignored.

---

## 2. Build: CMake

### CMakeLists.txt

```cmake
cmake_minimum_required(VERSION 3.25)
project(ProjectName VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)    # for clangd / tooling
set(CMAKE_COMPILE_WARNING_AS_ERROR ON)   # zero-warning policy

file(GLOB_RECURSE PROJECT_SOURCES CONFIGURE_DEPENDS
    ${CMAKE_CURRENT_SOURCE_DIR}/src/*.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/*.hpp
)

add_executable(${PROJECT_NAME})
target_sources(${PROJECT_NAME} PRIVATE ${PROJECT_SOURCES})

target_include_directories(${PROJECT_NAME} PRIVATE src)
target_precompile_headers(${PROJECT_NAME} PRIVATE src/pch.hpp)

if(MSVC)
    target_compile_options(${PROJECT_NAME} PRIVATE
        /W4 /permissive- /utf-8 /EHsc /Zc:__cplusplus /Zc:preprocessor)
else()
    target_compile_options(${PROJECT_NAME} PRIVATE
        -Wall -Wextra -Wpedantic -Wshadow)
endif()

if(WIN32)
    target_compile_definitions(${PROJECT_NAME} PRIVATE NOMINMAX WIN32_LEAN_AND_MEAN)
endif()
```

- Sources are collected with `file(GLOB_RECURSE ...)`, so any `.cpp` or `.hpp` anywhere under `src/`, including subfolders, is part of the build. Don't list files by hand.
- `CONFIGURE_DEPENDS` makes CMake re-check the glob on every build, so adding, removing, or moving a file is picked up without manually re-running the configure step.
- Headers are globbed too, so IDEs show them in the project tree.
- `src/` is the only project include directory. Includes are written relative to the including file or as a path from `src/` (see section 5). Don't add subfolders as extra include directories.
- `/EHsc` turns on standard C++ exception handling for MSVC. CMake normally adds it already, but it's listed explicitly because the codebase relies on exceptions. Clang enables exceptions by default; never build with `-fno-exceptions`.
- `NOMINMAX` stops `<windows.h>` from defining `min`/`max` macros that break `std::min`/`std::max`.
- `/Zc:__cplusplus` makes MSVC report the real language version in `__cplusplus`.

### CMakePresets.json

```json
{
    "version": 6,
    "configurePresets": [
        {
            "name": "base",
            "hidden": true,
            "generator": "Ninja Multi-Config",
            "binaryDir": "${sourceDir}/build/${presetName}",
            "toolchainFile": "$env{VCPKG_ROOT}/scripts/buildsystems/vcpkg.cmake"
        },
        {
            "name": "windows-msvc",
            "inherits": "base",
            "cacheVariables": {
                "CMAKE_CXX_COMPILER": "cl"
            },
            "condition": { "type": "equals", "lhs": "${hostSystemName}", "rhs": "Windows" }
        },
        {
            "name": "linux-clang",
            "inherits": "base",
            "cacheVariables": {
                "CMAKE_CXX_COMPILER": "clang++"
            },
            "condition": { "type": "equals", "lhs": "${hostSystemName}", "rhs": "Linux" }
        }
    ],
    "buildPresets": [
        { "name": "windows-debug",   "configurePreset": "windows-msvc", "configuration": "Debug" },
        { "name": "windows-release", "configurePreset": "windows-msvc", "configuration": "Release" },
        { "name": "linux-debug",     "configurePreset": "linux-clang",  "configuration": "Debug" },
        { "name": "linux-release",   "configurePreset": "linux-clang",  "configuration": "Release" }
    ]
}
```

Building:

```sh
cmake --preset linux-clang
cmake --build --preset linux-debug
```

On Windows, run from a Developer PowerShell / Developer Command Prompt (or open the folder in Visual Studio or VS Code with CMake Tools) so `cl` and Ninja are on `PATH`.

---

## 3. Dependencies: vcpkg

- Manifest mode only. Every dependency is declared in `vcpkg.json`; nothing is installed globally by hand.
- The `VCPKG_ROOT` environment variable points at the vcpkg clone. The presets use it to find the toolchain file.
- Versions are pinned with `builtin-baseline`. After creating `vcpkg.json`, run once:
  ```sh
  vcpkg x-update-baseline --add-initial-baseline
  ```
- The manifest `name` must be lowercase with hyphens.

```json
{
    "$schema": "https://raw.githubusercontent.com/microsoft/vcpkg-tool/main/docs/vcpkg.schema.json",
    "name": "project-name",
    "version": "0.1.0",
    "dependencies": []
}
```

To add a dependency, add its name to `dependencies`, then wire it up with the usage text vcpkg prints on install:

```cmake
find_package(spdlog CONFIG REQUIRED)
target_link_libraries(${PROJECT_NAME} PRIVATE spdlog::spdlog)
```

---

## 4. Precompiled header

`src/pch.hpp` holds every standard library include, the fixed-width type aliases, and `std::literals`.

```cpp
#pragma once

#include <algorithm>
#include <array>
#include <bit>
#include <cassert>
#include <chrono>
#include <concepts>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <exception>
#include <filesystem>
#include <format>        // Linux: needs libstdc++ 13+ or libc++ 17+
#include <fstream>
#include <functional>
#include <map>
#include <memory>
#include <optional>
#include <ranges>
#include <span>
#include <stdexcept>
#include <string>
#include <string_view>
#include <system_error>
#include <unordered_map>
#include <utility>
#include <variant>
#include <vector>

using u8  = std::uint8_t;
using u16 = std::uint16_t;
using u32 = std::uint32_t;
using u64 = std::uint64_t;

using s8  = std::int8_t;
using s16 = std::int16_t;
using s32 = std::int32_t;
using s64 = std::int64_t;

using f32 = float;
using f64 = double;

static_assert(sizeof(f32) == 4);
static_assert(sizeof(f64) == 8);

using namespace std::literals;
```

Rules:

- Standard headers are included here and nowhere else. Add to this list as needed.
- Only stable headers go in the PCH. Project headers that change often don't belong here, since every edit would rebuild everything. Mature third-party headers used across most of the codebase are fine.
- Never include `<windows.h>` here. It defines ALL_CAPS macros (`ERROR`, `DELETE`, `IN`, `OUT`, `min`, `max`, ...) that collide with the standard library and with ALL_CAPS constants. Keep it confined to the platform-specific `.cpp` files that need it.

---

## 5. Files and includes

### Headers (`.hpp`)

- Use `#pragma once`, not include guards.
- Headers don't include `pch.hpp`; they rely on it for the standard library and the type aliases.
- No `using namespace` in headers. `std::literals` in the PCH is the single exception.

#### Headers only include what their own declarations need

A header includes another header only when the header itself requires it: a class, struct, or enum that appears in one of its function prototypes or data declarations (members, parameters, return types). Everything else goes in the `.cpp`.

- Headers needed only by the implementation are included in the `.cpp`, never in the header.
- A header never includes something just to make it available to the files that include it.
- Never forward declare. When a type is needed, include its header, even if the type is only used by pointer or reference.

```cpp
// src/Graphics/Renderer.hpp
#pragma once

#include "../Core/ConfigFile.hpp"   // required: ConfigFile is in the constructor's prototype
#include "BlendMode_e.hpp"          // required: BlendMode_e is a data member and a parameter
#include "Vertex_s.hpp"             // required: Vertex_s is in Draw's prototype

class Renderer
{
public:
    explicit Renderer(const ConfigFile& config);

    void Draw(std::span<const Vertex_s> vertices);
    void SetBlendMode(BlendMode_e blendMode);

private:
    BlendMode_e m_blendMode;
};
```

```cpp
// src/Graphics/Renderer.cpp
#include "pch.hpp"
#include "Renderer.hpp"

#include "../Core/ConfigFile.hpp"   // the implementation uses ConfigFile, so it's included even though Renderer.hpp has it
#include "TextureCache.hpp"         // only the implementation uses TextureCache
```

### Source files (`.cpp`)

A `.cpp` includes every header it uses, even when its own header or another include already brings it in. Never rely on a header arriving indirectly. A type counts as used even when the code never names it, such as reading `message.closeInfo.code` through another object. The only exception is anything already in `pch.hpp`.

Include order is always (shown for `src/Graphics/TextureCache.cpp`):

```cpp
#include "pch.hpp"                  // 1. the PCH, always first
#include "TextureCache.hpp"         // 2. this file's own header, if it exists

#include "../Core/ConfigFile.hpp"   // 3. other project headers
#include "Renderer.hpp"

#include <spdlog/spdlog.h>          // 4. third-party headers
```

### Include paths

- Project includes may be written relative to the file doing the including: `#include "Renderer.hpp"` for a header in the same folder, `#include "../Core/ConfigFile.hpp"` for one in another folder. `../` is allowed.
- A path from `src/` also works, because `src/` is an include directory: `#include "Core/ConfigFile.hpp"`. Use whichever reads more clearly.
- In a header, relative paths resolve from the header's own folder, not from the `.cpp` that includes it.
- A file's own header is included by bare name, since it sits in the same folder.
- `pch.hpp` is always included by bare name. It resolves from any folder through the `src/` include directory.
- Use `"..."` for project headers and `<...>` for standard and third-party headers.

CMake's `target_precompile_headers` already force-includes the PCH, so the explicit `#include "pch.hpp"` is a no-op thanks to `#pragma once`. It stays anyway so every file is self-describing and editors resolve symbols correctly.

### Anonymous namespaces

Data and helper functions that only matter to one `.cpp` file go in an anonymous namespace at the top of that file. Don't use `static` for file-local free functions or variables.

```cpp
namespace
{
    constexpr auto MAX_RETRIES = 3;

    bool IsValidName(std::string_view name)
    {
        return !name.empty() && name.size() < 64;
    }
}
```

### Every `.cpp` has a class

Each `.cpp` file implements exactly one class, named after the file. If the file only holds utility functions, they become static members of a non-instantiable class:

```cpp
// src/Core/StringUtils.hpp
#pragma once

class StringUtils
{
public:
    StringUtils() = delete;

    [[nodiscard]] static std::string ToLower(std::string_view text);
    [[nodiscard]] static std::vector<std::string_view> Split(std::string_view text, char delimiter);
};
```

The only exception is `main.cpp`, which stays tiny, hands off to a class, and acts as the last-resort catch for exceptions:

```cpp
#include "pch.hpp"
#include "Application.hpp"

int main()
{
    try
    {
        auto app = Application{};
        return app.Run();
    }
    catch (const std::exception& e)
    {
        std::fprintf(stderr, "Fatal error: %s\n", e.what());
        return EXIT_FAILURE;
    }
}
```

---

## 6. Naming

| Element | Convention | Example |
|---|---|---|
| Classes | PascalCase | `TextureCache` |
| Structs | PascalCase + `_s` | `Vertex_s` |
| Enums | `enum class`, PascalCase + `_e`, PascalCase values | `BlendMode_e::Additive` |
| Functions, methods | PascalCase | `LoadFromFile()` |
| Local variables, parameters | camelCase | `frameCount` |
| Private data members | `m_` + camelCase | `m_frameCount` |
| Constants | `constexpr`, ALL_CAPS | `constexpr u32 MAX_TEXTURES = 256;` |
| Public struct fields | camelCase | `position` |
| Namespaces | PascalCase | `Renderer` |
| Template parameters | PascalCase, `T` prefix | `T`, `TKey` |
| Type aliases | PascalCase (PCH aliases excepted) | `using TextureMap = ...;` |
| Files | Exactly the type name | `TextureCache.hpp`, `Vertex_s.hpp` |

- The `_s` and `_e` suffixes make a type's kind obvious at every use site, so `Vertex_s`, `BlendMode_e`, and `TextureCache` can be told apart without looking them up.
- Use a `struct` for plain data with all-public fields and no invariants to protect. Anything with private members or behaviour that must keep its state valid is a `class`.
- Structs and enums usually live in the header of the class that owns them. When one needs its own header, the file name includes the suffix (`Vertex_s.hpp`, `BlendMode_e.hpp`).

```cpp
struct Vertex_s
{
    f32 x;
    f32 y;
    f32 z;
    u32 color;
};

enum class BlendMode_e : u8
{
    Opaque,
    AlphaBlend,
    Additive,
};
```

- Constants are `constexpr` rather than `#define`. Class-level constants are `static constexpr`; file-level constants live in the anonymous namespace.
- Macros are ALL_CAPS with a project prefix (`PROJECT_ASSERT`). See Preprocessor in section 8 for when to use one.

---

## 7. Formatting and comments

- Indent with 4 spaces. Never tabs, in any file: C++, CMake, JSON, YAML, Markdown.
- LF line endings only. Never CR or CRLF, on every platform, including Windows working copies.
- Allman braces: every opening brace on its own line.
- No line length limit.
- Always use braces, even for single-statement `if`/`for`/`while` bodies.
- The `*` and `&` attach to the type: `Texture* texture`, `const Config& config`.
- One declaration per line (`int* a, b;` is a trap).

Three files enforce this. `.clang-format` handles C++ code, `.editorconfig` makes every editor use spaces and LF for every file type, and `.gitattributes` guarantees git stores and checks out LF regardless of anyone's `core.autocrlf` setting.

### `.clang-format`

Requires clang-format 16 or newer for `LineEnding`.

```yaml
BasedOnStyle: Microsoft
Language: Cpp
Standard: c++20
IndentWidth: 4
TabWidth: 4
UseTab: Never
LineEnding: LF
ColumnLimit: 0       # no line length limit
BreakBeforeBraces: Allman
PointerAlignment: Left
DerivePointerAlignment: false
NamespaceIndentation: All
AllowShortFunctionsOnASingleLine: None
AllowShortIfStatementsOnASingleLine: Never
AllowShortLoopsOnASingleLine: false
SortIncludes: Never   # keeps pch.hpp and the own header first
```

### `.editorconfig`

Visual Studio reads this natively; VS Code needs the EditorConfig extension.

```ini
root = true

[*]
indent_style = space
indent_size = 4
tab_width = 4
end_of_line = lf
charset = utf-8
insert_final_newline = true
trim_trailing_whitespace = true
```

### `.gitattributes`

```gitattributes
# Store and check out every text file with LF endings
* text=auto eol=lf
```

When adding this to an existing repo, convert the files already committed with `git add --renormalize .` and commit the result.

### Comments

Code should explain itself. Comments are used sparingly, and only for two things:

- **TODOs**, written as `// TODO: <what needs doing>`.
- **Necessary explanations** of *why* something is done when the code can't say it on its own: a compiler workaround, a non-obvious requirement, or a deliberate choice that looks wrong at first glance.

Everything else is made clear by the code itself:

- Use names that say what things are and do: `remainingRetries`, not `n` with a comment beside it.
- Split responsibly. Keep functions small with one job each. When a block of code needs a comment to explain what it does, extract it into a function whose name says that instead.
- Use named constants instead of magic numbers: `MAX_TEXTURES`, not `256` with a comment.
- Don't write comments that restate the code, commented-out code (version control keeps the history), banner or section-divider comments, or boilerplate doc comments on every function.

```cpp
// Needs a comment to be understood
// check whether the cached texture is too old
if (std::chrono::steady_clock::now() - entry.loadedAt > 30s)

// Explains itself
if (IsExpired(entry))
```

The comments in this document's examples, such as file path labels and include annotations, are there to explain the conventions. They wouldn't appear in real code.

---

## 8. Language usage

### `auto`

Use `auto` wherever it's available:

```cpp
auto texture = std::make_unique<Texture>(path);
auto count = u32{0};
auto name = "player"s;
const auto& settings = config.GetSettings();

for (const auto& entry : entries)
{
    // ...
}
```

- To commit to a specific type, write `auto x = Type{...};`.
- `auto` drops `const` and references, so spell out `const auto&` or `auto&` when that's what you mean.
- Watch out for proxy types such as `std::vector<bool>::reference`.

### Control flow: return early

Use a return-early style. Deal with the cases that end a function first, and leave the main logic at the lowest indentation level instead of nesting it inside `if` blocks. This keeps nesting shallow and the main path easy to follow.

- Put guard clauses at the top of a function: check each condition that ends it and `return` or `throw` immediately.
- In loops, skip items that don't apply with `continue` at the top of the body, rather than wrapping the rest of the body in an `if`.
- `return` or `break` as soon as the result is known.
- No `else` after a branch that ends with `return`, `throw`, `continue`, or `break`. The code after the `if` already is the "else".
- The one exception is `if constexpr`: keep the `else` there, because only an `else` branch is actually discarded at compile time.
- If code still nests deeply after this, extract part of it into a well-named function.

```cpp
// Nested
void TextureCache::ReloadChanged()
{
    if (m_hotReloadEnabled)
    {
        for (const auto& texture : m_textures)
        {
            if (texture->IsDirty())
            {
                if (std::filesystem::exists(texture->GetPath()))
                {
                    texture->Reload();
                }
            }
        }
    }
}

// Return early, continue in the loop
void TextureCache::ReloadChanged()
{
    if (!m_hotReloadEnabled)
    {
        return;
    }

    for (const auto& texture : m_textures)
    {
        if (!texture->IsDirty())
        {
            continue;
        }

        if (!std::filesystem::exists(texture->GetPath()))
        {
            continue;
        }

        texture->Reload();
    }
}
```

### Memory and ownership (RAII)

- Owning heap objects are held in `std::unique_ptr`, created with `std::make_unique`. No naked `new` or `delete`.
- `std::shared_ptr` only when ownership is genuinely shared.
- Raw `Type*` and `Type&` are non-owning observers. Never `delete` through them.
- Prefer values and standard containers over heap allocation when possible.
- Follow the rule of zero: members that manage themselves mean the default copy/move/destructor are correct.
- Wrap C and OS handles in RAII types:

```cpp
struct FileCloser_s
{
    void operator()(std::FILE* file) const noexcept
    {
        std::fclose(file);
    }
};

using FilePtr = std::unique_ptr<std::FILE, FileCloser_s>;
```

### Copies and move semantics

Avoid copies wherever they aren't needed. Move objects instead of copying them, and construct objects in place where it makes sense.

#### Parameters

- Pass cheap types by value: built-ins, enums, small trivially copyable structs, and views such as `std::string_view` and `std::span`.
- Pass larger types the function only reads by `const&`.
- Pass "sink" parameters, which the function keeps a copy of, by value and `std::move` them into place. Callers then choose: pass a temporary or `std::move` for no copy, or an lvalue for exactly one copy.
- Pass move-only types such as `std::unique_ptr` by value to transfer ownership.

```cpp
ConfigFile::ConfigFile(std::filesystem::path path)
    : m_path{std::move(path)}
{
}
```

#### Moving

- `std::move` an object at its last use when it's being handed to something that keeps it.
- Never use a moved-from object again, except to assign a new value to it or let it be destroyed.
- Don't `std::move` a `const` object. It silently copies instead.
- Capture by move in lambdas when the lambda should own the data: `[data = std::move(data)]`.
- Following the rule of zero gives every class correct moves for free. Move operations are `noexcept` (see Error handling).

#### Returning

- Return by value, including large objects and containers. The compiler elides the copy. Don't use output parameters to avoid a copy.
- Never write `return std::move(local);`. It blocks copy elision and makes the return slower.

#### Containers

- Use `emplace_back`, `emplace`, and `try_emplace` to build an element directly in the container from constructor arguments.
- When you already have the object, `push_back(std::move(object))` is clearer, and `emplace_back` gains nothing.
- For maps, prefer `try_emplace`, which doesn't construct the value at all if the key is already present. Use `insert_or_assign` to overwrite.
- `emplace` calls `explicit` constructors, so check that the arguments build what you intend: `emplace_back(10)` on a `std::vector<std::vector<int>>` adds a 10-element vector.
- `reserve` when the final size is known, so the container doesn't reallocate and move elements repeatedly.
- Iterate with `const auto&` or `auto&`, never plain `auto`, unless a copy of each element is really wanted.
- Use heterogeneous lookup (a transparent hash and `std::equal_to<>`) for string-keyed maps, so looking up a `std::string_view` doesn't build a temporary `std::string`. See `StringHash_s` in the complete example.

```cpp
auto lines = std::vector<std::string>{};
lines.reserve(lineCount);
lines.emplace_back(40, '-');
lines.push_back(std::move(header));

auto textures = std::unordered_map<std::string, Texture>{};
textures.try_emplace(name, path, TextureFormat_e::Rgba8);
```

### Error handling: exceptions

Failures are reported by throwing exceptions. Functions don't return `bool` or error codes to signal failure.

- Throw when a function can't do what its name promises: a required file can't be opened, input is malformed, a resource can't be created.
- Use `std::optional` when "nothing" is a normal, expected result rather than an error, such as looking up a key that may be absent.
- Throw standard exception types (`std::runtime_error`, `std::invalid_argument`, `std::out_of_range`, `std::system_error`) or project types derived from them. Never throw anything that doesn't derive from `std::exception`.
- Give exceptions useful messages with `std::format`:
  ```cpp
  throw std::runtime_error{std::format("Failed to open {}", path.string())};
  ```
- Throw by value, catch by `const&`: `catch (const std::exception& e)`.
- Rethrow with `throw;`, never `throw e;`, which slices and loses the original type.
- Only catch where the error can actually be handled, where useful context can be added, or at a boundary: `main`, thread entry points, and callbacks invoked by C or OS code. Don't catch just to log and rethrow.
- Never use exceptions for normal control flow.
- Don't throw for bugs in the code itself, such as a broken precondition or an impossible state. Those are asserts (see below).
- Convert OS and C library failures into exceptions where they enter the codebase, for example `std::system_error` carrying the error code.
- Use the throwing overloads of `std::filesystem` functions, not the `std::error_code` ones.
- Exceptions must never escape a destructor, a `noexcept` function, or a callback called from C code.
- Mark move constructors, move assignment operators, and `swap` as `noexcept` so standard containers move instead of copy.
- RAII is what makes this safe: when every resource is owned by an object, a thrown exception leaks nothing.

Create a custom exception type only when callers need to catch that specific failure. Name it with an `Error` suffix and inherit the base constructors:

```cpp
// src/Core/ConfigError.hpp
#pragma once

class ConfigError : public std::runtime_error
{
public:
    using std::runtime_error::runtime_error;
};
```

### Asserts

Use `assert` (from `<cassert>`, included in the PCH) to check anything that must always be true if the code is correct: preconditions, postconditions, and invariants.

- Asserts catch bugs; exceptions report failures. A missing file or malformed input can happen in a correct program, so it throws. An out-of-range index, or a null pointer that should never be null, is a bug, so it asserts.
- Assert freely, especially on a function's preconditions and on assumptions the rest of the function relies on.
- Give every assert a message with `&&` so a failure explains itself.
- Asserts are compiled out in Release builds (CMake defines `NDEBUG`), so an assert must never have side effects. `assert(m_textures.erase(name) == 1)` would skip the erase entirely in Release.
- Never use an assert to validate external input such as files, network data, or user input. That always throws, in every build.
- Use `static_assert` for anything that can be checked at compile time.

```cpp
const Vertex_s& Mesh::GetVertex(u32 index) const
{
    assert(index < m_vertices.size() && "Vertex index out of range");
    return m_vertices[index];
}

void Renderer::EndFrame()
{
    assert(m_frameInProgress && "EndFrame called without a matching BeginFrame");
    m_frameInProgress = false;
}
```

### Preprocessor

The preprocessor is allowed, but prefer `constexpr` and ordinary C++ whenever they can do the same job. Language features respect scope and namespaces, are type-checked, and show up in the debugger. Macros are text substitution and do none of that.

- Constants are `constexpr` variables, not `#define`.
- Function-like macros become `constexpr` functions or templates.
- `#if` on a value C++ can see becomes `if constexpr`.

Use the preprocessor for what C++ can't do:

- Platform and compiler detection (`_WIN32`, `__linux__`, `__clang__`, `_MSC_VER`), and code that only compiles on one platform.
- Values passed in from the build with `target_compile_definitions`.
- Code that must not exist at all in some builds, such as debug-only members behind `#ifndef NDEBUG`.
- Stringizing (`#`) and token pasting (`##`), such as an assert macro that prints the text of the failing expression.

Even then, keep the preprocessor at the edge. When a condition only picks a value, turn it into a `constexpr` once and use that everywhere else:

```cpp
// src/Core/Platform.hpp
#pragma once

class Platform
{
public:
    Platform() = delete;

#ifdef _WIN32
    static constexpr bool IS_WINDOWS = true;
#else
    static constexpr bool IS_WINDOWS = false;
#endif
};
```

```cpp
if constexpr (Platform::IS_WINDOWS)
{
    // ...
}
```

Outside a template, both branches of an `if constexpr` must still compile, so code that calls platform-only APIs stays behind `#if`.

When writing a macro:

- Name it ALL_CAPS with a project prefix (`PROJECT_ASSERT`), so it can't be mistaken for a `constexpr` constant or collide with another library's macros.
- Define a macro used by one `.cpp` in that `.cpp`, not in a header. A macro in a header leaks into every file that includes it.
- Parenthesize every parameter and the whole expansion, and wrap multi-statement bodies in `do { ... } while (false)`, so the macro behaves like a single expression or statement where it's used.

### `nullptr`

Always `nullptr`. Never `0` or `NULL` for pointers.

### Other defaults

- `const` on anything that doesn't change, including locals (`const auto`).
- `[[nodiscard]]` on functions whose result must not be ignored.
- `explicit` on single-argument constructors.
- `enum class` instead of plain `enum`.
- C++ casts only (`static_cast`, `reinterpret_cast`, ...), never C-style casts.
- `std::string_view` and `std::span` for non-owning parameters.

---

## 9. Portability and endianness

### Portability rules

- Use the fixed-width aliases (`u8`, `s32`, ...) for anything with a size requirement.
- Never use `long`: it's 32-bit on Windows and 64-bit on Linux.
- `char` signedness is implementation-defined. Use `u8` or `std::byte` for raw binary data.
- `wchar_t` is 16-bit on Windows and 32-bit on Linux. Use UTF-8 `std::string` internally and convert only at the Windows API boundary (`/utf-8` is on for MSVC).
- Use `std::filesystem::path` and its `/` operator for paths; never build them by hand.
- Keep platform code in dedicated files. Detect the OS with `_WIN32` / `__linux__`; detect the compiler with `__clang__` / `_MSC_VER`, checking `__clang__` first since clang-cl also defines `_MSC_VER`.

### Endianness rules

- Every serialized format (files, network, save data) has a defined byte order. Default to little-endian.
- All reads and writes of serialized integers go through `Endian`.
- Floats are serialized through their bit pattern: `Endian::ToLittle(std::bit_cast<u32>(value))`.
- Never `memcpy`/`fwrite` a struct directly to or from disk; padding and byte order are not portable. Serialize field by field.

### `src/Core/Endian.hpp`

```cpp
#pragma once

static_assert(std::endian::native == std::endian::little || std::endian::native == std::endian::big,
              "Mixed-endian platforms are not supported");

class Endian
{
public:
    Endian() = delete;

    static constexpr bool IS_LITTLE = std::endian::native == std::endian::little;

    // TODO: replace with std::byteswap when moving to C++23
    template <std::integral T>
    [[nodiscard]] static constexpr T ByteSwap(T value) noexcept
    {
        auto bytes = std::bit_cast<std::array<std::byte, sizeof(T)>>(value);
        std::ranges::reverse(bytes);
        return std::bit_cast<T>(bytes);
    }

    template <std::integral T>
    [[nodiscard]] static constexpr T ToLittle(T value) noexcept
    {
        if constexpr (IS_LITTLE)
        {
            return value;
        }
        else
        {
            return ByteSwap(value);
        }
    }

    template <std::integral T>
    [[nodiscard]] static constexpr T ToBig(T value) noexcept
    {
        if constexpr (IS_LITTLE)
        {
            return ByteSwap(value);
        }
        else
        {
            return value;
        }
    }

    // Swapping is symmetric, so "from" is the same operation as "to".
    template <std::integral T>
    [[nodiscard]] static constexpr T FromLittle(T value) noexcept
    {
        return ToLittle(value);
    }

    template <std::integral T>
    [[nodiscard]] static constexpr T FromBig(T value) noexcept
    {
        return ToBig(value);
    }
};
```

---

## 10. Complete example

`src/Core/StringHash_s.hpp`:

```cpp
#pragma once

struct StringHash_s
{
    using is_transparent = void;

    [[nodiscard]] std::size_t operator()(std::string_view text) const noexcept
    {
        return std::hash<std::string_view>{}(text);
    }
};
```

`src/Core/ConfigFile.hpp`:

```cpp
#pragma once

#include "StringHash_s.hpp"

class ConfigFile
{
public:
    explicit ConfigFile(std::filesystem::path path);

    void Load();
    [[nodiscard]] std::optional<std::string_view> GetValue(std::string_view key) const;

private:
    std::filesystem::path m_path;
    std::unordered_map<std::string, std::string, StringHash_s, std::equal_to<>> m_values;
};
```

`src/Core/ConfigFile.cpp`:

```cpp
#include "pch.hpp"
#include "ConfigFile.hpp"

namespace
{
    constexpr auto COMMENT_PREFIX = '#';
    constexpr auto WHITESPACE = " \t\r"sv;

    std::string_view Trim(std::string_view text)
    {
        const auto first = text.find_first_not_of(WHITESPACE);
        if (first == std::string_view::npos)
        {
            return {};
        }

        const auto last = text.find_last_not_of(WHITESPACE);
        return text.substr(first, last - first + 1);
    }
}

ConfigFile::ConfigFile(std::filesystem::path path)
    : m_path{std::move(path)}
{
}

void ConfigFile::Load()
{
    auto file = std::ifstream{m_path};
    if (!file)
    {
        throw std::runtime_error{std::format("Failed to open config file: {}", m_path.string())};
    }

    auto line = std::string{};
    auto lineNumber = u32{0};
    while (std::getline(file, line))
    {
        ++lineNumber;

        const auto trimmed = Trim(line);
        if (trimmed.empty() || trimmed.front() == COMMENT_PREFIX)
        {
            continue;
        }

        const auto separator = trimmed.find('=');
        if (separator == std::string_view::npos)
        {
            throw std::runtime_error{std::format("{}:{}: expected 'key = value'", m_path.string(), lineNumber)};
        }

        auto key = std::string{Trim(trimmed.substr(0, separator))};
        auto value = std::string{Trim(trimmed.substr(separator + 1))};
        m_values.insert_or_assign(std::move(key), std::move(value));
    }
}

std::optional<std::string_view> ConfigFile::GetValue(std::string_view key) const
{
    const auto it = m_values.find(key);
    if (it == m_values.end())
    {
        return std::nullopt;
    }

    return it->second;
}
```

---

## 11. New project checklist

- [ ] Copy `CONVENTIONS.md`, `.clang-format`, `.editorconfig`, `.gitattributes`, and `CMakePresets.json` into the new repo.
- [ ] Create `vcpkg.json` with the project name, then run `vcpkg x-update-baseline --add-initial-baseline`.
- [ ] Create `CMakeLists.txt` from the template and set the project name.
- [ ] Create `src/pch.hpp`, `src/main.cpp`, and `src/Application.hpp` / `.cpp`.
- [ ] Add `build/` to `.gitignore`.
- [ ] Configure and build with both presets (`windows-msvc` and `linux-clang`) with zero warnings.
