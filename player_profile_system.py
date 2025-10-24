import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from abc import ABC, abstractmethod

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GameStatistics:
    """
    Encapsulates game statistics with private attributes and controlled access.
    Demonstrates ENCAPSULATION principle.
    """
    
    def __init__(self):
        # Private attributes (encapsulation)
        self.__total_games = 0
        self.__wins = 0
        self.__losses = 0
        self.__pushes = 0
        self.__blackjacks = 0
        self.__busts = 0
        self.__total_hands_played = 0
        self.__total_cards_dealt = 0
        self.__win_streak = 0
        self.__current_streak = 0
        self.__longest_streak = 0
        self.__session_start = None
        self.__total_playtime_seconds = 0
        self.__game_history = []  # List of game results
    
    # Public getter methods (controlled access)
    def get_total_games(self) -> int:
        """Returns total number of games played."""
        return self.__total_games
    
    def get_wins(self) -> int:
        """Returns total wins."""
        return self.__wins
    
    def get_losses(self) -> int:
        """Returns total losses."""
        return self.__losses
    
    def get_win_rate(self) -> float:
        """Calculates and returns win percentage."""
        if self.__total_games == 0:
            return 0.0
        return (self.__wins / self.__total_games) * 100
    
    def get_blackjacks(self) -> int:
        """Returns total blackjacks achieved."""
        return self.__blackjacks
    
    def get_longest_streak(self) -> int:
        """Returns the longest winning streak."""
        return self.__longest_streak
    
    def get_current_streak(self) -> int:
        """Returns the current winning streak."""
        return self.__current_streak
    
    # Public methods to update statistics
    def record_game_result(self, result: str, player_score: int, dealer_score: int, 
                          cards_dealt: int, is_blackjack: bool = False):
        """
        Records the result of a game and updates statistics.
        
        Args:
            result: 'win', 'loss', or 'push'
            player_score: Final player score
            dealer_score: Final dealer score
            cards_dealt: Number of cards dealt in the game
            is_blackjack: Whether player achieved blackjack
        """
        self.__total_games += 1
        self.__total_cards_dealt += cards_dealt
        
        # Record to history
        game_record = {
            'game_number': self.__total_games,
            'result': result,
            'player_score': player_score,
            'dealer_score': dealer_score,
            'timestamp': datetime.now().isoformat(),
            'blackjack': is_blackjack
        }
        self.__game_history.append(game_record)
        
        # Update result-specific stats
        if result == 'win':
            self.__wins += 1
            self.__current_streak += 1
            if self.__current_streak > self.__longest_streak:
                self.__longest_streak = self.__current_streak
        elif result == 'loss':
            self.__losses += 1
            self.__current_streak = 0
            if player_score > 21:
                self.__busts += 1
        else:  # push
            self.__pushes += 1
        
        if is_blackjack:
            self.__blackjacks += 1
    
    def start_session(self):
        """Marks the start of a play session."""
        self.__session_start = datetime.now()
    
    def end_session(self):
        """Marks the end of a play session and calculates duration."""
        if self.__session_start:
            session_duration = (datetime.now() - self.__session_start).total_seconds()
            self.__total_playtime_seconds += session_duration
            self.__session_start = None
    
    def get_summary(self) -> Dict:
        """Returns a dictionary summary of all statistics."""
        return {
            'total_games': self.__total_games,
            'wins': self.__wins,
            'losses': self.__losses,
            'pushes': self.__pushes,
            'win_rate': self.get_win_rate(),
            'blackjacks': self.__blackjacks,
            'busts': self.__busts,
            'longest_streak': self.__longest_streak,
            'current_streak': self.__current_streak,
            'total_playtime_hours': self.__total_playtime_seconds / 3600
        }
    
    def to_dict(self) -> Dict:
        """Converts statistics to dictionary for serialization."""
        return {
            'total_games': self.__total_games,
            'wins': self.__wins,
            'losses': self.__losses,
            'pushes': self.__pushes,
            'blackjacks': self.__blackjacks,
            'busts': self.__busts,
            'longest_streak': self.__longest_streak,
            'current_streak': self.__current_streak,
            'total_playtime_seconds': self.__total_playtime_seconds,
            'game_history': self.__game_history
        }
    
    def from_dict(self, data: Dict):
        """Loads statistics from dictionary."""
        self.__total_games = data.get('total_games', 0)
        self.__wins = data.get('wins', 0)
        self.__losses = data.get('losses', 0)
        self.__pushes = data.get('pushes', 0)
        self.__blackjacks = data.get('blackjacks', 0)
        self.__busts = data.get('busts', 0)
        self.__longest_streak = data.get('longest_streak', 0)
        self.__current_streak = data.get('current_streak', 0)
        self.__total_playtime_seconds = data.get('total_playtime_seconds', 0)
        self.__game_history = data.get('game_history', [])


