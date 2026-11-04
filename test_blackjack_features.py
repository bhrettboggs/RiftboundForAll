"""
Test Suite for Accessible Blackjack - Bhrett's Modules
Tests cover: Player Profile System, Achievement System, and Betting System

This test suite ensures reliability, data integrity, and correct game mechanics
for user-facing features that track progress and manage game resources.
"""

import pytest
import os
import tempfile
import shutil
from player_profile_system import (
    GameStatistics,
    StandardPlayerProfile,
    BeginnerPlayerProfile,
    ExpertPlayerProfile,
    ProfileManager
)
from achievement_system import (
    AchievementManager,
    WinStreakAchievement,
    TotalWinsAchievement,
    AchievementRarity
)
from betting_system import (
    ChipManager,
    BettingManager,
    Bet,
    BetOutcome,
    InsufficientChipsError
)


# ============================================================================
# PLAYER PROFILE SYSTEM TESTS
# ============================================================================

class TestGameStatistics:
    """Tests for GameStatistics class - ensures accurate stat tracking"""
    
    def test_initial_statistics_are_zero(self):
        """Verify new player starts with clean stats"""
        stats = GameStatistics()
        assert stats.get_total_games() == 0
        assert stats.get_wins() == 0
        assert stats.get_losses() == 0
        assert stats.get_win_rate() == 0.0
    
    def test_record_win_updates_correctly(self):
        """Ensure wins are recorded and win rate calculated correctly"""
        stats = GameStatistics()
        stats.record_game_result('win', 20, 18, 4, False)
        
        assert stats.get_total_games() == 1
        assert stats.get_wins() == 1
        assert stats.get_losses() == 0
        assert stats.get_win_rate() == 100.0
    
    def test_win_streak_tracking(self):
        """Verify consecutive win tracking for achievements"""
        stats = GameStatistics()
        
        # Win 3 games in a row
        for _ in range(3):
            stats.record_game_result('win', 20, 18, 4, False)
        
        assert stats.get_current_streak() == 3
        assert stats.get_longest_streak() == 3
    
    def test_streak_resets_after_loss(self):
        """Ensure streak resets properly (important for achievement system)"""
        stats = GameStatistics()
        
        # Win 2, lose 1
        stats.record_game_result('win', 20, 18, 4, False)
        stats.record_game_result('win', 21, 19, 4, False)
        stats.record_game_result('loss', 23, 20, 5, False)
        
        assert stats.get_current_streak() == 0
        assert stats.get_longest_streak() == 2
    
    def test_blackjack_tracking(self):
        """Verify blackjack achievements are recorded"""
        stats = GameStatistics()
        stats.record_game_result('win', 21, 19, 2, is_blackjack=True)
        
        assert stats.get_blackjacks() == 1


class TestPlayerProfiles:
    """Tests for player profile system - ensures personalization works"""
    
    def test_standard_profile_creation(self):
        """Verify standard profile initializes correctly"""
        profile = StandardPlayerProfile("TestPlayer")
        assert profile.get_name() == "TestPlayer"
        assert profile.get_profile_type() == "Standard"
    
    def test_different_profiles_give_different_messages(self):
        """Ensure polymorphism works - different profiles, different feedback"""
        standard = StandardPlayerProfile("Alice")
        beginner = BeginnerPlayerProfile("Bob")
        expert = ExpertPlayerProfile("Charlie")
        
        msg_standard = standard.get_encouragement_message('win')
        msg_beginner = beginner.get_encouragement_message('win')
        msg_expert = expert.get_encouragement_message('win')
        
        # All should be different (polymorphism test)
        assert msg_standard != msg_expert
        assert msg_beginner != msg_expert
    
    def test_profile_records_games(self):
        """Ensure profile correctly stores game history"""
        profile = StandardPlayerProfile("TestPlayer")
        profile.record_game('win', 20, 18, 4, False)
        
        stats = profile.get_statistics()
        assert stats.get_total_games() == 1
        assert stats.get_wins() == 1


