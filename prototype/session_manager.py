import uuid
import pickle
from prototype.controller_secure import SecureController


class SessionManager:
    def __init__(self, workers):
        self.controller = SecureController(workers)
        self.sessions = {}

    def join_worker(self, worker_url: str, handshake: bool = True):
        """Join a worker to the active worker pool."""
        self.controller.add_worker(worker_url, handshake=handshake)

    def leave_worker(self, worker_url: str):
        """Leave/remove a worker from the active worker pool."""
        self.controller.remove_worker(worker_url)

    def reconnect_worker(self, worker_url: str) -> bool:
        """Reconnect a worker and refresh secure session keys."""
        return self.controller.reconnect_worker(worker_url)

    def start_session(self, model, num_slices=2, encrypt=False):
        session_id = str(uuid.uuid4())
        slices = self.controller.partition_model(model, num_slices=num_slices)
        assigned = self.controller.preload_slices(slices, encrypt=encrypt)
        self.sessions[session_id] = {"assigned": assigned, "encrypt": encrypt}
        return session_id

    def infer(self, session_id, x):
        s = self.sessions[session_id]
        x_blob = pickle.dumps(x)
        out_blob = self.controller.run_distributed(
            s['assigned'], x_blob, encrypt=s['encrypt']
        )
        out = pickle.loads(out_blob)
        return out

    def end_session(self, session_id):
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
