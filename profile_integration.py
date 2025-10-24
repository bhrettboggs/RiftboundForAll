import logging
from typing import Optional
from player_profile_system import ProfileManager, PlayerProfile

# Configure logging
logger = logging.getLogger(__name__)


class ProfileIntegratedBlackjackSystem:
    """
    Extends the accessible blackjack system with player profile management.
    
    This class wraps the base blackjack system and adds:
    - Profile creation and selection
    - Game statistics tracking
    - Personalized feedback based on profile type
    - Automatic progress saving
    """
    
    def __init__(self, base_system):
        """
        Initialize the profile-integrated system.
        
        Args:
            base_system: Instance of AccessibleBlackjackSystem to wrap
        """
        self.base_system = base_system
        self.profile_manager = ProfileManager()
        self.current_profile: Optional[PlayerProfile] = None
        
        logger.info("Profile-integrated blackjack system initialized")
    
    def create_new_profile(self, name: str, profile_type: str = "Standard") -> bool:
        """
        Create a new player profile.
        
        Args:
            name: Player name
            profile_type: One of "Standard", "Beginner", or "Expert"
            
        Returns:
            True if profile created successfully, False otherwise
        """
        try:
            profile = self.profile_manager.create_profile(name, profile_type)
            self.current_profile = profile
            logger.info(f"Created new {profile_type} profile for {name}")
            return True
        except Exception as e:
            logger.error(f"Error creating profile for {name}: {e}")
            return False
    
    def select_profile(self, name: str) -> bool:
        """
        Select an existing profile.
        
        Args:
            name: Name of profile to select
            
        Returns:
            True if profile loaded successfully, False otherwise
        """
        if self.profile_manager.set_current_profile(name):
            self.current_profile = self.profile_manager.get_current_profile()
            logger.info(f"Selected profile: {name}")
            return True
        else:
            logger.warning(f"Profile not found: {name}")
            return False
    
    def list_available_profiles(self) -> list:
        """
        Get list of all available profiles.
        
        Returns:
            List of profile names
        """
        return self.profile_manager.list_profiles()
    
    def start_game_session(self):
        """
        Start a new game session with the current profile.
        Should be called when starting gameplay.
        """
        if self.current_profile:
            self.current_profile.get_statistics().start_session()
            logger.info(f"Started session for {self.current_profile.get_name()}")
    
    def end_game_session(self):
        """
        End the current game session.
        Should be called when stopping gameplay.
        """
        if self.current_profile:
            self.current_profile.get_statistics().end_session()
            self.profile_manager.save_current_profile()
            logger.info(f"Ended session for {self.current_profile.get_name()}")
    
    def record_game_result(self, result: str, player_score: int, 
                          dealer_score: int, cards_dealt: int, 
                          is_blackjack: bool = False):
        """
        Record a game result to the current profile.
        
        Args:
            result: 'win', 'loss', or 'push'
            player_score: Final player score
            dealer_score: Final dealer score
            cards_dealt: Number of cards dealt
            is_blackjack: Whether player got blackjack
        """
        if self.current_profile:
            self.current_profile.record_game(
                result, player_score, dealer_score, cards_dealt, is_blackjack
            )
            logger.debug(f"Recorded {result} for {self.current_profile.get_name()}")
    
    def get_encouragement_message(self, result: str) -> str:
        """
        Get personalized encouragement message based on profile type.
        
        Args:
            result: 'win', 'loss', or 'push'
            
        Returns:
            Encouragement message appropriate for the profile type
        """
        if self.current_profile:
            return self.current_profile.get_encouragement_message(result)
        return "Game complete."
    
    def get_stats_announcement(self) -> str:
        """
        Get formatted statistics announcement.
        
        Returns:
            Statistics message appropriate for the profile type
        """
        if self.current_profile:
            return self.current_profile.get_stats_announcement()
        return "No profile selected."
    
    def get_current_profile_name(self) -> Optional[str]:
        """
        Get the name of the current profile.
        
        Returns:
            Profile name or None if no profile selected
        """
        if self.current_profile:
            return self.current_profile.get_name()
        return None
    
    def get_current_profile_type(self) -> Optional[str]:
        """
        Get the type of the current profile.
        
        Returns:
            Profile type or None if no profile selected
        """
        if self.current_profile:
            return self.current_profile.get_profile_type()
        return None
    
    def is_profile_selected(self) -> bool:
        """
        Check if a profile is currently selected.
        
        Returns:
            True if profile is selected, False otherwise
        """
        return self.current_profile is not None
    
    def update_accessibility_settings(self, settings: dict):
        """
        Update accessibility settings for current profile.
        
        Args:
            settings: Dictionary of settings to update
        """
        if self.current_profile:
            self.current_profile.update_accessibility_settings(settings)
            self.profile_manager.save_current_profile()
            logger.info(f"Updated accessibility settings for {self.current_profile.get_name()}")
    
    def get_accessibility_settings(self) -> dict:
        """
        Get accessibility settings for current profile.
        
        Returns:
            Dictionary of accessibility settings
        """
        if self.current_profile:
            return self.current_profile.get_accessibility_settings()
        return {}
    
    def delete_current_profile(self) -> bool:
        """
        Delete the currently selected profile.
        
        Returns:
            True if deleted successfully, False otherwise
        """
        if self.current_profile:
            name = self.current_profile.get_name()
            if self.profile_manager.delete_profile(name):
                self.current_profile = None
                logger.info(f"Deleted profile: {name}")
                return True
        return False
    
    def save_progress(self):
        """
        Save current profile progress.
        Should be called periodically and before exiting.
        """
        if self.current_profile:
            self.profile_manager.save_current_profile()
            logger.debug(f"Saved progress for {self.current_profile.get_name()}")
    
    def cleanup(self):
        """
        Cleanup and save before shutdown.
        Should be called when application is closing.
        """
        if self.current_profile:
            self.end_game_session()
            self.save_progress()
            logger.info(f"Cleanup complete for {self.current_profile.get_name()}")


