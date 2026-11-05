# 🎰 Generator liczb do gier liczbowych

🇬🇧 [English version](README.en.md)

Program w języku **Python 3** losujący liczby w popularnych grach liczbowych (**Lotto 6/49**, **Mini Lotto 5/42**, **Multi Multi 20/80**) z użyciem generatora liczb pseudolosowych. **Liczby w jednym losowaniu nigdy się nie powtarzają.**

Projekt powstał jako ćwiczenie laboratoryjne *„Generowanie liczb w grach liczbowych”* (metody Monte Carlo, generatory liczb pseudolosowych).

![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)
![Tests](https://img.shields.io/badge/tests-unittest-success)

## Funkcje

- 🎲 trzy gry: Lotto (6 z 49), Mini Lotto (5 z 42), Multi Multi (20 z 80),
- 🧮 dwie metody losowania:
  - **Monte Carlo z odrzucaniem powtórzeń** (rejection sampling) – losujemy z rozkładu równomiernego i odrzucamy liczby, które już wypadły,
  - **tasowanie Fishera-Yatesa** (wariant Durstenfelda),
- 🔧 trzy generatory liczb pseudolosowych:
  - **Mersenne Twister** (`random.Random`),
  - **własna implementacja LCG** (generator kongruencji liniowej),
  - **SystemRandom** (entropia systemu operacyjnego),
- ✅ walidacja każdego losowania (właściwa liczba wyników, zakres, brak powtórzeń),
- 📊 **symulacja Monte Carlo**: test chi-kwadrat równomierności rozkładu oraz porównanie oszacowanych prawdopodobieństw trafień z teoretycznymi (rozkład hipergeometryczny),
- 🔁 powtarzalność wyników dzięki ustawianiu ziarna (`--seed`),
- 🖥️ interfejs tekstowy (CLI) oraz aplikacja okienkowa (Tkinter).

## Wymagania

- Python **3.9+** (zalecany 3.10+),
- brak zewnętrznych bibliotek – tylko biblioteka standardowa,
- do trybu `--gui` potrzebny moduł `tkinter` (w Windows i macOS jest w standardowej instalacji; w Linuksie: `sudo apt install python3-tk`).

## Instalacja i uruchomienie

```bash
git clone https://github.com/<twoj-login>/<nazwa-repozytorium>.git
cd <nazwa-repozytorium>
python lotto.py
```

### Przykłady użycia

```bash
python lotto.py                            # jedno losowanie Lotto
python lotto.py -g mini -n 5               # 5 zakładów Mini Lotto
python lotto.py -g multi -m fisher         # Multi Multi, metoda Fishera-Yatesa
python lotto.py -p lcg --seed 2024 -n 3    # własny LCG, ziarno 2024 (powtarzalne)
python lotto.py --simulate 200000 --seed 42 # symulacja Monte Carlo, 200 000 losowań
python lotto.py --gui                      # aplikacja okienkowa
python lotto.py --help                     # pełna lista opcji
```

### Opcje

| Opcja | Opis | Wartości (domyślnie) |
|---|---|---|
| `-g`, `--game` | gra liczbowa | `lotto` · `mini` · `multi` (`lotto`) |
| `-m`, `--method` | metoda losowania | `reject` · `fisher` (`reject`) |
| `-p`, `--prng` | generator liczb pseudolosowych | `mt` · `lcg` · `sys` (`mt`) |
| `-n`, `--count` | liczba zakładów | liczba całkowita (`1`) |
| `-s`, `--seed` | ziarno generatora | liczba całkowita (losowe) |
| `--simulate N` | symulacja Monte Carlo z N losowań | liczba całkowita |
| `--gui` | uruchom aplikację okienkową | – |

### Przykładowe wyjście

```text
$ python lotto.py -n 3 -s 42
Gra:       Lotto (6 z 49)
Metoda:    Monte Carlo z odrzucaniem powtórzeń
Generator: Mersenne Twister
Ziarno:    42
------------------------------------------------------------
Zakład  1: 02 11 14 32 34 37  (wygenerowano 6 kandydatów)
Zakład  2: 02 05 11 21 25 44  (wygenerowano 6 kandydatów)
Zakład  3: 02 10 11 27 29 32  (wygenerowano 6 kandydatów)
```

Symulacja Monte Carlo (`python lotto.py --simulate 200000 -s 42`):

```text
Test chi-kwadrat: chi2 = 38.66, df = 48, wartość krytyczna (alfa=0,05) = 65.17
Wniosek: brak podstaw do odrzucenia hipotezy o równomierności rozkładu.

Trafienia dla stałego kuponu {1..k}:
 trafień   obserwowane     oczekiwane       P obs.      P teor.
       0         86964        87193.0     0.434820     0.435965
       1         82842        82603.9     0.414210     0.413019
       2         26464        26475.6     0.132320     0.132378
       3          3538         3530.1     0.017690     0.017650
       ...
```

## Jak to działa?

### Monte Carlo z odrzucaniem
1. Wylosuj `u ∈ [0, 1)` z generatora PRNG i przekształć je w liczbę `n = 1 + ⌊u · N⌋`.
2. Jeżeli `n` już wypadła – **odrzuć** ją i losuj ponownie (warunek braku powtórzeń).
3. Powtarzaj, aż uzbierasz `k` różnych liczb; na końcu posortuj wynik.

Każdy zestaw `k` różnych liczb jest równie prawdopodobny, a liczba możliwych wyników to `C(N, k)`, np. `C(49, 6) = 13 983 816`.

### Tasowanie Fishera-Yatesa
Dla tablicy `1..N` wykonujemy `k` kroków: w kroku `i` zamieniamy element `i` z losowym elementem z zakresu `i..N-1`. Pierwsze `k` elementów to wynik. Metoda wykonuje stałą liczbę losowań (bez odrzuceń).

### Generator LCG
```
X(n+1) = (a · X(n) + c) mod m,   a = 1664525, c = 1013904223, m = 2^32
```
Prosty generator edukacyjny (parametry z *Numerical Recipes*). **Nie** nadaje się do zastosowań kryptograficznych ani do prawdziwych gier hazardowych.

### Test równomierności (chi-kwadrat)
Dla losowania `k` z `N` liczb każda liczba wypada z prawdopodobieństwem `p = k/N`. Statystyka

```
chi2 = Σ (O_i − E_i)² / ( n · p · (1 − p) · N/(N − 1) ),   df = N − 1
```

porównywana jest z wartością krytyczną rozkładu chi-kwadrat na poziomie istotności α = 0,05.

## Struktura repozytorium

```text
.
├── lotto.py        # program: generatory, metody losowania, symulacja, CLI i GUI
├── test_lotto.py   # testy jednostkowe (unittest)
├── README.md       # README po polsku
└── README.en.md    # README po angielsku
```

## Testy

```bash
python -m unittest -v
```

Testy sprawdzają m.in. brak powtórzeń i zakres liczb dla wszystkich gier, metod i generatorów, powtarzalność przy stałym ziarnie, poprawność LCG oraz rozkład hipergeometryczny.

## Zrzuty ekranu

<!-- Wstaw własne zrzuty ekranu, np.: -->
<!-- ![Aplikacja okienkowa](docs/gui.png) -->
<!-- ![Wyniki w terminalu](docs/cli.png) -->

## Literatura

1. D. E. Knuth, *The Art of Computer Programming, Vol. 2: Seminumerical Algorithms*, 3rd ed., Addison-Wesley, 1997.
2. N. Metropolis, S. Ulam, *The Monte Carlo Method*, Journal of the American Statistical Association, 44(247), 1949, s. 335–341.
3. M. Matsumoto, T. Nishimura, *Mersenne Twister: a 623-dimensionally equidistributed uniform pseudo-random number generator*, ACM Transactions on Modeling and Computer Simulation, 8(1), 1998, s. 3–30.
4. R. Durstenfeld, *Algorithm 235: Random permutation*, Communications of the ACM, 7(7), 1964, s. 420.
5. W. H. Press i in., *Numerical Recipes: The Art of Scientific Computing*, 3rd ed., Cambridge University Press, 2007.
6. Dokumentacja Pythona: moduł `random` – <https://docs.python.org/3/library/random.html>.

## Autor

**[Imię i nazwisko]** · nr albumu: **[nr albumu]** · [Uczelnia, wydział, kierunek] · rok akademicki [20XX/20XX]

## Licencja

Projekt edukacyjny. Dodaj plik `LICENSE` (np. MIT), jeśli chcesz udostępnić kod publicznie.