class TestProfileManager:
    """Tests for profile persistence - critical for not losing user data"""
    
    def setup_method(self):
        """Create temporary directory for each test"""
        self.test_dir = tempfile.mkdtemp()
        self.manager = ProfileManager(profiles_directory=self.test_dir)
    
    def teardown_method(self):
        """Clean up temporary files after each test"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_create_and_retrieve_profile(self):
        """Verify profiles can be created and retrieved"""
        profile = self.manager.create_profile("TestUser", "Standard")
        retrieved = self.manager.get_profile("TestUser")
        
        assert retrieved is not None
        assert retrieved.get_name() == "TestUser"
    
    def test_profile_persistence(self):
        """CRITICAL: Ensure saved profiles load correctly (data integrity)"""
        # Create profile and record data
        profile = self.manager.create_profile("TestUser", "Standard")
        self.manager.set_current_profile("TestUser")  # create_profile doesn't make it current
        profile.record_game('win', 20, 18, 4, False)
        self.manager.save_current_profile()
        
        # Create new manager (simulates app restart)
        new_manager = ProfileManager(profiles_directory=self.test_dir)
        loaded_profile = new_manager.get_profile("TestUser")
        
        # Data should persist
        assert loaded_profile is not None
        assert loaded_profile.get_statistics().get_total_games() == 1
        assert loaded_profile.get_statistics().get_wins() == 1


# ============================================================================
# ACHIEVEMENT SYSTEM TESTS
# ============================================================================

class TestAchievementSystem:
    """Tests for achievement tracking - ensures rewards work correctly"""
    
    def test_achievement_manager_initialization(self):
        """Verify achievement manager loads default achievements"""
        manager = AchievementManager()
        achievements = manager.get_all_achievements()
        
        assert len(achievements) > 0
        assert manager.get_achievement("first_win") is not None
    
    def test_first_win_achievement_unlocks(self):
        """Verify first win achievement triggers correctly"""
        manager = AchievementManager()
        
        game_stats = {
            'total_games': 1,
            'wins': 1,
            'losses': 0,
            'pushes': 0,
            'blackjacks': 0,
            'current_streak': 1,
            'win_rate': 100.0,
            'total_playtime_hours': 0.1
        }
        
        unlocked = manager.update_achievements(game_stats)
        
        assert len(unlocked) > 0
        first_win = manager.get_achievement("first_win")
        assert first_win.is_unlocked()
    
    def test_win_streak_achievement(self):
        """Verify streak achievements unlock at correct thresholds"""
        manager = AchievementManager()
        
        # Simulate 3-game win streak
        game_stats = {
            'total_games': 3,
            'wins': 3,
            'losses': 0,
            'pushes': 0,
            'blackjacks': 0,
            'current_streak': 3,
            'win_rate': 100.0,
            'total_playtime_hours': 0.3
        }
        
        manager.update_achievements(game_stats)
        
        streak_achievement = manager.get_achievement("win_streak_3")
        assert streak_achievement.is_unlocked()
    
    def test_achievement_does_not_unlock_prematurely(self):
        """SAFETY: Ensure achievements only unlock when conditions are met"""
        manager = AchievementManager()
        
        # Only 2 wins, should NOT unlock 3-streak achievement
        game_stats = {
            'total_games': 2,
            'wins': 2,
            'current_streak': 2,
            'win_rate': 100.0,
            'total_playtime_hours': 0.2
        }
        
        manager.update_achievements(game_stats)
        
        streak_achievement = manager.get_achievement("win_streak_3")
        assert not streak_achievement.is_unlocked()


# ============================================================================
# BETTING SYSTEM TESTS
# ============================================================================

class TestChipManager:
    """Tests for chip management - ensures financial integrity"""
    
    def test_initial_balance(self):
        """Verify starting balance is correct"""
        chip_manager = ChipManager(initial_balance=1000)
        assert chip_manager.get_balance() == 1000
    
    def test_deduct_chips_successful(self):
        """Verify chips are deducted correctly for bets"""
        chip_manager = ChipManager(initial_balance=1000)
        chip_manager.deduct_chips(100)
        
        assert chip_manager.get_balance() == 900
    
    def test_insufficient_chips_raises_error(self):
        """CRITICAL: Prevent betting more than available (security)"""
        chip_manager = ChipManager(initial_balance=100)
        
        with pytest.raises(InsufficientChipsError):
            chip_manager.deduct_chips(200)
    
    def test_add_chips_from_winnings(self):
        """Verify winnings are added correctly"""
        chip_manager = ChipManager(initial_balance=1000)
        chip_manager.deduct_chips(100)
        chip_manager.add_chips(200, "WINNINGS")
        
        assert chip_manager.get_balance() == 1100
    
    def test_negative_bet_rejected(self):
        """SECURITY: Prevent negative bets (exploit prevention)"""
        chip_manager = ChipManager(initial_balance=1000)
        
        with pytest.raises(ValueError):
            chip_manager.deduct_chips(-50)


class TestBettingManager:
    """Tests for betting workflow - ensures game economy works"""
    
    def test_place_bet_within_limits(self):
        """Verify bets within limits are accepted"""
        chip_manager = ChipManager(initial_balance=1000)
        betting_manager = BettingManager(chip_manager)
        
        bet = betting_manager.place_bet(50)
        
        assert bet is not None
        assert bet.get_amount() == 50
        assert chip_manager.get_balance() == 950
    
    def test_bet_below_minimum_rejected(self):
        """Ensure minimum bet rules are enforced"""
        chip_manager = ChipManager(initial_balance=1000)
        betting_manager = BettingManager(chip_manager)
        
        with pytest.raises(ValueError):
            betting_manager.place_bet(5)  # Below minimum of 10
    
    def test_win_payout_calculation(self):
        """Verify winning bets pay correctly (1:1)"""
        chip_manager = ChipManager(initial_balance=1000)
        betting_manager = BettingManager(chip_manager)
        
        betting_manager.place_bet(100)
        betting_manager.resolve_bet(BetOutcome.WIN)
        
        # Should have 1000 - 100 + 200 = 1100
        assert chip_manager.get_balance() == 1100
    
    def test_blackjack_payout_calculation(self):
        """Verify blackjack pays 3:2 correctly"""
        chip_manager = ChipManager(initial_balance=1000)
        betting_manager = BettingManager(chip_manager)
        
        betting_manager.place_bet(100)
        betting_manager.resolve_bet(BetOutcome.BLACKJACK)
        
        # Should have 1000 - 100 + 250 = 1150
        assert chip_manager.get_balance() == 1150
    
    def test_loss_no_payout(self):
        """Verify losses result in no payout"""
        chip_manager = ChipManager(initial_balance=1000)
        betting_manager = BettingManager(chip_manager)
        
        betting_manager.place_bet(100)
        betting_manager.resolve_bet(BetOutcome.LOSS)
        
        # Should have 1000 - 100 = 900
        assert chip_manager.get_balance() == 900
    
    def test_push_returns_bet(self):
        """Verify push (tie) returns original bet"""
        chip_manager = ChipManager(initial_balance=1000)
        betting_manager = BettingManager(chip_manager)
        
        betting_manager.place_bet(100)
        betting_manager.resolve_bet(BetOutcome.PUSH)
        
        # Should have original 1000 back
        assert chip_manager.get_balance() == 1000
    
    def test_double_down_functionality(self):
        """Verify double down doubles the bet correctly"""
        chip_manager = ChipManager(initial_balance=1000)
        betting_manager = BettingManager(chip_manager)
        
        betting_manager.place_bet(100)
        betting_manager.double_down()
        
        # Should have deducted 100 + 100 = 200
        assert chip_manager.get_balance() == 800
        assert betting_manager.get_current_bet().get_amount() == 200


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestSystemIntegration:
    """Integration tests - verify systems work together correctly"""
    
    def test_complete_game_with_all_systems(self):
        """Full workflow: profile + achievements + betting"""
        # Setup
        test_dir = tempfile.mkdtemp()
        try:
            manager = ProfileManager(profiles_directory=test_dir)
            profile = manager.create_profile("IntegrationTest", "Standard")
            
            achievement_manager = AchievementManager()
            chip_manager = ChipManager(initial_balance=1000)
            betting_manager = BettingManager(chip_manager)
            
            # Play a game
            betting_manager.place_bet(50)
            profile.record_game('win', 20, 18, 4, False)
            betting_manager.resolve_bet(BetOutcome.WIN)
            
            # Check achievements
            stats = profile.get_statistics().get_summary()
            unlocked = achievement_manager.update_achievements(stats)
            
            # Verify everything worked
            assert profile.get_statistics().get_wins() == 1
            assert chip_manager.get_balance() == 1050
            assert len(unlocked) > 0
            
        finally:
            shutil.rmtree(test_dir)


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])