import os
from typing import Optional
from game import Game, GameState
from betting import BettingAction
from ai import AIPlayer as AILogic


class CLI:
    def __init__(self):
        self.game: Optional[Game] = None
        self.ai_logic: Optional[AILogic] = None

    def clear_screen(self):
        """Clear the terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')

    def display_game_state(self):
        """Display the current game state"""
        if self.game is None:
            return

        print("\n" + "=" * 60)
        print(f"Hand #{self.game.hand_number}")
        print("=" * 60)

        # Display player information
        hp = self.game.human_player
        ap = self.game.ai_player
        print(f"\n{hp.name}: {hp.chips} chips")
        print(f"{ap.name}: {ap.chips} chips")
        pot = (self.game.current_betting_round.pot
               if self.game.current_betting_round else 0)
        print(f"Pot: {pot} chips")

        # Display community cards
        if self.game.community_cards:
            cards = ' '.join(str(c) for c in self.game.community_cards)
            print(f"\nCommunity Cards: {cards}")
        else:
            print("\nCommunity Cards: (none yet)")

        # Display player's hole cards
        cards = ' '.join(str(c) for c in self.game.human_player.hole_cards)
        print(f"\nYour Cards: {cards}")

        # Display current betting round info
        if self.game.current_betting_round:
            current_bet = self.game.current_betting_round.current_bet
            br = self.game.current_betting_round
            human_contribution = br.player_contributions[0]
            amount_to_call = br.get_amount_to_call(0)

            print(f"\nCurrent Bet: {current_bet}")
            print(f"Your Contribution: {human_contribution}")
            if amount_to_call > 0:
                print(f"Amount to Call: {amount_to_call}")
            else:
                print("You can check")

    def get_player_action(self) -> tuple[BettingAction, Optional[int]]:
        """Get betting action from human player"""
        if self.game is None or self.game.current_betting_round is None:
            return BettingAction.FOLD, None

        amount_to_call = self.game.current_betting_round.get_amount_to_call(0)
        current_bet = self.game.current_betting_round.current_bet
        min_raise = (
            current_bet * 2 if current_bet > 0 else self.game.big_blind * 2
        )
        player_chips = self.game.human_player.chips

        print("\n" + "-" * 60)
        print("Your Action:")

        if amount_to_call == 0:
            print("  [c]heck")
            print("  [r]aise <amount>")
        else:
            print("  [f]old")
            print(f"  [c]all ({amount_to_call} chips)")
            print("  [r]aise <amount>")

        if player_chips > 0:
            print("  [a]ll-in")

        while True:
            try:
                choice = input("\nEnter your action: ").strip().lower()

                if choice == 'f' or choice == 'fold':
                    return BettingAction.FOLD, None

                elif choice == 'c' or choice == 'call' or choice == 'check':
                    if amount_to_call == 0:
                        return BettingAction.CHECK, None
                    else:
                        return BettingAction.CALL, None

                elif choice.startswith('r') or choice.startswith('raise'):
                    # Parse raise amount
                    parts = choice.split()
                    if len(parts) > 1:
                        raise_amount = int(parts[1])
                    else:
                        raise_amount = int(input("Enter raise amount: "))

                    if raise_amount < min_raise:
                        print(f"Minimum raise is {min_raise}")
                        continue

                    br = self.game.current_betting_round
                    contrib = br.player_contributions[0]
                    max_raise = player_chips + contrib
                    if raise_amount > max_raise:
                        print("Insufficient chips")
                        continue

                    return BettingAction.RAISE, raise_amount

                elif choice == 'a' or choice == 'all-in':
                    if player_chips == 0:
                        print("You're already all-in")
                        continue
                    return BettingAction.ALL_IN, None

                else:
                    print("Invalid action. Please try again.")

            except ValueError:
                print("Invalid input. Please enter a number for raise amount.")
            except KeyboardInterrupt:
                print("\n\nGame interrupted.")
                return BettingAction.FOLD, None

    def display_action(
        self, player_name: str, action: BettingAction,
        amount: Optional[int] = None
    ):
        """Display a player's action"""
        action_str = {
            BettingAction.FOLD: "folds",
            BettingAction.CHECK: "checks",
            BettingAction.CALL: "calls",
            BettingAction.RAISE: f"raises to {amount}",
            BettingAction.ALL_IN: "goes all-in"
        }
        print(f"\n{player_name} {action_str[action]}")

    def display_winner(self):
        """Display winner information"""
        if self.game is None:
            return

        winner_info = self.game.get_winner_info()
        if winner_info is None:
            return

        print("\n" + "=" * 60)
        print("HAND RESULT")
        print("=" * 60)

        if winner_info["reason"] == "Showdown":
            hp = self.game.human_player
            print(f"\n{hp.name}: {winner_info['human_hand']}")
            print(f"{self.game.ai_player.name}: {winner_info['ai_hand']}")
            print(f"\nWinner: {winner_info['winner']}")
        else:
            print(f"\n{winner_info['reason']}")
            print(f"Winner: {winner_info['winner']}")

        hp = self.game.human_player
        ap = self.game.ai_player
        print(f"\n{hp.name}: {hp.chips} chips")
        print(f"{ap.name}: {ap.chips} chips")

    def run(self):
        """Main game loop"""
        print("Welcome to Texas Hold'em Poker!")
        print("You'll be playing against an AI opponent.")

        # Initialize game
        self.game = Game(starting_chips=1000, small_blind=10)
        self.ai_logic = AILogic(self.game.ai_player, difficulty="medium")

        while not self.game.is_game_over():
            # Start new hand
            self.game.start_new_hand()

            # Main hand loop
            while self.game.state != GameState.GAME_OVER:
                # Check if betting round is complete
                br = self.game.current_betting_round
                if br and br.round_complete:
                    # Round complete, will advance on next iteration
                    continue

                self.clear_screen()
                self.display_game_state()

                # Determine whose turn it is
                # Check who needs to act
                betting_round = self.game.current_betting_round
                human_acted = betting_round.players_acted[0]
                ai_acted = betting_round.players_acted[1]
                human_contribution = betting_round.player_contributions[0]
                ai_contribution = betting_round.player_contributions[1]
                current_bet = betting_round.current_bet

                # Determine who acts:
                # If neither has acted, first to act (after dealer) goes
                # If one has acted, the other goes
                # Both acted, contributions match - round complete
                if not human_acted and not ai_acted:
                    # Neither has acted - first to act is player after dealer
                    active_index = self.game.get_active_player_index()
                elif not human_acted:
                    # Human hasn't acted
                    active_index = 0
                elif not ai_acted:
                    # AI hasn't acted
                    active_index = 1
                else:
                    # Both acted - check if someone raised
                    if human_contribution < ai_contribution:
                        active_index = 0
                    elif ai_contribution < human_contribution:
                        active_index = 1
                    elif (current_bet > 0 and
                          betting_round.last_to_act is not None):
                        # Someone raised - the other player needs to respond
                        if betting_round.last_to_act == 0:
                            # Human raised, AI needs to respond
                            active_index = 1
                        else:
                            # AI raised, human needs to respond
                            active_index = 0
                    else:
                        # Should be complete - if not, there's a bug
                        # But try to continue by checking who needs to match
                        human_short = (
                            current_bet > 0
                            and human_contribution < current_bet
                        )
                        if human_short:
                            active_index = 0
                        elif current_bet > 0 and ai_contribution < current_bet:
                            active_index = 1
                        else:
                            # Round should be complete - skip
                            continue

                if active_index == 0:  # Human player
                    hp = self.game.human_player
                    if hp.folded or hp.all_in:
                        # Skip if folded or all-in
                        continue

                    action, amount = self.get_player_action()
                    success, message = self.game.process_betting_action(
                        0, action, amount
                    )

                    if not success:
                        print(f"Error: {message}")
                        input("Press Enter to continue...")
                        continue

                    self.display_action(
                        self.game.human_player.name, action, amount
                    )

                    # Small delay for readability
                    import time
                    time.sleep(0.5)

                else:  # AI player
                    ap = self.game.ai_player
                    if ap.folded or ap.all_in:
                        # Skip if folded or all-in
                        continue

                    print(f"\n{self.game.ai_player.name} is thinking...")
                    import time
                    time.sleep(1)  # Brief pause for realism

                    # Get AI action
                    br = self.game.current_betting_round
                    amount_to_call = br.get_amount_to_call(1)
                    current_bet = br.current_bet
                    min_raise = (
                        current_bet * 2
                        if current_bet > 0
                        else self.game.big_blind * 2
                    )

                    action, amount = self.ai_logic.get_action(
                        amount_to_call,
                        current_bet,
                        min_raise,
                        self.game.community_cards,
                        self.game.current_betting_round.pot
                    )

                    success, message = self.game.process_betting_action(
                        1, action, amount
                    )

                    if success:
                        self.display_action(
                            self.game.ai_player.name, action, amount
                        )
                    else:
                        print(f"AI action error: {message}")

                    # Small delay for readability
                    time.sleep(0.5)

            # Hand over - pot distributed by _determine_winner()
            self.clear_screen()
            # Display winner (updated chip counts)
            self.display_winner()
            # Then show final game state
            self.display_game_state()

            # Check if game is over
            if self.game.is_game_over():
                # Winner: more chips, or other if one has 0
                if self.game.human_player.chips > self.game.ai_player.chips:
                    winner = self.game.human_player
                elif self.game.ai_player.chips > self.game.human_player.chips:
                    winner = self.game.ai_player
                else:
                    # Equal chips (shouldn't happen, but handle it)
                    hp = self.game.human_player
                    ap = self.game.ai_player
                    winner = hp if hp.chips > 0 else ap
                print(f"\n{'=' * 60}")
                print(f"GAME OVER! {winner.name} wins!")
                print(f"{'=' * 60}")
                break

            # Ask to play another hand
            while True:
                prompt = "\nPlay another hand? (y/n): "
                play_again = input(prompt).strip().lower()
                if play_again == 'y' or play_again == 'yes':
                    break
                elif play_again == 'n' or play_again == 'no':
                    print("\nThanks for playing!")
                    return
                else:
                    print("Please enter 'y' or 'n'")

        print("\nThanks for playing!")
