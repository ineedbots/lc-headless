#include "pch.hpp"
#include "ControlBindings.hpp"

#include "../../Accounts/Account.hpp"
#include "../../Config/Revision_e.hpp"
#include "../Convert/PyValue.hpp"
#include "../ScriptContext.hpp"
#include "../ScriptControl.hpp"
#include "BindingSupport.hpp"

#include <pocketpy.h>

namespace
{
    constexpr auto MAX_RELOG_SECONDS = s64{ScriptControl::MAX_RELOG.count()};

    bool GetStepTime(int, py_StackRef) noexcept
    {
        return BindingSupport::Guard([]
        {
            return BindingSupport::ReturnInt(BindingSupport::GetContext().GetControl().GetStepTime());
        });
    }

    bool GetRevision(int, py_StackRef) noexcept
    {
        return BindingSupport::Guard([]
        {
            return BindingSupport::ReturnInt(static_cast<u16>(BindingSupport::GetContext().GetRevision()));
        });
    }

    bool NoteProgress(int, py_StackRef) noexcept
    {
        return BindingSupport::Guard([]
        {
            BindingSupport::GetContext().GetControl().NoteProgress();
            return BindingSupport::ReturnNone();
        });
    }

    // When note_progress() was last called, in step time, or None.
    bool GetLastProgress(int, py_StackRef) noexcept
    {
        return BindingSupport::Guard([]
        {
            const auto last = BindingSupport::GetContext().GetControl().GetLastProgress();
            return last ? BindingSupport::ReturnInt(*last) : BindingSupport::ReturnNone();
        });
    }

    bool Relog(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            const auto delay = PyValue::ToInt(py_arg(0), "delay_seconds", 0, MAX_RELOG_SECONDS);
            BindingSupport::GetContext().GetControl().RequestRelog(std::chrono::seconds{delay});
            return BindingSupport::ReturnNone();
        });
    }

    // settings_store.save() has checked the value and turned it into JSON.
    bool SaveSetting(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            auto save = SettingSave_s{
                .name = PyValue::ToString(py_arg(0), "name"),
                .key = PyValue::ToString(py_arg(1), "key"),
                .valueJson = PyValue::ToString(py_arg(2), "value_json"),
            };
            BindingSupport::GetContext().GetControl().RequestSettingSave(std::move(save));
            return BindingSupport::ReturnNone();
        });
    }

    bool StopScript(int, py_StackRef) noexcept
    {
        return BindingSupport::Guard([]
        {
            BindingSupport::GetContext().GetControl().RequestStop(StopRequest_e::Script);
            return BindingSupport::ReturnNone();
        });
    }

    bool StopAccount(int, py_StackRef) noexcept
    {
        return BindingSupport::Guard([]
        {
            BindingSupport::GetContext().GetControl().RequestStop(StopRequest_e::Account);
            return BindingSupport::ReturnNone();
        });
    }

    bool SendBotMessage(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            const auto username = PyValue::ToString(py_arg(0), "username");

            if (!py_json_dumps(py_arg(1), 0))
            {
                return false;
            }

            const auto sent = BindingSupport::GetContext().SendBotMessage(username, PyValue::ToString(py_retval(), "message"));
            if (!sent)
            {
                throw std::invalid_argument{std::format("No account in this process has the username {}", username)};
            }

            return BindingSupport::ReturnBool(*sent);
        });
    }
}

void ControlBindings::Add(std::vector<BoundFunction_s>& functions)
{
    functions.insert(functions.end(), {
                                          {"step_time()", GetStepTime},
                                          {"get_revision()", GetRevision},
                                          {"note_progress()", NoteProgress},
                                          {"last_progress()", GetLastProgress},
                                          {"relog(delay_seconds=0)", Relog},
                                          {"save_setting(name, key, value_json)", SaveSetting},
                                          {"stop_script()", StopScript},
                                          {"stop_account()", StopAccount},
                                          {"send_bot_message(username, message)", SendBotMessage},
                                      });
}
