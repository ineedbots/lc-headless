#pragma once

#include <pocketpy.h>

// Plain values both ways. Reading a value of the wrong type throws ScriptTypeError, and a number out of range
// std::invalid_argument, which the bindings raise as TypeError and ValueError.
class PyValue
{
public:
    static constexpr auto BUILTINS_MODULE = "builtins";

    PyValue() = delete;

    static void FromString(py_OutRef out, std::string_view text);
    static void FromPoint(py_OutRef out, s32 x, s32 z);

    // Each item is set to None as it's appended and converted in place, so the list never holds an
    // uninitialized value when a conversion allocates and the collector runs.
    template <typename T, typename TConvert>
    static void FromList(py_OutRef out, const std::vector<T>& values, TConvert convert)
    {
        py_newlist(out);

        for (const auto& value : values)
        {
            const auto item = py_list_emplace(out);
            py_newnone(item);
            convert(item, value);
        }
    }

    template <typename T, typename TConvert>
    static void FromOptional(py_OutRef out, const std::optional<T>& value, TConvert convert)
    {
        if (!value)
        {
            py_newnone(out);
            return;
        }

        convert(out, *value);
    }

    [[nodiscard]] static s64 ToInt(py_Ref value, std::string_view name);
    [[nodiscard]] static s64 ToInt(py_Ref value, std::string_view name, s64 min, s64 max);
    [[nodiscard]] static bool ToBool(py_Ref value, std::string_view name);
    [[nodiscard]] static std::string ToString(py_Ref value, std::string_view name);
    [[nodiscard]] static std::optional<s64> ToOptionalInt(py_Ref value, std::string_view name);
    [[nodiscard]] static std::optional<bool> ToOptionalBool(py_Ref value, std::string_view name);
    [[nodiscard]] static u16 ToU16(py_Ref value, std::string_view name);

    // An instance of the class builtins has under that name.
    [[nodiscard]] static bool IsInstance(py_Ref value, std::string_view className);
    // Throws ScriptTypeError when the object has no such attribute.
    [[nodiscard]] static py_Ref GetField(py_Ref object, const char* name);
    // For error messages.
    [[nodiscard]] static std::string_view GetTypeName(py_Ref value);
};