class PlayerProfile(ABC):
    """
    Abstract base class for player profiles.
    Demonstrates INHERITANCE and POLYMORPHISM principles.
    
    This is the parent class that defines common behavior for all player types.
    Subclasses can override methods to provide specialized behavior.
    """
    
    def __init__(self, name: str, profile_type: str):
        # Protected attributes (accessible by subclasses)
        self._name = name
        self._profile_type = profile_type
        self._created_date = datetime.now().isoformat()
        self._last_played = None
        
        # Composition: Profile "has-a" GameStatistics object
        self._statistics = GameStatistics()
        
        # Accessibility preferences
        self._accessibility_settings = {
            'speech_rate': 150,
            'announcement_verbosity': 'normal',  # 'minimal', 'normal', 'detailed'
            'auto_announce_stats': True
        }
    
    # Getter methods
    def get_name(self) -> str:
        """Returns the player name."""
        return self._name
    
    def get_profile_type(self) -> str:
        """Returns the profile type."""
        return self._profile_type
    
    def get_statistics(self) -> GameStatistics:
        """Returns the statistics object (composition relationship)."""
        return self._statistics
    
    def get_accessibility_settings(self) -> Dict:
        """Returns current accessibility settings."""
        return self._accessibility_settings.copy()
    
    # Setter methods
    def update_accessibility_settings(self, settings: Dict):
        """Updates accessibility preferences."""
        self._accessibility_settings.update(settings)
    
    # Abstract methods (must be implemented by subclasses)
    @abstractmethod
    def get_encouragement_message(self, game_result: str) -> str:
        """Returns an appropriate message based on game result (polymorphism)."""
        pass
    
    @abstractmethod
    def get_stats_announcement(self) -> str:
        """Returns formatted statistics announcement (polymorphism)."""
        pass
    
    # Concrete methods (shared by all profiles)
    def record_game(self, result: str, player_score: int, dealer_score: int, 
                   cards_dealt: int, is_blackjack: bool = False):
        """Records a game result and updates last played time."""
        self._statistics.record_game_result(result, player_score, dealer_score, 
                                           cards_dealt, is_blackjack)
        self._last_played = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        """Converts profile to dictionary for serialization."""
        return {
            'name': self._name,
            'profile_type': self._profile_type,
            'created_date': self._created_date,
            'last_played': self._last_played,
            'statistics': self._statistics.to_dict(),
            'accessibility_settings': self._accessibility_settings
        }


class StandardPlayerProfile(PlayerProfile):
    """Standard player profile with balanced announcements."""
    
    def __init__(self, name: str):
        super().__init__(name, "Standard")
    
    def get_encouragement_message(self, game_result: str) -> str:
        """Returns encouraging feedback for standard players."""
        messages = {
            'win': f"Congratulations, {self._name}! You won this hand!",
            'loss': f"Better luck next time, {self._name}.",
            'push': f"It's a tie, {self._name}. Your bet is returned."
        }
        return messages.get(game_result, "Game complete.")
    
    def get_stats_announcement(self) -> str:
        """Returns standard statistics announcement."""
        stats = self._statistics.get_summary()
        return (f"{self._name}, you've played {stats['total_games']} games. "
                f"You've won {stats['wins']} games with a {stats['win_rate']:.1f}% win rate. "
                f"Your current winning streak is {stats['current_streak']}.")


