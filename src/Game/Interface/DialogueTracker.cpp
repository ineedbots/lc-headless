#include "pch.hpp"
#include "DialogueTracker.hpp"

#include "../State/Interfaces_s.hpp"
#include "ChatDialog.hpp"
#include "InterfaceView.hpp"

std::optional<u16> DialogueTracker::FindContinue(const InterfaceView& view) const
{
    if (m_continuedAt == view.GetInterfaces().modalChanges)
    {
        return std::nullopt;
    }

    return ChatDialog::FindContinue(view);
}

bool DialogueTracker::IsCountDialogOpen(const Interfaces_s& interfaces) const
{
    return interfaces.countDialogOpen && m_answeredAt != interfaces.modalChanges;
}

void DialogueTracker::NoteContinued(const Interfaces_s& interfaces)
{
    m_continuedAt = interfaces.modalChanges;
}

void DialogueTracker::NoteAnswered(const Interfaces_s& interfaces)
{
    m_answeredAt = interfaces.modalChanges;
}
