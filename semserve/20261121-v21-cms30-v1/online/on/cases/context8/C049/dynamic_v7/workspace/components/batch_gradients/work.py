import math


def _matmul(A, B):
    """A: (m, k), B: (k, n) -> (m, n)."""
    m = len(A)
    k = len(B)
    n = len(B[0])
    out = [[0.0] * n for _ in range(m)]
    for i in range(m):
        ai = A[i]
        oi = out[i]
        for p in range(k):
            aip = ai[p]
            bp = B[p]
            for j in range(n):
                oi[j] += aip * bp[j]
    return out


def _matmul_T(A, B):
    """A: (m, k), B: (n, k) -> A @ B^T = (m, n)."""
    m = len(A)
    n = len(B)
    k = len(B[0])
    out = [[0.0] * n for _ in range(m)]
    for i in range(m):
        ai = A[i]
        oi = out[i]
        for j in range(n):
            bj = B[j]
            s = 0.0
            for p in range(k):
                s += ai[p] * bj[p]
            oi[j] = s
    return out


def _outer_sum(A, B):
    """sum_r A[r]^T @ B[r] -> (len(A[0]), len(B[0]))."""
    m = len(A)
    k = len(A[0])
    n = len(B[0])
    out = [[0.0] * n for _ in range(k)]
    for r in range(m):
        ar = A[r]
        br = B[r]
        for p in range(k):
            ap = ar[p]
            op = out[p]
            for j in range(n):
                op[j] += ap * br[j]
    return out


def compute(payload):
    """按实际 stage 保留每个微批激活并反传；返回整题格式的 loss 和各层 gradients，采用微批等权和 float64。"""
    layers = payload["layers"]
    microbatches = payload["microbatches"]

    L = len(layers)
    weights = [layer["weight"] for layer in layers]
    biases = [layer["bias"] for layer in layers]

    grad_weights = [[[0.0] * len(w[0]) for _ in range(len(w))] for w in weights]
    grad_biases = [[0.0] * len(b) for b in biases]

    total_loss = 0.0
    num_microbatches = len(microbatches)

    for mb in microbatches:
        inputs = mb["inputs"]
        targets = mb["targets"]
        batch_size = len(inputs)

        # Forward pass, storing activations per layer.
        activations = [inputs]
        x = inputs
        for i in range(L):
            z = _matmul_T(x, weights[i])
            bi = biases[i]
            for r in range(batch_size):
                zr = z[r]
                for c in range(len(bi)):
                    zr[c] += bi[c]
            if i < L - 1:
                x = [[math.tanh(v) for v in row] for row in z]
            else:
                x = z
            activations.append(x)

        logits = activations[-1]

        # Softmax cross-entropy loss (mean over the microbatch).
        probs = []
        log_probs = []
        for r in range(batch_size):
            row = logits[r]
            m = max(row)
            shifted = [v - m for v in row]
            exps = [math.exp(v) for v in shifted]
            s = sum(exps)
            pr = [e / s for e in exps]
            probs.append(pr)
            log_probs.append([(v - m) - math.log(s) for v in row])

        loss = -sum(log_probs[r][targets[r]] for r in range(batch_size)) / batch_size
        total_loss += loss

        # Backward pass.
        dlogits = [row[:] for row in probs]
        for r in range(batch_size):
            dlogits[r][targets[r]] -= 1.0
        inv_batch = 1.0 / batch_size
        for r in range(batch_size):
            dr = dlogits[r]
            for c in range(len(dr)):
                dr[c] *= inv_batch

        d_activation = dlogits
        for i in range(L - 1, -1, -1):
            a_prev = activations[i]
            # grad_weights[i] += sum_r d_activation[r]^T @ a_prev[r]
            gw = _outer_sum(d_activation, a_prev)
            gwi = grad_weights[i]
            for r in range(len(gw)):
                for c in range(len(gw[r])):
                    gwi[r][c] += gw[r][c]
            # grad_biases[i] += sum over batch
            gbi = grad_biases[i]
            for c in range(len(gbi)):
                s = 0.0
                for r in range(batch_size):
                    s += d_activation[r][c]
                gbi[c] += s
            if i > 0:
                # d_z = d_activation @ weights[i]
                d_z = _matmul(d_activation, weights[i])
                # derivative of tanh
                a_i = activations[i]
                d_activation = [
                    [d_z[r][c] * (1.0 - a_i[r][c] * a_i[r][c]) for c in range(len(d_z[r]))]
                    for r in range(batch_size)
                ]

    loss = total_loss / num_microbatches

    gradients = []
    for i in range(L):
        gradients.append({
            "weight": grad_weights[i],
            "bias": grad_biases[i],
        })

    return {
        "loss": loss,
        "gradients": gradients,
    }
