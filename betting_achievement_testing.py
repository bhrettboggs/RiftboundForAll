"""
Integration Module: Betting System + Achievement System
Demonstrates how both new features work together with existing profile system
"""

from betting_system import ChipManager, BettingManager, BetOutcome, integrate_betting_with_profile
from achievement_system import AchievementManager, integrate_achievements_with_profile
from player_profile_system import ProfileManager, StandardPlayerProfile
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnhancedGameSession:
    """
    Enhanced game session that integrates betting and achievements.
    Demonstrates how the two new features work together.
    """
    
    def __init__(self, profile):
        """
        Initialize enhanced game session.
        
        Args:
            profile: PlayerProfile instance
        """
        self.profile = profile
        
        # Integrate betting system
        self.betting_manager = integrate_betting_with_profile(profile)
        
        # Integrate achievement system
        self.achievement_manager = integrate_achievements_with_profile(profile)
        
        # Track session stats
        self.hands_played_this_session = 0
    
    def start_hand(self, bet_amount: int):
        """
        Starts a new blackjack hand with betting.
        
        Args:
            bet_amount: Amount to bet on this hand
        """
        logger.info(f"\n{'='*50}")
        logger.info(f"Starting new hand - Bet: {bet_amount} chips")
        
        try:
            # Place bet
            bet = self.betting_manager.place_bet(bet_amount)
            logger.info(f"✓ Bet placed: {bet.get_amount()} chips")
            logger.info(f"  Remaining balance: {self.betting_manager.chip_manager.get_balance()}")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ Could not place bet: {e}")
            return False
    
    def end_hand(self, player_score: int, dealer_score: int, is_blackjack: bool = False):
        """
        Ends the hand, resolves bet, updates stats, and checks achievements.
        This is where both systems interact!
        
        Args:
            player_score: Final player score
            dealer_score: Final dealer score
            is_blackjack: Whether player got blackjack
        """
        self.hands_played_this_session += 1
        
        # Determine outcome
        if is_blackjack:
            outcome = BetOutcome.BLACKJACK
            result = 'win'
            logger.info("🎰 BLACKJACK!")
        elif player_score > 21:
            outcome = BetOutcome.LOSS
            result = 'loss'
            logger.info("💥 Bust - You lose")
        elif dealer_score > 21:
            outcome = BetOutcome.WIN
            result = 'win'
            logger.info("🎉 Dealer busts - You win!")
        elif player_score > dealer_score:
            outcome = BetOutcome.WIN
            result = 'win'
            logger.info("🎉 You win!")
        elif dealer_score > player_score:
            outcome = BetOutcome.LOSS
            result = 'loss'
            logger.info("😞 You lose")
        else:
            outcome = BetOutcome.PUSH
            result = 'push'
            logger.info("🤝 Push - Bet returned")
        
        # Resolve bet (Betting System)
        self.betting_manager.resolve_bet(outcome)
        logger.info(f"  Balance after hand: {self.betting_manager.chip_manager.get_balance()}")
        
        # Record game in profile
        self.profile.record_game(result, player_score, dealer_score, 4, is_blackjack)
        
        # Update achievements (Achievement System)
        current_stats = self.profile.get_statistics().get_summary()
        newly_unlocked = self.achievement_manager.update_achievements(current_stats)
        
        # Announce any new achievements
        if newly_unlocked:
            logger.info("\n" + "🏆" * 20)
            logger.info("ACHIEVEMENT UNLOCKED!")
            for achievement in newly_unlocked:
                logger.info(f"  🏆 {achievement.get_name()}")
                logger.info(f"     {achievement.get_description()}")
                logger.info(f"     +{achievement.get_points()} points | {achievement.get_rarity().value}")
            logger.info("🏆" * 20 + "\n")
        
        # Clear bet for next hand
        self.betting_manager.clear_bet()
    
    def get_session_summary(self):
        """
        Gets comprehensive summary of the session.
        Shows data from both betting and achievement systems.
        """
        betting_summary = self.betting_manager.get_betting_summary()
        achievement_summary = self.achievement_manager.get_summary()
        profile_stats = self.profile.get_statistics().get_summary()
        
        return {
            'hands_played': self.hands_played_this_session,
            'betting': betting_summary,
            'achievements': achievement_summary,
            'profile_stats': profile_stats
        }
    
    def display_session_summary(self):
        """Displays formatted session summary."""
        summary = self.get_session_summary()
        
        print("\n" + "="*60)
        print("SESSION SUMMARY")
        print("="*60)
        
        print(f"\n📊 Hands Played: {summary['hands_played']}")
        
        print(f"\n💰 BETTING STATS")
        print(f"   Current Balance: {summary['betting']['current_balance']} chips")
        print(f"   Total Wagered: {summary['betting']['total_wagered']} chips")
        print(f"   Total Won: {summary['betting']['total_won']} chips")
        print(f"   Net Profit: {summary['betting']['net_profit']:+d} chips")
        print(f"   Largest Bet: {summary['betting']['largest_bet']} chips")
        
        print(f"\n🏆 ACHIEVEMENTS")
        print(f"   Progress: {summary['achievements']['completion_percentage']:.1f}%")
        print(f"   Unlocked: {summary['achievements']['unlocked']}/{summary['achievements']['total_achievements']}")
        print(f"   Total Points: {summary['achievements']['total_points']}")
        
        print(f"\n🎮 GAME STATS")
        print(f"   Total Games: {summary['profile_stats']['total_games']}")
        print(f"   Wins: {summary['profile_stats']['wins']}")
        print(f"   Win Rate: {summary['profile_stats']['win_rate']:.1f}%")
        print(f"   Blackjacks: {summary['profile_stats']['blackjacks']}")
        print(f"   Win Streak: {summary['profile_stats']['current_streak']}")
        
        print("\n" + "="*60)
    
    def show_next_achievements(self):
        """Shows achievements closest to unlocking."""
        print("\n📋 NEXT ACHIEVEMENTS TO UNLOCK:")
        next_achievements = self.achievement_manager.get_next_achievements(3)
        
        for achievement in next_achievements:
            progress = achievement.get_progress_percentage()
            print(f"\n  {achievement.get_name()} [{achievement.get_rarity().value}]")
            print(f"  {achievement.get_description()}")
            print(f"  Progress: [{'█' * int(progress/5)}{'░' * (20-int(progress/5))}] {progress:.0f}%")
            print(f"  Reward: {achievement.get_points()} points")


