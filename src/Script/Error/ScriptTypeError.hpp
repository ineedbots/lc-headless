#pragma once

// A script passed a value of the wrong type; the bindings raise it as TypeError.
class ScriptTypeError : public std::runtime_error
{
public:
    using std::runtime_error::runtime_error;
};
