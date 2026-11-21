"""Author-only microbatch AFAB pipeline with explicit stage boundaries."""
import numpy as np


def combine(payload, left, right):
    return dict(loss=left['loss'],gradients=left['gradients'],partitions=right['partitions'],events=right['events'])

from pathlib import Path
import json
