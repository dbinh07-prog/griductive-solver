"""Tabbed bottom panel for Deduction Trace, Public KB + SAT queries, and Metrics."""
from collections.abc import Callable
import pygame

from contracts.models import Analysis, SessionMetrics, TraceEntry
from ui.theme import THEME, get_font, truncate_text, wrap_text


_TABS: tuple[tuple[str, str], ...] = (
    ("trace", "Deduction Trace"),
    ("kb", "Public KB + SAT"),
    ("metrics", "Metrics"),
)


class TracePanel:
    """Display deduction history, public CNF/SAT queries, and session metrics."""

    def __init__(self, on_select_step: Callable[[int], None]) -> None:
        self.on_select_step = on_select_step
        self._rect = pygame.Rect(0, 0, 1200, 180)
        self._active_tab = "trace"
        self._selected_step: int | None = None
        self._analysis: Analysis | None = None
        self._metrics: SessionMetrics | None = None
        self._scroll_y = 0
        self._max_scroll = 0
        self._detail_scroll_y = 0
        self._detail_max_scroll = 0
        self._tab_rects: list[tuple[pygame.Rect, str]] = []
        self._step_rects: list[tuple[pygame.Rect, int]] = []
        self._content_rect = pygame.Rect(0, 0, 1200, 140)
        self._trace_left_rect = pygame.Rect(0, 0, 0, 0)
        self._trace_right_rect = pygame.Rect(0, 0, 0, 0)

    def set_rect(self, rect: pygame.Rect) -> None:
        self._rect = pygame.Rect(rect)

    def set_active_tab(self, tab: str) -> None:
        normalized = tab.strip().lower()
        if normalized in {"trace", "kb", "metrics"} and normalized != self._active_tab:
            self._active_tab = normalized
            self._scroll_y = 0
            self._max_scroll = 0
            self._detail_scroll_y = 0
            self._detail_max_scroll = 0

    def set_selected_step(self, step: int | None) -> None:
        if step != self._selected_step:
            self._selected_step = step
            self._detail_scroll_y = 0
            self._detail_max_scroll = 0

    def set_context(self, analysis: Analysis | None, metrics: SessionMetrics | None) -> None:
        self._analysis = analysis
        self._metrics = metrics

    def scroll_by(self, delta_y: int) -> None:
        self._scroll_y = max(0, min(self._scroll_y + delta_y, self._max_scroll))

    def scroll_detail_by(self, delta_y: int) -> None:
        self._detail_scroll_y = max(0, min(self._detail_scroll_y + delta_y, self._detail_max_scroll))

    def _route_scroll(self, pos: tuple[int, int], delta_y: int) -> None:
        if self._active_tab == "trace" and self._trace_right_rect.collidepoint(pos):
            self.scroll_detail_by(delta_y)
        else:
            self.scroll_by(delta_y)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEWHEEL:
            pos = getattr(event, "pos", None) or pygame.mouse.get_pos()
            if self._rect.collidepoint(pos) or pos == (0, 0):
                self._route_scroll(pos, -event.y * 24)
            return

        if event.type != pygame.MOUSEBUTTONDOWN:
            return
        if event.button == 4 and self._rect.collidepoint(event.pos):
            self._route_scroll(event.pos, -24)
            return
        if event.button == 5 and self._rect.collidepoint(event.pos):
            self._route_scroll(event.pos, 24)
            return
        if event.button != 1:
            return

        for tab_rect, tab_id in self._tab_rects:
            if tab_rect.collidepoint(event.pos):
                self.set_active_tab(tab_id)
                return

        if self._active_tab == "trace" and self._content_rect.collidepoint(event.pos):
            for step_rect, step_num in self._step_rects:
                if step_rect.collidepoint(event.pos):
                    self.set_selected_step(step_num)
                    self.on_select_step(step_num)
                    return

    def render(self, surface: pygame.Surface, entries: tuple[TraceEntry, ...]) -> None:
        pygame.draw.rect(surface, THEME.panel_bg, self._rect, border_radius=8)
        pygame.draw.rect(surface, THEME.border, self._rect, 1, border_radius=8)

        tab_font = get_font(12, bold=True)
        body_font = get_font(12)
        mono_font = get_font(11, mono=True)

        pad = 8
        tab_x = self._rect.x + pad
        tab_y = self._rect.y + 6
        tab_h = 26
        self._tab_rects = []
        for tab_id, label in _TABS:
            text = f"{label} ({len(entries)})" if tab_id == "trace" else label
            tw = tab_font.size(text)[0] + 22
            t_rect = pygame.Rect(tab_x, tab_y, tw, tab_h)
            is_active = self._active_tab == tab_id
            bg = THEME.accent if is_active else THEME.panel_alt_bg
            fg = THEME.accent_text if is_active else THEME.text
            pygame.draw.rect(surface, bg, t_rect, border_radius=5)
            txt = tab_font.render(text, True, fg)
            surface.blit(txt, txt.get_rect(center=t_rect.center))
            self._tab_rects.append((t_rect, tab_id))
            tab_x += tw + 6

        line_y = tab_y + tab_h + 4
        pygame.draw.line(surface, THEME.border, (self._rect.x + pad, line_y), (self._rect.right - pad, line_y), 1)

        self._content_rect = pygame.Rect(
            self._rect.x + pad,
            line_y + 6,
            max(40, self._rect.width - pad * 2),
            max(24, self._rect.bottom - pad - (line_y + 6)),
        )
        self._step_rects = []

        if self._active_tab == "trace":
            self._render_trace_tab(surface, entries, body_font, mono_font)
        elif self._active_tab == "kb":
            self._render_kb_tab(surface, body_font, mono_font)
        else:
            self._render_metrics_tab(surface, body_font, mono_font)

    def _render_trace_tab(
        self,
        surface: pygame.Surface,
        entries: tuple[TraceEntry, ...],
        body_font: pygame.font.Font,
        mono_font: pygame.font.Font,
    ) -> None:
        if not entries:
            self._max_scroll = 0
            self._scroll_y = 0
            self._detail_max_scroll = 0
            self._detail_scroll_y = 0
            self._trace_left_rect = pygame.Rect(0, 0, 0, 0)
            self._trace_right_rect = pygame.Rect(0, 0, 0, 0)
            surface.blit(
                body_font.render("No deduction steps recorded yet.", True, THEME.text_muted),
                self._content_rect.topleft,
            )
            return

        left_w = max(200, int(self._content_rect.width * 0.36))
        left_rect = pygame.Rect(self._content_rect.x, self._content_rect.y, left_w, self._content_rect.height)
        right_rect = pygame.Rect(
            left_rect.right + 10,
            self._content_rect.y,
            max(80, self._content_rect.width - left_w - 10),
            self._content_rect.height,
        )
        self._trace_left_rect = left_rect
        self._trace_right_rect = right_rect

        row_h = 24
        total_h = len(entries) * row_h
        self._max_scroll = max(0, total_h - left_rect.height)
        self._scroll_y = max(0, min(self._scroll_y, self._max_scroll))

        active_step = self._selected_step if self._selected_step is not None else entries[-1].step
        selected_entry = next((e for e in entries if e.step == active_step), entries[-1])

        list_w = left_rect.width - (10 if self._max_scroll > 0 else 0)
        prev_clip = surface.get_clip()
        surface.set_clip(left_rect)
        y = left_rect.y - self._scroll_y
        for entry in entries:
            row_rect = pygame.Rect(left_rect.x, y, list_w, row_h - 2)
            if row_rect.bottom >= left_rect.y and row_rect.y <= left_rect.bottom:
                is_sel = entry.step == selected_entry.step
                bg = THEME.clue_tint if is_sel else THEME.card_face_up
                border = THEME.select_border if is_sel else THEME.border
                pygame.draw.rect(surface, bg, row_rect, border_radius=4)
                pygame.draw.rect(surface, border, row_rect, 1, border_radius=4)
                hit_rect = row_rect.clip(left_rect)
                if hit_rect.width > 0 and hit_rect.height > 0:
                    self._step_rects.append((hit_rect, entry.step))

                label = truncate_text(
                    f"#{entry.step}  {entry.cell} = {entry.verdict.value}  (+{entry.revealed_clue_id})",
                    body_font,
                    row_rect.width - 10,
                )
                surface.blit(body_font.render(label, True, THEME.text), (row_rect.x + 5, row_rect.y + 3))
            y += row_h
        surface.set_clip(prev_clip)

        if self._max_scroll > 0:
            track = pygame.Rect(left_rect.right - 7, left_rect.y, 6, left_rect.height)
            self._draw_scrollbar(surface, track, self._scroll_y, self._max_scroll, total_h)

        # Render details strictly from the selected historical TraceEntry, never current KB state.
        pygame.draw.rect(surface, THEME.card_face_up, right_rect, border_radius=5)
        pygame.draw.rect(surface, THEME.border, right_rect, 1, border_radius=5)
        detail_lines = [
            f"Step {selected_entry.step} (prior revision {selected_entry.revision}) | "
            f"Verdict: {selected_entry.cell} = {selected_entry.verdict.value} | "
            f"New Clue: {selected_entry.revealed_clue_id}",
            f"Active Clue IDs Before Reveal: {', '.join(selected_entry.active_clue_ids) or 'None'}",
            f"SAT Queries Executed ({len(selected_entry.sat_queries)}):",
        ]
        for idx, query in enumerate(selected_entry.sat_queries, start=1):
            assump = "Base KB ()" if not query.assumptions else str(query.assumptions)
            outcome = "SAT" if query.satisfiable else "UNSAT"
            st = query.stats
            detail_lines.append(
                f"  Q{idx}: {assump} -> {outcome} "
                f"[d={st.decisions}, p={st.propagations}, b={st.backtracks}, {st.runtime_ms:.2f}ms]"
            )

        inner_detail = right_rect.inflate(-10, -10)
        self._detail_scroll_y, self._detail_max_scroll = self._render_scrollable_lines(
            surface,
            inner_detail,
            detail_lines,
            mono_font,
            self._detail_scroll_y,
        )

    def _render_kb_tab(
        self,
        surface: pygame.Surface,
        body_font: pygame.font.Font,
        mono_font: pygame.font.Font,
    ) -> None:
        self._detail_max_scroll = 0
        self._detail_scroll_y = 0
        self._trace_left_rect = pygame.Rect(0, 0, 0, 0)
        self._trace_right_rect = pygame.Rect(0, 0, 0, 0)

        if self._analysis is None:
            self._max_scroll = 0
            self._scroll_y = 0
            surface.blit(body_font.render("Not Available", True, THEME.text_muted), self._content_rect.topleft)
            return

        an = self._analysis
        cnf = an.cnf
        aux_count = max(0, cnf.variable_count - len(cnf.primary_variables))
        var_map = ", ".join(f"{cell}={vid}" for cell, vid in cnf.primary_variables)
        lines = [
            f"Puzzle: {an.puzzle_id} | Revision: {an.revision} | Consistent: {'No (UNSAT)' if an.inconsistent else 'Yes'}",
            f"Variables: {len(cnf.primary_variables)} primary + {aux_count} auxiliary = {cnf.variable_count} total | Clauses: {len(cnf.clauses)}",
            f"Primary Var Map: {var_map or 'None'}",
            f"SAT Queries ({len(an.queries)}):",
        ]
        for idx, query in enumerate(an.queries, start=1):
            assump = "Base KB ()" if not query.assumptions else str(query.assumptions)
            outcome = "SAT" if query.satisfiable else "UNSAT"
            st = query.stats
            lines.append(
                f"  Q{idx}: {assump} -> {outcome} "
                f"[d={st.decisions}, p={st.propagations}, b={st.backtracks}, {st.runtime_ms:.2f}ms]"
            )
        clause_preview = " | ".join("(" + " v ".join(str(lit) for lit in cl) + ")" for cl in cnf.clauses)
        lines.append(f"Public Clauses: {clause_preview or '() [True]'}")
        self._scroll_y, self._max_scroll = self._render_scrollable_lines(
            surface,
            self._content_rect,
            lines,
            mono_font,
            self._scroll_y,
        )

    def _render_metrics_tab(
        self,
        surface: pygame.Surface,
        body_font: pygame.font.Font,
        mono_font: pygame.font.Font,
    ) -> None:
        self._max_scroll = 0
        self._scroll_y = 0
        self._detail_max_scroll = 0
        self._detail_scroll_y = 0
        self._trace_left_rect = pygame.Rect(0, 0, 0, 0)
        self._trace_right_rect = pygame.Rect(0, 0, 0, 0)

        if self._metrics is None:
            surface.blit(body_font.render("Not Available", True, THEME.text_muted), self._content_rect.topleft)
            return

        m = self._metrics
        items = (
            ("Primary Variables", str(m.primary_variables)),
            ("Auxiliary Variables", "--" if m.auxiliary_variables is None else str(m.auxiliary_variables)),
            ("Active Clauses", "--" if m.active_clauses is None else str(m.active_clauses)),
            ("SAT Calls", str(m.sat_calls)),
            ("Decisions", str(m.decisions)),
            ("Propagations", str(m.propagations)),
            ("Backtracks", str(m.backtracks)),
            ("Deduction Steps", str(m.deduction_steps)),
            ("SAT Runtime (ms)", f"{m.sat_runtime_ms:.2f}"),
        )
        cols = 3
        col_w = max(120, self._content_rect.width // cols)
        row_h = max(24, self._content_rect.height // 3)
        for idx, (label, val) in enumerate(items):
            col = idx % cols
            row = idx // cols
            cell_rect = pygame.Rect(
                self._content_rect.x + col * col_w,
                self._content_rect.y + row * row_h,
                col_w - 8,
                row_h - 6,
            )
            pygame.draw.rect(surface, THEME.card_face_up, cell_rect, border_radius=4)
            pygame.draw.rect(surface, THEME.border, cell_rect, 1, border_radius=4)
            surface.blit(body_font.render(f"{label}:", True, THEME.text_muted), (cell_rect.x + 8, cell_rect.y + 4))
            val_surf = mono_font.render(val, True, THEME.text)
            surface.blit(val_surf, (cell_rect.right - val_surf.get_width() - 8, cell_rect.y + 5))

    def _render_scrollable_lines(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        lines: list[str],
        font: pygame.font.Font,
        scroll_y: int,
    ) -> tuple[int, int]:
        if rect.width <= 12 or rect.height <= 8:
            return 0, 0
        bar_w = 8
        max_w = max(20, rect.width - bar_w - 6)
        wrapped_all: list[str] = []
        for raw in lines:
            wrapped_all.extend(wrap_text(raw, font, max_w))

        step_h = font.get_height() + 2
        total_h = len(wrapped_all) * step_h
        max_scroll = max(0, total_h - rect.height)
        clamped_y = max(0, min(scroll_y, max_scroll))

        prev_clip = surface.get_clip()
        surface.set_clip(rect)
        y = rect.y - clamped_y
        for line in wrapped_all:
            if y + step_h >= rect.y and y <= rect.bottom:
                surface.blit(font.render(line, True, THEME.text), (rect.x + 2, y))
            y += step_h
        surface.set_clip(prev_clip)

        if max_scroll > 0:
            track = pygame.Rect(rect.right - bar_w + 2, rect.y, bar_w - 2, rect.height)
            self._draw_scrollbar(surface, track, clamped_y, max_scroll, total_h)
        return clamped_y, max_scroll

    def _draw_scrollbar(
        self,
        surface: pygame.Surface,
        track: pygame.Rect,
        scroll_y: int,
        max_scroll: int,
        total_h: int,
    ) -> None:
        if track.height <= 4 or max_scroll <= 0 or total_h <= 0:
            return
        pygame.draw.rect(surface, THEME.panel_alt_bg, track, border_radius=3)
        thumb_h = max(16, int(track.height * (track.height / total_h)))
        thumb_h = min(track.height, thumb_h)
        usable = max(1, track.height - thumb_h)
        thumb_y = track.y + int(usable * (scroll_y / max_scroll))
        pygame.draw.rect(surface, THEME.border, (track.x, thumb_y, track.width, thumb_h), border_radius=3)
