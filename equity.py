try:
    import eval7
except ImportError:
    eval7 = None
import random
from typing import List

def calculate_equity(hero_cards_str: str, opponent_hands_str: List[str], iterations: int = 5000) -> float:
    """
    Рассчитывает префлоп-эквити для руки Hero против одной или нескольких рук оппонентов
    методом Монте-Карло через eval7.
    hero_cards_str – например "AcKc" (4 символа).
    opponent_hands_str – список строк, каждая по 4 символа, например ["7d2s"].
    """
    if eval7 is None:
        print("Warning: eval7 not installed. Returning placeholder equity 0.5")
        return 0.5

    hero_cards = [eval7.Card(hero_cards_str[0:2]), eval7.Card(hero_cards_str[2:4])]
    villain_cards_list = []
    for hand_str in opponent_hands_str:
        try:
            villain_cards_list.append([eval7.Card(hand_str[0:2]), eval7.Card(hand_str[2:4])])
        except ValueError:
            raise ValueError(f"Invalid hand format: '{hand_str}'. Expected 4 chars like 'AcKc'.")

    all_known = hero_cards.copy()
    for vc in villain_cards_list:
        all_known.extend(vc)

    # Проверка на дубликаты карт
    if len(set(str(c) for c in all_known)) != len(all_known):
        raise ValueError(f"Duplicate cards detected: {hero_cards_str} vs {opponent_hands_str}")

    hero_wins = 0
    hero_ties = 0
    for _ in range(iterations):
        deck = eval7.Deck()
        for c in all_known:
            deck.cards.remove(c)
        deck.shuffle()
        board = deck.deal(5)

        hero_score = eval7.evaluate(hero_cards + board)
        best_villain_score = max(eval7.evaluate(v + board) for v in villain_cards_list)

        if hero_score > best_villain_score:
            hero_wins += 1
        elif hero_score == best_villain_score:
            hero_ties += 1

    return (hero_wins + hero_ties / 2) / iterations