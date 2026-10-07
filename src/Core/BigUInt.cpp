#include "pch.hpp"
#include "BigUInt.hpp"

namespace
{
    constexpr auto LIMB_BITS = std::size_t{32};
    constexpr auto LIMB_BYTES = std::size_t{4};
    constexpr auto SIGN_BIT = u8{0x80};
    constexpr auto DECIMAL_RADIX = u32{10};
    constexpr auto HEX_RADIX = u32{16};

    bool HasHexPrefix(std::string_view text)
    {
        return text.size() >= 2 && text[0] == '0' && (text[1] == 'x' || text[1] == 'X');
    }

    std::optional<u32> GetDigitValue(char digit, u32 radix)
    {
        auto value = u32{0};
        if (digit >= '0' && digit <= '9')
        {
            value = static_cast<u32>(digit - '0');
        }
        else if (digit >= 'a' && digit <= 'f')
        {
            value = static_cast<u32>(digit - 'a' + 10);
        }
        else if (digit >= 'A' && digit <= 'F')
        {
            value = static_cast<u32>(digit - 'A' + 10);
        }
        else
        {
            return std::nullopt;
        }

        if (value >= radix)
        {
            return std::nullopt;
        }

        return value;
    }
}

BigUInt BigUInt::Parse(std::string_view text)
{
    if (HasHexPrefix(text))
    {
        return ParseDigits(text.substr(2), HEX_RADIX);
    }

    return ParseDigits(text, DECIMAL_RADIX);
}

BigUInt BigUInt::FromBytesBigEndian(std::span<const u8> bytes)
{
    auto result = BigUInt{};
    result.m_limbs.resize((bytes.size() + LIMB_BYTES - 1) / LIMB_BYTES);
    for (std::size_t i = 0; i < bytes.size(); ++i)
    {
        const auto byte = bytes[bytes.size() - 1 - i];
        result.m_limbs[i / LIMB_BYTES] |= static_cast<u32>(byte) << (8 * (i % LIMB_BYTES));
    }

    result.Normalize();
    return result;
}

BigUInt BigUInt::ModPow(const BigUInt& base, const BigUInt& exponent, const BigUInt& modulus)
{
    if (modulus.GetBitLength() <= 1)
    {
        throw std::invalid_argument{"BigUInt::ModPow needs a modulus greater than 1"};
    }

    if (base >= modulus)
    {
        throw std::invalid_argument{"BigUInt::ModPow needs a base smaller than the modulus"};
    }

    auto result = BigUInt{};
    result.m_limbs = {1};
    auto factor = base;
    const auto bitLength = exponent.GetBitLength();
    for (std::size_t bit = 0; bit < bitLength; ++bit)
    {
        if (exponent.GetBit(bit))
        {
            result = result.MultiplyMod(factor, modulus);
        }

        factor = factor.MultiplyMod(factor, modulus);
    }

    return result;
}

std::vector<u8> BigUInt::ToBytesBigEndian() const
{
    auto bytes = std::vector<u8>{};
    if (m_limbs.empty())
    {
        return bytes;
    }

    bytes.reserve(m_limbs.size() * LIMB_BYTES + 1);
    for (auto limb = m_limbs.rbegin(); limb != m_limbs.rend(); ++limb)
    {
        for (auto shift = LIMB_BITS; shift > 0; shift -= 8)
        {
            const auto byte = static_cast<u8>(*limb >> (shift - 8));
            if (bytes.empty() && byte == 0)
            {
                continue;
            }

            bytes.push_back(byte);
        }
    }

    // Matches JS bigIntToBytes: a leading zero keeps the value positive when read as two's complement.
    if ((bytes.front() & SIGN_BIT) != 0)
    {
        bytes.insert(bytes.begin(), 0);
    }

    return bytes;
}

std::strong_ordering BigUInt::operator<=>(const BigUInt& other) const
{
    if (m_limbs.size() != other.m_limbs.size())
    {
        return m_limbs.size() <=> other.m_limbs.size();
    }

    for (auto i = m_limbs.size(); i > 0; --i)
    {
        if (m_limbs[i - 1] != other.m_limbs[i - 1])
        {
            return m_limbs[i - 1] <=> other.m_limbs[i - 1];
        }
    }

    return std::strong_ordering::equal;
}

