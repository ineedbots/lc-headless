#pragma once

#include "LocType_s.hpp"
#include "MapSquare.hpp"

struct MapIndexEntry_s
{
    u16 square = 0;
    u16 landFile = 0;
    u16 locFile = 0;
};

class MapDecoder
{
public:
    MapDecoder() = delete;

    // Throws CacheError when the length isn't a multiple of an entry's 7 bytes.
    [[nodiscard]] static std::vector<MapIndexEntry_s> DecodeIndex(std::span<const u8> data);
    // Takes the square's land and loc files, already unpacked, and the loc types, which decide what's
    // decoration. Throws CacheError, naming the square and file, for data that doesn't decode.
    [[nodiscard]] static MapSquare DecodeSquare(u16 square, std::span<const u8> land, std::span<const u8> locs, std::span<const LocType_s> types);
    // As errors name it: x_z, in squares.
    [[nodiscard]] static std::string DescribeSquare(u16 square);
};
