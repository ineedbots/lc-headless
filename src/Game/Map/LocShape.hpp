#pragma once

#include "../State/Zone_s.hpp"

// The webclient's loc shapes. A shape decides the layer a loc sits in on its tile, and how it blocks.
class LocShape
{
public:
    static constexpr u8 WALL_STRAIGHT = 0;
    static constexpr u8 WALL_DIAGONAL_CORNER = 1;
    static constexpr u8 WALL_L = 2;
    static constexpr u8 WALL_SQUARE_CORNER = 3;
    static constexpr u8 WALLDECOR_STRAIGHT_NOOFFSET = 4;
    static constexpr u8 WALLDECOR_STRAIGHT_OFFSET = 5;
    static constexpr u8 WALLDECOR_DIAGONAL_OFFSET = 6;
    static constexpr u8 WALLDECOR_DIAGONAL_NOOFFSET = 7;
    static constexpr u8 WALLDECOR_DIAGONAL_BOTH = 8;
    static constexpr u8 WALL_DIAGONAL = 9;
    static constexpr u8 CENTREPIECE_STRAIGHT = 10;
    static constexpr u8 CENTREPIECE_DIAGONAL = 11;
    static constexpr u8 ROOF_STRAIGHT = 12;
    static constexpr u8 ROOFEDGE_SQUARE_CORNER = 21;
    static constexpr u8 GROUND_DECOR = 22;

    LocShape() = delete;

    // Throws ProtocolError for a shape past GROUND_DECOR.
    [[nodiscard]] static LocLayer_e GetLayer(u8 shape);
};
