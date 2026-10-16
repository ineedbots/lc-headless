#pragma once

class ConfigError : public std::runtime_error
{
public:
    using std::runtime_error::runtime_error;
};
