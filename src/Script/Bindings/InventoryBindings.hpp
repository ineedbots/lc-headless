#pragma once

#include "../../Cache/GameCache_s.hpp"
#include "BindingSupport.hpp"

class InventoryBindings
{
public:
    InventoryBindings() = delete;

    static void Add(std::vector<BoundFunction_s>& functions, const GameCache_s& cache);
};
