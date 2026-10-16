#pragma once

// Where a value sits in the text, as byte offsets, and an object's members in the order the text has them.
struct JsoncValue_s
{
    struct Member_s
    {
        std::string key;
        std::size_t keyBegin = 0;
    };

    std::size_t begin = 0;
    std::size_t end = 0;
    bool isObject = false;
    std::vector<Member_s> members;
    // values[i] is members[i]'s value.
    std::vector<JsoncValue_s> values;
};
