#!/usr/bin/env python3
"""
Generator liczb do gier liczbowych (Lotto, Mini Lotto, Multi Multi).

Program losuje liczby z wykorzystaniem generatora liczb pseudolosowych (PRNG).
Warunek zadania: liczby w jednym losowaniu NIE MOGĄ SIĘ POWTARZAĆ.

Zaimplementowane metody losowania:
  * reject  - metoda Monte Carlo z odrzucaniem (rejection sampling):
              losuj liczbę z U[1, N], jeśli już wypadła - odrzuć i losuj ponownie,
  * fisher  - częściowe tasowanie Fishera-Yatesa (wariant Durstenfelda).

Dostępne generatory liczb pseudolosowych:
  * mt  - Mersenne Twister (random.Random z biblioteki standardowej),
  * lcg - własna implementacja generatora kongruencji liniowej,
  * sys - random.SystemRandom (źródło entropii systemu operacyjnego).

Dodatkowo program potrafi wykonać symulację Monte Carlo (--simulate), która
sprawdza równomierność rozkładu wylosowanych liczb (test chi-kwadrat) oraz
porównuje oszacowane prawdopodobieństwa trafień z wartościami teoretycznymi.

Użycie:
    python lotto.py                          # jedno losowanie Lotto
    python lotto.py -g mini -n 5             # 5 zakładów Mini Lotto
    python lotto.py -g multi -p lcg --seed 1 # Multi Multi, własny LCG, ziarno 1
    python lotto.py --simulate 200000        # symulacja Monte Carlo
    python lotto.py --gui                    # aplikacja okienkowa (Tkinter)
"""

from __future__ import annotations

import argparse
import math
import random
import secrets
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Protocol

__version__ = "1.0.0"


# --------------------------------------------------------------------------- #
#  Definicje gier
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Game:
    """Opis gry liczbowej: losujemy `picks` różnych liczb z zakresu 1..`pool`."""

    key: str
    name: str
    pool: int
    picks: int


GAMES: Dict[str, Game] = {
    "lotto": Game("lotto", "Lotto (6 z 49)", 49, 6),
    "mini": Game("mini", "Mini Lotto (5 z 42)", 42, 5),
    "multi": Game("multi", "Multi Multi (20 z 80)", 80, 20),
}

METHODS = {
    "reject": "Monte Carlo z odrzucaniem powtórzeń",
    "fisher": "Tasowanie Fishera-Yatesa",
}

PRNGS = {
    "mt": "Mersenne Twister",
    "lcg": "Generator kongruencji liniowej (LCG)",
    "sys": "SystemRandom (entropia systemu)",
}


# --------------------------------------------------------------------------- #
#  Generatory liczb pseudolosowych
# --------------------------------------------------------------------------- #
class RandomSource(Protocol):
    """Minimalny interfejs generatora: zwraca liczby z przedziału [0, 1)."""

    def random(self) -> float: ...


class LCG:
    """Generator kongruencji liniowej (Linear Congruential Generator).

        X(n+1) = (a * X(n) + c) mod m

    Parametry z "Numerical Recipes": a = 1664525, c = 1013904223, m = 2^32.
    Implementacja edukacyjna - nie nadaje się do zastosowań kryptograficznych.
    """

    A = 1664525
    C = 1013904223
    M = 2**32

    def __init__(self, seed: int | None = None) -> None:
        if seed is None:
            seed = time.time_ns()
        self.state = seed % self.M

    def next_int(self) -> int:
        """Zwraca kolejną liczbę całkowitą z przedziału [0, m)."""
        self.state = (self.A * self.state + self.C) % self.M
        return self.state

    def random(self) -> float:
        """Zwraca kolejną liczbę rzeczywistą z przedziału [0, 1)."""
        return self.next_int() / self.M


def make_rng(prng: str, seed: int | None = None) -> RandomSource:
    """Tworzy generator o podanej nazwie ('mt', 'lcg' lub 'sys')."""
    if prng == "mt":
        return random.Random(seed)
    if prng == "lcg":
        return LCG(seed)
    if prng == "sys":
        return random.SystemRandom()
    raise ValueError(f"Nieznany generator: {prng!r}")


def uniform_int(rng: RandomSource, low: int, high: int) -> int:
    """Liczba całkowita z rozkładu równomiernego na [low, high] (włącznie)."""
    return low + int(rng.random() * (high - low + 1))


# --------------------------------------------------------------------------- #
#  Metody losowania
# --------------------------------------------------------------------------- #
@dataclass
class DrawResult:
    numbers: List[int]  # posortowane, bez powtórzeń
    attempts: int  # ile liczb wygenerowano (w tym odrzuconych)