class BeginnerPlayerProfile(PlayerProfile):
    """Beginner profile with detailed, encouraging announcements."""
    
    def __init__(self, name: str):
        super().__init__(name, "Beginner")
        # More verbose settings for beginners
        self._accessibility_settings['announcement_verbosity'] = 'detailed'
    
    def get_encouragement_message(self, game_result: str) -> str:
        """Returns detailed, encouraging feedback for beginners."""
        messages = {
            'win': f"Excellent work, {self._name}! You won this round! Keep up the great play!",
            'loss': f"Don't worry, {self._name}. Every game is a learning opportunity. You'll do better next time!",
            'push': f"This hand is a tie, {self._name}. That means nobody wins or loses. Let's try again!"
        }
        return messages.get(game_result, "Game complete. Ready for the next hand?")
    
    def get_stats_announcement(self) -> str:
        """Returns detailed, beginner-friendly statistics."""
        stats = self._statistics.get_summary()
        return (f"Hi {self._name}! Let me tell you about your progress. "
                f"You've played {stats['total_games']} games so far. "
                f"You won {stats['wins']} times, lost {stats['losses']} times, "
                f"and tied {stats['pushes']} times. "
                f"That means you're winning about {stats['win_rate']:.1f}% of your games. "
                f"You've also gotten {stats['blackjacks']} blackjacks! "
                f"Your best winning streak was {stats['longest_streak']} games in a row!")


class ExpertPlayerProfile(PlayerProfile):
    """Expert profile with concise, data-focused announcements."""
    
    def __init__(self, name: str):
        super().__init__(name, "Expert")
        # Minimal announcements for experts
        self._accessibility_settings['announcement_verbosity'] = 'minimal'
        self._advanced_stats = {
            'optimal_plays': 0,
            'risky_plays': 0
        }
    
    def get_encouragement_message(self, game_result: str) -> str:
        """Returns brief, expert-level feedback."""
        messages = {
            'win': f"Win confirmed.",
            'loss': f"Loss recorded.",
            'push': f"Push."
        }
        return messages.get(game_result, "Complete.")
    
    def get_stats_announcement(self) -> str:
        """Returns concise, data-focused statistics."""
        stats = self._statistics.get_summary()
        return (f"Record: {stats['wins']}-{stats['losses']}-{stats['pushes']}. "
                f"Win rate: {stats['win_rate']:.1f}%. "
                f"Streak: {stats['current_streak']} (best: {stats['longest_streak']}).")
    
    def record_play_quality(self, play_type: str):
        """Records advanced play quality metrics (expert-only feature)."""
        if play_type == 'optimal':
            self._advanced_stats['optimal_plays'] += 1
        elif play_type == 'risky':
            self._advanced_stats['risky_plays'] += 1


