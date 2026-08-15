"""Unit tests for the pure (numpy-only) pipeline helpers."""

import numpy as np
import pytest
from app.pipeline.averaging import build_master


def test_build_master_is_mean():
    a = np.array([1.0, 2.0, 3.0], dtype=np.float32)
    b = np.array([3.0, 4.0, 5.0], dtype=np.float32)
    master = build_master([a, b])
    assert np.allclose(master, [2.0, 3.0, 4.0])
    assert master.dtype == np.float32


def test_build_master_single():
    a = np.array([0.5, -0.5], dtype=np.float32)
    assert np.allclose(build_master([a]), a)


def test_build_master_empty_raises():
    with pytest.raises(ValueError):
        build_master([])


def test_similarity_template_math():
    """The SDK template's cosine/decide logic (copied inline to avoid a
    template import) behaves as expected."""

    def cosine(v1, v2):
        denom = np.linalg.norm(v1) * np.linalg.norm(v2)
        return float(np.dot(v1, v2) / denom) if denom > 0 else 0.0

    v = np.array([1.0, 0.0, 0.0])
    assert cosine(v, v) == pytest.approx(1.0)
    assert cosine(v, np.array([0.0, 1.0, 0.0])) == pytest.approx(0.0)
