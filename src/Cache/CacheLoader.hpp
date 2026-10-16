#pragma once

#include "../Config/Revision_e.hpp"
#include "../Console/Logger.hpp"
#include "GameCache_s.hpp"

// Reads the revision's layout: the 225 engine's folder of loose archive files and map files, or 289's store.
class CacheLoader
{
public:
    static constexpr u32 CONFIG_ARCHIVE = 2;
    static constexpr u32 INTERFACE_ARCHIVE = 3;
    static constexpr u32 VERSIONLIST_ARCHIVE = 5;
    // 225's archive files, in the order its login CRCs list them after a leading 0.
    static constexpr auto ARCHIVE_FILES_225 = std::to_array<std::string_view>({"title", "config", "interface", "media", "models", "textures", "wordenc", "sounds"});
    static constexpr auto MAPS_FOLDER_225 = "maps"sv;

    CacheLoader() = delete;

    [[nodiscard]] static GameCache_s Load(const std::filesystem::path& directory, Revision_e revision, Logger& logger = *Logger::GetDefault());
};
