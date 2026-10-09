#pragma once

#include "../Core/Logger.hpp"
#include "GameCache_s.hpp"

class CacheLoader
{
public:
    static constexpr u32 CONFIG_ARCHIVE = 2;
    static constexpr u32 INTERFACE_ARCHIVE = 3;
    static constexpr u32 VERSIONLIST_ARCHIVE = 5;

    CacheLoader() = delete;

    // Reads and decodes the server's store in the folder, then closes it. Throws CacheError, with the
    // folder in front of the message, when a file is missing or damaged.
    [[nodiscard]] static GameCache_s Load(const std::filesystem::path& directory, Logger& logger = *Logger::GetDefault());
};
