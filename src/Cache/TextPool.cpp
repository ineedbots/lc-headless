#include "pch.hpp"
#include "TextPool.hpp"

#include "CacheError.hpp"

TextPool::TextPool()
    : m_options{std::string_view{}}
{
}

std::string_view TextPool::Intern(std::string_view text)
{
    assert(!m_finished && "Text interned after FinishInterning");
    if (text.empty())
    {
        return {};
    }

    const auto existing = m_strings.find(text);
    if (existing != m_strings.end())
    {
        return *existing;
    }

    char* destination = nullptr;
    if (text.size() > CHUNK_SIZE)
    {
        // A string that fills a chunk on its own gets one, and the next string starts a fresh chunk.
        m_chunks.push_back(std::make_unique<char[]>(text.size()));
        destination = m_chunks.back().get();
        m_chunkUsed = CHUNK_SIZE;
    }
    else
    {
        if (m_chunks.empty() || m_chunkUsed + text.size() > CHUNK_SIZE)
        {
            m_chunks.push_back(std::make_unique<char[]>(CHUNK_SIZE));
            m_chunkUsed = 0;
        }

        destination = m_chunks.back().get() + m_chunkUsed;
        m_chunkUsed += text.size();
    }

    std::ranges::copy(text, destination);
    const auto interned = std::string_view{destination, text.size()};
    m_strings.insert(interned);
    return interned;
}

u16 TextPool::InternOption(std::string_view text)
{
    assert(!m_finished && "Option interned after FinishInterning");
    if (text.empty())
    {
        return NO_OPTION;
    }

    const auto existing = m_optionIds.find(text);
    if (existing != m_optionIds.end())
    {
        return existing->second;
    }

    if (m_options.size() > std::numeric_limits<u16>::max())
    {
        throw CacheError{std::format("the types have more than {} distinct options", std::numeric_limits<u16>::max())};
    }

    const auto id = static_cast<u16>(m_options.size());
    const auto interned = Intern(text);
    m_options.push_back(interned);
    m_optionIds.emplace(interned, id);
    return id;
}

std::string_view TextPool::GetOption(u16 id) const
{
    assert(id < m_options.size() && "Option id out of range");
    return m_options[id];
}

std::size_t TextPool::GetOptionCount() const
{
    return m_options.size();
}

void TextPool::FinishInterning()
{
    m_strings = {};
    m_optionIds = {};
    m_finished = true;
}
