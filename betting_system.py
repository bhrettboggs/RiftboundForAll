from typing import Optional, Dict, List
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class BetOutcome(Enum):
    """Enumeration of possible betting outcomes."""
    WIN = "win"
    LOSS = "loss"
    PUSH = "push"
    BLACKJACK = "blackjack"
    SURRENDER = "surrender"


class InsufficientChipsError(Exception):
    """Raised when player doesn't have enough chips for an action."""
    pass


class ChipManager:
    """
    Manages player's chip balance with encapsulation.
    Demonstrates ENCAPSULATION - private balance with controlled access.
    """
    
    def __init__(self, initial_balance: int = 1000):
        """
        Initialize chip manager with starting balance.
        
        Args:
            initial_balance: Starting chip amount (default 1000)
        """
        self.__balance = initial_balance  # Private attribute
        self.__total_wagered = 0
        self.__total_won = 0
        self.__total_lost = 0
        self.__largest_bet = 0
        self.__transaction_history: List[Dict] = []
    
    # Getter methods (controlled access to private data)
    def get_balance(self) -> int:
        """Returns current chip balance."""
        return self.__balance
    
    def get_total_wagered(self) -> int:
        """Returns total amount wagered across all bets."""
        return self.__total_wagered
    
    def get_total_won(self) -> int:
        """Returns total amount won."""
        return self.__total_won
    
    def get_total_lost(self) -> int:
        """Returns total amount lost."""
        return self.__total_lost
    
    def get_largest_bet(self) -> int:
        """Returns the largest single bet placed."""
        return self.__largest_bet
    
    def get_net_profit(self) -> int:
        """Calculates net profit/loss."""
        return self.__total_won - self.__total_lost
    
    def can_afford(self, amount: int) -> bool:
        """
        Checks if player can afford a bet.
        
        Args:
            amount: Bet amount to check
            
        Returns:
            True if player has sufficient balance
        """
        return self.__balance >= amount
    
    def deduct_chips(self, amount: int) -> bool:
        """
        Deducts chips from balance (placing a bet).
        
        Args:
            amount: Amount to deduct
            
        Returns:
            True if successful, False if insufficient funds
            
        Raises:
            InsufficientChipsError: If balance too low
        """
        if amount <= 0:
            raise ValueError("Bet amount must be positive")
        
        if not self.can_afford(amount):
            raise InsufficientChipsError(
                f"Insufficient chips. Balance: {self.__balance}, Required: {amount}"
            )
        
        self.__balance -= amount
        self.__total_wagered += amount
        
        if amount > self.__largest_bet:
            self.__largest_bet = amount
        
        self.__record_transaction("BET_PLACED", -amount, self.__balance)
        logger.info(f"Bet placed: {amount} chips. New balance: {self.__balance}")
        return True
    
    def add_chips(self, amount: int, reason: str = "WINNINGS"):
        """
        Adds chips to balance (winning a bet or buying chips).
        
        Args:
            amount: Amount to add
            reason: Reason for addition (e.g., 'WINNINGS', 'PURCHASE')
        """
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        self.__balance += amount
        
        if reason == "WINNINGS":
            self.__total_won += amount
        
        self.__record_transaction(reason, amount, self.__balance)
        logger.info(f"Chips added: {amount} ({reason}). New balance: {self.__balance}")
    
    def reset_balance(self, new_balance: int = 1000):
        """
        Resets balance to specified amount.
        
        Args:
            new_balance: New balance amount
        """
        self.__balance = new_balance
        self.__record_transaction("BALANCE_RESET", new_balance, new_balance)
        logger.info(f"Balance reset to {new_balance}")
    
    def __record_transaction(self, transaction_type: str, amount: int, 
                            balance_after: int):
        """
        Records a transaction in history (private method).
        
        Args:
            transaction_type: Type of transaction
            amount: Amount involved (positive or negative)
            balance_after: Balance after transaction
        """
        self.__transaction_history.append({
            'type': transaction_type,
            'amount': amount,
            'balance_after': balance_after
        })
    
    def get_transaction_history(self) -> List[Dict]:
        """Returns copy of transaction history."""
        return self.__transaction_history.copy()
    
    def to_dict(self) -> Dict:
        """Serializes chip manager state to dictionary."""
        return {
            'balance': self.__balance,
            'total_wagered': self.__total_wagered,
            'total_won': self.__total_won,
            'total_lost': self.__total_lost,
            'largest_bet': self.__largest_bet,
            'transaction_history': self.__transaction_history
        }
    
    def from_dict(self, data: Dict):
        """Loads chip manager state from dictionary."""
        self.__balance = data.get('balance', 1000)
        self.__total_wagered = data.get('total_wagered', 0)
        self.__total_won = data.get('total_won', 0)
        self.__total_lost = data.get('total_lost', 0)
        self.__largest_bet = data.get('largest_bet', 0)
        self.__transaction_history = data.get('transaction_history', [])


