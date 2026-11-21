"""C049 AFAB pipeline training for a small fully-connected network.

Implements the public business contract in TASK.md:
  - transform(payload) -> result dict (loss, gradients, partitions, events)
  - load_payload(input_path) -> object
  - build_component(input_path, output_path) -> result (also writes UTF-8 JSON)

The network is trained with a pipelined forward/backward schedule (AFAB:
all-forward then all-backward).  Each rank owns a half-open layer interval
[floor(L*r/world), floor(L*(r+1)/world)).  Microbatches are processed in
order during the forward pass and in reverse order during the backward pass.
Activations and their gradients are passed across stages; the last
microbatch's activations are never reused for other microbatches.
"""

import json
from pathlib import Path

import numpy as np


def _tanh(x):
    return np.tanh(x)


def _softmax_cross_entropy(logits, targets):
    """Mean cross entropy over the batch (per-microbatch average)."""
    shifted = logits - np.max(logits, axis=1, keepdims=True)
    exps = np.exp(shifted)
    probs = exps / np.sum(exps, axis=1, keepdims=True)
    n = logits.shape[0]
    log_probs = np.log(np.clip(probs[np.arange(n), targets], 1e-300, None))
    return -np.mean(log_probs)


def _layer_forward(weight, bias, x, activation):
    z = x @ weight.T + bias
    if activation:
        a = _tanh(z)
        return z, a
    return z, z


def _layer_backward(weight, x, z, grad_out, activation):
    """Return (grad_weight, grad_bias, grad_x)."""
    if activation:
        dz = grad_out * (1.0 - _tanh(z) ** 2)
    else:
        dz = grad_out
    grad_weight = dz.T @ x
    grad_bias = np.sum(dz, axis=0)
    grad_x = dz @ weight
    return grad_weight, grad_bias, grad_x


def _partitions(layers, world_size):
    L = len(layers)
    parts = []
    for r in range(world_size):
        start = int(np.floor(L * r / world_size))
        stop = int(np.floor(L * (r + 1) / world_size))
        parts.append({"stage": r, "start": start, "stop": stop})
    return parts


def _stage_of_layer(layer_idx, parts):
    for p in parts:
        if p["start"] <= layer_idx < p["stop"]:
            return p["stage"]
    raise ValueError("layer not in any partition")


def transform(payload):
    layers = payload["layers"]
    microbatches = payload["microbatches"]
    world_size = payload.get("world_size", 1)

    L = len(layers)
    parts = _partitions(layers, world_size)

    # Per-layer gradient accumulators (summed over microbatches).
    grad_weights = [np.zeros_like(np.asarray(l["weight"], dtype=np.float64))
                    for l in layers]
    grad_biases = [np.zeros_like(np.asarray(l["bias"], dtype=np.float64))
                   for l in layers]

    losses = []
    events = []

    # Forward pass: each microbatch traverses all stages in order.
    mb_activations = []  # list over microbatches of list over layers of (z, a)
    for mb_idx, mb in enumerate(microbatches):
        x = np.asarray(mb["inputs"], dtype=np.float64)
        acts = []
        for l in range(L):
            weight = np.asarray(layers[l]["weight"], dtype=np.float64)
            bias = np.asarray(layers[l]["bias"], dtype=np.float64)
            is_last = (l == L - 1)
            z, a = _layer_forward(weight, bias, x, activation=not is_last)
            acts.append((z, a))
            x = a
        mb_activations.append(acts)
        logits = acts[-1][1]
        losses.append(_softmax_cross_entropy(logits, mb["targets"]))
        for p in parts:
            events.append({"kind": "forward", "microbatch": mb_idx,
                           "stage": p["stage"]})
        for p in parts[:-1]:
            events.append({"kind": "send_activation",
                           "source": p["stage"], "target": p["stage"] + 1})

    # Backward pass: microbatches in reverse order, stages in reverse order.
    for mb_idx in range(len(microbatches) - 1, -1, -1):
        mb = microbatches[mb_idx]
        acts = mb_activations[mb_idx]
        n = len(mb["targets"])
        logits = acts[-1][1]
        shifted = logits - np.max(logits, axis=1, keepdims=True)
        exps = np.exp(shifted)
        probs = exps / np.sum(exps, axis=1, keepdims=True)
        grad_logits = probs.copy()
        grad_logits[np.arange(n), mb["targets"]] -= 1.0
        grad_logits /= n

        grad_out = grad_logits
        for l in range(L - 1, -1, -1):
            weight = np.asarray(layers[l]["weight"], dtype=np.float64)
            z, a = acts[l]
            x_in = (np.asarray(mb["inputs"], dtype=np.float64)
                    if l == 0 else mb_activations[mb_idx][l - 1][1])
            is_last = (l == L - 1)
            gw, gb, grad_out = _layer_backward(weight, x_in, z, grad_out,
                                               activation=not is_last)
            grad_weights[l] += gw
            grad_biases[l] += gb

        for p in reversed(parts):
            events.append({"kind": "backward", "microbatch": mb_idx,
                           "stage": p["stage"]})
        for p in reversed(parts[1:]):
            events.append({"kind": "send_gradient",
                           "source": p["stage"], "target": p["stage"] - 1})

    loss = float(np.mean(losses))

    gradients = [
        {"weight": grad_weights[l].tolist(), "bias": grad_biases[l].tolist()}
        for l in range(L)
    ]

    return {
        "loss": loss,
        "gradients": gradients,
        "partitions": parts,
        "events": events,
    }


def load_payload(input_path):
    with open(input_path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_component(input_path, output_path):
    payload = load_payload(input_path)
    result = transform(payload)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f)
    return result
