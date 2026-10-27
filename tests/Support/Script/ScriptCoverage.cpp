#include "pch.hpp"
// The executable-line map is the one version-dependent part of coverage. Keep pocketpy internals
// here in test support; the application and its scripting API only use the public headers.
// Include internals before the public wrapper, which otherwise also defines py_TValue.
extern "C"
{
#include <pocketpy/objects/codeobject.h>
}

#include "ScriptCoverage.hpp"

#include <nlohmann/json.hpp>

namespace
{
    ScriptCoverage* active = nullptr;

    void CollectLines(const CodeObject& code, std::vector<int>& lines)
    {
        const auto* instructions = static_cast<const Bytecode*>(code.codes.data);
        const auto* locations = static_cast<const BytecodeEx*>(code.codes_ex.data);
        for (auto i = 0; i < code.codes.length; ++i)
        {
            // ceval.c does not send a line event for a synthetic implicit return.
            if (instructions[i].op == OP_RETURN_VALUE && instructions[i].arg == BC_RETURN_VIRTUAL)
            {
                continue;
            }
            if (locations[i].lineno > 0)
            {
                lines.push_back(locations[i].lineno);
            }
        }
        const auto* declarations = static_cast<const FuncDecl_*>(code.func_decls.data);
        for (auto i = 0; i < code.func_decls.length; ++i)
        {
            CollectLines(declarations[i]->code, lines);
        }
    }
}

ScriptCoverage::ScriptCoverage(std::span<const StdlibFile_s> files)
{
    for (const auto& file : files)
    {
        m_hits.emplace(file.path, std::vector<u64>(static_cast<std::size_t>(std::ranges::count(file.source, '\n')) + 2));
    }
    m_previous = active;
    m_previousCtor = py_appcallbacks()->on_vm_ctor;
    if (m_previousCtor != nullptr && m_previousCtor != OnVmCreated)
    {
        throw std::runtime_error{"Script coverage cannot replace another VM constructor callback"};
    }
    active = this;
    py_appcallbacks()->on_vm_ctor = OnVmCreated;
}

ScriptCoverage::~ScriptCoverage()
{
    Stop();
}

void ScriptCoverage::AttachToCurrentVm()
{
    py_sys_settrace(Trace, true);
    m_attached = true;
}

void ScriptCoverage::OnVmCreated(int)
{
    active->AttachToCurrentVm();
}

void ScriptCoverage::Stop()
{
    if (!m_enabled)
    {
        return;
    }
    assert(active == this && "Coverage collectors must be stopped in reverse construction order");
    if (m_attached && m_previous == nullptr)
    {
        py_sys_settrace(nullptr, true);
    }
    active = m_previous;
    py_appcallbacks()->on_vm_ctor = m_previousCtor;
    m_enabled = false;
}

void ScriptCoverage::Trace(py_Frame* frame, py_TraceEvent event) noexcept
{
    if (event != TRACE_EVENT_LINE || active == nullptr)
    {
        return;
    }
    try
    {
        auto line = 0;
        auto path = std::string_view{py_Frame_sourceloc(frame, &line)};
        auto normalized = std::string{};
        if (path.find('\\') != std::string_view::npos)
        {
            normalized = path;
            std::ranges::replace(normalized, '\\', '/');
            path = normalized;
        }
        if (path != active->m_lastPath || active->m_lastLines == nullptr)
        {
            const auto found = active->m_hits.find(path);
            if (found == active->m_hits.end())
            {
                return;
            }
            active->m_lastPath = found->first;
            active->m_lastLines = &found->second;
        }
        auto& counts = *active->m_lastLines;
        if (line <= 0 || static_cast<std::size_t>(line) >= counts.size())
        {
            active->m_failed = true;
            return;
        }
        ++counts[static_cast<std::size_t>(line)];
    }
    catch (...)
    {
        // No C++ exception may escape the interpreter's C callback.
        active->m_failed = true;
    }
}

const std::map<std::string, std::vector<u64>, std::less<>>& ScriptCoverage::GetHits() const
{
    return m_hits;
}

bool ScriptCoverage::Failed() const
{
    return m_failed;
}

std::chrono::milliseconds ScriptCoverage::AdjustTimeout(std::chrono::milliseconds timeout)
{
    return active != nullptr ? timeout * 5 : timeout;
}

void ScriptCoverage::Write(const std::filesystem::path& path) const
{
    auto files = nlohmann::json::object();
    for (const auto& [name, counts] : m_hits)
    {
        auto lines = nlohmann::json::object();
        for (auto line = std::size_t{1}; line < counts.size(); ++line)
        {
            if (counts[line] != 0)
            {
                lines[std::to_string(line)] = counts[line];
            }
        }
        if (!lines.empty())
        {
            files[name] = std::move(lines);
        }
    }
    auto output = std::ofstream{};
    output.exceptions(std::ios::failbit | std::ios::badbit);
    output.open(path, std::ios::binary);
    output << nlohmann::json{{"version", 1}, {"failed", m_failed}, {"files", std::move(files)}}.dump() << '\n';
}

std::vector<int> ScriptCoverage::ExecutableLines(std::string_view source, std::string_view filename)
{
    if (!py_compile(std::string{source}.c_str(), std::string{filename}.c_str(), EXEC_MODE, false))
    {
        auto* error = py_formatexc();
        const auto message = std::string{error == nullptr ? "Cannot compile coverage source" : error};
        py_free(error);
        py_clearexc(nullptr);
        throw std::runtime_error{message};
    }
    auto lines = std::vector<int>{};
    CollectLines(*static_cast<const CodeObject*>(py_touserdata(py_retval())), lines);
    std::ranges::sort(lines);
    lines.erase(std::unique(lines.begin(), lines.end()), lines.end());
    return lines;
}
