#pragma once

#include "Core/Logger.hpp"

class DefaultLoggerScope
{
public:
    explicit DefaultLoggerScope(std::shared_ptr<Logger> logger);
    ~DefaultLoggerScope();

    DefaultLoggerScope(const DefaultLoggerScope&) = delete;
    DefaultLoggerScope& operator=(const DefaultLoggerScope&) = delete;

private:
    std::shared_ptr<Logger> m_previous;
};