def validate_draw(game: Game, numbers: List[int]) -> None:
    """Warunek zadania: właściwa ilość, zakres 1..N i brak powtórzeń."""
    if len(numbers) != game.picks:
        raise ValueError(f"Oczekiwano {game.picks} liczb, otrzymano {len(numbers)}.")
    if len(set(numbers)) != len(numbers):
        raise ValueError(f"Liczby się powtarzają: {numbers}")
    if any(not 1 <= n <= game.pool for n in numbers):
        raise ValueError(f"Liczba spoza zakresu 1..{game.pool}: {numbers}")


def draw_reject(game: Game, rng: RandomSource) -> DrawResult:
    """Monte Carlo z odrzucaniem: losuj z U[1, N] aż do uzyskania k różnych liczb."""
    chosen: set[int] = set()
    attempts = 0
    while len(chosen) < game.picks:
        attempts += 1
        candidate = uniform_int(rng, 1, game.pool)
        if candidate in chosen:  # warunek: liczby nie mogą się powtarzać
            continue
        chosen.add(candidate)
    return DrawResult(sorted(chosen), attempts)


def draw_fisher(game: Game, rng: RandomSource) -> DrawResult:
    """Częściowe tasowanie Fishera-Yatesa: k kroków na tablicy 1..N."""
    deck = list(range(1, game.pool + 1))
    for i in range(game.picks):
        j = uniform_int(rng, i, game.pool - 1)
        deck[i], deck[j] = deck[j], deck[i]
    return DrawResult(sorted(deck[: game.picks]), game.picks)


def draw(game: Game, rng: RandomSource, method: str = "reject") -> DrawResult:
    """Jedno losowanie wybraną metodą, z walidacją wyniku."""
    if method == "reject":
        result = draw_reject(game, rng)
    elif method == "fisher":
        result = draw_fisher(game, rng)
    else:
        raise ValueError(f"Nieznana metoda: {method!r}")
    validate_draw(game, result.numbers)
    return result


# --------------------------------------------------------------------------- #
#  Symulacja Monte Carlo i test równomierności
# --------------------------------------------------------------------------- #
@dataclass
class SimulationReport:
    game: Game
    draws: int
    counts: Dict[int, int]  # ile razy wypadła każda liczba
    chi2: float
    df: int
    chi2_critical: float  # wartość krytyczna dla alfa = 0,05
    hits_observed: Dict[int, int]  # liczba trafień -> ile losowań
    hits_expected: Dict[int, float]  # wartości teoretyczne (rozkład hipergeometryczny)

    @property
    def uniform_ok(self) -> bool:
        return self.chi2 <= self.chi2_critical


def chi2_critical_005(df: int) -> float:
    """Wartość krytyczna chi-kwadrat dla alfa = 0,05 (przybliżenie Wilsona-Hilferty)."""
    z = 1.6448536269514722  # kwantyl rzędu 0,95 rozkładu N(0, 1)
    a = 2.0 / (9.0 * df)
    return df * (1.0 - a + z * math.sqrt(a)) ** 3


def hypergeometric_pmf(game: Game, matches: int) -> float:
    """P(dokładnie `matches` trafień) dla stałego kuponu z `picks` liczbami."""
    k, n = game.picks, game.pool
    if matches > k or k - matches > n - k:
        return 0.0
    return math.comb(k, matches) * math.comb(n - k, k - matches) / math.comb(n, k)


def simulate(game: Game, method: str, prng: str, draws: int, seed: int | None) -> SimulationReport:
    """Wykonuje `draws` losowań i bada rozkład wyników.

    Test chi-kwadrat: dla losowania bez zwracania k z N liczb każda liczba wypada
    z prawdopodobieństwem p = k/N, a wektor liczności ma macierz kowariancji
    n * p(1-p) * N/(N-1) * (I - J/N), stąd statystyka
        chi2 = sum_i (O_i - E_i)^2 / (n * p * (1-p) * N/(N-1)),  df = N - 1.
    """
    rng = make_rng(prng, seed)
    counts = {i: 0 for i in range(1, game.pool + 1)}
    hits_observed = {m: 0 for m in range(game.picks + 1)}
    ticket = set(range(1, game.picks + 1))  # stały kupon {1, ..., k}

    for _ in range(draws):
        numbers = draw(game, rng, method).numbers
        for n in numbers:
            counts[n] += 1
        hits_observed[len(ticket.intersection(numbers))] += 1

    p = game.picks / game.pool
    expected = draws * p
    variance = draws * p * (1 - p) * game.pool / (game.pool - 1)
    chi2 = sum((o - expected) ** 2 for o in counts.values()) / variance
    df = game.pool - 1
    hits_expected = {m: draws * hypergeometric_pmf(game, m) for m in range(game.picks + 1)}
    return SimulationReport(
        game, draws, counts, chi2, df, chi2_critical_005(df), hits_observed, hits_expected
    )


