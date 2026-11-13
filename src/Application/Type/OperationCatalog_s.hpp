#pragma once

#include "../../Utils/Type/TypeCatalog_s.hpp"
#include "ApplicationRequestContext_s.hpp"
#include "RequestControl_s.hpp"

template <typename... Operations>
struct OperationCatalog_s : TypeCatalog_s<Operations...>
{
    using Result = std::variant<typename Operations::Result...>;

    template <typename T>
    static auto Execute(const ApplicationRequestContext_s& context, const std::shared_ptr<RequestControl_s>& control, const T& request)
    {
        using Operation = typename TypeCatalog_s<Operations...>::template Definition<T>;
        return Operation::Execute(context, control, request);
    }
};