class Bet:
    """
    Represents a single bet in a blackjack game.
    Demonstrates ENCAPSULATION and state management.
    """
    
    def __init__(self, amount: int):
        """
        Creates a new bet.
        
        Args:
            amount: Bet amount in chips
        """
        if amount <= 0:
            raise ValueError("Bet amount must be positive")
        
        self.__amount = amount
        self.__is_active = True
        self.__outcome: Optional[BetOutcome] = None
        self.__payout = 0
        self.__can_double_down = True
        self.__can_split = True
        self.__is_doubled = False
    
    def get_amount(self) -> int:
        """Returns bet amount."""
        return self.__amount
    
    def is_active(self) -> bool:
        """Returns whether bet is still active."""
        return self.__is_active
    
    def can_double_down(self) -> bool:
        """Returns whether player can double down."""
        return self.__can_double_down and self.__is_active
    
    def can_split(self) -> bool:
        """Returns whether player can split."""
        return self.__can_split and self.__is_active
    
    def double_down(self) -> int:
        """
        Doubles the bet amount.
        
        Returns:
            Additional amount needed
            
        Raises:
            ValueError: If double down not allowed
        """
        if not self.can_double_down():
            raise ValueError("Cannot double down on this bet")
        
        additional = self.__amount
        self.__amount *= 2
        self.__is_doubled = True
        self.__can_double_down = False
        self.__can_split = False
        
        logger.info(f"Bet doubled to {self.__amount}")
        return additional
    
    def resolve(self, outcome: BetOutcome) -> int:
        """
        Resolves the bet and calculates payout.
        
        Args:
            outcome: Result of the hand
            
        Returns:
            Payout amount (0 for loss)
        """
        if not self.__is_active:
            raise ValueError("Bet already resolved")
        
        self.__outcome = outcome
        self.__is_active = False
        
        # Calculate payout based on outcome
        if outcome == BetOutcome.WIN:
            self.__payout = self.__amount * 2  # Bet back + equal winnings
        elif outcome == BetOutcome.BLACKJACK:
            self.__payout = int(self.__amount * 2.5)  # 3:2 payout
        elif outcome == BetOutcome.PUSH:
            self.__payout = self.__amount  # Bet returned
        elif outcome == BetOutcome.SURRENDER:
            self.__payout = self.__amount // 2  # Half bet returned
        else:  # LOSS
            self.__payout = 0
        
        logger.info(f"Bet resolved: {outcome.value}, Payout: {self.__payout}")
        return self.__payout
    
    def get_outcome(self) -> Optional[BetOutcome]:
        """Returns bet outcome if resolved."""
        return self.__outcome
    
    def get_payout(self) -> int:
        """Returns payout amount."""
        return self.__payout
    
    def disable_actions(self):
        """Disables double down and split options."""
        self.__can_double_down = False
        self.__can_split = False


