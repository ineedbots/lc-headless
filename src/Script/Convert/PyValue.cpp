#include "pch.hpp"
#include "PyValue.hpp"

#include "../Error/ScriptTypeError.hpp"

#include <pocketpy.h>

void PyValue::FromString(py_OutRef out, std::string_view text)
{
    py_newstrv(out, c11_sv{text.data(), static_cast<int>(text.size())});
}

void PyValue::FromPoint(py_OutRef out, s32 x, s32 z)
{
    py_newtuple(out, 2);
    py_newint(py_tuple_getitem(out, 0), x);
    py_newint(py_tuple_getitem(out, 1), z);
}

s64 PyValue::ToInt(py_Ref value, std::string_view name)
{
    if (!py_isint(value))
    {
        throw ScriptTypeError{std::format("{} must be an int, not {}", name, GetTypeName(value))};
    }

    return py_toint(value);
}

s64 PyValue::ToInt(py_Ref value, std::string_view name, s64 min, s64 max)
{
    const auto number = ToInt(value, name);
    if (number < min || number > max)
    {
        throw std::invalid_argument{std::format("{} must be from {} to {}, not {}", name, min, max, number)};
    }

    return number;
}

bool PyValue::ToBool(py_Ref value, std::string_view name)
{
    if (!py_isbool(value))
    {
        throw ScriptTypeError{std::format("{} must be True or False, not {}", name, GetTypeName(value))};
    }

    return py_tobool(value);
}

std::string PyValue::ToString(py_Ref value, std::string_view name)
{
    if (!py_isstr(value))
    {
        throw ScriptTypeError{std::format("{} must be a str, not {}", name, GetTypeName(value))};
    }

    auto size = 0;
    const auto* text = py_tostrn(value, &size);
    return std::string{text, static_cast<std::size_t>(size)};
}

std::optional<s64> PyValue::ToOptionalInt(py_Ref value, std::string_view name)
{
    if (py_isnone(value))
    {
        return std::nullopt;
    }

    return ToInt(value, name);
}

std::optional<bool> PyValue::ToOptionalBool(py_Ref value, std::string_view name)
{
    if (py_isnone(value))
    {
        return std::nullopt;
    }

    return ToBool(value, name);
}

u16 PyValue::ToU16(py_Ref value, std::string_view name)
{
    return static_cast<u16>(ToInt(value, name, 0, std::numeric_limits<u16>::max()));
}

bool PyValue::IsInstance(py_Ref value, std::string_view className)
{
    const auto name = std::string{className};
    const auto type = py_gettype(BUILTINS_MODULE, py_name(name.c_str()));
    return type != 0 && py_isinstance(value, type);
}

py_Ref PyValue::GetField(py_Ref object, const char* name)
{
    const auto field = py_getdict(object, py_name(name));
    if (field == nullptr)
    {
        throw ScriptTypeError{std::format("the object has no {} attribute", name)};
    }

    return field;
}

std::string_view PyValue::GetTypeName(py_Ref value)
{
    return py_tpname(py_typeof(value));
}
