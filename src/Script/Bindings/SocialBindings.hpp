#pragma once

#include "BindingSupport.hpp"

class SocialBindings
{
public:
    SocialBindings() = delete;

    static void Add(std::vector<BoundFunction_s>& functions);
};
