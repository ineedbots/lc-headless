#pragma once

// A script failed: it didn't compile, raised an exception, ran past its time limit, or broke what the
// host expects of it. When Python raised, the message is pocketpy's traceback.
class ScriptError : public std::runtime_error
{
public:
    using std::runtime_error::runtime_error;
};
