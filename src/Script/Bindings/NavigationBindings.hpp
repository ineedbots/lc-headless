#pragma once

#include "BindingSupport.hpp"

class NavigationBindings
{
public:
    NavigationBindings() = delete;

    static void Add(std::vector<BoundFunction_s>& functions);
};
