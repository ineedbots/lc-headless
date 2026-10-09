#include "pch.hpp"
#include "LocShape.hpp"

#include "../ProtocolError.hpp"
#include "../State/Zone_s.hpp"

LocLayer_e LocShape::GetLayer(u8 shape)
{
    if (shape <= WALL_SQUARE_CORNER)
    {
        return LocLayer_e::Wall;
    }

    if (shape <= WALLDECOR_DIAGONAL_BOTH)
    {
        return LocLayer_e::WallDecor;
    }

    if (shape <= ROOFEDGE_SQUARE_CORNER)
    {
        return LocLayer_e::Ground;
    }

    if (shape == GROUND_DECOR)
    {
        return LocLayer_e::GroundDecor;
    }

    throw ProtocolError{std::format("Loc shape {} is not 0 to {}", shape, GROUND_DECOR)};
}
