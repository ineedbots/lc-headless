#pragma once

#include "BindingSupport.hpp"

class WorldBindings
{
public:
    WorldBindings() = delete;

    static void Add(std::vector<BoundFunction_s>& functions);
};
