#include "pch.hpp"
#include "ScriptVm.hpp"

#include "../Core/Logger.hpp"
#include "ScriptError.hpp"
#include "ScriptRuntime.hpp"
#include "Stdlib.hpp"

#include <pocketpy.h>

namespace
{
    constexpr auto SOURCE_EXTENSION = ".py";
    constexpr auto MAIN_MODULE = "__main__";
    constexpr auto BUILTINS_MODULE = "builtins";
    constexpr auto TIME_MODULE = "time";
    constexpr auto JSON_MODULE = "json";

    using PyText = std::unique_ptr<char, decltype(&py_free)>;

    c11_sv ToSv(std::string_view text)
    {
        return c11_sv{text.data(), static_cast<int>(text.size())};
    }

    std::optional<std::string> ReadText(const std::filesystem::path& path)
    {
        auto file = std::ifstream{path, std::ios::binary};
        if (!file)
        {
            return std::nullopt;
        }

        return std::string{std::istreambuf_iterator<char>{file}, std::istreambuf_iterator<char>{}};
    }

    bool IsInsideFolder(const std::filesystem::path& relative)
    {
        if (relative.empty() || relative.has_root_name() || relative.has_root_directory())
        {
            return false;
        }

        return std::ranges::none_of(relative, [](const std::filesystem::path& part)
        {
            return part == "..";
        });
    }

    // pocketpy frees what an import callback returns, so it's copied into pocketpy's allocator.
    char* CopyForPocketpy(std::string_view source, int* size)
    {
        auto* data = static_cast<char*>(py_malloc(source.size() + 1));
        std::memcpy(data, source.data(), source.size());
        data[source.size()] = '\0';
        if (size != nullptr)
        {
            *size = static_cast<int>(source.size());
        }

        return data;
    }

    std::string TrimTrailingNewlines(std::string text)
    {
        while (!text.empty() && (text.back() == '\n' || text.back() == '\r'))
        {
            text.pop_back();
        }

        return text;
    }
}

ScriptVm::ScriptVm(ScriptRuntime& runtime, ScriptVmOptions_s options, std::shared_ptr<Logger> logger)
    : m_runtime{runtime}
    , m_options{std::move(options)}
    , m_logger{std::move(logger)}
    , m_slot{runtime.AcquireSlot()}
{
    try
    {
        Activate();
        py_setvmctx(this);
        auto* callbacks = py_callbacks();
        callbacks->importfile = ImportFile;
        callbacks->print = Print;
        callbacks->flush = Flush;
        InstallBuiltins();
        DisableSleep();
    }
    catch (const std::exception&)
    {
        m_runtime.ReleaseSlot(m_slot);
        throw;
    }
}

ScriptVm::~ScriptVm()
{
    Activate();
    FlushOutput();
    m_runtime.ReleaseSlot(m_slot);
}

void ScriptVm::RunFile(const std::filesystem::path& relativePath)
{
    if (!IsInsideFolder(relativePath))
    {
        throw ScriptError{std::format("Script path {} must be relative to the scripts directory", relativePath.generic_string())};
    }

    const auto path = m_options.scriptsDirectory / relativePath;
    m_files.push_back(path);
    const auto source = ReadText(path);
    if (!source)
    {
        throw ScriptError{std::format("Can't read script {}", path.generic_string())};
    }

    RunSource(*source, relativePath.generic_string());
}

void ScriptVm::RunSource(std::string_view source, std::string_view filename, py_GlobalRef module)
{
    Activate();
    const auto sourceText = std::string{source};
    const auto filenameText = std::string{filename};
    RunGuarded([&sourceText, &filenameText, module]
    {
        return py_exec(sourceText.c_str(), filenameText.c_str(), EXEC_MODE, module);
    });
}

bool ScriptVm::HasFunction(std::string_view name)
{
    Activate();
    const auto item = py_getdict(GetMain(), py_namev(ToSv(name)));
    return item != nullptr && py_callable(item);
}

py_GlobalRef ScriptVm::Call(std::string_view function, std::span<const py_Ref> args)
{
    return CallIn(GetMain(), function, args);
}

py_GlobalRef ScriptVm::CallBuiltin(std::string_view function, std::span<const py_Ref> args)
{
    return CallIn(GetBuiltins(), function, args);
}

py_GlobalRef ScriptVm::LoadJson(const std::string& json)
{
    Activate();
    if (py_import(JSON_MODULE) != 1)
    {
        ThrowPythonError(nullptr);
    }

    RunGuarded([&json]
    {
        return py_json_loads(json.c_str());
    });

    return py_retval();
}

void ScriptVm::WaitForDebugger()
{
    Activate();
    m_logger->Info("Waiting for VS Code's pocketpy debugger to attach on {}:{}", DEBUGGER_HOST, DEBUGGER_PORT);
    py_debugger_waitforattach(DEBUGGER_HOST, DEBUGGER_PORT);
    m_logger->Info("Debugger attached");
}

py_GlobalRef ScriptVm::CallIn(py_GlobalRef module, std::string_view function, std::span<const py_Ref> args)
{
    Activate();
    const auto callable = py_getdict(module, py_namev(ToSv(function)));
    if (callable == nullptr || !py_callable(callable))
    {
        throw ScriptError{std::format("The script has no function {}()", function)};
    }

    RunGuarded([callable, args]
    {
        py_push(callable);
        py_pushnil();
        for (const auto arg : args)
        {
            py_push(arg);
        }

        return py_vectorcall(static_cast<u16>(args.size()), 0);
    });

    return py_retval();
}

