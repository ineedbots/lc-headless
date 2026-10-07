#include "pch.hpp"
#include "Isaac.hpp"

namespace
{
    constexpr auto STATE_SIZE = std::size_t{8};
    constexpr auto INIT_ROUNDS = 4;

    using State = std::array<u32, STATE_SIZE>;

    void Mix(State& state)
    {
        auto& [a, b, c, d, e, f, g, h] = state;
        a ^= b << 11;
        d += a;
        b += c;
        b ^= c >> 2;
        e += b;
        c += d;
        c ^= d << 8;
        f += c;
        d += e;
        d ^= e >> 16;
        g += d;
        e += f;
        e ^= f << 10;
        h += e;
        f += g;
        f ^= g >> 4;
        a += f;
        g += h;
        g ^= h << 8;
        b += g;
        h += a;
        h ^= a >> 9;
        c += h;
        a += b;
    }

    void MixInto(State& state, std::span<const u32> source, std::span<u32> memory)
    {
        assert(source.size() == memory.size() && "Isaac source and memory differ in size");

        for (std::size_t i = 0; i < memory.size(); i += STATE_SIZE)
        {
            for (std::size_t j = 0; j < STATE_SIZE; ++j)
            {
                state[j] += source[i + j];
            }

            Mix(state);
            std::ranges::copy(state, memory.begin() + static_cast<std::ptrdiff_t>(i));
        }
    }
}

Isaac::Isaac(std::span<const s32> seed)
{
    assert(seed.size() <= SIZE && "Isaac seed is longer than its state");

    std::ranges::transform(seed, m_results.begin(), [](s32 word)
    {
        return std::bit_cast<u32>(word);
    });

    Init();
}

s32 Isaac::NextInt()
{
    if (m_count == 0)
    {
        Generate();
        m_count = SIZE;
    }

    return std::bit_cast<s32>(m_results[--m_count]);
}

void Isaac::Init()
{
    auto state = State{};
    state.fill(GOLDEN_RATIO);
    for (auto round = 0; round < INIT_ROUNDS; ++round)
    {
        Mix(state);
    }

    MixInto(state, m_results, m_memory);
    MixInto(state, m_memory, m_memory);

    Generate();
    m_count = SIZE;
}

void Isaac::Generate()
{
    ++m_c;
    m_b += m_c;

    for (std::size_t i = 0; i < SIZE; ++i)
    {
        const auto x = m_memory[i];
        switch (i & 3)
        {
        case 0:
            m_a ^= m_a << 13;
            break;
        case 1:
            m_a ^= m_a >> 6;
            break;
        case 2:
            m_a ^= m_a << 2;
            break;
        case 3:
            m_a ^= m_a >> 16;
            break;
        }

        m_a += m_memory[(i + SIZE / 2) % SIZE];
        const auto y = m_memory[(x >> 2) % SIZE] + m_a + m_b;
        m_memory[i] = y;
        m_b = m_memory[(y >> 10) % SIZE] + x;
        m_results[i] = m_b;
    }
}