def format_report(r: SimulationReport) -> str:
    """Tekstowa prezentacja raportu symulacji."""
    expected = r.draws * r.game.picks / r.game.pool
    lines = [
        f"Symulacja Monte Carlo: {r.game.name}, {r.draws} losowań",
        "",
        f"Oczekiwana liczba wystąpień każdej liczby: {expected:.1f}",
        f"Najrzadziej: {min(r.counts.values())}   Najczęściej: {max(r.counts.values())}",
        "",
        f"Test chi-kwadrat: chi2 = {r.chi2:.2f}, df = {r.df}, "
        f"wartość krytyczna (alfa=0,05) = {r.chi2_critical:.2f}",
        "Wniosek: " + (
            "brak podstaw do odrzucenia hipotezy o równomierności rozkładu."
            if r.uniform_ok
            else "odrzucamy hipotezę o równomierności rozkładu."
        ),
        "",
        "Trafienia dla stałego kuponu {1..k}:",
        f"{'trafień':>8} {'obserwowane':>13} {'oczekiwane':>14} {'P obs.':>12} {'P teor.':>12}",
    ]
    for m in range(r.game.picks + 1):
        obs, exp = r.hits_observed[m], r.hits_expected[m]
        if obs == 0 and exp < 0.01:
            continue
        lines.append(
            f"{m:>8} {obs:>13} {exp:>14.1f} {obs / r.draws:>12.6f} {exp / r.draws:>12.6f}"
        )
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
#  Interfejs tekstowy
# --------------------------------------------------------------------------- #
def format_numbers(numbers: List[int]) -> str:
    return " ".join(f"{n:02d}" for n in numbers)


