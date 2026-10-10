#include "pch.hpp"
#include "InterfaceView.hpp"

#include "../Cache/GameCache_s.hpp"
#include "../Cache/IfComponent_s.hpp"
#include "State/Interfaces_s.hpp"

namespace
{
    bool EqualsIgnoringCase(std::string_view left, std::string_view right)
    {
        return std::ranges::equal(left, right, [](char a, char b)
        {
            return std::tolower(static_cast<unsigned char>(a)) == std::tolower(static_cast<unsigned char>(b));
        });
    }

    bool Contains(const ComponentPoint_s& corner, const IfComponent_s& component, const ComponentPoint_s& point)
    {
        return point.x >= corner.x && point.y >= corner.y && point.x < corner.x + component.width && point.y < corner.y + component.height;
    }
}

InterfaceView::InterfaceView(const GameCache_s& cache, const Interfaces_s& interfaces)
    : m_cache{cache}
    , m_interfaces{interfaces}
{
}

const GameCache_s& InterfaceView::GetCache() const
{
    return m_cache;
}

const Interfaces_s& InterfaceView::GetInterfaces() const
{
    return m_interfaces;
}

const IfComponent_s* InterfaceView::Find(s32 id) const
{
    return m_cache.FindComponent(id);
}

std::vector<u16> InterfaceView::GetOpenRoots() const
{
    auto roots = std::vector<u16>{};
    const auto add = [&roots](s32 id)
    {
        if (id >= 0 && std::ranges::find(roots, static_cast<u16>(id)) == roots.end())
        {
            roots.push_back(static_cast<u16>(id));
        }
    };

    add(m_interfaces.mainModal);
    add(m_interfaces.sideModal);
    add(m_interfaces.chatModal);
    add(m_interfaces.overlay);
    for (const auto tab : m_interfaces.tabs)
    {
        add(tab);
    }

    return roots;
}

bool InterfaceView::IsOpen(u16 root) const
{
    const auto roots = GetOpenRoots();
    return std::ranges::find(roots, root) != roots.end();
}

std::string_view InterfaceView::GetText(const IfComponent_s& component) const
{
    const auto* const set = FindSet(component.id);
    return set != nullptr && set->text ? std::string_view{*set->text} : std::string_view{component.text};
}

u32 InterfaceView::GetColour(const IfComponent_s& component) const
{
    const auto* const set = FindSet(component.id);
    return set != nullptr && set->colour ? *set->colour : component.colour;
}

bool InterfaceView::IsHidden(const IfComponent_s& component) const
{
    const auto* const set = FindSet(component.id);
    return set != nullptr && set->hidden ? *set->hidden : component.hidden;
}

std::optional<u16> InterfaceView::GetObject(const IfComponent_s& component) const
{
    const auto* const set = FindSet(component.id);
    if (set == nullptr || !set->model || set->model->kind != ComponentModelKind_e::Object)
    {
        return std::nullopt;
    }

    return set->model->id;
}

bool InterfaceView::IsVisible(const IfComponent_s& component) const
{
    const auto* current = &component;
    while (true)
    {
        if (IsHidden(*current))
        {
            return false;
        }

        if (!current->parent)
        {
            return IsOpen(current->id);
        }

        const auto* const parent = Find(*current->parent);
        if (parent == nullptr)
        {
            return false;
        }

        current = parent;
    }
}

ComponentPoint_s InterfaceView::GetPosition(const IfComponent_s& component) const
{
    auto position = ComponentPoint_s{};
    const auto* current = &component;
    while (current->parent)
    {
        const auto* const parent = Find(*current->parent);
        if (parent == nullptr)
        {
            break;
        }

        const auto* const set = FindSet(current->id);
        if (set != nullptr && set->position)
        {
            position.x += set->position->x;
            position.y += set->position->y;
        }
        else
        {
            const auto child = std::ranges::find(parent->children, current->id, &IfChild_s::id);
            if (child != parent->children.end())
            {
                position.x += child->x;
                position.y += child->y;
            }
        }

        const auto* const parentSet = FindSet(parent->id);
        if (parentSet != nullptr && parentSet->scrollPosition)
        {
            position.y -= *parentSet->scrollPosition;
        }

        current = parent;
    }

    return position;
}

std::vector<const IfComponent_s*> InterfaceView::GetTree(u16 root) const
{
    auto tree = std::vector<const IfComponent_s*>{};
    if (const auto* const component = Find(root))
    {
        AddTree(*component, tree);
    }

    return tree;
}

std::vector<const IfComponent_s*> InterfaceView::FindText(std::string_view text, std::optional<u16> root) const
{
    const auto roots = root ? std::vector<u16>{*root} : GetOpenRoots();
    auto found = std::vector<const IfComponent_s*>{};
    for (const auto id : roots)
    {
        for (const auto* const component : GetTree(id))
        {
            if (component->type == ComponentType_e::Text && EqualsIgnoringCase(GetText(*component), text) && IsVisible(*component))
            {
                found.push_back(component);
            }
        }
    }

    return found;
}

const IfComponent_s* InterfaceView::ButtonAt(const IfComponent_s& component) const
{
    const auto corner = GetPosition(component);
    const auto centre = ComponentPoint_s{.x = corner.x + component.width / 2, .y = corner.y + component.height / 2};
    const IfComponent_s* hit = nullptr;
    for (const auto* const candidate : GetTree(component.root))
    {
        if (candidate->buttonType == ButtonType_e::None || !Contains(GetPosition(*candidate), *candidate, centre) || !IsVisible(*candidate))
        {
            continue;
        }

        hit = candidate;
    }

    return hit;
}

const Component_s* InterfaceView::FindSet(u16 id) const
{
    const auto found = m_interfaces.components.find(id);
    return found == m_interfaces.components.end() ? nullptr : &found->second;
}

void InterfaceView::AddTree(const IfComponent_s& component, std::vector<const IfComponent_s*>& tree) const
{
    tree.push_back(&component);
    for (const auto& child : component.children)
    {
        if (const auto* const found = Find(child.id))
        {
            AddTree(*found, tree);
        }
    }
}
