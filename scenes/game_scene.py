"""Main gameplay scene composing board, evidence, inspector, trace, and controls."""
import pygame

from app_controller import TerminalState
from contracts.models import Status
from scenes.base_scene import BaseScene, UIButton
from ui.board_view import BoardView
from ui.evidence_panel import EvidencePanel
from ui.inspector_panel import InspectorPanel
from ui.theme import THEME, compute_game_layout, get_font, truncate_text
from ui.trace_panel import TracePanel


_SPEED_CYCLE: tuple[float, ...] = (0.5, 1.0, 2.0)


class GameScene(BaseScene):
    """Compose the four main panels, top toolbar, status bar, and terminal banners."""

    def __init__(self, controller) -> None:
        super().__init__(controller)
        self._size = (1280, 720)
        self._layout = compute_game_layout(*self._size)

        self.board_view = BoardView(self.controller.select_cell)
        self.evidence_panel = EvidencePanel(self.controller.select_clue)
        self.inspector_panel = InspectorPanel(self.controller.submit_verdict)
        self.trace_panel = TracePanel(self.controller.select_trace_step)
        self.board_view.set_animation_manager(self.controller.animations)

        self._btn_load = UIButton(pygame.Rect(0, 0, 72, 30), "Load", self.controller.show_case_select)
        self._btn_restart = UIButton(pygame.Rect(0, 0, 78, 30), "Restart", self.controller.restart)
        self._btn_hint = UIButton(pygame.Rect(0, 0, 68, 30), "Hint", self.controller.hint)
        self._btn_next = UIButton(pygame.Rect(0, 0, 92, 30), "Next Step", self.controller.next_step)
        self._btn_auto = UIButton(pygame.Rect(0, 0, 100, 30), "Auto Solve", self.controller.toggle_auto)
        self._btn_speed = UIButton(pygame.Rect(0, 0, 96, 30), "Speed: 1x", self._cycle_speed)
        self._btn_mute = UIButton(pygame.Rect(0, 0, 94, 30), "Sound: On", self.controller.toggle_mute)
        self._btn_tutorial = UIButton(pygame.Rect(0, 0, 82, 30), "Tutorial", self.controller.show_tutorial)
        self._btn_menu = UIButton(pygame.Rect(0, 0, 72, 30), "Menu", self.controller.show_menu)
        self._toolbar_buttons: tuple[UIButton, ...] = (
            self._btn_load,
            self._btn_restart,
            self._btn_hint,
            self._btn_next,
            self._btn_auto,
            self._btn_speed,
            self._btn_mute,
            self._btn_tutorial,
            self._btn_menu,
        )

        self._btn_export_trace = UIButton(pygame.Rect(0, 0, 102, 22), "Export Trace", self._handle_export_trace)
        self._btn_export_cnf = UIButton(pygame.Rect(0, 0, 94, 22), "Export CNF", self._handle_export_cnf)
        self._export_error = ""
        self._apply_layout()

    def on_enter(self) -> None:
        self._export_error = ""
        self._apply_layout()

    def on_resize(self, width: int, height: int) -> None:
        self._size = (max(640, width), max(480, height))
        self._apply_layout()

    def _apply_layout(self) -> None:
        self._layout = compute_game_layout(*self._size)
        self.evidence_panel.set_rect(self._layout.evidence)
        self._sync_board_rect()
        self.inspector_panel.set_rect(self._layout.inspector)
        self.trace_panel.set_rect(self._layout.trace)
        self._build_toolbar()

    def _sync_board_rect(self) -> None:
        rect = pygame.Rect(self._layout.board)
        if self.controller.terminal_state != TerminalState.NONE and rect.height >= 160:
            rect.height -= 62
        self.board_view.set_rect(rect)

    def _build_toolbar(self) -> None:
        tb = self._layout.toolbar
        pad_x = 6
        gap = 6
        base_widths = (74, 80, 68, 94, 102, 100, 96, 84, 74)
        avail = max(240, tb.width - pad_x * 2 - gap * (len(base_widths) - 1))
        total_base = sum(base_widths)
        scale = min(1.0, avail / total_base) if total_base > avail else 1.0

        x = tb.x + pad_x
        btn_h = max(24, tb.height - 8)
        btn_y = tb.y + (tb.height - btn_h) // 2
        for btn, base_w in zip(self._toolbar_buttons, base_widths):
            w = max(44, int(base_w * scale))
            btn.rect = pygame.Rect(x, btn_y, w, btn_h)
            x += w + gap

        sb = self._layout.status_bar
        export_h = max(20, sb.height - 4)
        export_y = sb.y + (sb.height - export_h) // 2
        cnf_w = 96
        trace_w = 104
        self._btn_export_cnf.rect = pygame.Rect(sb.right - cnf_w - 4, export_y, cnf_w, export_h)
        self._btn_export_trace.rect = pygame.Rect(self._btn_export_cnf.rect.x - 6 - trace_w, export_y, trace_w, export_h)

    def _cycle_speed(self) -> None:
        cur = self.controller.auto_speed
        idx = min(range(len(_SPEED_CYCLE)), key=lambda i: abs(_SPEED_CYCLE[i] - cur))
        next_speed = _SPEED_CYCLE[(idx + 1) % len(_SPEED_CYCLE)]
        self.controller.set_auto_speed(next_speed)

    def _save_dialog(self, title: str, default_ext: str, filetypes: list[tuple[str, str]]) -> str:
        root = None
        try:
            import tkinter as tk
            from tkinter import filedialog

            root = tk.Tk()
            root.withdraw()
            return filedialog.asksaveasfilename(title=title, defaultextension=default_ext, filetypes=filetypes)
        except Exception as exc:
            self._export_error = f"Export dialog unavailable: {exc}"
            return ""
        finally:
            if root is not None:
                try:
                    root.destroy()
                except Exception:
                    pass

    def _handle_export_trace(self) -> None:
        self._export_error = ""
        path = self._save_dialog(
            "Export Deduction Trace",
            ".json",
            [("JSON files", "*.json"), ("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if path:
            self.controller.export_trace(path)

    def _handle_export_cnf(self) -> None:
        self._export_error = ""
        path = self._save_dialog(
            "Export Public CNF",
            ".cnf",
            [("DIMACS CNF", "*.cnf"), ("Text files", "*.txt"), ("All files", "*.*")],
        )
        if path:
            self.controller.export_public_cnf(path)

    def _sync_toolbar_state(self) -> None:
        loading = self.controller.is_loading
        auto = self.controller.auto_running
        has_state = self.controller.public_state is not None
        term = self.controller.terminal_state

        self._btn_restart.enabled = has_state
        self._btn_hint.enabled = has_state and not loading and term not in (TerminalState.SOLVED, TerminalState.INCONSISTENT)
        self._btn_next.enabled = has_state and not loading and term not in (TerminalState.SOLVED, TerminalState.INCONSISTENT)

        self._btn_auto.label = "Pause" if auto else "Auto Solve"
        self._btn_auto.active = auto
        self._btn_auto.enabled = has_state and (auto or (not loading and term == TerminalState.NONE))

        self._btn_speed.label = f"Speed: {self.controller.auto_speed:g}x"
        self._btn_mute.label = "Muted" if self.controller.muted else "Sound: On"
        self._btn_mute.active = self.controller.muted
        self._btn_export_trace.enabled = has_state
        self._btn_export_cnf.enabled = has_state

    def _handle_shortcut(self, key: int) -> None:
        if key == pygame.K_ESCAPE:
            self.controller.show_menu()
        elif key == pygame.K_h and self._btn_hint.enabled:
            self.controller.hint()
        elif key == pygame.K_n and self._btn_next.enabled:
            self.controller.next_step()
        elif key == pygame.K_SPACE and self._btn_auto.enabled:
            self.controller.toggle_auto()
        elif key == pygame.K_r and self._btn_restart.enabled:
            self.controller.restart()
        elif key in (pygame.K_c, pygame.K_i):
            state = self.controller.public_state
            cell = self.controller.selected_cell
            if state is None or cell is None or self.controller.is_loading:
                return
            if cell in dict(state.proved_statuses):
                return
            verdict = Status.CRIMINAL if key == pygame.K_c else Status.INNOCENT
            self.controller.submit_verdict(cell, verdict)

    def handle_event(self, event: pygame.event.Event) -> None:
        self._sync_toolbar_state()

        for btn in self._toolbar_buttons:
            if btn.handle_event(event):
                self._export_error = ""
                return
        if self._btn_export_trace.handle_event(event):
            return
        if self._btn_export_cnf.handle_event(event):
            return

        if event.type == pygame.KEYDOWN:
            self._export_error = ""
            self._handle_shortcut(event.key)
            return

        if event.type == pygame.MOUSEBUTTONDOWN and getattr(event, "button", None) == 1:
            self._export_error = ""

        self.evidence_panel.handle_event(event)
        self.board_view.handle_event(event)
        self.inspector_panel.handle_event(event)
        self.trace_panel.handle_event(event)

    def update(self, dt: float) -> None:
        self._sync_toolbar_state()

    def _status_badge(self) -> tuple[str, tuple[int, int, int], tuple[int, int, int]]:
        term = self.controller.terminal_state
        if self.controller.is_loading:
            return "Loading...", THEME.accent_text, THEME.accent
        if term == TerminalState.SOLVED:
            return "Solved", THEME.innocent, THEME.innocent_bg
        if term == TerminalState.UNKNOWN:
            return "UNKNOWN", THEME.warn, THEME.clue_tint
        if term == TerminalState.INCONSISTENT:
            return "INCONSISTENT", THEME.criminal, THEME.criminal_bg
        if term == TerminalState.TIMEOUT:
            return "Timeout", THEME.criminal, THEME.criminal_bg
        if term == TerminalState.ERROR:
            return "Error", THEME.criminal, THEME.criminal_bg
        if self.controller.auto_running:
            return "Auto Solve", THEME.accent_text, THEME.accent
        return "Playing", THEME.accent, THEME.panel_alt_bg

    def _render_header(self, surface: pygame.Surface) -> None:
        hdr = self._layout.header
        pygame.draw.rect(surface, THEME.panel_bg, hdr, border_radius=8)
        pygame.draw.rect(surface, THEME.border, hdr, 1, border_radius=8)

        title_font = get_font(15, bold=True)
        meta_font = get_font(12, bold=True)
        badge_txt, badge_fg, badge_bg = self._status_badge()
        badge_w = max(84, meta_font.size(badge_txt)[0] + 20)
        badge_rect = pygame.Rect(hdr.right - badge_w - 8, hdr.y + 7, badge_w, hdr.height - 14)
        pygame.draw.rect(surface, badge_bg, badge_rect, border_radius=5)
        pygame.draw.rect(surface, THEME.border, badge_rect, 1, border_radius=5)
        b_surf = meta_font.render(badge_txt, True, badge_fg)
        surface.blit(b_surf, b_surf.get_rect(center=badge_rect.center))

        state = self.controller.public_state
        if state is None:
            t_surf = title_font.render("Griductive Solver", True, THEME.text)
            surface.blit(t_surf, t_surf.get_rect(left=hdr.x + 12, centery=hdr.centery))
            return

        total = state.size * state.size
        revealed = len(state.proved_statuses)
        prog_txt = f"Grid: {state.size}x{state.size}   |   Revealed: {revealed}/{total}"
        prog_surf = meta_font.render(prog_txt, True, THEME.text_muted)
        prog_x = badge_rect.x - prog_surf.get_width() - 14
        surface.blit(prog_surf, prog_surf.get_rect(left=prog_x, centery=hdr.centery))

        max_title_w = max(80, prog_x - (hdr.x + 12) - 12)
        title_txt = truncate_text(state.title, title_font, max_title_w)
        t_surf = title_font.render(title_txt, True, THEME.text)
        surface.blit(t_surf, t_surf.get_rect(left=hdr.x + 12, centery=hdr.centery))

    def _render_toolbar(self, surface: pygame.Surface) -> None:
        tb = self._layout.toolbar
        pygame.draw.rect(surface, THEME.panel_bg, tb, border_radius=8)
        pygame.draw.rect(surface, THEME.border, tb, 1, border_radius=8)
        btn_font = get_font(12, bold=True)
        for btn in self._toolbar_buttons:
            btn.draw(surface, btn_font)

    def _render_terminal_banner(self, surface: pygame.Surface) -> None:
        term = self.controller.terminal_state
        if term == TerminalState.NONE:
            return

        b = self._layout.board
        banner_rect = pygame.Rect(b.x + 4, b.bottom - 56, b.width - 8, 54)
        if term == TerminalState.SOLVED:
            bg, border, title = THEME.innocent_bg, THEME.innocent, "Case Solved"
            detail = f"Completed in {len(self.controller.trace_entries)} deduction steps."
        elif term == TerminalState.UNKNOWN:
            bg, border, title = THEME.clue_tint, THEME.warn, "UNKNOWN - No Forced Move"
            detail = "Public evidence leaves multiple consistent assignments. Hidden labels stay concealed."
        elif term == TerminalState.INCONSISTENT:
            bg, border, title = THEME.criminal_bg, THEME.criminal, "INCONSISTENT (UNSAT)"
            detail = "Current public clues have no satisfying assignment."
        elif term == TerminalState.TIMEOUT:
            bg, border, title = THEME.criminal_bg, THEME.criminal, "Solver Timeout"
            detail = "SAT solver exceeded the time limit before proving or refuting."
        else:
            bg, border, title = THEME.criminal_bg, THEME.criminal, "Runtime Error"
            detail = self.controller.status_message or "An error interrupted execution."

        metrics = self.controller.metrics
        if metrics is not None:
            meta_txt = f"Steps: {metrics.deduction_steps} | SAT: {metrics.sat_calls} | {metrics.sat_runtime_ms:.1f}ms"
        else:
            meta_txt = f"Steps: {len(self.controller.trace_entries)}"

        pygame.draw.rect(surface, bg, banner_rect, border_radius=7)
        pygame.draw.rect(surface, border, banner_rect, 2, border_radius=7)
        title_font = get_font(13, bold=True)
        sub_font = get_font(11)

        meta_max_w = max(80, banner_rect.width // 2)
        meta_surf = sub_font.render(truncate_text(meta_txt, sub_font, meta_max_w), True, THEME.text_muted)
        meta_x = banner_rect.right - 10 - meta_surf.get_width()
        surface.blit(meta_surf, (meta_x, banner_rect.y + 8))

        title_max_w = max(60, meta_x - (banner_rect.x + 10) - 8)
        surface.blit(
            title_font.render(truncate_text(title, title_font, title_max_w), True, border),
            (banner_rect.x + 10, banner_rect.y + 7),
        )
        surface.blit(
            sub_font.render(truncate_text(detail, sub_font, banner_rect.width - 20), True, THEME.text),
            (banner_rect.x + 10, banner_rect.y + 29),
        )

    def _render_status_and_export_bar(self, surface: pygame.Surface) -> None:
        sb = self._layout.status_bar
        pygame.draw.rect(surface, THEME.panel_bg, sb, border_radius=6)
        pygame.draw.rect(surface, THEME.border, sb, 1, border_radius=6)

        msg_font = get_font(11)
        btn_font = get_font(11, bold=True)
        msg = self._export_error or self.controller.status_message or "Ready."
        term = self.controller.terminal_state
        is_err = bool(self._export_error) or term in (
            TerminalState.INCONSISTENT,
            TerminalState.TIMEOUT,
            TerminalState.ERROR,
        )
        fg = THEME.criminal if is_err else THEME.text_muted

        max_msg_w = max(80, self._btn_export_trace.rect.x - sb.x - 16)
        txt = truncate_text(msg, msg_font, max_msg_w)
        surf = msg_font.render(txt, True, fg)
        surface.blit(surf, surf.get_rect(left=sb.x + 10, centery=sb.centery))

        self._btn_export_trace.draw(surface, btn_font)
        self._btn_export_cnf.draw(surface, btn_font)

    def render(self, surface: pygame.Surface) -> None:
        if surface.get_size() != self._size:
            self.on_resize(*surface.get_size())

        surface.fill(THEME.bg)
        self._sync_toolbar_state()
        self._sync_board_rect()

        self._render_header(surface)
        self._render_toolbar(surface)

        state = self.controller.public_state
        if state is None:
            b = self._layout.board
            pygame.draw.rect(surface, THEME.panel_bg, b, border_radius=8)
            pygame.draw.rect(surface, THEME.border, b, 1, border_radius=8)
            msg = get_font(13).render("No active puzzle loaded. Use Load or Menu.", True, THEME.text_muted)
            surface.blit(msg, msg.get_rect(center=b.center))
        else:
            hint_move = self.controller.hint_move
            self.board_view.set_hint_cell(hint_move[0] if hint_move is not None else None)
            self.inspector_panel.set_feedback(self.controller.feedback)
            self.inspector_panel.set_hint(hint_move, self.controller.no_forced_message)
            self.inspector_panel.set_loading(self.controller.is_loading)
            self.trace_panel.set_context(self.controller.analysis, self.controller.metrics)
            self.trace_panel.set_selected_step(self.controller.selected_trace_step)

            self.evidence_panel.render(surface, state, self.controller.selected_clue_id)
            self.board_view.render(
                surface,
                state,
                self.controller.selected_cell,
                self.controller.highlighted_cells,
            )
            self.inspector_panel.render(
                surface,
                state,
                self.controller.analysis,
                self.controller.selected_cell,
            )
            self.trace_panel.render(surface, self.controller.trace_entries)
            self._render_terminal_banner(surface)

        self._render_status_and_export_bar(surface)

    def on_exit(self) -> None:
        return None
