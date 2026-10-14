#pragma once

// When Python raised, the message is pocketpy's traceback.
class ScriptError : public std::runtime_error
{
public:
    using std::runtime_error::runtime_error;
};
