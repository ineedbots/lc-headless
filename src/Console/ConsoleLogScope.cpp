#include "pch.hpp"
#include "ConsoleLogScope.hpp"

#include "ConsoleInput.hpp"

ConsoleLogScope::ConsoleLogScope(Install install, std::shared_ptr<ConsoleInput> console)
    : m_install{std::move(install)}
    , m_console{std::move(console)}
{
    m_install(m_console);
}

ConsoleLogScope::~ConsoleLogScope()
{
    if (m_console)
    {
        m_console->Close();
    }

    m_install(nullptr);
}
