#pragma once

// The game cache is missing, or holds data that can't be decoded.
class CacheError : public std::runtime_error
{
public:
    using std::runtime_error::runtime_error;
};
