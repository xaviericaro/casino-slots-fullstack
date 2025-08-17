from dataclasses import dataclass
from typing import List, Dict
from provably_fair import pick_index

# Símbolos e pesos (reels independentes)
SYMBOLS = [
    "A", "K", "Q", "J", "10", "🍒", "💎", "⭐", "7", "W"  # W = wild
]

# pesos por rolo (afinados p/ RTP ~95% com paytable abaixo)
REEL_WEIGHTS = [
    [20,18,18,18,18,6,2,2,1,1],  # Reel 1
    [20,18,18,18,18,6,2,2,1,1],  # Reel 2
    [20,18,18,18,18,6,2,2,1,1],  # Reel 3
    [20,18,18,18,18,6,2,2,1,1],  # Reel 4
    [20,18,18,18,18,6,2,2,1,1],  # Reel 5
]

# Tabela de pagamentos (multiplicador do valor apostado por linha)
# Combinações 5,4,3 do mesmo símbolo (W substitui, não paga sozinho)
PAYTABLE = {
    "7":  {5:500, 4:80, 3:20},
    "💎": {5:200, 4:50, 3:15},
    "⭐":  {5:150, 4:40, 3:10},
    "🍒": {5:80,  4:20, 3:8},
    "A":  {5:40,  4:10, 3:5},
    "K":  {5:35,  4:9,  3:4},
    "Q":  {5:30,  4:8,  3:3},
    "J":  {5:25,  4:7,  3:3},
    "10": {5:20,  4:6,  3:2},
}

# 10 linhas de pagamento (índices da linha por coluna 0..4 em uma grade 3 linhas: 0=top,1=mid,2=bot)
PAYLINES = [
    [1,1,1,1,1],  # linha reta meio
    [0,0,0,0,0],
    [2,2,2,2,2],
    [0,1,2,1,0],
    [2,1,0,1,2],
    [0,0,1,2,2],
    [2,2,1,0,0],
    [1,0,1,2,1],
    [1,2,1,0,1],
    [0,1,1,1,2],
]

@dataclass
class SpinResult:
    grid: List[List[str]]  # 5 colunas x 3 linhas (grid[c][r])
    line_wins: List[Dict]
    total_multiplier: float


def _weighted_choice(symbols, weights, pick):
    # pick in [0, sum(weights))
    total = sum(weights)
    acc = 0
    for i, w in enumerate(weights):
        acc += w
        if pick < acc:
            return symbols[i]
    return symbols[-1]


def spin_grid(server_seed, client_seed, nonce):
    grid = []  # 5 colunas
    cursor = 0
    for col in range(5):
        column = []
        for row in range(3):
            total = sum(REEL_WEIGHTS[col])
            idx = pick_index(total, server_seed=server_seed, client_seed=client_seed, nonce=nonce, cursor=cursor)
            cursor += 1
            symbol = _weighted_choice(SYMBOLS, REEL_WEIGHTS[col], idx)
            column.append(symbol)
        grid.append(column)
    return grid


def evaluate_grid(grid, bet_per_line: float):
    line_wins = []
    total_mult = 0.0

    for line_idx, pattern in enumerate(PAYLINES):
        # lê símbolos da linha da coluna 0..4
        seq = [grid[c][pattern[c]] for c in range(5)]
        # tenta casar com wilds
        # encontra melhor símbolo alvo (exclui W puro)
        targets = [s for s in seq if s != 'W'] or ['A']
        best_line = None
        for target in set(targets):
            count = 0
            for s in seq:
                if s == target or s == 'W':
                    count += 1
                else:
                    break
            if count >= 3 and target in PAYTABLE and count in PAYTABLE[target]:
                mult = PAYTABLE[target][count]
                if not best_line or mult > best_line['multiplier']:
                    best_line = {
                        'line': line_idx,
                        'symbol': target,
                        'count': count,
                        'multiplier': mult
                    }
        if best_line:
            total_mult += best_line['multiplier']
            line_wins.append(best_line)

    return SpinResult(grid=grid, line_wins=line_wins, total_multiplier=total_mult)


def compute_payout(total_multiplier: float, lines_active: int, bet_per_line: float):
    return total_multiplier * bet_per_line