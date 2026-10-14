#pragma once

class CacheError : public std::runtime_error
{
public:
    using std::runtime_error::runtime_error;
};
