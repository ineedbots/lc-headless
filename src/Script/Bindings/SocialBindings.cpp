#include "pch.hpp"
#include "SocialBindings.hpp"

#include "../../Game/State/GameState_s.hpp"
#include "../../Game/State/Social_s.hpp"
#include "../Convert/PyValue.hpp"
#include "../ScriptActions.hpp"
#include "../ScriptContext.hpp"
#include "BindingSupport.hpp"

#include <pocketpy.h>

namespace
{
    bool Say(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            BindingSupport::GetContext().GetActions().Say(PyValue::ToString(py_arg(0), "text"));
            return BindingSupport::ReturnNone();
        });
    }

    bool SendPm(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            BindingSupport::GetContext().GetActions().SendPrivateMessage(PyValue::ToString(py_arg(0), "name"), PyValue::ToString(py_arg(1), "text"));
            return BindingSupport::ReturnNone();
        });
    }

    bool Command(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            BindingSupport::GetContext().GetActions().SendCommand(PyValue::ToString(py_arg(0), "text"));
            return BindingSupport::ReturnNone();
        });
    }

    template <void (ScriptActions::*TCall)(std::string_view)>
    bool CallWithName(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            (BindingSupport::GetContext().GetActions().*TCall)(PyValue::ToString(py_arg(0), "name"));
            return BindingSupport::ReturnNone();
        });
    }

    bool GetFriends(int, py_StackRef) noexcept
    {
        return BindingSupport::Guard([]
        {
            PyValue::FromList(py_retval(), BindingSupport::GetContext().GetState().social.friends, BindingSupport::FromFriend);
            return true;
        });
    }

    bool GetIgnores(int, py_StackRef) noexcept
    {
        return BindingSupport::Guard([]
        {
            PyValue::FromList(py_retval(), BindingSupport::GetContext().GetState().social.ignores, BindingSupport::FromName);
            return true;
        });
    }

    // The newest message's sequence number, or 0 before any: a mark to read later messages from.
    bool GetMessageMark(int, py_StackRef) noexcept
    {
        return BindingSupport::Guard([]
        {
            return BindingSupport::ReturnInt(static_cast<s64>(BindingSupport::GetContext().GetState().messageCount));
        });
    }

    // (sequence, text) for each game message after the mark, oldest first, of the 100 the state keeps.
    bool GetGameMessagesSince(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            const auto mark = PyValue::ToInt(py_arg(0), "mark");
            auto found = std::vector<const ChatMessage_s*>{};
            for (const auto& message : BindingSupport::GetContext().GetState().messages)
            {
                if (message.type == MessageType_e::Game && static_cast<s64>(message.sequence) > mark)
                {
                    found.push_back(&message);
                }
            }

            PyValue::FromList(py_retval(), found, [](py_OutRef out, const ChatMessage_s* message)
            {
                py_newtuple(out, 2);
                py_newint(py_tuple_getitem(out, 0), static_cast<s64>(message->sequence));
                py_newnone(py_tuple_getitem(out, 1));
                PyValue::FromString(py_tuple_getitem(out, 1), message->text);
            });
            return true;
        });
    }
}

void SocialBindings::Add(std::vector<BoundFunction_s>& functions)
{
    functions.insert(functions.end(), {
                                          {"get_friends()", GetFriends},
                                          {"get_ignores()", GetIgnores},
                                          {"message_mark()", GetMessageMark},
                                          {"game_messages_since(mark)", GetGameMessagesSince},
                                          {"say(text)", Say},
                                          {"send_pm(name, text)", SendPm},
                                          {"command(text)", Command},
                                          {"add_friend(name)", CallWithName<&ScriptActions::AddFriend>},
                                          {"remove_friend(name)", CallWithName<&ScriptActions::RemoveFriend>},
                                          {"add_ignore(name)", CallWithName<&ScriptActions::AddIgnore>},
                                          {"remove_ignore(name)", CallWithName<&ScriptActions::RemoveIgnore>},
                                      });
}
