import pickle
import numpy as np
from prototype.model_tools import ToyModel
from prototype.session_manager import SessionManager

workers = ["http://127.0.0.1:8003"]
sm = SessionManager(workers)
model = ToyModel([8,16,16,8], seed=42)

x = np.random.default_rng(1).standard_normal((8,1)).astype('float32')
baseline = model.forward(x)

sid = sm.start_session(model, num_slices=2, encrypt=True)
out = sm.infer(sid, x)
print('Max diff:', float(np.max(np.abs(baseline - out))))
sm.end_session(sid)
