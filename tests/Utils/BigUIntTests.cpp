#include "pch.hpp"

#include "Utils/BigUInt.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/generators/catch_generators.hpp>

namespace
{
    struct ByteRoundTrip_s
    {
        std::vector<u8> input;
        std::vector<u8> output;
    };

    struct ModPowCase_s
    {
        std::string_view base;
        std::string_view exponent;
        std::string_view modulus;
        std::string_view result;
    };

    BigUInt FromBytes(std::initializer_list<u8> bytes)
    {
        return BigUInt::FromBytesBigEndian(std::vector<u8>{bytes});
    }
}

TEST_CASE("BigUInt::Parse accepts decimal and 0x-hex numbers", "[BigUInt]")
{
    CHECK(BigUInt::Parse("0") == BigUInt{});
    CHECK(BigUInt::Parse("000") == BigUInt{});

    const auto byteMax = FromBytes({0xFF});
    CHECK(BigUInt::Parse("255") == byteMax);
    CHECK(BigUInt::Parse("0xFF") == byteMax);
    CHECK(BigUInt::Parse("0Xff") == byteMax);
    CHECK(BigUInt::Parse("0xfF") == byteMax);

    CHECK(BigUInt::Parse("000123") == BigUInt::Parse("123"));

    const auto twoLimbs = FromBytes({0x01, 0x00, 0x00, 0x00, 0x00});
    CHECK(BigUInt::Parse("4294967296") == twoLimbs);
    CHECK(BigUInt::Parse("0x100000000") == twoLimbs);

    CHECK_NOTHROW(BigUInt::Parse(std::string(1024, '9')));
    CHECK_NOTHROW(BigUInt::Parse("0x" + std::string(1024, 'f')));
}

TEST_CASE("BigUInt::Parse rejects malformed numbers", "[BigUInt]")
{
    const auto text = GENERATE(
        std::string{""},
        std::string{"0x"},
        std::string{"0x0x1"},
        std::string{"12a"},
        std::string{"0xg"},
        std::string{"-1"},
        std::string{"+1"},
        std::string{" 1"},
        std::string{"1 "},
        std::string(1025, '9'),
        "0x" + std::string(1025, 'f'));

    CAPTURE(text);
    CHECK_THROWS_AS(BigUInt::Parse(text), std::invalid_argument);
}

TEST_CASE("BigUInt orders by value", "[BigUInt]")
{
    CHECK(BigUInt::Parse("1") < BigUInt::Parse("2"));
    CHECK(BigUInt::Parse("0xFFFFFFFF") < BigUInt::Parse("0x100000000"));
    CHECK(BigUInt::Parse("0x100000001") < BigUInt::Parse("0x200000000"));
    CHECK(BigUInt::Parse("0x100000001") < BigUInt::Parse("0x100000002"));
    CHECK(FromBytes({0x00, 0x00, 0x01}) == BigUInt::Parse("1"));
}

TEST_CASE("BigUInt round-trips big-endian bytes", "[BigUInt]")
{
    const auto testCase = GENERATE(
        ByteRoundTrip_s{{}, {}},
        ByteRoundTrip_s{{0x00}, {}},
        ByteRoundTrip_s{{0x7F}, {0x7F}},
        ByteRoundTrip_s{{0x80}, {0x00, 0x80}},
        ByteRoundTrip_s{{0x00, 0x00, 0x01}, {0x01}},
        ByteRoundTrip_s{{0x01, 0x00, 0x00, 0x00, 0x00}, {0x01, 0x00, 0x00, 0x00, 0x00}},
        ByteRoundTrip_s{{0xFF, 0xFF, 0xFF, 0xFF}, {0x00, 0xFF, 0xFF, 0xFF, 0xFF}});

    CHECK(BigUInt::FromBytesBigEndian(testCase.input).ToBytesBigEndian() == testCase.output);
}

TEST_CASE("BigUInt::ModPow", "[BigUInt]")
{
    const auto testCase = GENERATE(
        ModPowCase_s{"4", "13", "497", "445"},
        ModPowCase_s{"5", "0", "7", "1"},
        ModPowCase_s{"0", "5", "7", "0"},
        ModPowCase_s{"3", "1", "7", "3"},
        ModPowCase_s{"3", "5", "16", "3"},
        ModPowCase_s{"65", "17", "3233", "2790"},
        ModPowCase_s{"2790", "2753", "3233", "65"},
        ModPowCase_s{"3", "0x7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFE", "0x7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF", "1"});

    CAPTURE(testCase.base, testCase.exponent, testCase.modulus);

    const auto result = BigUInt::ModPow(BigUInt::Parse(testCase.base), BigUInt::Parse(testCase.exponent), BigUInt::Parse(testCase.modulus));
    CHECK(result == BigUInt::Parse(testCase.result));
}

TEST_CASE("BigUInt modular exponentiation carries and borrows across uneven limb counts", "[BigUInt][NativeBoundaryCoverage]")
{
    // Expected values computed independently with Python's three-argument pow.
    const auto sample = GENERATE(
        ModPowCase_s{"0x1000000000000000000000001", "37", "0xffffffffffffffffffffffffffffff61", "0x18bfa65387499755d00bb534591fa0d7"},
        ModPowCase_s{"0xffffffffffffffffffffffffffffff60", "2", "0xffffffffffffffffffffffffffffff61", "1"},
        ModPowCase_s{"0xffffffffffffffffffffffff", "17", "0x100000000000000000000000000000033", "0xf1ba87f6526fc5b9c9da51c355a20895"},
        ModPowCase_s{"0x10000000000000001", "65537", "0x100000000000000000000000000000033", "0xab2627e3b978a5d029cba38dee0dcdbf"});
    CAPTURE(sample.base, sample.exponent, sample.modulus);
    const auto base = BigUInt::Parse(sample.base);
    const auto modulus = BigUInt::Parse(sample.modulus);
    const auto result = BigUInt::ModPow(base, BigUInt::Parse(sample.exponent), modulus);
    CHECK(result == BigUInt::Parse(sample.result));
    CHECK(result < modulus);
    CHECK(base == BigUInt::Parse(sample.base));
    CHECK(modulus == BigUInt::Parse(sample.modulus));
}

TEST_CASE("BigUInt::ModPow rejects operands the server couldn't decrypt", "[BigUInt]")
{
    const auto two = BigUInt::Parse("2");

    CHECK_THROWS_AS(BigUInt::ModPow(BigUInt{}, two, BigUInt{}), std::invalid_argument);
    CHECK_THROWS_AS(BigUInt::ModPow(BigUInt{}, two, BigUInt::Parse("1")), std::invalid_argument);
    CHECK_THROWS_AS(BigUInt::ModPow(BigUInt::Parse("7"), two, BigUInt::Parse("7")), std::invalid_argument);
    CHECK_THROWS_AS(BigUInt::ModPow(BigUInt::Parse("8"), two, BigUInt::Parse("7")), std::invalid_argument);
}

TEST_CASE("BigUInt::ToHexString writes lower-case hex without leading zeros", "[BigUInt]")
{
    CHECK(BigUInt{}.ToHexString() == "0x0");
    CHECK(BigUInt::Parse("255").ToHexString() == "0xff");
    CHECK(BigUInt::Parse("256").ToHexString() == "0x100");
    CHECK(BigUInt::Parse("0x0102030405060708090A").ToHexString() == "0x102030405060708090a");
}
