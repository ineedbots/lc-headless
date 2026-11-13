#pragma once

template <typename Entry>
struct TypeCatalogEntry_s
{
    static std::type_identity<Entry> Find(std::type_identity<typename Entry::Payload>);
};
