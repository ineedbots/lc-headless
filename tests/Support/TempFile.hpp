#pragma once

// Closing the stream also removes the temporary file.
inline std::unique_ptr<std::FILE, decltype(&std::fclose)> MakeTempFile()
{
#ifdef _WIN32
    auto* file = static_cast<std::FILE*>(nullptr);
    if (tmpfile_s(&file) != 0)
    {
        throw std::runtime_error{"Can't create a temporary file"};
    }
#else
    auto* file = std::tmpfile();
    if (file == nullptr)
    {
        throw std::runtime_error{"Can't create a temporary file"};
    }
#endif
    return {file, &std::fclose};
}
