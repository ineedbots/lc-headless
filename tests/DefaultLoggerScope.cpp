#include "pch.hpp"
#include "DefaultLoggerScope.hpp"

#include "Core/Logger.hpp"

DefaultLoggerScope::DefaultLoggerScope(std::shared_ptr<Logger> logger)
    : m_previous{Logger::SetDefault(std::move(logger))}
{
}

DefaultLoggerScope::~DefaultLoggerScope()
{
    Logger::SetDefault(std::move(m_previous));
}
