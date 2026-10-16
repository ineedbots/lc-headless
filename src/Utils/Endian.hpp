#pragma once

static_assert(std::endian::native == std::endian::little || std::endian::native == std::endian::big,
              "Mixed-endian platforms are not supported");

class Endian
{
public:
    Endian() = delete;

    static constexpr bool IS_LITTLE = std::endian::native == std::endian::little;

    // TODO: replace with std::byteswap when moving to C++23
    template <std::integral T>
    [[nodiscard]] static constexpr T ByteSwap(T value) noexcept
    {
        auto bytes = std::bit_cast<std::array<std::byte, sizeof(T)>>(value);
        std::ranges::reverse(bytes);
        return std::bit_cast<T>(bytes);
    }

    template <std::integral T>
    [[nodiscard]] static constexpr T ToLittle(T value) noexcept
    {
        if constexpr (IS_LITTLE)
        {
            return value;
        }
        else
        {
            return ByteSwap(value);
        }
    }

    template <std::integral T>
    [[nodiscard]] static constexpr T ToBig(T value) noexcept
    {
        if constexpr (IS_LITTLE)
        {
            return ByteSwap(value);
        }
        else
        {
            return value;
        }
    }

    // Swapping is symmetric, so "from" is the same operation as "to".
    template <std::integral T>
    [[nodiscard]] static constexpr T FromLittle(T value) noexcept
    {
        return ToLittle(value);
    }

    template <std::integral T>
    [[nodiscard]] static constexpr T FromBig(T value) noexcept
    {
        return ToBig(value);
    }
};
