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

    [[nodiscard]] static std::vector<MapIndexEntry_s> DecodeIndex(std::span<const u8> data);
    // The loc types decide what's decoration. An empty land or locs span stands for a file the square doesn't
    // have, which a real file never is: open ground with no flags, or no locs.
    [[nodiscard]] static MapSquare DecodeSquare(u16 square, std::span<const u8> land, std::span<const u8> locs, std::span<const LocType_s> types);
    // x_z, in squares.
    [[nodiscard]] static std::string DescribeSquare(u16 square);
};