class ProfileManager:
    """
    Manages player profiles with file persistence.
    Demonstrates COMPOSITION - ProfileManager "has-many" PlayerProfile objects.
    """
    
    def __init__(self, profiles_directory: str = "player_profiles"):
        self._profiles_dir = profiles_directory
        self._current_profile: Optional[PlayerProfile] = None
        self._profiles: Dict[str, PlayerProfile] = {}
        
        # Create profiles directory if it doesn't exist
        os.makedirs(self._profiles_dir, exist_ok=True)
        
        # Load existing profiles
        self._load_all_profiles()
    
    def create_profile(self, name: str, profile_type: str = "Standard") -> PlayerProfile:
        """
        Factory method to create different profile types.
        Returns the appropriate profile subclass based on type.
        
        Args:
            name: Player name
            profile_type: One of "Standard", "Beginner", or "Expert"
            
        Returns:
            Created PlayerProfile instance
        """
        if profile_type == "Beginner":
            profile = BeginnerPlayerProfile(name)
        elif profile_type == "Expert":
            profile = ExpertPlayerProfile(name)
        else:
            profile = StandardPlayerProfile(name)
        
        self._profiles[name] = profile
        self._save_profile(profile)
        logger.info(f"Created {profile_type} profile for {name}")
        return profile
    
    def get_profile(self, name: str) -> Optional[PlayerProfile]:
        """Retrieves a profile by name."""
        return self._profiles.get(name)
    
    def set_current_profile(self, name: str) -> bool:
        """
        Sets the active profile.
        
        Args:
            name: Name of profile to activate
            
        Returns:
            True if profile was set successfully, False otherwise
        """
        profile = self.get_profile(name)
        if profile:
            self._current_profile = profile
            logger.info(f"Set current profile to {name}")
            return True
        logger.warning(f"Profile {name} not found")
        return False
    
    def get_current_profile(self) -> Optional[PlayerProfile]:
        """Returns the currently active profile."""
        return self._current_profile
    
    def list_profiles(self) -> List[str]:
        """Returns list of all profile names."""
        return list(self._profiles.keys())
    
    def delete_profile(self, name: str) -> bool:
        """
        Deletes a profile.
        
        Args:
            name: Name of profile to delete
            
        Returns:
            True if profile was deleted successfully, False otherwise
        """
        if name in self._profiles:
            del self._profiles[name]
            profile_file = os.path.join(self._profiles_dir, f"{name}.json")
            if os.path.exists(profile_file):
                os.remove(profile_file)
            logger.info(f"Deleted profile {name}")
            return True
        logger.warning(f"Profile {name} not found for deletion")
        return False
    
    def _save_profile(self, profile: PlayerProfile):
        """Saves a profile to file."""
        os.makedirs(self._profiles_dir, exist_ok=True)
        profile_file = os.path.join(self._profiles_dir, f"{profile.get_name()}.json")
        try:
            with open(profile_file, 'w') as f:
                json.dump(profile.to_dict(), f, indent=2)
            logger.debug(f"Saved profile {profile.get_name()}")
        except Exception as e:
            logger.error(f"Error saving profile {profile.get_name()}: {e}")
    
    def save_current_profile(self):
        """Saves the current profile."""
        if self._current_profile:
            name = self._current_profile.get_name()
            if name in self._profiles:
                self._save_profile(self._profiles[name])
            else:
                self._save_profile(self._current_profile)
    
    def save_all_profiles(self):
        """Saves all profiles to disk."""
        for profile in self._profiles.values():
            self._save_profile(profile)
        logger.info(f"Saved all {len(self._profiles)} profiles")
    
    def _load_all_profiles(self):
        """Loads all profiles from the profiles directory."""
        if not os.path.exists(self._profiles_dir):
            return
        
        for filename in os.listdir(self._profiles_dir):
            if filename.endswith('.json'):
                profile_path = os.path.join(self._profiles_dir, filename)
                try:
                    with open(profile_path, 'r') as f:
                        data = json.load(f)
                    
                    # Reconstruct profile based on type
                    profile_type = data.get('profile_type', 'Standard')
                    name = data.get('name')
                    
                    if profile_type == "Beginner":
                        profile = BeginnerPlayerProfile(name)
                    elif profile_type == "Expert":
                        profile = ExpertPlayerProfile(name)
                    else:
                        profile = StandardPlayerProfile(name)
                    
                    # Load saved data
                    profile._created_date = data.get('created_date')
                    profile._last_played = data.get('last_played')
                    profile._statistics.from_dict(data.get('statistics', {}))
                    profile._accessibility_settings = data.get('accessibility_settings', 
                                                              profile._accessibility_settings)
                    
                    self._profiles[name] = profile
                    logger.debug(f"Loaded profile {name}")
                    
                except Exception as e:
                    logger.error(f"Error loading profile {filename}: {e}")
        
        if self._profiles:
            logger.info(f"Loaded {len(self._profiles)} profiles from disk")
