"""Visual-only card flip, hint pulse, and reject shake animations."""
from collections.abc import Callable
from dataclasses import dataclass
import math


@dataclass
class CardFlipEffect:
    cell: str
    duration: float
    elapsed: float = 0.0
    on_complete: Callable[[], None] | None = None


@dataclass
class PulseEffect:
    cell: str
    duration: float
    elapsed: float = 0.0


@dataclass
class _RejectEffect:
    cell: str
    duration: float
    elapsed: float = 0.0


class AnimationManager:
    """Track non-blocking visual animations keyed by cell ID."""

    def __init__(self) -> None:
        self._flips: dict[str, CardFlipEffect] = {}
        self._pulses: dict[str, PulseEffect] = {}
        self._rejects: dict[str, _RejectEffect] = {}

    def trigger_flip(
        self,
        cell: str,
        on_complete: Callable[[], None] | None = None,
        duration: float = 0.28,
    ) -> None:
        self._flips[cell] = CardFlipEffect(
            cell=cell,
            duration=max(0.01, duration),
            on_complete=on_complete,
        )

    def trigger_pulse(self, cell: str, duration: float = 1.2) -> None:
        self._pulses[cell] = PulseEffect(cell=cell, duration=max(0.01, duration))

    def trigger_reject(self, cell: str, duration: float = 0.25) -> None:
        self._rejects[cell] = _RejectEffect(cell=cell, duration=max(0.01, duration))

    def update(self, dt: float) -> None:
        if dt <= 0:
            return

        completed: list[CardFlipEffect] = []
        for cell, effect in list(self._flips.items()):
            effect.elapsed += dt
            if effect.elapsed >= effect.duration:
                del self._flips[cell]
                completed.append(effect)

        # Fire callbacks after removing finished flips so is_flipping(cell) is already False.
        for effect in completed:
            if effect.on_complete is not None:
                effect.on_complete()

        for cell, effect in list(self._pulses.items()):
            effect.elapsed += dt
            if effect.elapsed >= effect.duration:
                del self._pulses[cell]

        for cell, effect in list(self._rejects.items()):
            effect.elapsed += dt
            if effect.elapsed >= effect.duration:
                del self._rejects[cell]

    def flip_scale_x(self, cell: str) -> float:
        effect = self._flips.get(cell)
        if effect is None:
            return 1.0
        progress = min(1.0, effect.elapsed / effect.duration)
        return max(0.06, abs(math.cos(progress * math.pi)))

    def is_flipping(self, cell: str) -> bool:
        return cell in self._flips

    def pulse_strength(self, cell: str) -> float:
        effect = self._pulses.get(cell)
        if effect is None:
            return 0.0
        progress = min(1.0, effect.elapsed / effect.duration)
        return 0.5 + 0.5 * math.sin(progress * math.pi * 4.0)

    def reject_offset_x(self, cell: str) -> float:
        effect = self._rejects.get(cell)
        if effect is None:
            return 0.0
        progress = min(1.0, effect.elapsed / effect.duration)
        return math.sin(progress * math.pi * 4.0) * (1.0 - progress) * 6.0

    def clear(self) -> None:
        self._flips.clear()
        self._pulses.clear()
        self._rejects.clear()


default_animation_manager = AnimationManager()


def flip_card(cell: str, on_complete: Callable[[], None] | None) -> None:
    """Register a visual card flip on the shared default animation manager."""
    default_animation_manager.trigger_flip(cell, on_complete=on_complete)
