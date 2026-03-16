import json
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, String, Text, DateTime
from database import Base


def _now():
    return datetime.now(timezone.utc)


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    name = Column(String, nullable=False)

    # BoFire domain spec — stored as JSON (DomainCreate schema)
    domain_json = Column(Text, nullable=False)

    # Optional BoFire strategy spec — stored as JSON (SuggestRequest schema)
    strategy_json = Column(Text, nullable=True)

    # Optional free-text explanation for LLM context
    context = Column(Text, nullable=True)

    # Proposals dict — {"initial_proposal": [...], "proposal1": [...], ...}
    proposals_json = Column(Text, nullable=False, default="{}")

    # Experiment observations fed back after each proposal round
    experiments_json = Column(Text, nullable=False, default="[]")

    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    # ── helpers ──────────────────────────────────────────────────────────────

    def get_domain(self) -> dict:
        return json.loads(self.domain_json)

    def get_strategy(self) -> dict | None:
        return json.loads(self.strategy_json) if self.strategy_json else None

    def get_proposals(self) -> dict:
        return json.loads(self.proposals_json)

    def get_experiments(self) -> list:
        return json.loads(self.experiments_json)

    def set_proposals(self, proposals: dict):
        self.proposals_json = json.dumps(proposals)

    def set_experiments(self, experiments: list):
        self.experiments_json = json.dumps(experiments)

    def next_proposal_key(self) -> str:
        """Return the next sequential proposal key."""
        proposals = self.get_proposals()
        if not proposals:
            return "initial_proposal"
        n = len(proposals)  # initial_proposal counts as index 0
        return f"proposal{n}"