def run_cli(args: argparse.Namespace) -> int:
    game = GAMES[args.game]
    seed = args.seed if args.seed is not None else secrets.randbits(32)

    if args.simulate:
        print(f"Generator: {PRNGS[args.prng]}, metoda: {METHODS[args.method]}, ziarno: {seed}\n")
        report = simulate(game, args.method, args.prng, args.simulate, seed)
        print(format_report(report))
        return 0

    rng = make_rng(args.prng, seed)
    print(f"Gra:       {game.name}")
    print(f"Metoda:    {METHODS[args.method]}")
    print(f"Generator: {PRNGS[args.prng]}")
    print(f"Ziarno:    {seed if args.prng != 'sys' else '(nie dotyczy)'}")
    print(f"Data:      {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("-" * 60)
    for i in range(1, args.count + 1):
        result = draw(game, rng, args.method)
        extra = f"  (wygenerowano {result.attempts} kandydatów)" if args.method == "reject" else ""
        print(f"Zakład {i:>2}: {format_numbers(result.numbers)}{extra}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generator liczb do gier liczbowych (Lotto, Mini Lotto, Multi Multi).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-g", "--game", choices=GAMES, default="lotto", help="gra liczbowa")
    parser.add_argument("-m", "--method", choices=METHODS, default="reject", help="metoda losowania")
    parser.add_argument("-p", "--prng", choices=PRNGS, default="mt", help="generator liczb pseudolosowych")
    parser.add_argument("-n", "--count", type=int, default=1, help="liczba zakładów (losowań)")
    parser.add_argument("-s", "--seed", type=int, default=None, help="ziarno (powtarzalność wyników)")
    parser.add_argument("--simulate", type=int, metavar="N", help="symulacja Monte Carlo z N losowań")
    parser.add_argument("--gui", action="store_true", help="uruchom aplikację okienkową")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


# --------------------------------------------------------------------------- #
#  Aplikacja okienkowa (Tkinter)
# --------------------------------------------------------------------------- #
def launch_gui() -> None:
    import tkinter as tk
    from tkinter import ttk

    root = tk.Tk()
    root.title("Generator liczb - gry liczbowe")
    root.geometry("760x640")
    root.minsize(640, 520)

    game_names = {g.name: k for k, g in GAMES.items()}
    method_names = {v: k for k, v in METHODS.items()}
    prng_names = {v: k for k, v in PRNGS.items()}

    controls = ttk.LabelFrame(root, text="Ustawienia", padding=10)
    controls.pack(fill="x", padx=10, pady=(10, 5))

    def add_combo(row: int, label: str, values: List[str]) -> ttk.Combobox:
        ttk.Label(controls, text=label).grid(row=row, column=0, sticky="w", pady=2)
        box = ttk.Combobox(controls, values=values, state="readonly", width=42)
        box.current(0)
        box.grid(row=row, column=1, sticky="w", padx=8, pady=2)
        return box

    game_box = add_combo(0, "Gra:", list(game_names))
    method_box = add_combo(1, "Metoda:", list(method_names))
    prng_box = add_combo(2, "Generator:", list(prng_names))

    ttk.Label(controls, text="Liczba zakładów:").grid(row=3, column=0, sticky="w", pady=2)
    count_var = tk.IntVar(value=5)
    ttk.Spinbox(controls, from_=1, to=50, textvariable=count_var, width=6).grid(
        row=3, column=1, sticky="w", padx=8, pady=2
    )
    ttk.Label(controls, text="Ziarno (puste = losowe):").grid(row=4, column=0, sticky="w", pady=2)
    seed_var = tk.StringVar()
    ttk.Entry(controls, textvariable=seed_var, width=14).grid(row=4, column=1, sticky="w", padx=8, pady=2)

    # --- obszar wyników ---
    holder = ttk.Frame(root)
    holder.pack(fill="both", expand=True, padx=10, pady=5)
    canvas = tk.Canvas(holder, background="white", highlightthickness=1, highlightbackground="#bbb")
    scrollbar = ttk.Scrollbar(holder, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    status = tk.StringVar(value="Wybierz ustawienia i kliknij „Losuj”.")
    ttk.Label(root, textvariable=status, anchor="w").pack(fill="x", padx=10, pady=(0, 8))

    def parse_seed() -> int:
        text = seed_var.get().strip()
        return int(text) if text else secrets.randbits(32)

    def show_error(msg: str) -> None:
        status.set(msg)

    def do_draw() -> None:
        try:
            seed = parse_seed()
            count = max(1, int(count_var.get()))
        except ValueError:
            show_error("Ziarno musi być liczbą całkowitą.")
            return
        game = GAMES[game_names[game_box.get()]]
        method = method_names[method_box.get()]
        prng = prng_names[prng_box.get()]
        rng = make_rng(prng, seed)

        canvas.delete("all")
        d, gap, per_row = 34, 6, 10
        y = 12
        for i in range(1, count + 1):
            numbers = draw(game, rng, method).numbers
            canvas.create_text(12, y + d / 2, text=f"{i}.", anchor="w", font=("Helvetica", 11, "bold"))
            for idx, n in enumerate(numbers):
                row, col = divmod(idx, per_row)
                x = 48 + col * (d + gap)
                yy = y + row * (d + gap)
                canvas.create_oval(x, yy, x + d, yy + d, fill="#ffd54f", outline="#f9a825", width=2)
                canvas.create_text(x + d / 2, yy + d / 2, text=str(n), font=("Helvetica", 11, "bold"))
            rows = (len(numbers) + per_row - 1) // per_row
            y += rows * (d + gap) + 10
        canvas.configure(scrollregion=(0, 0, 600, y))
        status.set(
            f"{game.name} | {METHODS[method]} | {PRNGS[prng]} | "
            f"ziarno: {seed if prng != 'sys' else 'n/d'} | {datetime.now():%H:%M:%S}"
        )

    def do_simulate() -> None:
        try:
            seed = parse_seed()
        except ValueError:
            show_error("Ziarno musi być liczbą całkowitą.")
            return
        game = GAMES[game_names[game_box.get()]]
        status.set("Trwa symulacja Monte Carlo (100 000 losowań)...")
        root.update_idletasks()
        report = simulate(game, method_names[method_box.get()], prng_names[prng_box.get()], 100_000, seed)
        win = tk.Toplevel(root)
        win.title("Symulacja Monte Carlo")
        text = tk.Text(win, width=78, height=22, font=("Courier", 10))
        text.insert("1.0", format_report(report))
        text.configure(state="disabled")
        text.pack(padx=10, pady=10)
        status.set("Symulacja zakończona.")

    buttons = ttk.Frame(controls)
    buttons.grid(row=5, column=0, columnspan=2, sticky="w", pady=(10, 0))
    ttk.Button(buttons, text="Losuj", command=do_draw).pack(side="left")
    ttk.Button(buttons, text="Symulacja Monte Carlo", command=do_simulate).pack(side="left", padx=8)

    do_draw()
    root.mainloop()


# --------------------------------------------------------------------------- #
def main(argv: List[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # polskie znaki w konsoli Windows
    args = build_parser().parse_args(argv)
    if args.count < 1:
        print("Liczba zakładów musi być dodatnia.", file=sys.stderr)
        return 2
    if args.gui:
        launch_gui()
        return 0
    return run_cli(args)


if __name__ == "__main__":
    sys.exit(main())