# Integration Helper Functions
# These can be used to add profile functionality to your existing game

def integrate_with_game_end(integration: ProfileIntegratedBlackjackSystem,
                           game_result: str,
                           player_score: int,
                           dealer_score: int,
                           cards_dealt: int,
                           is_blackjack: bool = False) -> str:
    """
    Helper function to call when a game ends.
    
    Args:
        integration: ProfileIntegratedBlackjackSystem instance
        game_result: 'win', 'loss', or 'push'
        player_score: Final player score
        dealer_score: Final dealer score
        cards_dealt: Number of cards dealt
        is_blackjack: Whether player got blackjack
        
    Returns:
        Encouragement message to announce to player
    """
    # Record the game
    integration.record_game_result(
        game_result, player_score, dealer_score, cards_dealt, is_blackjack
    )
    
    # Get personalized feedback
    message = integration.get_encouragement_message(game_result)
    
    # Save progress
    integration.save_progress()
    
    return message


def integrate_with_stats_request(integration: ProfileIntegratedBlackjackSystem) -> str:
    """
    Helper function to call when player requests statistics.
    
    Args:
        integration: ProfileIntegratedBlackjackSystem instance
        
    Returns:
        Statistics announcement message
    """
    return integration.get_stats_announcement()


# Example usage patterns for integration
"""
INTEGRATION PATTERN 1: Basic Integration
=========================================

from profile_integration import ProfileIntegratedBlackjackSystem

# In your game initialization:
profile_system = ProfileIntegratedBlackjackSystem(your_blackjack_system)

# At start of gameplay:
if profile_system.is_profile_selected():
    profile_system.start_game_session()
else:
    # Prompt user to create or select profile
    pass

# When a hand ends:
profile_system.record_game_result('win', 20, 18, 4, False)
message = profile_system.get_encouragement_message('win')
# Announce message to player

# When player requests stats:
stats = profile_system.get_stats_announcement()
# Announce stats to player

# Before exiting:
profile_system.cleanup()


INTEGRATION PATTERN 2: With Voice Commands
===========================================

# Add these commands to your voice command handler:
commands = {
    'new profile': handle_new_profile,
    'select profile': handle_select_profile,
    'view stats': handle_view_stats,
    'change profile': handle_change_profile
}

def handle_new_profile():
    name = get_player_name_from_voice()
    type_choice = get_profile_type_from_voice()  # "standard", "beginner", or "expert"
    profile_system.create_new_profile(name, type_choice.title())

def handle_select_profile():
    profiles = profile_system.list_available_profiles()
    # Present choices to user
    name = get_choice_from_voice()
    profile_system.select_profile(name)

def handle_view_stats():
    stats = profile_system.get_stats_announcement()
    speak(stats)


INTEGRATION PATTERN 3: Automatic Profile Management
====================================================

class MyBlackjackGame:
    def __init__(self):
        self.profile_system = ProfileIntegratedBlackjackSystem(base_system)
        self._auto_save_counter = 0
    
    def play_hand(self):
        # Play the hand...
        result = self.determine_winner()
        
        # Auto-record if profile is selected
        if self.profile_system.is_profile_selected():
            self.profile_system.record_game_result(
                result, self.player_score, self.dealer_score, 
                self.cards_dealt, self.is_blackjack
            )
            
            # Get and speak encouragement
            message = self.profile_system.get_encouragement_message(result)
            self.speak(message)
            
            # Auto-save every 5 games
            self._auto_save_counter += 1
            if self._auto_save_counter >= 5:
                self.profile_system.save_progress()
                self._auto_save_counter = 0
"""
