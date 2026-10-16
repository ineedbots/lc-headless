#pragma once

#include "BindingSupport.hpp"

class PlayerBindings
{
public:
    PlayerBindings() = delete;

    static void Add(std::vector<BoundFunction_s>& functions);
};
