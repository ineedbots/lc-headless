#include "pch.hpp"
#include "ApplicationEventBridge.hpp"

#include "EventProtocol.hpp"
#include "Type/ApplicationEvent_s.hpp"
#include "Type/EventSubscription_s.hpp"
#include "../../Accounts/Type/ProgressReport_s.hpp"

namespace
{
    void Increment(u64& value)
    {
        if (value != std::numeric_limits<u64>::max())
        {
            ++value;
        }
    }
}

ApplicationEventBridge::ApplicationEventBridge(std::vector<std::string> accounts)
    : m_accounts{std::move(accounts)}
{
    if (m_accounts.size() > 16 || std::ranges::any_of(m_accounts, [](const auto& name)
    {
        return name.empty() || name.size() > 128;
    }))
    {
        throw std::invalid_argument{"Event accounts must contain at most 16 names of 1..128 bytes"};
    }

    auto random = std::random_device{};
    m_instance = std::format("{:08x}{:08x}{:08x}{:08x}", random(), random(), random(), random());
}

u64 ApplicationEventBridge::Connect()
{
    if (m_stopping || m_clients.size() >= 128 || m_nextClient == std::numeric_limits<u64>::max())
    {
        return 0;
    }

    const auto id = ++m_nextClient;
    m_clients.emplace(id, Client_s{});
    return id;
}

void ApplicationEventBridge::Disconnect(u64 client)
{
    m_clients.erase(client);
    // Do not retain disconnected clients' commands behind a slow fan-out.
    std::erase_if(m_journal, [&](const auto& entry)
    {
        const auto incoming = std::get_if<Incoming_s>(&entry.value);
        if (!incoming || incoming->client != client)
        {
            return false;
        }

        m_journalBytes -= entry.bytes;
        return true;
    });
}

bool ApplicationEventBridge::Append(JournalEntry_s entry)
{
    const auto activeBytes = m_fanout ? m_fanout->event.text->size() : 0;
    const auto activeItems = m_fanout ? std::size_t{1} : std::size_t{0};
    if (m_journal.size() + activeItems >= MAX_JOURNAL_ITEMS || activeBytes > MAX_JOURNAL_BYTES - m_journalBytes ||
        entry.bytes > MAX_JOURNAL_BYTES - m_journalBytes - activeBytes)
    {
        return false;
    }

    m_journalBytes += entry.bytes;
    m_journal.push_back(std::move(entry));
    m_diagnostics.journalHighWaterItems = std::max(m_diagnostics.journalHighWaterItems, m_journal.size() + activeItems);
    m_diagnostics.journalHighWaterBytes = std::max(m_diagnostics.journalHighWaterBytes, m_journalBytes + activeBytes);
    return true;
}

void ApplicationEventBridge::Enqueue(u64 client, std::string message)
{
    if (IsClosing(client))
    {
        return;
    }

    const auto bytes = message.size();
    if (bytes > MAX_MESSAGE_BYTES || !Append({Incoming_s{client, std::move(message)}, bytes}))
    {
        Overflow(client);
    }
}

bool ApplicationEventBridge::Publish(ApplicationEvent_s event)
{
    if (m_stopping)
    {
        return false;
    }

    const auto bytes = EventProtocol::Measure(event.payload);

    if (std::ranges::find(m_accounts, event.account) == m_accounts.end() || !bytes || *bytes > MAX_JOURNAL_BYTES ||
        !Append({std::move(event), std::max(*bytes, MAX_EVENT_BYTES)}))
    {
        ResetPublisher();
        return false;
    }

    return true;
}

bool ApplicationEventBridge::PublishProgress(std::string_view account, const ProgressReport_s& report)
{
    if (m_stopping)
    {
        return false;
    }

    if (account.size() > 128 || !EventProtocol::Measure(report))
    {
        ResetPublisher();
        return false;
    }

    return Publish({std::string{account}, report});
}

