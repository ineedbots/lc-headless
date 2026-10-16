#pragma once

#include "BindingSupport.hpp"

class ActionBindings
{
public:
    ActionBindings() = delete;

    static void Add(std::vector<BoundFunction_s>& functions);
};
