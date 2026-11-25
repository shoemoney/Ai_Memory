"""Differentiable PR training paths without modifying the dependency checkout."""


def install():
    import mlx.core as mx
    from mlx_lm.models.inkling2 import layers

    layers._use_kernels = lambda: False

    def route(self, hidden_states):
        logits = hidden_states.astype(mx.float32) @ self.weight.T
        scores = mx.sigmoid(logits)
        biased = scores + self.e_score_correction_bias
        # Top-k selection is discrete. Preserve the gradient through selected
        # scores, but not through the integer indices into those scores.
        indices = mx.stop_gradient(mx.argpartition(-biased, kth=self.top_k - 1, axis=-1)[..., :self.top_k])
        weights = mx.take_along_axis(scores, indices, axis=-1)
        weights = weights / (weights.sum(axis=-1, keepdims=True) + 1e-20)
        return indices, weights * self.routed_scaling_factor

    layers.TopKRouter.__call__ = route