bool ApplicationEventBridge::Matches(const EventSubscription_s& subscription, std::string_view event, std::string_view account)
{
    return std::ranges::find(subscription.events, event) != subscription.events.end() &&
        (subscription.accounts.empty() || std::ranges::find(subscription.accounts, account) != subscription.accounts.end());
}

void ApplicationEventBridge::Send(u64 client, std::shared_ptr<const std::string> text)
{
    const auto it = m_clients.find(client);
    if (it == m_clients.end() || it->second.closing)
    {
        return;
    }

    auto& state = it->second;
    if (state.outbox.size() >= MAX_OUTBOX_ITEMS || text->size() > MAX_OUTBOX_BYTES - state.bytes)
    {
        Overflow(client);
        return;
    }

    state.bytes += text->size();
    state.outbox.push_back(std::move(text));
    m_diagnostics.clientHighWaterItems = std::max(m_diagnostics.clientHighWaterItems, state.outbox.size());
    m_diagnostics.clientHighWaterBytes = std::max(m_diagnostics.clientHighWaterBytes, state.bytes);
}

void ApplicationEventBridge::Apply(Incoming_s incoming)
{
    if (IsClosing(incoming.client))
    {
        return;
    }

    auto decoded = EventProtocol::Decode(incoming.message);
    const auto reject = [&](std::string_view id, std::string_view code)
    {
        Increment(m_diagnostics.rejectedSubscriptions);
        Send(incoming.client, std::make_shared<const std::string>(EventProtocol::Error(id, code)));
    };

    if (const auto error = std::get_if<EventProtocolError_s>(&decoded))
    {
        reject(error->id, error->code);
        return;
    }

    auto command = std::get<EventCommand_s>(std::move(decoded));
    auto& subscriptions = m_clients.at(incoming.client).subscriptions;
    const auto existing = std::ranges::find(subscriptions, command.subscription.id, &EventSubscription_s::id);

    if (command.action == "unsubscribe")
    {
        if (existing == subscriptions.end())
        {
            reject(command.subscription.id, "unknown_subscription");
            return;
        }

        subscriptions.erase(existing);
        Send(incoming.client, std::make_shared<const std::string>(EventProtocol::Ack(command.subscription.id, command.action, m_instance, m_sequence)));
        return;
    }

    if (existing != subscriptions.end() || subscriptions.size() >= 16 || std::ranges::any_of(command.subscription.accounts, [&](const auto& account)
    {
        return std::ranges::find(m_accounts, account) == m_accounts.end();
    }))
    {
        reject(command.subscription.id, "invalid_subscription");
        return;
    }

    auto snapshot = std::vector<std::shared_ptr<const std::string>>{};
    for (const auto& [key, event] : m_latest)
    {
        if (Matches(command.subscription, event.name, key.first))
        {
            snapshot.push_back(event.text);
        }
    }

    auto ack = std::make_shared<const std::string>(EventProtocol::Ack(command.subscription.id, command.action, m_instance, m_sequence));
    auto initial = std::make_shared<const std::string>(EventProtocol::Snapshot(command.subscription.id, m_instance, m_sequence, snapshot));
    subscriptions.push_back(std::move(command.subscription));
    Send(incoming.client, std::move(ack));
    Send(incoming.client, std::move(initial));
}