void ScriptVm::Activate() const
{
    py_switchvm(m_slot);
}

py_GlobalRef ScriptVm::GetBuiltins() const
{
    Activate();
    return py_getmodule(BUILTINS_MODULE);
}

py_GlobalRef ScriptVm::GetMain() const
{
    Activate();
    return py_getmodule(MAIN_MODULE);
}

s32 ScriptVm::GetSlot() const
{
    return m_slot;
}

Logger& ScriptVm::GetLogger() const
{
    return *m_logger;
}

const std::vector<std::filesystem::path>& ScriptVm::GetFiles() const
{
    return m_files;
}

ScriptVm& ScriptVm::GetCurrent()
{
    auto* vm = static_cast<ScriptVm*>(py_getvmctx());
    assert(vm != nullptr && "The current pocketpy VM isn't owned by a ScriptVm");
    return *vm;
}

void ScriptVm::InstallBuiltins()
{
    const auto builtins = GetBuiltins();
    py_bind(builtins, "log(*args)", Log);
    py_bind(builtins, "debug(*args)", Debug);
}

void ScriptVm::DisableSleep()
{
    if (py_import(TIME_MODULE) != 1)
    {
        ThrowPythonError(nullptr);
    }

    py_bindfunc(py_getmodule(TIME_MODULE), "sleep", Sleep);
}

template <typename TCall>
void ScriptVm::RunGuarded(TCall call)
{
    const auto unwindPoint = py_peek(0);
    py_watchdog_begin(m_options.callTimeout.count());
    const auto succeeded = call();
    py_watchdog_end();
    if (!succeeded)
    {
        ThrowPythonError(unwindPoint);
    }
}

void ScriptVm::ThrowPythonError(py_StackRef unwindPoint)
{
    auto message = std::string{"Python raised an exception"};
    const auto traceback = PyText{py_formatexc(), &py_free};
    if (traceback != nullptr)
    {
        message = TrimTrailingNewlines(traceback.get());
    }

    py_clearexc(unwindPoint);
    throw ScriptError{message};
}

std::optional<std::filesystem::path> ScriptVm::ResolveImport(std::string_view request) const
{
    const auto relative = std::filesystem::path{request};
    if (relative.extension() != SOURCE_EXTENSION || !IsInsideFolder(relative))
    {
        return std::nullopt;
    }

    for (const auto& folder : {m_options.scriptsDirectory, m_options.scriptsDirectory / LIBRARY_FOLDER})
    {
        auto candidate = folder / relative;
        if (std::filesystem::is_regular_file(candidate))
        {
            return candidate;
        }
    }

    return std::nullopt;
}

void ScriptVm::AppendOutput(std::string_view text)
{
    m_output += text;
    for (auto lineEnd = m_output.find('\n'); lineEnd != std::string::npos; lineEnd = m_output.find('\n'))
    {
        m_logger->Info("{}", std::string_view{m_output}.substr(0, lineEnd));
        m_output.erase(0, lineEnd + 1);
    }
}

void ScriptVm::FlushOutput()
{
    if (m_output.empty())
    {
        return;
    }

    m_logger->Info("{}", m_output);
    m_output.clear();
}

bool ScriptVm::Log(int argc, py_StackRef argv) noexcept
{
    PY_CHECK_ARGC(1);
    return WriteLog(LogLevel_e::Info, py_arg(0));
}

bool ScriptVm::Debug(int argc, py_StackRef argv) noexcept
{
    PY_CHECK_ARGC(1);
    return WriteLog(LogLevel_e::Verbose, py_arg(0));
}

bool ScriptVm::WriteLog(LogLevel_e level, py_Ref args) noexcept
{
    auto message = std::string{};
    const auto count = py_tuple_len(args);
    for (auto i = 0; i < count; ++i)
    {
        if (!py_str(py_tuple_getitem(args, i)))
        {
            return false;
        }

        auto size = 0;
        const auto* text = py_tostrn(py_retval(), &size);
        if (i > 0)
        {
            message += ' ';
        }

        message.append(text, static_cast<std::size_t>(size));
    }

    GetCurrent().m_logger->Log(level, "{}", message);
    py_newnone(py_retval());
    return true;
}

bool ScriptVm::Sleep(int, py_StackRef) noexcept
{
    return py_exception(tp_RuntimeError, "time.sleep() would stall every account; return a delay from loop() instead");
}

char* ScriptVm::ImportFile(const char* path, int* size) noexcept
{
    // Called from pocketpy's C code, so no exception may leave it; a file that can't be read is a missing module.
    try
    {
        // The standard library comes first, so a script can't shadow it. It isn't one of the script's files.
        if (const auto library = Stdlib::Find(path))
        {
            return CopyForPocketpy(*library, size);
        }

        auto& vm = GetCurrent();
        const auto file = vm.ResolveImport(path);
        if (!file)
        {
            return nullptr;
        }

        vm.m_files.push_back(*file);
        const auto source = ReadText(*file);
        if (!source)
        {
            return nullptr;
        }

        return CopyForPocketpy(*source, size);
    }
    catch (const std::exception& e)
    {
        GetCurrent().m_logger->Warning("Can't import {}: {}", path, e.what());
        return nullptr;
    }
}

void ScriptVm::Print(const char* text) noexcept
{
    GetCurrent().AppendOutput(text);
}

void ScriptVm::Flush() noexcept
{
    GetCurrent().FlushOutput();
}
