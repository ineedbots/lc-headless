#include "pch.hpp"
#include "Compression.hpp"

#include "CacheError.hpp"
#include "CacheStore.hpp"

#include <bzlib.h>
#include <zlib.h>

namespace
{
    constexpr auto BZIP2_HEADER = std::to_array<char>({'B', 'Z', 'h', '1'});
    constexpr auto GZIP_WINDOW_BITS = 16 + MAX_WBITS;
    constexpr auto MIN_GZIP_OUTPUT = std::size_t{4096};
    constexpr auto GZIP_GROWTH = std::size_t{4};

    std::string_view DescribeBzip2Error(int code)
    {
        switch (code)
        {
        case BZ_DATA_ERROR:
            return "BZ_DATA_ERROR";
        case BZ_DATA_ERROR_MAGIC:
            return "BZ_DATA_ERROR_MAGIC";
        case BZ_MEM_ERROR:
            return "BZ_MEM_ERROR";
        case BZ_PARAM_ERROR:
            return "BZ_PARAM_ERROR";
        case BZ_SEQUENCE_ERROR:
            return "BZ_SEQUENCE_ERROR";
        case BZ_UNEXPECTED_EOF:
            return "BZ_UNEXPECTED_EOF";
        default:
            return "unknown error";
        }
    }

    std::string_view DescribeZlibError(int code)
    {
        switch (code)
        {
        case Z_DATA_ERROR:
            return "Z_DATA_ERROR";
        case Z_MEM_ERROR:
            return "Z_MEM_ERROR";
        case Z_STREAM_ERROR:
            return "Z_STREAM_ERROR";
        case Z_NEED_DICT:
            return "Z_NEED_DICT";
        case Z_VERSION_ERROR:
            return "Z_VERSION_ERROR";
        default:
            return "unknown error";
        }
    }

    char* ToBzip2Input(const char* data)
    {
        // libbzip2 only reads its input, but declares it non-const.
        return const_cast<char*>(data);
    }

    // libbzip2's decompression state, released on every path.
    class Bzip2Stream
    {
    public:
        Bzip2Stream()
        {
            const auto result = BZ2_bzDecompressInit(&m_stream, 0, 0);
            if (result != BZ_OK)
            {
                throw CacheError{std::format("bzip2 can't start ({})", DescribeBzip2Error(result))};
            }
        }

        ~Bzip2Stream()
        {
            BZ2_bzDecompressEnd(&m_stream);
        }

        Bzip2Stream(const Bzip2Stream&) = delete;
        Bzip2Stream& operator=(const Bzip2Stream&) = delete;

        [[nodiscard]] bz_stream& Get()
        {
            return m_stream;
        }

    private:
        bz_stream m_stream{};
    };

    // zlib's decompression state, released on every path.
    class GzipStream
    {
    public:
        GzipStream()
        {
            const auto result = inflateInit2(&m_stream, GZIP_WINDOW_BITS);
            if (result != Z_OK)
            {
                throw CacheError{std::format("zlib can't start ({})", DescribeZlibError(result))};
            }
        }

        ~GzipStream()
        {
            inflateEnd(&m_stream);
        }

        GzipStream(const GzipStream&) = delete;
        GzipStream& operator=(const GzipStream&) = delete;

        [[nodiscard]] z_stream& Get()
        {
            return m_stream;
        }

    private:
        z_stream m_stream{};
    };
}

std::vector<u8> Compression::Bunzip2(std::span<const u8> source, std::size_t expectedSize)
{
    // One byte more than expected, so a stream that unpacks to too much fills the buffer instead of
    // stopping at exactly the right size.
    auto output = std::vector<u8>(expectedSize + 1);
    auto bzip2 = Bzip2Stream{};
    auto& stream = bzip2.Get();
    stream.next_in = ToBzip2Input(BZIP2_HEADER.data());
    stream.avail_in = static_cast<unsigned int>(BZIP2_HEADER.size());
    stream.next_out = reinterpret_cast<char*>(output.data());
    stream.avail_out = static_cast<unsigned int>(output.size());

    auto sourceGiven = false;
    while (true)
    {
        const auto result = BZ2_bzDecompress(&stream);
        if (result == BZ_STREAM_END)
        {
            break;
        }

        if (result != BZ_OK)
        {
            throw CacheError{std::format("bzip2 data is damaged ({})", DescribeBzip2Error(result))};
        }

        if (stream.avail_out == 0)
        {
            throw CacheError{std::format("bzip2 data unpacks to more than {} bytes", expectedSize)};
        }

        if (stream.avail_in > 0)
        {
            continue;
        }

        if (sourceGiven)
        {
            throw CacheError{"bzip2 data ends early"};
        }

        stream.next_in = ToBzip2Input(reinterpret_cast<const char*>(source.data()));
        stream.avail_in = static_cast<unsigned int>(source.size());
        sourceGiven = true;
    }

    const auto produced = output.size() - stream.avail_out;
    if (produced != expectedSize)
    {
        throw CacheError{std::format("bzip2 data unpacks to {} bytes, not {}", produced, expectedSize)};
    }

    output.resize(expectedSize);
    return output;
}

std::vector<u8> Compression::Gunzip(std::span<const u8> source)
{
    auto gzip = GzipStream{};
    auto& stream = gzip.Get();
    stream.next_in = const_cast<Bytef*>(source.data());
    stream.avail_in = static_cast<uInt>(source.size());

    auto output = std::vector<u8>(std::min(std::max(source.size() * GZIP_GROWTH, MIN_GZIP_OUTPUT), CacheStore::MAX_FILE_SIZE + 1));
    while (true)
    {
        const auto produced = static_cast<std::size_t>(stream.total_out);
        if (produced == output.size())
        {
            if (produced > CacheStore::MAX_FILE_SIZE)
            {
                throw CacheError{std::format("gzip data unpacks to more than {} bytes", CacheStore::MAX_FILE_SIZE)};
            }

            output.resize(std::min(output.size() * 2, CacheStore::MAX_FILE_SIZE + 1));
        }

        stream.next_out = output.data() + produced;
        stream.avail_out = static_cast<uInt>(output.size() - produced);
        const auto result = inflate(&stream, Z_NO_FLUSH);
        if (result == Z_STREAM_END)
        {
            break;
        }

        if (result == Z_BUF_ERROR && stream.avail_in == 0)
        {
            throw CacheError{"gzip data ends early"};
        }

        if (result != Z_OK && result != Z_BUF_ERROR)
        {
            throw CacheError{std::format("gzip data is damaged ({})", DescribeZlibError(result))};
        }
    }

    output.resize(static_cast<std::size_t>(stream.total_out));
    if (output.size() > CacheStore::MAX_FILE_SIZE)
    {
        throw CacheError{std::format("gzip data unpacks to more than {} bytes", CacheStore::MAX_FILE_SIZE)};
    }

    return output;
}
