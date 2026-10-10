"""Names for the proposed scheduler and its ablation variants."""
from .rgobi import RGOBIScheduler

VARIANTS = {
    'GOBI+A': dict(use_A=True, use_B=False),    # uncertainty-aware objective only
    'GOBI+B': dict(use_A=False, use_B=True),    # forecast calibration only
    'R-GOBI': dict(use_A=True, use_B=True),     # full method
}


def make(name, hosts):
    if name not in VARIANTS:
        raise ValueError(f'Unknown scheduler {name}')
    return RGOBIScheduler(hosts, **VARIANTS[name])