void ApplicationEventBridge::Service()
{
    auto visits = std::size_t{0};
    auto items = std::size_t{0};
    while (!m_stopping && items < 32)
    {
        if (m_fanout)
        {
            auto it = m_clients.upper_bound(m_fanout->cursor);
            while (it != m_clients.end() && visits < 256)
            {
                const auto id = it->first;
                const auto& subscriptions = it->second.subscriptions;
                if (std::ranges::any_of(subscriptions, [&](const auto& subscription)
                {
                    return Matches(subscription, m_fanout->event.name, m_fanout->account);
                }))
                {
                    Send(id, m_fanout->event.text);
                    m_diagnostics.maxDeliveryLagMs = std::max(m_diagnostics.maxDeliveryLagMs,
                                                              std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - m_fanout->created).count());
                }

                m_fanout->cursor = id;
                ++it;
                ++visits;
            }

            if (it != m_clients.end())
            {
                return;
            }

            m_fanout.reset();
        }

        if (m_journal.empty())
        {
            return;
        }

        auto entry = std::move(m_journal.front());
        m_journal.pop_front();
        m_journalBytes -= entry.bytes;
        ++items;

        if (auto incoming = std::get_if<Incoming_s>(&entry.value))
        {
            Apply(std::move(*incoming));
            continue;
        }

        auto event = std::get<ApplicationEvent_s>(std::move(entry.value));
        auto text = std::string{};
        try
        {
            if (m_sequence == std::numeric_limits<u64>::max())
            {
                Stop();
                return;
            }

            text = EventProtocol::Encode(event, m_instance, m_sequence + 1);
        }
        catch (const std::exception&)
        {
            ResetPublisher();
            return;
        }

        if (text.size() > MAX_EVENT_BYTES)
        {
            ResetPublisher();
            return;
        }

        auto cached = CachedEvent_s{std::string{EventProtocol::Name(event.payload)}, std::make_shared<const std::string>(std::move(text))};
        ++m_sequence;
        m_latest[{event.account, cached.name}] = cached;
        m_fanout = Fanout_s{std::move(event.account), std::move(cached), 0, entry.created};
    }
}

void ApplicationEventBridge::Overflow(u64 client)
{
    const auto it = m_clients.find(client);
    if (it == m_clients.end() || it->second.closing)
    {
        return;
    }

    it->second = Client_s{.closing = true};
    Increment(m_diagnostics.overflowDisconnects);
}

void ApplicationEventBridge::ResetPublisher()
{
    Increment(m_diagnostics.publisherResets);
    m_journal.clear();
    m_journalBytes = 0;
    m_latest.clear();
    m_fanout.reset();

    for (const auto& [id, client] : m_clients)
    {
        static_cast<void>(client);
        Overflow(id);
    }
}

void ApplicationEventBridge::Stop()
{
    m_stopping = true;
    m_journal.clear();
    m_journalBytes = 0;
    m_fanout.reset();
    m_latest.clear();

    for (auto& [id, client] : m_clients)
    {
        static_cast<void>(id);
        client = Client_s{.closing = true};
    }
}

bool ApplicationEventBridge::HasIncoming() const
{
    return !m_journal.empty() || m_fanout.has_value();
}

bool ApplicationEventBridge::IsClosing(u64 client) const
{
    const auto it = m_clients.find(client);
    return m_stopping || it == m_clients.end() || it->second.closing;
}

bool ApplicationEventBridge::IsStopping() const
{
    return m_stopping;
}

std::shared_ptr<const std::string> ApplicationEventBridge::Front(u64 client) const
{
    const auto it = m_clients.find(client);
    if (it == m_clients.end() || it->second.outbox.empty())
    {
        return {};
    }

    return it->second.outbox.front();
}

void ApplicationEventBridge::Pop(u64 client)
{
    const auto it = m_clients.find(client);
    if (it != m_clients.end() && !it->second.outbox.empty())
    {
        it->second.bytes -= it->second.outbox.front()->size();
        it->second.outbox.pop_front();
    }
}

ApplicationEventBridge::Diagnostics_s ApplicationEventBridge::GetDiagnostics() const
{
    auto result = m_diagnostics;
    result.connections = m_clients.size();
    result.journalItems = m_journal.size() + (m_fanout ? 1 : 0);
    result.journalBytes = m_journalBytes + (m_fanout ? m_fanout->event.text->size() : 0);

    for (const auto& [id, client] : m_clients)
    {
        static_cast<void>(id);
        result.subscriptions += client.subscriptions.size();
        result.outgoingItems += client.outbox.size();
        result.outgoingBytes += client.bytes;
    }

    return result;
}
