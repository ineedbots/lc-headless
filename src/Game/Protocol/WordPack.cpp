#include "pch.hpp"
#include "WordPack.hpp"

namespace
{
    constexpr auto ONE_NIBBLE_LIMIT = 13;
    constexpr auto TWO_NIBBLE_OFFSET = 195;
    constexpr auto NO_CARRY = -1;
    constexpr auto NIBBLE_BITS = 4;
    constexpr auto NIBBLE_MASK = 0xF;

    // '\xA3' is the pound sign as a Latin-1 byte, the encoding every protocol string uses.
    constexpr auto TABLE = std::to_array<char>({
        ' ', 'e', 't', 'a', 'o', 'i', 'h', 'n', 's', 'r', 'd', 'l', 'u',
        'm', 'w', 'c', 'y', 'f', 'g', 'p', 'b', 'v', 'k', 'x', 'j', 'q', 'z',
        '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
        ' ', '!', '?', '.', ',', ':', ';', '(', ')', '-', '&', '*', '\\', '\'', '@', '#', '+', '=', '\xA3', '$', '%', '"', '[', ']',
    });

    static_assert(TABLE.size() == 61, "WordPack has 61 characters");

    char ToLower(char character)
    {
        if (character >= 'A' && character <= 'Z')
        {
            return static_cast<char>(character - 'A' + 'a');
        }

        return character;
    }

    s32 GetIndex(char character)
    {
        const auto found = std::ranges::find(TABLE, character);
        if (found == TABLE.end())
        {
            return 0;
        }

        return static_cast<s32>(found - TABLE.begin());
    }

    void UnpackNibble(s32 nibble, s32& carry, std::string& text)
    {
        if (carry != NO_CARRY)
        {
            text.push_back(TABLE[static_cast<std::size_t>((carry << NIBBLE_BITS) + nibble - TWO_NIBBLE_OFFSET)]);
            carry = NO_CARRY;
            return;
        }

        if (nibble < ONE_NIBBLE_LIMIT)
        {
            text.push_back(TABLE[static_cast<std::size_t>(nibble)]);
            return;
        }

        carry = nibble;
    }

    void ApplySentenceCase(std::string& text)
    {
        auto capitalizeNext = true;
        for (auto& character : text)
        {
            if (capitalizeNext && character >= 'a' && character <= 'z')
            {
                character = static_cast<char>(character - 'a' + 'A');
                capitalizeNext = false;
            }

            if (character == '.' || character == '!')
            {
                capitalizeNext = true;
            }
        }
    }
}

std::vector<u8> WordPack::Pack(std::string_view text)
{
    auto packed = std::vector<u8>{};
    auto carry = NO_CARRY;
    for (const auto character : text.substr(0, MAX_PACK_LENGTH))
    {
        auto index = GetIndex(ToLower(character));
        if (index >= ONE_NIBBLE_LIMIT)
        {
            index += TWO_NIBBLE_OFFSET;
        }

        if (carry == NO_CARRY)
        {
            if (index < ONE_NIBBLE_LIMIT)
            {
                carry = index;
                continue;
            }

            packed.push_back(static_cast<u8>(index));
            continue;
        }

        if (index < ONE_NIBBLE_LIMIT)
        {
            packed.push_back(static_cast<u8>((carry << NIBBLE_BITS) + index));
            carry = NO_CARRY;
            continue;
        }

        packed.push_back(static_cast<u8>((carry << NIBBLE_BITS) + (index >> NIBBLE_BITS)));
        carry = index & NIBBLE_MASK;
    }

    if (carry != NO_CARRY)
    {
        packed.push_back(static_cast<u8>(carry << NIBBLE_BITS));
    }

    return packed;
}

std::string WordPack::Unpack(std::span<const u8> packed)
{
    auto text = std::string{};
    auto carry = NO_CARRY;
    for (const auto byte : packed)
    {
        // As in TS, the limit is checked per byte, so a final byte can take the text one past it.
        if (text.size() >= MAX_UNPACK_LENGTH)
        {
            break;
        }

        UnpackNibble(byte >> NIBBLE_BITS, carry, text);
        UnpackNibble(byte & NIBBLE_MASK, carry, text);
    }

    ApplySentenceCase(text);
    return text;
}
