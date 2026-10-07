#pragma once

class Isaac
{
public:
    explicit Isaac(std::span<const s32> seed);

    [[nodiscard]] s32 NextInt();

private:
    static constexpr std::size_t SIZE = 256;
    static constexpr u32 GOLDEN_RATIO = 0x9E3779B9;

    void Init();
    void Generate();

    std::array<u32, SIZE> m_results{};
    std::array<u32, SIZE> m_memory{};
    u32 m_a = 0;
    u32 m_b = 0;
    u32 m_c = 0;
    u32 m_count = 0;
};
