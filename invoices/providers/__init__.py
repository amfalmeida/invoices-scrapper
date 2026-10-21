from ..state import State
from .base import Provider
from .lidl import LidlProvider

REGISTRY: dict[str, type[Provider]] = {
    LidlProvider.name: LidlProvider,
}


def build(names: list[str], state: State) -> list[Provider]:
    unknown = [n for n in names if n not in REGISTRY]
    if unknown:
        raise SystemExit(f"Unknown provider(s): {', '.join(unknown)}. Available: {', '.join(REGISTRY)}")
    return [REGISTRY[n](state) for n in names]
