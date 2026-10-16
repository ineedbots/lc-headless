#pragma once

// Python already raised; the bindings leave its exception in place.
class ScriptRaisedError : public std::runtime_error
{
public:
    using std::runtime_error::runtime_error;
};
