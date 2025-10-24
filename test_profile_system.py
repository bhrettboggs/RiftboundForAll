import unittest
import os
import shutil
import json
import tempfile
from datetime import datetime
from player_profile_system import (
    GameStatistics,
    PlayerProfile,
    StandardPlayerProfile,
    BeginnerPlayerProfile,
    ExpertPlayerProfile,
    ProfileManager
)


class TestGameStatistics(unittest.TestCase):
    """Test cases for GameStatistics class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.stats = GameStatistics()
    
    def test_initial_state(self):
        """Test statistics start at zero."""
        self.assertEqual(self.stats.get_total_games(), 0)
        self.assertEqual(self.stats.get_wins(), 0)
        self.assertEqual(self.stats.get_losses(), 0)
        self.assertEqual(self.stats.get_win_rate(), 0.0)
    
    def test_record_win(self):
        """Test recording a win."""
        self.stats.record_game_result('win', 20, 18, 4, False)
        self.assertEqual(self.stats.get_total_games(), 1)
        self.assertEqual(self.stats.get_wins(), 1)
        self.assertEqual(self.stats.get_losses(), 0)
        self.assertEqual(self.stats.get_win_rate(), 100.0)
    
    def test_record_loss(self):
        """Test recording a loss."""
        self.stats.record_game_result('loss', 23, 20, 5, False)
        self.assertEqual(self.stats.get_total_games(), 1)
        self.assertEqual(self.stats.get_wins(), 0)
        self.assertEqual(self.stats.get_losses(), 1)
        self.assertEqual(self.stats.get_win_rate(), 0.0)
    
    def test_record_blackjack(self):
        """Test recording a blackjack."""
        self.stats.record_game_result('win', 21, 19, 2, True)
        self.assertEqual(self.stats.get_blackjacks(), 1)
    
    def test_win_streak(self):
        """Test winning streak tracking."""
        self.stats.record_game_result('win', 20, 18, 4, False)
        self.stats.record_game_result('win', 21, 19, 4, False)
        self.stats.record_game_result('win', 19, 17, 4, False)
        self.assertEqual(self.stats.get_current_streak(), 3)
        self.assertEqual(self.stats.get_longest_streak(), 3)
    
    def test_streak_reset_on_loss(self):
        """Test streak resets after a loss."""
        self.stats.record_game_result('win', 20, 18, 4, False)
        self.stats.record_game_result('win', 21, 19, 4, False)
        self.stats.record_game_result('loss', 23, 20, 5, False)
        self.assertEqual(self.stats.get_current_streak(), 0)
        self.assertEqual(self.stats.get_longest_streak(), 2)
    
    def test_win_rate_calculation(self):
        """Test win rate calculation."""
        self.stats.record_game_result('win', 20, 18, 4, False)
        self.stats.record_game_result('loss', 23, 20, 5, False)
        self.stats.record_game_result('win', 21, 19, 4, False)
        self.assertEqual(self.stats.get_total_games(), 3)
        self.assertAlmostEqual(self.stats.get_win_rate(), 66.67, places=1)
    
    def test_session_tracking(self):
        """Test session time tracking."""
        self.stats.start_session()
        self.stats.end_session()
        summary = self.stats.get_summary()
        self.assertGreaterEqual(summary['total_playtime_hours'], 0)
    
    def test_to_dict_from_dict(self):
        """Test serialization and deserialization."""
        self.stats.record_game_result('win', 20, 18, 4, False)
        self.stats.record_game_result('loss', 23, 20, 5, False)
        
        data = self.stats.to_dict()
        new_stats = GameStatistics()
        new_stats.from_dict(data)
        
        self.assertEqual(new_stats.get_total_games(), 2)
        self.assertEqual(new_stats.get_wins(), 1)
        self.assertEqual(new_stats.get_losses(), 1)


class TestPlayerProfiles(unittest.TestCase):
    """Test cases for PlayerProfile classes."""
    
    def test_standard_profile_creation(self):
        """Test StandardPlayerProfile creation."""
        profile = StandardPlayerProfile("Alice")
        self.assertEqual(profile.get_name(), "Alice")
        self.assertEqual(profile.get_profile_type(), "Standard")
    
    def test_beginner_profile_creation(self):
        """Test BeginnerPlayerProfile creation."""
        profile = BeginnerPlayerProfile("Bob")
        self.assertEqual(profile.get_name(), "Bob")
        self.assertEqual(profile.get_profile_type(), "Beginner")
    
    def test_expert_profile_creation(self):
        """Test ExpertPlayerProfile creation."""
        profile = ExpertPlayerProfile("Charlie")
        self.assertEqual(profile.get_name(), "Charlie")
        self.assertEqual(profile.get_profile_type(), "Expert")
    
    def test_encouragement_messages_differ(self):
        """Test that different profile types give different messages."""
        standard = StandardPlayerProfile("Alice")
        beginner = BeginnerPlayerProfile("Bob")
        expert = ExpertPlayerProfile("Charlie")
        
        msg_standard = standard.get_encouragement_message('win')
        msg_beginner = beginner.get_encouragement_message('win')
        msg_expert = expert.get_encouragement_message('win')
        
        # Messages should be different (polymorphism)
        self.assertNotEqual(msg_standard, msg_expert)
        self.assertNotEqual(msg_beginner, msg_expert)
    
    def test_stats_announcements_differ(self):
        """Test that different profile types format stats differently."""
        standard = StandardPlayerProfile("Alice")
        beginner = BeginnerPlayerProfile("Bob")
        expert = ExpertPlayerProfile("Charlie")
        
        # Record same game for all
        for profile in [standard, beginner, expert]:
            profile.record_game('win', 20, 18, 4, False)
        
        msg_standard = standard.get_stats_announcement()
        msg_beginner = beginner.get_stats_announcement()
        msg_expert = expert.get_stats_announcement()
        
        # Announcements should be different (polymorphism)
        self.assertNotEqual(msg_standard, msg_expert)
        self.assertNotEqual(msg_beginner, msg_expert)
    
    def test_record_game(self):
        """Test recording a game updates statistics."""
        profile = StandardPlayerProfile("Alice")
        profile.record_game('win', 20, 18, 4, False)
        
        stats = profile.get_statistics()
        self.assertEqual(stats.get_total_games(), 1)
        self.assertEqual(stats.get_wins(), 1)
    
    def test_accessibility_settings(self):
        """Test accessibility settings management."""
        profile = StandardPlayerProfile("Alice")
        settings = profile.get_accessibility_settings()
        
        self.assertIn('speech_rate', settings)
        self.assertIn('announcement_verbosity', settings)
        
        # Update settings
        profile.update_accessibility_settings({'speech_rate': 180})
        updated_settings = profile.get_accessibility_settings()
        self.assertEqual(updated_settings['speech_rate'], 180)
    
    def test_profile_serialization(self):
        """Test profile can be serialized and deserialized."""
        profile = StandardPlayerProfile("Alice")
        profile.record_game('win', 20, 18, 4, False)
        
        data = profile.to_dict()
        self.assertIn('name', data)
        self.assertIn('statistics', data)
        self.assertIn('accessibility_settings', data)


class TestProfileManager(unittest.TestCase):
    """Test cases for ProfileManager class."""
    
    def setUp(self):
        """Set up test fixtures with temporary directory."""
        self.test_dir = tempfile.mkdtemp()
        self.manager = ProfileManager(profiles_directory=self.test_dir)
    
    def tearDown(self):
        """Clean up test directory."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_create_profile(self):
        """Test profile creation."""
        profile = self.manager.create_profile("Alice", "Standard")
        self.assertIsNotNone(profile)
        self.assertEqual(profile.get_name(), "Alice")
    
    def test_create_different_profile_types(self):
        """Test creating different profile types."""
        standard = self.manager.create_profile("Alice", "Standard")
        beginner = self.manager.create_profile("Bob", "Beginner")
        expert = self.manager.create_profile("Charlie", "Expert")
        
        self.assertIsInstance(standard, StandardPlayerProfile)
        self.assertIsInstance(beginner, BeginnerPlayerProfile)
        self.assertIsInstance(expert, ExpertPlayerProfile)
    
    def test_get_profile(self):
        """Test retrieving a profile."""
        self.manager.create_profile("Alice", "Standard")
        profile = self.manager.get_profile("Alice")
        
        self.assertIsNotNone(profile)
        self.assertEqual(profile.get_name(), "Alice")
    
    def test_list_profiles(self):
        """Test listing all profiles."""
        self.manager.create_profile("Alice", "Standard")
        self.manager.create_profile("Bob", "Beginner")
        
        profiles = self.manager.list_profiles()
        self.assertEqual(len(profiles), 2)
        self.assertIn("Alice", profiles)
        self.assertIn("Bob", profiles)
    
    def test_set_current_profile(self):
        """Test setting the current profile."""
        self.manager.create_profile("Alice", "Standard")
        result = self.manager.set_current_profile("Alice")
        
        self.assertTrue(result)
        current = self.manager.get_current_profile()
        self.assertEqual(current.get_name(), "Alice")
    
    def test_delete_profile(self):
        """Test deleting a profile."""
        self.manager.create_profile("Alice", "Standard")
        result = self.manager.delete_profile("Alice")
        
        self.assertTrue(result)
        self.assertIsNone(self.manager.get_profile("Alice"))
    
    def test_profile_persistence(self):
        """Test profiles are saved and loaded correctly."""
        # Create and save profile
        profile = self.manager.create_profile("Alice", "Standard")
        profile.record_game('win', 20, 18, 4, False)
        self.manager.save_current_profile()
        
        # Create new manager and load profiles
        new_manager = ProfileManager(profiles_directory=self.test_dir)
        loaded_profile = new_manager.get_profile("Alice")
        
        self.assertIsNotNone(loaded_profile)
        self.assertEqual(loaded_profile.get_name(), "Alice")
        self.assertEqual(loaded_profile.get_statistics().get_total_games(), 1)
    
    def test_save_all_profiles(self):
        """Test saving all profiles at once."""
        self.manager.create_profile("Alice", "Standard")
        self.manager.create_profile("Bob", "Beginner")
        
        # Modify profiles
        alice = self.manager.get_profile("Alice")
        bob = self.manager.get_profile("Bob")
        alice.record_game('win', 20, 18, 4, False)
        bob.record_game('loss', 23, 20, 5, False)
        
        # Save all
        self.manager.save_all_profiles()
        
        # Reload and verify
        new_manager = ProfileManager(profiles_directory=self.test_dir)
        self.assertEqual(len(new_manager.list_profiles()), 2)
    
    def test_nonexistent_profile(self):
        """Test getting nonexistent profile returns None."""
        profile = self.manager.get_profile("NonExistent")
        self.assertIsNone(profile)
    
    def test_set_nonexistent_profile(self):
        """Test setting nonexistent profile returns False."""
        result = self.manager.set_current_profile("NonExistent")
        self.assertFalse(result)


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete system."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.manager = ProfileManager(profiles_directory=self.test_dir)
    
    def tearDown(self):
        """Clean up test directory."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_complete_game_session(self):
        """Test a complete game session workflow."""
        # Create profile
        profile = self.manager.create_profile("Alice", "Standard")
        self.manager.set_current_profile("Alice")
        
        # Start session
        profile.get_statistics().start_session()
        
        # Play games
        results = [
            ('win', 20, 18, 4, False),
            ('loss', 23, 20, 5, False),
            ('win', 21, 19, 3, True),
            ('push', 19, 19, 4, False),
        ]
        
        for result, p_score, d_score, cards, is_bj in results:
            profile.record_game(result, p_score, d_score, cards, is_bj)
        
        # End session
        profile.get_statistics().end_session()
        
        # Verify statistics
        stats = profile.get_statistics()
        self.assertEqual(stats.get_total_games(), 4)
        self.assertEqual(stats.get_wins(), 2)
        self.assertEqual(stats.get_losses(), 1)
        self.assertEqual(stats.get_blackjacks(), 1)
        
        # Save and reload
        self.manager.save_current_profile()
        new_manager = ProfileManager(profiles_directory=self.test_dir)
        loaded = new_manager.get_profile("Alice")
        
        self.assertEqual(loaded.get_statistics().get_total_games(), 4)
    
    def test_multiple_sessions(self):
        """Test multiple game sessions are tracked correctly."""
        profile = self.manager.create_profile("Alice", "Standard")
        
        # Session 1
        profile.get_statistics().start_session()
        profile.record_game('win', 20, 18, 4, False)
        profile.get_statistics().end_session()
        
        # Session 2
        profile.get_statistics().start_session()
        profile.record_game('win', 21, 19, 4, False)
        profile.get_statistics().end_session()
        
        # Verify both games recorded
        self.assertEqual(profile.get_statistics().get_total_games(), 2)


def run_tests():
    """Run all tests and return results."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestGameStatistics))
    suite.addTests(loader.loadTestsFromTestCase(TestPlayerProfiles))
    suite.addTests(loader.loadTestsFromTestCase(TestProfileManager))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == "__main__":
    result = run_tests()
    
    # Exit with proper code
    exit(0 if result.wasSuccessful() else 1)
