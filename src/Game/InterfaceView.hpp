#pragma once

#include "../Cache/GameCache_s.hpp"
#include "../Cache/IfComponent_s.hpp"
#include "State/Interfaces_s.hpp"

struct ComponentPoint_s
{
    s32 x = 0;
    s32 y = 0;
};

// The interfaces as the player sees them: the cache's components, with what the server has set on them
// (text, colour, hiding, position, scroll) taking the cache's place. It reads both in place, so it's cheap
// to make whenever it's needed, and it can't go stale.
class InterfaceView
{
public:
    InterfaceView(const GameCache_s& cache, const Interfaces_s& interfaces);

    [[nodiscard]] const IfComponent_s* Find(s32 id) const;
    // The interfaces that are open: the main, side and chat modals, the overlay, and each tab's.
    [[nodiscard]] std::vector<u16> GetOpenRoots() const;
    [[nodiscard]] bool IsOpen(u16 root) const;

    [[nodiscard]] std::string_view GetText(const IfComponent_s& component) const;
    [[nodiscard]] u32 GetColour(const IfComponent_s& component) const;
    [[nodiscard]] bool IsHidden(const IfComponent_s& component) const;
    // In an open interface, with neither it nor any layer above it hidden.
    [[nodiscard]] bool IsVisible(const IfComponent_s& component) const;
    // Its corner, from its interface's corner, through each layer's offset and scroll.
    [[nodiscard]] ComponentPoint_s GetPosition(const IfComponent_s& component) const;

    // The root and everything under it, in drawing order; empty for an id the cache doesn't have.
    [[nodiscard]] std::vector<const IfComponent_s*> GetTree(u16 root) const;
    // Visible text components whose text matches, without regard to case, in the open interfaces or
    // only in root's.
    [[nodiscard]] std::vector<const IfComponent_s*> FindText(std::string_view text, std::optional<u16> root = std::nullopt) const;
    // The button a click on the component's centre hits: of the visible buttons in its interface under that
    // point, the last in drawing order, as the webclient's menu puts the last one first. A button component
    // under nothing else hits itself.
    [[nodiscard]] const IfComponent_s* ButtonAt(const IfComponent_s& component) const;

private:
    [[nodiscard]] const Component_s* FindSet(u16 id) const;
    void AddTree(const IfComponent_s& component, std::vector<const IfComponent_s*>& tree) const;

    const GameCache_s& m_cache;
    const Interfaces_s& m_interfaces;
};
