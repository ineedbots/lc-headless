#pragma once

#include "BindingSupport.hpp"

class InterfaceBindings
{
public:
    InterfaceBindings() = delete;

    static void Add(std::vector<BoundFunction_s>& functions);
};