class BettingManager:
    """
    Manages betting for a blackjack game session.
    Demonstrates COMPOSITION - uses ChipManager and Bet objects.
    """
    
    def __init__(self, chip_manager: ChipManager):
        """
        Initializes betting manager.
        
        Args:
            chip_manager: ChipManager instance for this player
        """
        self.chip_manager = chip_manager
        self.current_bet: Optional[Bet] = None
        self.min_bet = 10
        self.max_bet = 1000
        self.betting_history: List[Dict] = []
    
    def get_min_bet(self) -> int:
        """Returns minimum bet allowed."""
        return self.min_bet
    
    def get_max_bet(self) -> int:
        """Returns maximum bet allowed."""
        return self.max_bet
    
    def set_bet_limits(self, min_bet: int, max_bet: int):
        """
        Sets betting limits for the table.
        
        Args:
            min_bet: Minimum bet allowed
            max_bet: Maximum bet allowed
        """
        if min_bet <= 0 or max_bet < min_bet:
            raise ValueError("Invalid bet limits")
        
        self.min_bet = min_bet
        self.max_bet = max_bet
        logger.info(f"Bet limits set: {min_bet}-{max_bet}")
    
    def place_bet(self, amount: int) -> Bet:
        """
        Places a new bet for the current hand.
        
        Args:
            amount: Bet amount
            
        Returns:
            Created Bet object
            
        Raises:
            ValueError: If amount is outside limits or bet already active
            InsufficientChipsError: If player can't afford bet
        """
        if self.current_bet and self.current_bet.is_active():
            raise ValueError("A bet is already active")
        
        # Validate bet amount
        if amount < self.min_bet:
            raise ValueError(f"Bet below minimum: {self.min_bet}")
        
        if amount > self.max_bet:
            raise ValueError(f"Bet above maximum: {self.max_bet}")
        
        # Check if player can afford it
        if not self.chip_manager.can_afford(amount):
            raise InsufficientChipsError(
                f"Insufficient chips. Balance: {self.chip_manager.get_balance()}"
            )
        
        # Deduct chips and create bet
        self.chip_manager.deduct_chips(amount)
        self.current_bet = Bet(amount)
        
        logger.info(f"Bet placed: {amount} chips")
        return self.current_bet
    
    def double_down(self) -> bool:
        """
        Attempts to double down on current bet.
        
        Returns:
            True if successful
            
        Raises:
            ValueError: If no active bet or double down not allowed
            InsufficientChipsError: If player can't afford
        """
        if not self.current_bet or not self.current_bet.is_active():
            raise ValueError("No active bet to double")
        
        additional = self.current_bet.get_amount()
        
        if not self.chip_manager.can_afford(additional):
            raise InsufficientChipsError(
                f"Cannot afford to double down. Need: {additional}, "
                f"Have: {self.chip_manager.get_balance()}"
            )
        
        self.chip_manager.deduct_chips(additional)
        self.current_bet.double_down()
        
        logger.info(f"Doubled down for additional {additional} chips")
        return True
    
    def resolve_bet(self, outcome: BetOutcome):
        """
        Resolves current bet and processes payout.
        
        Args:
            outcome: Result of the hand
            
        Raises:
            ValueError: If no active bet
        """
        if not self.current_bet or not self.current_bet.is_active():
            raise ValueError("No active bet to resolve")
        
        payout = self.current_bet.resolve(outcome)
        
        if payout > 0:
            self.chip_manager.add_chips(payout, "WINNINGS")
        
        # Record in betting history
        self.betting_history.append({
            'bet_amount': self.current_bet.get_amount(),
            'outcome': outcome.value,
            'payout': payout,
            'net': payout - self.current_bet.get_amount()
        })
        
        logger.info(
            f"Bet resolved: {outcome.value}, "
            f"Bet: {self.current_bet.get_amount()}, Payout: {payout}"
        )
    
    def get_current_bet(self) -> Optional[Bet]:
        """Returns current active bet if any."""
        return self.current_bet if self.current_bet and self.current_bet.is_active() else None
    
    def clear_bet(self):
        """Clears current bet (used after resolution)."""
        self.current_bet = None
    
    def get_betting_summary(self) -> Dict:
        """Returns summary of betting activity."""
        return {
            'current_balance': self.chip_manager.get_balance(),
            'total_wagered': self.chip_manager.get_total_wagered(),
            'total_won': self.chip_manager.get_total_won(),
            'total_lost': self.chip_manager.get_total_lost(),
            'net_profit': self.chip_manager.get_net_profit(),
            'largest_bet': self.chip_manager.get_largest_bet(),
            'hands_played': len(self.betting_history)
        }
    
    def get_suggested_bet(self) -> int:
        """
        Suggests a reasonable bet based on balance.
        
        Returns:
            Suggested bet amount
        """
        balance = self.chip_manager.get_balance()
        
        # Conservative betting: 1-5% of balance
        suggested = max(self.min_bet, min(balance // 20, self.max_bet))
        
        # Round to nearest 5
        suggested = (suggested // 5) * 5
        
        return suggested


def integrate_betting_with_profile(profile):
    """
    Helper function to add betting capability to existing player profile.
    
    Args:
        profile: PlayerProfile instance
        
    Returns:
        BettingManager instance
    """
    # Create or load chip manager
    if not hasattr(profile, '_chip_manager'):
        profile._chip_manager = ChipManager()
    
    # Create betting manager
    betting_manager = BettingManager(profile._chip_manager)
    
    return betting_manager


# Example usage and integration
if __name__ == "__main__":
    # Example 1: Basic betting flow
    print("=== Example 1: Basic Betting Flow ===")
    chip_manager = ChipManager(initial_balance=1000)
    betting_manager = BettingManager(chip_manager)
    
    print(f"Starting balance: {chip_manager.get_balance()}")
    
    # Place a bet
    bet = betting_manager.place_bet(50)
    print(f"Bet placed: {bet.get_amount()}")
    print(f"Balance after bet: {chip_manager.get_balance()}")
    
    # Resolve with win
    betting_manager.resolve_bet(BetOutcome.WIN)
    print(f"Balance after win: {chip_manager.get_balance()}")
    
    print("\n=== Example 2: Double Down ===")
    betting_manager.clear_bet()
    bet = betting_manager.place_bet(100)
    print(f"Initial bet: {bet.get_amount()}")
    
    betting_manager.double_down()
    print(f"Doubled bet: {bet.get_amount()}")
    
    betting_manager.resolve_bet(BetOutcome.BLACKJACK)
    print(f"Balance after blackjack: {chip_manager.get_balance()}")
    
    print("\n=== Betting Summary ===")
    summary = betting_manager.get_betting_summary()
    for key, value in summary.items():
        print(f"{key}: {value}")


