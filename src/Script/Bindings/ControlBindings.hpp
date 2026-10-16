#pragma once

#include "BindingSupport.hpp"

class ControlBindings
{
public:
    ControlBindings() = delete;

    static void Add(std::vector<BoundFunction_s>& functions);
};
