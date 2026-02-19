from typing import List, Optional, Tuple
from enum import Enum
from card import Deck, Card
from player import Player, HumanPlayer, AIPlayer
from betting import BettingRound, BettingAction
from handEvaluator import HandEvaluator


class GameState(Enum):
    PRE_FLOP = "pre_flop"
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"
    SHOWDOWN = "showdown"
    GAME_OVER = "game_over"


class Game:
    def __init__(self, human_name: str = "Player", ai_name: str = "AI", 
                 starting_chips: int = 1000, small_blind: int = 10):
        self.deck = Deck()
        self.players: List[Player] = [
            HumanPlayer(human_name, starting_chips),
            AIPlayer(ai_name, starting_chips)
        ]
        self.human_player = self.players[0]
        self.ai_player = self.players[1]
        self.ai = None  # Will be set when AI module is imported
        
        self.small_blind = small_blind
        self.big_blind = small_blind * 2
        self.dealer_index = 0  # Rotates each hand
        
        self.community_cards: List[Card] = []
        self.current_betting_round: Optional[BettingRound] = None
        self.state = GameState.GAME_OVER
        
        self.hand_number = 0

    def start_new_hand(self):
        """Start a new hand"""
        self.hand_number += 1
        self.deck.reset()
        self.community_cards = []
        
        # Reset players
        for player in self.players:
            player.reset_for_new_hand()
        
        # Rotate dealer
        self.dealer_index = (self.dealer_index + 1) % 2
        
        # Deal hole cards
        for player in self.players:
            player.deal_cards(self.deck.deal(2))
        
        # Start pre-flop betting
        self.state = GameState.PRE_FLOP
        self.current_betting_round = BettingRound(
            self.small_blind, self.big_blind
        )
        
        # Post blinds
        stacks = [p.chips for p in self.players]
        self.current_betting_round.post_blinds(stacks, self.dealer_index)
        self.players[0].chips = stacks[0]
        self.players[1].chips = stacks[1]

    def deal_flop(self):
        """Deal the flop (3 community cards)"""
        if self.state != GameState.PRE_FLOP:
            raise ValueError("Cannot deal flop - not in pre-flop state")
        
        # Burn a card
        self.deck.deal(1)
        # Deal flop
        self.community_cards = self.deck.deal(3)
        self.state = GameState.FLOP
        
        # Carry over pot and player states to new betting round
        previous_pot = (
            self.current_betting_round.pot if self.current_betting_round else 0
        )
        self.current_betting_round = BettingRound(
            self.small_blind, self.big_blind
        )
        self.current_betting_round.pot = previous_pot
        # Sync player states
        self.current_betting_round.folded = [p.folded for p in self.players]
        self.current_betting_round.all_in = [p.all_in for p in self.players]

    def deal_turn(self):
        """Deal the turn (1 community card)"""
        if self.state != GameState.FLOP:
            raise ValueError("Cannot deal turn - not in flop state")
        
        # Burn a card
        self.deck.deal(1)
        # Deal turn
        self.community_cards.append(self.deck.deal(1)[0])
        self.state = GameState.TURN
        
        # Carry over pot and player states to new betting round
        previous_pot = (
            self.current_betting_round.pot if self.current_betting_round else 0
        )
        self.current_betting_round = BettingRound(
            self.small_blind, self.big_blind
        )
        self.current_betting_round.pot = previous_pot
        # Sync player states
        self.current_betting_round.folded = [p.folded for p in self.players]
        self.current_betting_round.all_in = [p.all_in for p in self.players]

    def deal_river(self):
        """Deal the river (1 community card)"""
        if self.state != GameState.TURN:
            raise ValueError("Cannot deal river - not in turn state")
        
        # Burn a card
        self.deck.deal(1)
        # Deal river
        self.community_cards.append(self.deck.deal(1)[0])
        self.state = GameState.RIVER
        
        # Carry over pot and player states to new betting round
        previous_pot = (
            self.current_betting_round.pot if self.current_betting_round else 0
        )
        self.current_betting_round = BettingRound(
            self.small_blind, self.big_blind
        )
        self.current_betting_round.pot = previous_pot
        # Sync player states
        self.current_betting_round.folded = [p.folded for p in self.players]
        self.current_betting_round.all_in = [p.all_in for p in self.players]

    def process_betting_action(
        self, player_index: int, action: BettingAction,
        amount: Optional[int] = None
    ) -> Tuple[bool, str]:
        """
        Process a betting action.
        Returns: (success, message)
        """
        if self.current_betting_round is None:
            return False, "No active betting round"
        
        player = self.players[player_index]
        current_stack = self.players[player_index].chips
        other_index = 1 - player_index
        other_stack = self.players[other_index].chips
        
        success, message, new_stack = self.current_betting_round.make_action(
            player_index, action, amount, current_stack, other_stack
        )
        
        if success:
            # Update player's chips with new stack value from make_action
            self.players[player_index].chips = new_stack
            
            # Update player state - sync with betting round state
            if action == BettingAction.FOLD:
                player.fold()
            if self.current_betting_round.all_in[player_index]:
                player.all_in = True
            else:
                player.all_in = False
            
            # Check if betting round is complete
            if self.current_betting_round.round_complete:
                self._advance_game_state()
        
        return success, message

    def _deal_remaining_cards(self):
        """Deal remaining community cards when both players are all-in"""
        if self.state == GameState.PRE_FLOP:
            # Burn and deal flop
            self.deck.deal(1)
            self.community_cards = self.deck.deal(3)
            # Burn and deal turn
            self.deck.deal(1)
            self.community_cards.append(self.deck.deal(1)[0])
            # Burn and deal river
            self.deck.deal(1)
            self.community_cards.append(self.deck.deal(1)[0])
        elif self.state == GameState.FLOP:
            # Burn and deal turn
            self.deck.deal(1)
            self.community_cards.append(self.deck.deal(1)[0])
            # Burn and deal river
            self.deck.deal(1)
            self.community_cards.append(self.deck.deal(1)[0])
        elif self.state == GameState.TURN:
            # Burn and deal river
            self.deck.deal(1)
            self.community_cards.append(self.deck.deal(1)[0])

    def _advance_game_state(self):
        """Advance to the next game state after betting round completes"""
        if any(self.current_betting_round.folded):
            # Someone folded, game over - determine winner and distribute pot
            self.state = GameState.GAME_OVER
            self._determine_winner()
            return
        
        # If both players are all-in, skip to showdown immediately
        # Check both betting round state and player state to be safe
        both_all_in = (all(self.current_betting_round.all_in) or
                       (self.players[0].all_in and
                        self.players[1].all_in))
        if both_all_in:
            # Both all-in - deal remaining community cards and go to showdown
            try:
                self._deal_remaining_cards()
            except (ValueError, IndexError):
                # If dealing cards fails (e.g., deck issue), just proceed
                # to showdown with whatever cards we have
                pass
            self.state = GameState.SHOWDOWN
            self._determine_winner()
            return
        
        # If one player is all-in (but not both), skip betting rounds
        # and deal remaining cards, then go to showdown
        one_all_in = (any(self.current_betting_round.all_in) and
                     not all(self.current_betting_round.all_in))
        if one_all_in:
            # One player is all-in - deal remaining cards and go to showdown
            try:
                self._deal_remaining_cards()
            except (ValueError, IndexError):
                # If dealing cards fails, just proceed to showdown
                pass
            self.state = GameState.SHOWDOWN
            self._determine_winner()
            return
        
        if self.state == GameState.PRE_FLOP:
            self.deal_flop()
        elif self.state == GameState.FLOP:
            self.deal_turn()
        elif self.state == GameState.TURN:
            self.deal_river()
        elif self.state == GameState.RIVER:
            self.state = GameState.SHOWDOWN
            self._determine_winner()

    def _determine_winner(self):
        """Determine the winner and distribute the pot"""
        self.state = GameState.GAME_OVER
        
        # Get the pot amount before distribution
        pot_amount = (
            self.current_betting_round.pot
            if self.current_betting_round else 0
        )
        
        # If someone folded, they lose
        if self.human_player.folded:
            self.ai_player.chips += pot_amount
            if self.current_betting_round:
                self.current_betting_round.pot = 0
            return
        if self.ai_player.folded:
            self.human_player.chips += pot_amount
            if self.current_betting_round:
                self.current_betting_round.pot = 0
            return
        
        # Showdown - compare hands
        human_hand = self.human_player.hole_cards + self.community_cards
        ai_hand = self.ai_player.hole_cards + self.community_cards
        
        result = HandEvaluator.compare_hands(human_hand, ai_hand)
        
        if result > 0:
            # Human wins
            self.human_player.chips += pot_amount
        elif result < 0:
            # AI wins
            self.ai_player.chips += pot_amount
        else:
            # Tie - split pot
            split = pot_amount // 2
            self.human_player.chips += split
            self.ai_player.chips += split
            if pot_amount % 2 == 1:
                # Odd chip goes to dealer
                dealer = self.players[self.dealer_index]
                dealer.chips += 1
        
        # Clear the pot after distribution
        if self.current_betting_round:
            self.current_betting_round.pot = 0

    def get_winner_info(self) -> Optional[dict]:
        """Get information about the winner of the last hand"""
        if self.state != GameState.GAME_OVER:
            return None
        
        if self.human_player.folded:
            return {
                "winner": self.ai_player.name,
                "reason": "Player folded"
            }
        if self.ai_player.folded:
            return {
                "winner": self.human_player.name,
                "reason": "AI folded"
            }
        
        # Showdown
        human_hand = self.human_player.hole_cards + self.community_cards
        ai_hand = self.ai_player.hole_cards + self.community_cards
        
        human_rank, _ = HandEvaluator.evaluate_hand(human_hand)
        ai_rank, _ = HandEvaluator.evaluate_hand(ai_hand)
        
        result = HandEvaluator.compare_hands(human_hand, ai_hand)
        
        if result > 0:
            return {
                "winner": self.human_player.name,
                "reason": "Showdown",
                "human_hand": HandEvaluator.get_hand_name(human_rank),
                "ai_hand": HandEvaluator.get_hand_name(ai_rank)
            }
        elif result < 0:
            return {
                "winner": self.ai_player.name,
                "reason": "Showdown",
                "human_hand": HandEvaluator.get_hand_name(human_rank),
                "ai_hand": HandEvaluator.get_hand_name(ai_rank)
            }
        else:
            return {
                "winner": "Tie",
                "reason": "Showdown - Split pot",
                "human_hand": HandEvaluator.get_hand_name(human_rank),
                "ai_hand": HandEvaluator.get_hand_name(ai_rank)
            }

    def is_game_over(self) -> bool:
        """Check if game is over (a player is out of chips)"""
        return any(player.chips <= 0 for player in self.players)

    def get_active_player_index(self) -> int:
        """Get the index of the player who should act next"""
        if self.current_betting_round is None:
            return 0
        
        # In pre-flop, small blind acts first (after big blind)
        # In other rounds, player after dealer acts first
        if self.state == GameState.PRE_FLOP:
            # Big blind has already acted, small blind acts first
            return (self.dealer_index + 1) % 2
        else:
            # Player after dealer acts first
            return (self.dealer_index + 1) % 2

