import uuid
import pickle
from prototype.controller_secure import SecureController

class SessionManager:
    def __init__(self, workers):
        self.controller = SecureController(workers)
        self.sessions = {}

    def start_session(self, model, num_slices=2, encrypt=False):
        session_id = str(uuid.uuid4())
        slices = self.controller.partition_model(model, num_slices=num_slices)
        assigned = self.controller.preload_slices(slices, encrypt=encrypt)
        self.sessions[session_id] = {"assigned": assigned, "encrypt": encrypt}
        return session_id

    def infer(self, session_id, x):
        s = self.sessions[session_id]
        x_blob = pickle.dumps(x)
        out_blob = self.controller.run_distributed(s['assigned'], x_blob, encrypt=s['encrypt'])
        out = pickle.loads(out_blob)
        return out

    def end_session(self, session_id):
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