BigUInt BigUInt::ParseDigits(std::string_view digits, u32 radix)
{
    if (digits.empty())
    {
        throw std::invalid_argument{"BigUInt::Parse needs at least one digit"};
    }

    if (digits.size() > MAX_DIGITS)
    {
        throw std::invalid_argument{std::format("BigUInt::Parse accepts at most {} digits", MAX_DIGITS)};
    }

    auto result = BigUInt{};
    for (const auto digit : digits)
    {
        const auto value = GetDigitValue(digit, radix);
        if (!value)
        {
            throw std::invalid_argument{std::format("BigUInt::Parse found a character that isn't a base-{} digit", radix)};
        }

        result.MultiplySmall(radix);
        result.AddSmall(*value);
    }

    result.Normalize();
    return result;
}

void BigUInt::Normalize()
{
    while (!m_limbs.empty() && m_limbs.back() == 0)
    {
        m_limbs.pop_back();
    }
}

bool BigUInt::GetBit(std::size_t bit) const
{
    const auto limb = bit / LIMB_BITS;
    return limb < m_limbs.size() && ((m_limbs[limb] >> (bit % LIMB_BITS)) & 1u) != 0;
}

std::size_t BigUInt::GetBitLength() const
{
    if (m_limbs.empty())
    {
        return 0;
    }

    return (m_limbs.size() - 1) * LIMB_BITS + static_cast<std::size_t>(std::bit_width(m_limbs.back()));
}

// Add, Subtract and AddMod work in place, and are safe when other is *this, so
// MultiplyMod's inner loop reuses its two buffers instead of allocating on every bit.
void BigUInt::Add(const BigUInt& other)
{
    if (m_limbs.size() < other.m_limbs.size())
    {
        m_limbs.resize(other.m_limbs.size());
    }

    auto carry = u64{0};
    for (std::size_t i = 0; i < m_limbs.size(); ++i)
    {
        if (carry == 0 && i >= other.m_limbs.size())
        {
            break;
        }

        const auto sum = u64{m_limbs[i]} + u64{i < other.m_limbs.size() ? other.m_limbs[i] : 0} + carry;
        m_limbs[i] = static_cast<u32>(sum);
        carry = sum >> LIMB_BITS;
    }

    if (carry != 0)
    {
        m_limbs.push_back(static_cast<u32>(carry));
    }
}

void BigUInt::Subtract(const BigUInt& other)
{
    assert(*this >= other && "BigUInt::Subtract would go below zero");

    auto borrow = u64{0};
    for (std::size_t i = 0; i < m_limbs.size(); ++i)
    {
        if (borrow == 0 && i >= other.m_limbs.size())
        {
            break;
        }

        const auto left = u64{m_limbs[i]};
        const auto right = u64{i < other.m_limbs.size() ? other.m_limbs[i] : 0} + borrow;
        m_limbs[i] = static_cast<u32>(left - right);
        borrow = left < right ? 1 : 0;
    }

    Normalize();
}

void BigUInt::AddMod(const BigUInt& other, const BigUInt& modulus)
{
    Add(other);
    if (*this >= modulus)
    {
        Subtract(modulus);
    }
}

BigUInt BigUInt::MultiplyMod(const BigUInt& other, const BigUInt& modulus) const
{
    auto result = BigUInt{};
    auto addend = *this;
    const auto bitLength = other.GetBitLength();
    for (std::size_t bit = 0; bit < bitLength; ++bit)
    {
        if (other.GetBit(bit))
        {
            result.AddMod(addend, modulus);
        }

        addend.AddMod(addend, modulus);
    }

    return result;
}

void BigUInt::MultiplySmall(u32 factor)
{
    auto carry = u64{0};
    for (auto& limb : m_limbs)
    {
        const auto product = u64{limb} * factor + carry;
        limb = static_cast<u32>(product);
        carry = product >> LIMB_BITS;
    }

    if (carry != 0)
    {
        m_limbs.push_back(static_cast<u32>(carry));
    }
}

void BigUInt::AddSmall(u32 value)
{
    auto carry = u64{value};
    for (std::size_t i = 0; carry != 0; ++i)
    {
        if (i == m_limbs.size())
        {
            m_limbs.push_back(0);
        }

        const auto sum = u64{m_limbs[i]} + carry;
        m_limbs[i] = static_cast<u32>(sum);
        carry = sum >> LIMB_BITS;
    }
}
