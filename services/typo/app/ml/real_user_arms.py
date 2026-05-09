"""5-arm balanced subset for real-user data collection (rev. 4 fix 42, §A.29).

With N=10 real-user observations we get ~2 per arm — sparse but sufficient
to compare arm means honestly.  The 5 arms are a diverse, interpretable
subset of the 16 available arms.

REAL_USER_ARM_INDICES: list of arm indices (into ml/arms.ARMS)
REAL_USER_ARMS: list of arm config dicts
"""

from __future__ import annotations

from app.ml.arms import ARMS

# Arm 0: default (all off)
# Arm 1: letter+word spacing only
# Arm 3: hyphenation + spacing
# Arm 6: color overlay + spacing
# Arm 10: emphasis + spacing  (reading emphasis visible)
REAL_USER_ARM_INDICES: list[int] = [0, 1, 3, 6, 10]

# Validate indices exist
assert all(0 <= i < len(ARMS) for i in REAL_USER_ARM_INDICES), (
    "REAL_USER_ARM_INDICES contains out-of-range indices"
)

REAL_USER_ARMS: list[dict] = [ARMS[i] for i in REAL_USER_ARM_INDICES]
