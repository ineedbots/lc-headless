#pragma once

#include "TypeCatalogEntry_s.hpp"

// Entries own the policy for a payload. Duplicate payloads make lookup ambiguous.
template <typename... Entries>
struct TypeCatalog_s : TypeCatalogEntry_s<Entries>...
{
    using TypeCatalogEntry_s<Entries>::Find...;
    using Payload = std::variant<typename Entries::Payload...>;

    template <typename T>
    using Definition = typename decltype(Find(std::type_identity<T>{}))::type;
};
