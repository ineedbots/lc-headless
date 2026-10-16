#pragma once

#include "../State/Interfaces_s.hpp"
#include "InterfaceView.hpp"

// The webclient sends one resume per dialogue and one answer per count dialog. The server doesn't say when either
// has closed it, so this remembers the modal change each was sent in, and hides it until the modals change again.
class DialogueTracker
{
public:
    // The chat modal's "Click here to continue" button, until it's been clicked.
    [[nodiscard]] std::optional<u16> FindContinue(const InterfaceView& view) const;
    // Open, and not yet answered.
    [[nodiscard]] bool IsCountDialogOpen(const Interfaces_s& interfaces) const;
    void NoteContinued(const Interfaces_s& interfaces);
    void NoteAnswered(const Interfaces_s& interfaces);

private:
    std::optional<u32> m_continuedAt;
    std::optional<u32> m_answeredAt;
};
