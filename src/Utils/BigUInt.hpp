#pragma once

class BigUInt
{
public:
    BigUInt() = default;

    [[nodiscard]] static BigUInt Parse(std::string_view text);
    [[nodiscard]] static BigUInt FromBytesBigEndian(std::span<const u8> bytes);
    [[nodiscard]] static BigUInt ModPow(const BigUInt& base, const BigUInt& exponent, const BigUInt& modulus);

    [[nodiscard]] std::vector<u8> ToBytesBigEndian() const;

    [[nodiscard]] std::strong_ordering operator<=>(const BigUInt& other) const;
    [[nodiscard]] bool operator==(const BigUInt& other) const = default;

private:
    static constexpr std::size_t MAX_DIGITS = 1024;

    [[nodiscard]] static BigUInt ParseDigits(std::string_view digits, u32 radix);

    void Normalize();
    [[nodiscard]] bool GetBit(std::size_t bit) const;
    [[nodiscard]] std::size_t GetBitLength() const;
    void Add(const BigUInt& other);
    void Subtract(const BigUInt& other);
    void AddMod(const BigUInt& other, const BigUInt& modulus);
    [[nodiscard]] BigUInt MultiplyMod(const BigUInt& other, const BigUInt& modulus) const;
    void MultiplySmall(u32 factor);
    void AddSmall(u32 value);

    std::vector<u32> m_limbs;
};
