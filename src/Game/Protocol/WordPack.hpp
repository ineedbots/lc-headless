#pragma once

class WordPack
{
public:
    static constexpr std::size_t MAX_PACK_LENGTH = 80;
    static constexpr std::size_t MAX_UNPACK_LENGTH = 100;

    WordPack() = delete;

    [[nodiscard]] static std::vector<u8> Pack(std::string_view text);
    [[nodiscard]] static std::string Unpack(std::span<const u8> packed);
};
