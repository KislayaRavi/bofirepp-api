"""
File-system backed campaign store.

Layout on disk::

    {DATABASE_PATH}/
        {campaign_id}/
            campaign.json     — full campaign record (human-readable JSON)
            strategy.json     — serialized BoFire strategy spec (written by the
                                POST /campaigns/{id}/strategy/serialize endpoint)

Set the DATABASE_PATH environment variable to choose the root folder.
Default: ./campaigns_data  (relative to the server working directory).
"""
from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

_DEFAULT_BASE = "campaigns_data"


def _base_path() -> Path:
    return Path(os.environ.get("DATABASE_PATH", _DEFAULT_BASE))


def get_campaign_store() -> "CampaignStore":
    """FastAPI dependency — returns a store rooted at DATABASE_PATH."""
    return CampaignStore(_base_path())


def init_storage() -> None:
    """Create the root campaigns folder at startup (idempotent)."""
    _base_path().mkdir(parents=True, exist_ok=True)


class CampaignStore:
    """Read/write campaigns as JSON files on the local file system."""

    def __init__(self, base: Path) -> None:
        self.base = Path(base)
        self.base.mkdir(parents=True, exist_ok=True)

    # ── internal paths ────────────────────────────────────────────────────────

    def _dir(self, campaign_id: str) -> Path:
        return self.base / campaign_id

    def _campaign_file(self, campaign_id: str) -> Path:
        return self._dir(campaign_id) / "campaign.json"

    def _strategy_file(self, campaign_id: str) -> Path:
        return self._dir(campaign_id) / "strategy.json"

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _dumps(data: dict) -> str:
        return json.dumps(data, indent=2, ensure_ascii=False)

    @staticmethod
    def _loads(path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    # ── campaign CRUD ─────────────────────────────────────────────────────────

    def exists(self, campaign_id: str) -> bool:
        return self._campaign_file(campaign_id).exists()

    def read(self, campaign_id: str) -> Optional[Dict]:
        f = self._campaign_file(campaign_id)
        return self._loads(f) if f.exists() else None

    def save(self, campaign: Dict) -> None:
        d = self._dir(campaign["id"])
        d.mkdir(parents=True, exist_ok=True)
        self._campaign_file(campaign["id"]).write_text(
            self._dumps(campaign), encoding="utf-8"
        )

    def delete(self, campaign_id: str) -> None:
        d = self._dir(campaign_id)
        if d.exists():
            shutil.rmtree(d)

    def list_all(self) -> List[Dict]:
        if not self.base.exists():
            return []
        campaigns = []
        for item in self.base.iterdir():
            if item.is_dir():
                f = item / "campaign.json"
                if f.exists():
                    campaigns.append(self._loads(f))
        return sorted(campaigns, key=lambda c: c.get("created_at", ""), reverse=True)

    # ── create convenience ────────────────────────────────────────────────────

    def create(
        self,
        name: str,
        domain: dict,
        strategy: Optional[dict] = None,
        context: Optional[str] = None,
    ) -> Dict:
        now = self._now()
        campaign = {
            "id": str(uuid4()),
            "name": name,
            "domain": domain,
            "strategy": strategy,
            "context": context,
            "proposals": {},
            "experiments": [],
            "created_at": now,
            "updated_at": now,
        }
        self.save(campaign)
        return campaign

    def update(self, campaign: Dict) -> Dict:
        campaign["updated_at"] = self._now()
        self.save(campaign)
        return campaign

    # ── serialized BoFire strategy ────────────────────────────────────────────

    def save_serialized_strategy(self, campaign_id: str, data: dict) -> None:
        """Write strategy.json into the campaign's folder."""
        self._strategy_file(campaign_id).write_text(
            self._dumps(data), encoding="utf-8"
        )

    def read_serialized_strategy(self, campaign_id: str) -> Optional[Dict]:
        """Return the contents of strategy.json, or None if not yet saved."""
        f = self._strategy_file(campaign_id)
        return self._loads(f) if f.exists() else None

    # ── proposal key sequencing ───────────────────────────────────────────────

    @staticmethod
    def next_proposal_key(proposals: dict) -> str:
        if not proposals:
            return "initial_proposal"
        return f"proposal{len(proposals)}"
