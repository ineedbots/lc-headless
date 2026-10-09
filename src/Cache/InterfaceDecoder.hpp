#pragma once

class InterfaceDecoder
{
public:
    InterfaceDecoder() = delete;

    // Takes the interface archive's data entry and returns the id of the first component with the
    // client code, or nothing when none has it. Throws CacheError, naming the component, for data that
    // doesn't decode before the component is found.
    [[nodiscard]] static std::optional<u16> FindClientCode(std::span<const u8> data, u16 clientCode);
};
