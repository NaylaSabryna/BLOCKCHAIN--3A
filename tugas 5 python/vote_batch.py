import datetime
from block import Block
from vote_status import VoteStatus

class VoteBatch:
    # PASTIKAN DUA UNDERSCORE: __init__ (bukan _init_)
    def __init__(self, batch_id: str, tps_location: str, total_voters: int, voter_id: str, candidate_choice: str, owner: str):
        self.batch_id = batch_id
        self.tps_location = tps_location
        self.total_voters = total_voters
        self.voter_id = voter_id
        self.candidate_choice = candidate_choice
        self.owner = owner
        self.status = VoteStatus.CREATED
        self.block = Block(
            index=1,
            data={
                "batch_id": batch_id,
                "voter_id": voter_id,
                "candidate_choice": candidate_choice,
                "tps": tps_location
            },
            previous_hash="0"
        )
        self.history = []
        
        self.add_history("VOTE_BATCH_CREATED", f"Kotak suara {batch_id} dibuka di {tps_location} oleh {owner}")

    def add_history(self, event_type: str, details: str):
        record = {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "event": event_type,
            "owner": self.owner,
            "status": self.status.name,
            "details": details
        }
        self.history.append(record)