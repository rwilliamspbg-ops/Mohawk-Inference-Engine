import numpy as np
import pickle

class ToyModel:
    def __init__(self, layer_sizes, seed=0):
        rng = np.random.default_rng(seed)
        self.weights = []
        for i in range(len(layer_sizes)-1):
            w = rng.standard_normal((layer_sizes[i+1], layer_sizes[i])).astype(np.float32)
            b = rng.standard_normal((layer_sizes[i+1],)).astype(np.float32)
            self.weights.append((w, b))

    def forward(self, x):
        out = x
        for (w,b) in self.weights:
            out = w @ out + b[:, None]
            out = np.tanh(out)
        return out

    def slice(self, start_layer, end_layer):
        # returns a new ToyModel with subset of layers
        sub = ToyModel.__new__(ToyModel)
        sub.weights = self.weights[start_layer:end_layer]
        return sub

    def serialize(self):
        return pickle.dumps(self.weights)

    @staticmethod
    def deserialize(blob):
        m = ToyModel.__new__(ToyModel)
        m.weights = pickle.loads(blob)
        return m

    def apply(self, x):
        out = x
        for (w,b) in self.weights:
            out = w @ out + b[:, None]
            out = np.tanh(out)
        return out
