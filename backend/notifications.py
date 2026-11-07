from uuid import uuid4, uuid5, NAMESPACE_URL
import httpx
from backend.graph import candidate_errors, rank_candidates
from backend.storage import now
from backend.tools import ToolError


class DiscordSender:
    def __init__(self, settings):
        self.settings = settings

    def allowed(self, recipient):
        return bool(self.settings.discord_bot_token) and recipient in {v.strip() for v in self.settings.discord_allowed_user_ids.split(",") if v.strip()}

    async def send(self, recipient, content):
        if not self.allowed(recipient):
            raise ToolError("discord_config", "Discord Bot과 동의받은 수신자 허용 목록 설정이 필요합니다.")
        try:
            async with httpx.AsyncClient(timeout=8, headers={"Authorization": "Bot " + self.settings.discord_bot_token}) as client:
                channel = await client.post("https://discord.com/api/v10/users/@me/channels", json={"recipient_id": recipient})
                channel.raise_for_status()
                message = await client.post(f"https://discord.com/api/v10/channels/{channel.json()['id']}/messages", json={"content": content[:1800], "allowed_mentions": {"parse": []}})
                message.raise_for_status()
                return {"status": "accepted", "provider_id": message.json()["id"]}
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            # Message POST timeout may be ambiguous; don't automatically duplicate a DM.
            raise ToolError("discord_delivery", "Discord 발송 실패 또는 수락 확인 불가: DM 허용·수신자·호출 제한을 확인하세요.") from exc


async def notify_matches(store, sender, owner, candidates):
    subscriptions = await store.list(owner, "subscription")
    sent = 0
    for sub in subscriptions:
        if not sub.get("active"):
            continue
        saved = await store.get(owner, "saved", sub["saved_search_id"])
        if not saved:
            continue
        for candidate in candidates:
            if candidate.get("sample") or candidate_errors([candidate], saved["conditions"]):
                continue
            ranked = rank_candidates([candidate], saved["conditions"])[0]
            has_features = any(saved["conditions"].get(k) for k in ("breed", "color", "features"))
            if has_features and ranked["score"] == 0:
                continue
            key = str(uuid5(NAMESPACE_URL, sub["id"] + ":" + candidate["id"]))
            record = {"subscription_id": sub["id"], "candidate_id": candidate["id"], "channel": "discord", "status": "pending", "created_at": now(), "sample": False}
            if not await store.put(owner, "notification", key, record, create_only=True):
                continue
            try:
                # At most 3 sends per explicit search. Others remain discoverable next search.
                record.update(await sender.send(sub["recipient"], f"[다시 만나] 확인할 유사 후보\n공고: {candidate['notice_no'] or candidate['id']}\n{candidate['breed']} / {candidate['color']}\n발견: {candidate['found_date']} · {candidate['found_place']}\n보호센터: {candidate['shelter_name']}\n{candidate['source_url']}\n동일 동물 여부는 보호센터에 확인해 주세요."))
            except ToolError as exc:
                record.update(status="failed_or_unknown", error=str(exc))
            await store.put(owner, "notification", key, record)
            sent += 1
            if sent >= 3:
                return