def demo_integrated_session():
    """
    Demonstrates both features working together in a realistic game session.
    """
    print("="*60)
    print("ENHANCED BLACKJACK SESSION DEMO")
    print("Demonstrating Betting System + Achievement System Integration")
    print("="*60)
    
    # Create profile
    manager = ProfileManager()
    profile = manager.create_profile("Demo Player", "Standard")
    
    # Start enhanced session
    session = EnhancedGameSession(profile)
    
    print(f"\nStarting balance: {session.betting_manager.chip_manager.get_balance()} chips")
    
    # Simulate several hands
    hands = [
        # (bet_amount, player_score, dealer_score, is_blackjack)
        (50, 20, 18, False),   # Win
        (50, 21, 19, True),    # Blackjack!
        (75, 23, 20, False),   # Bust
        (50, 19, 19, False),   # Push
        (100, 20, 17, False),  # Win (big bet!)
    ]
    
    for i, (bet, p_score, d_score, is_bj) in enumerate(hands, 1):
        print(f"\n{'─'*60}")
        print(f"HAND #{i}")
        print(f"{'─'*60}")
        
        # Start hand with bet
        if session.start_hand(bet):
            # Simulate game...
            print(f"  Player: {p_score}, Dealer: {d_score}")
            
            # End hand
            session.end_hand(p_score, d_score, is_bj)
    
    # Show session summary
    session.display_session_summary()
    
    # Show next achievements to unlock
    session.show_next_achievements()
    
    print("\n" + "="*60)
    print("Demo complete! Both features working together successfully.")
    print("="*60)


def demonstrate_observer_pattern():
    """
    Specifically demonstrates the Observer pattern in the achievement system.
    """
    print("\n" + "="*60)
    print("OBSERVER PATTERN DEMONSTRATION")
    print("="*60)
    
    profile = StandardPlayerProfile("Observer Demo")
    achievement_manager = integrate_achievements_with_profile(profile)
    
    # Register multiple observers
    def console_announcer(achievement):
        print(f"[CONSOLE] Achievement unlocked: {achievement.get_name()}")
    
    def logger_observer(achievement):
        logger.info(f"Achievement progress: {achievement.get_name()}")
    
    achievement_manager.add_unlock_notification(console_announcer)
    achievement_manager.add_unlock_notification(logger_observer)
    
    print("\nSimulating game progress that triggers achievements...")
    
    # Simulate winning first game
    profile.record_game('win', 20, 18, 4, False)
    stats = profile.get_statistics().get_summary()
    
    print("\nAfter first win:")
    unlocked = achievement_manager.update_achievements(stats)
    print(f"Unlocked {len(unlocked)} achievement(s)")
    
    # Simulate getting first blackjack
    profile.record_game('win', 21, 19, 2, True)
    stats = profile.get_statistics().get_summary()
    
    print("\nAfter first blackjack:")
    unlocked = achievement_manager.update_achievements(stats)
    print(f"Unlocked {len(unlocked)} achievement(s)")


def demonstrate_encapsulation():
    """
    Demonstrates encapsulation in the ChipManager.
    """
    print("\n" + "="*60)
    print("ENCAPSULATION DEMONSTRATION")
    print("="*60)
    
    chip_manager = ChipManager(initial_balance=1000)
    
    print("\n1. Private balance cannot be accessed directly:")
    print(f"   chip_manager.get_balance() = {chip_manager.get_balance()}")
    print(f"   chip_manager.__balance would raise AttributeError")
    
    print("\n2. Balance changes go through controlled methods:")
    print(f"   Before bet: {chip_manager.get_balance()}")
    chip_manager.deduct_chips(100)
    print(f"   After betting 100: {chip_manager.get_balance()}")
    
    print("\n3. Validation prevents invalid operations:")
    try:
        chip_manager.deduct_chips(-50)
    except ValueError as e:
        print(f"   ✓ Caught invalid bet: {e}")
    
    try:
        chip_manager.deduct_chips(10000)
    except Exception as e:
        print(f"   ✓ Caught insufficient funds: {e}")
    
    print("\n4. Transaction history tracks all changes:")
    history = chip_manager.get_transaction_history()
    print(f"   Transactions recorded: {len(history)}")


if __name__ == "__main__":
    # Run all demonstrations
    demo_integrated_session()
    demonstrate_observer_pattern()
    demonstrate_encapsulation()
    
    print("\n\n🎉 All demonstrations complete!")
    print("Both features successfully integrate with existing system.")