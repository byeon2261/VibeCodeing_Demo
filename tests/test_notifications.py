from backend.notifications import notify_matches
from backend.storage import SQLiteStore
from backend.tools import AnimalTools
from tests.test_workflow import settings, CONDITIONS


class FakeSender:
    def __init__(self):
        self.calls = []

    async def send(self, recipient, content):
        self.calls.append((recipient, content))
        return {"status": "accepted", "provider_id": "test-message"}


async def test_dedup_unsubscribe_and_sample_suppression(tmp_path):
    store, sender = SQLiteStore(str(tmp_path / "notify.db")), FakeSender()
    await store.put("a", "saved", "saved", {"conditions": CONDITIONS})
    await store.put("a", "subscription", "sub", {"active": True, "saved_search_id": "saved", "recipient": "123456789012345678"})
    candidates, _ = await AnimalTools(settings()).search(CONDITIONS)
    await notify_matches(store, sender, "a", candidates)
    assert not sender.calls  # Samples must never send messages.
    real = [{**candidates[0], "sample": False}]
    await notify_matches(store, sender, "a", real)
    await notify_matches(store, sender, "a", real)
    assert len(sender.calls) == 1
    assert (await store.list("a", "notification"))[0]["status"] == "accepted"
    await notify_matches(store, sender, "b", real)
    assert len(sender.calls) == 1
    await store.delete("a", "subscription", "sub")
    await notify_matches(store, sender, "a", [{**real[0], "id": "new"}])
    assert len(sender.calls) == 1
