from typing import List, Optional
from card import Card
from betting import BettingAction


class Player:
    def __init__(self, name: str, chips: int):
        self.name = name
        self.chips = chips
        self.hole_cards: List[Card] = []
        self.folded = False
        self.all_in = False

    def deal_cards(self, cards: List[Card]):
        """Deal hole cards to the player"""
        self.hole_cards = cards

    def clear_cards(self):
        """Clear hole cards"""
        self.hole_cards = []

    def fold(self):
        """Fold the hand"""
        self.folded = True

    def reset_for_new_hand(self):
        """Reset player state for a new hand"""
        self.folded = False
        self.all_in = False
        self.clear_cards()

    def __str__(self):
        return f"{self.name} ({self.chips} chips)"


class HumanPlayer(Player):
    def __init__(self, name: str, chips: int):
        super().__init__(name, chips)

    def get_action(
        self, amount_to_call: int, current_bet: int,
        min_raise: int, community_cards: List[Card]
    ) -> tuple[BettingAction, Optional[int]]:
        """
        Get action from human player via CLI.
        This will be handled by the CLI interface, so this is a placeholder.
        """
        # This method will be called by the game, but actual input
        # will be handled in the CLI module
        pass


class AIPlayer(Player):
    def __init__(self, name: str, chips: int):
        super().__init__(name, chips)

    def get_action(
        self, amount_to_call: int, current_bet: int,
        min_raise: int, community_cards: List[Card],
        pot_size: int
    ) -> tuple[BettingAction, Optional[int]]:
        """
        Get action from AI player.
        This will be implemented in the ai.py module.
        """
        # This will be implemented by the AI module
        pass
