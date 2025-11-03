from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Callable
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class AchievementRarity(Enum):
    """Achievement rarity levels."""
    COMMON = "Common"
    UNCOMMON = "Uncommon"
    RARE = "Rare"
    EPIC = "Epic"
    LEGENDARY = "Legendary"


class Achievement(ABC):
    """
    Abstract base class for achievements.
    Demonstrates INHERITANCE and ABSTRACTION.
    """
    
    def __init__(self, achievement_id: str, name: str, description: str, 
                 rarity: AchievementRarity, points: int):
        """
        Initialize achievement.
        
        Args:
            achievement_id: Unique identifier
            name: Display name
            description: What player must do
            rarity: Achievement rarity level
            points: Points awarded when unlocked
        """
        self._id = achievement_id
        self._name = name
        self._description = description
        self._rarity = rarity
        self._points = points
        
        # Private tracking attributes (encapsulation)
        self.__is_unlocked = False
        self.__unlock_date: Optional[datetime] = None
        self.__progress = 0
        self.__progress_max = 1
        self.__progress_notifications: List[Callable] = []
    
    # Getter methods
    def get_id(self) -> str:
        """Returns achievement ID."""
        return self._id
    
    def get_name(self) -> str:
        """Returns achievement name."""
        return self._name
    
    def get_description(self) -> str:
        """Returns achievement description."""
        return self._description
    
    def get_rarity(self) -> AchievementRarity:
        """Returns achievement rarity."""
        return self._rarity
    
    def get_points(self) -> int:
        """Returns points awarded."""
        return self._points
    
    def is_unlocked(self) -> bool:
        """Returns whether achievement is unlocked."""
        return self.__is_unlocked
    
    def get_unlock_date(self) -> Optional[datetime]:
        """Returns date achievement was unlocked."""
        return self.__unlock_date
    
    def get_progress(self) -> int:
        """Returns current progress."""
        return self.__progress
    
    def get_progress_max(self) -> int:
        """Returns progress needed to unlock."""
        return self.__progress_max
    
    def get_progress_percentage(self) -> float:
        """Returns progress as percentage."""
        if self.__progress_max == 0:
            return 100.0
        return (self.__progress / self.__progress_max) * 100
    
    # Abstract methods (must be implemented by subclasses)
    @abstractmethod
    def check_unlock_condition(self, game_stats: Dict) -> bool:
        """
        Checks if achievement should be unlocked.
        Subclasses implement specific logic.
        
        Args:
            game_stats: Dictionary of game statistics
            
        Returns:
            True if achievement should unlock
        """
        pass
    
    @abstractmethod
    def update_progress(self, game_stats: Dict):
        """
        Updates achievement progress based on stats.
        Subclasses implement specific logic.
        
        Args:
            game_stats: Dictionary of game statistics
        """
        pass
    
    # Protected method for subclasses
    def _set_progress(self, current: int, maximum: int):
        """
        Sets progress values (for use by subclasses).
        
        Args:
            current: Current progress
            maximum: Maximum progress needed
        """
        self.__progress = min(current, maximum)
        self.__progress_max = maximum
        
        # Notify observers of progress change
        for callback in self.__progress_notifications:
            callback(self)
    
    def _unlock(self):
        """Unlocks the achievement (for use by subclasses)."""
        if not self.__is_unlocked:
            self.__is_unlocked = True
            self.__unlock_date = datetime.now()
            self.__progress = self.__progress_max
            logger.info(f"Achievement unlocked: {self._name}")
    
    def add_progress_listener(self, callback: Callable):
        """
        Adds a callback for progress updates (Observer pattern).
        
        Args:
            callback: Function to call when progress changes
        """
        self.__progress_notifications.append(callback)
    
    def to_dict(self) -> Dict:
        """Serializes achievement to dictionary."""
        return {
            'id': self._id,
            'name': self._name,
            'description': self._description,
            'rarity': self._rarity.value,
            'points': self._points,
            'unlocked': self.__is_unlocked,
            'unlock_date': self.__unlock_date.isoformat() if self.__unlock_date else None,
            'progress': self.__progress,
            'progress_max': self.__progress_max
        }


class WinStreakAchievement(Achievement):
    """Achievement for winning consecutive games."""
    
    def __init__(self, streak_required: int, achievement_id: str, name: str, 
                 description: str, rarity: AchievementRarity, points: int):
        super().__init__(achievement_id, name, description, rarity, points)
        self.streak_required = streak_required
    
    def check_unlock_condition(self, game_stats: Dict) -> bool:
        """Checks if win streak requirement met."""
        current_streak = game_stats.get('current_streak', 0)
        return current_streak >= self.streak_required
    
    def update_progress(self, game_stats: Dict):
        """Updates progress based on current streak."""
        current_streak = game_stats.get('current_streak', 0)
        self._set_progress(current_streak, self.streak_required)
        
        if self.check_unlock_condition(game_stats):
            self._unlock()


class TotalWinsAchievement(Achievement):
    """Achievement for total number of wins."""
    
    def __init__(self, wins_required: int, achievement_id: str, name: str,
                 description: str, rarity: AchievementRarity, points: int):
        super().__init__(achievement_id, name, description, rarity, points)
        self.wins_required = wins_required
    
    def check_unlock_condition(self, game_stats: Dict) -> bool:
        """Checks if total wins requirement met."""
        total_wins = game_stats.get('wins', 0)
        return total_wins >= self.wins_required
    
    def update_progress(self, game_stats: Dict):
        """Updates progress based on total wins."""
        total_wins = game_stats.get('wins', 0)
        self._set_progress(total_wins, self.wins_required)
        
        if self.check_unlock_condition(game_stats):
            self._unlock()


class BlackjackAchievement(Achievement):
    """Achievement for getting blackjacks."""
    
    def __init__(self, blackjacks_required: int, achievement_id: str, name: str,
                 description: str, rarity: AchievementRarity, points: int):
        super().__init__(achievement_id, name, description, rarity, points)
        self.blackjacks_required = blackjacks_required
    
    def check_unlock_condition(self, game_stats: Dict) -> bool:
        """Checks if blackjack requirement met."""
        blackjacks = game_stats.get('blackjacks', 0)
        return blackjacks >= self.blackjacks_required
    
    def update_progress(self, game_stats: Dict):
        """Updates progress based on blackjacks."""
        blackjacks = game_stats.get('blackjacks', 0)
        self._set_progress(blackjacks, self.blackjacks_required)
        
        if self.check_unlock_condition(game_stats):
            self._unlock()


class WinRateAchievement(Achievement):
    """Achievement for maintaining high win rate."""
    
    def __init__(self, win_rate_required: float, min_games: int, 
                 achievement_id: str, name: str, description: str,
                 rarity: AchievementRarity, points: int):
        super().__init__(achievement_id, name, description, rarity, points)
        self.win_rate_required = win_rate_required
        self.min_games = min_games
    
    def check_unlock_condition(self, game_stats: Dict) -> bool:
        """Checks if win rate requirement met with minimum games."""
        total_games = game_stats.get('total_games', 0)
        win_rate = game_stats.get('win_rate', 0.0)
        
        return total_games >= self.min_games and win_rate >= self.win_rate_required
    
    def update_progress(self, game_stats: Dict):
        """Updates progress based on games played (min requirement)."""
        total_games = game_stats.get('total_games', 0)
        self._set_progress(total_games, self.min_games)
        
        if self.check_unlock_condition(game_stats):
            self._unlock()


class PlaytimeAchievement(Achievement):
    """Achievement for total playtime."""
    
    def __init__(self, hours_required: float, achievement_id: str, name: str,
                 description: str, rarity: AchievementRarity, points: int):
        super().__init__(achievement_id, name, description, rarity, points)
        self.hours_required = hours_required
    
    def check_unlock_condition(self, game_stats: Dict) -> bool:
        """Checks if playtime requirement met."""
        playtime_hours = game_stats.get('total_playtime_hours', 0.0)
        return playtime_hours >= self.hours_required
    
    def update_progress(self, game_stats: Dict):
        """Updates progress based on playtime."""
        playtime_hours = game_stats.get('total_playtime_hours', 0.0)
        self._set_progress(int(playtime_hours * 10), int(self.hours_required * 10))
        
        if self.check_unlock_condition(game_stats):
            self._unlock()


class AchievementManager:
    """
    Manages all achievements and tracks player progress.
    Demonstrates OBSERVER PATTERN - observes game statistics.
    """
    
    def __init__(self):
        """Initialize achievement manager."""
        self.achievements: Dict[str, Achievement] = {}
        self.notification_callbacks: List[Callable] = []
        self._initialize_default_achievements()
    
    def _initialize_default_achievements(self):
        """Creates the default set of achievements."""
        
        # Beginner achievements
        self.add_achievement(TotalWinsAchievement(
            1, "first_win", "First Victory",
            "Win your first game",
            AchievementRarity.COMMON, 10
        ))
        
        self.add_achievement(BlackjackAchievement(
            1, "first_blackjack", "Natural 21",
            "Get your first blackjack",
            AchievementRarity.COMMON, 15
        ))
        
        # Intermediate achievements
        self.add_achievement(WinStreakAchievement(
            3, "win_streak_3", "Hot Streak",
            "Win 3 games in a row",
            AchievementRarity.UNCOMMON, 25
        ))
        
        self.add_achievement(TotalWinsAchievement(
            10, "wins_10", "Skilled Player",
            "Win 10 games total",
            AchievementRarity.UNCOMMON, 30
        ))
        
        self.add_achievement(BlackjackAchievement(
            5, "blackjacks_5", "Blackjack Enthusiast",
            "Get 5 blackjacks",
            AchievementRarity.UNCOMMON, 35
        ))
        
        # Advanced achievements
        self.add_achievement(WinStreakAchievement(
            5, "win_streak_5", "On Fire",
            "Win 5 games in a row",
            AchievementRarity.RARE, 50
        ))
        
        self.add_achievement(TotalWinsAchievement(
            50, "wins_50", "Veteran Player",
            "Win 50 games total",
            AchievementRarity.RARE, 75
        ))
        
        self.add_achievement(WinRateAchievement(
            60.0, 20, "consistent_winner", "Consistent Winner",
            "Maintain 60% win rate over 20 games",
            AchievementRarity.RARE, 100
        ))
        
        # Expert achievements
        self.add_achievement(WinStreakAchievement(
            10, "win_streak_10", "Unstoppable",
            "Win 10 games in a row",
            AchievementRarity.EPIC, 150
        ))
        
        self.add_achievement(TotalWinsAchievement(
            100, "wins_100", "Blackjack Master",
            "Win 100 games total",
            AchievementRarity.EPIC, 200
        ))
        
        self.add_achievement(BlackjackAchievement(
            25, "blackjacks_25", "Lucky Streak",
            "Get 25 blackjacks",
            AchievementRarity.EPIC, 150
        ))
        
        # Legendary achievements
        self.add_achievement(TotalWinsAchievement(
            500, "wins_500", "Legend",
            "Win 500 games total",
            AchievementRarity.LEGENDARY, 500
        ))
        
        self.add_achievement(WinRateAchievement(
            70.0, 50, "elite_player", "Elite Player",
            "Maintain 70% win rate over 50 games",
            AchievementRarity.LEGENDARY, 750
        ))
        
        self.add_achievement(PlaytimeAchievement(
            10.0, "dedicated", "Dedicated Player",
            "Play for 10 hours total",
            AchievementRarity.RARE, 100
        ))
    
    def add_achievement(self, achievement: Achievement):
        """
        Adds an achievement to the manager.
        
        Args:
            achievement: Achievement to add
        """
        self.achievements[achievement.get_id()] = achievement
        logger.info(f"Added achievement: {achievement.get_name()}")
    
    def update_achievements(self, game_stats: Dict) -> List[Achievement]:
        """
        Updates all achievements based on current stats.
        This is the OBSERVER pattern in action - reacting to state changes.
        
        Args:
            game_stats: Current game statistics
            
        Returns:
            List of newly unlocked achievements
        """
        newly_unlocked = []
        
        for achievement in self.achievements.values():
            was_unlocked = achievement.is_unlocked()
            
            # Update progress
            achievement.update_progress(game_stats)
            
            # Check if newly unlocked
            if achievement.is_unlocked() and not was_unlocked:
                newly_unlocked.append(achievement)
                self._notify_unlock(achievement)
        
        return newly_unlocked
    
    def get_achievement(self, achievement_id: str) -> Optional[Achievement]:
        """
        Gets achievement by ID.
        
        Args:
            achievement_id: Achievement identifier
            
        Returns:
            Achievement if found, None otherwise
        """
        return self.achievements.get(achievement_id)
    
    def get_all_achievements(self) -> List[Achievement]:
        """Returns list of all achievements."""
        return list(self.achievements.values())
    
    def get_unlocked_achievements(self) -> List[Achievement]:
        """Returns list of unlocked achievements."""
        return [a for a in self.achievements.values() if a.is_unlocked()]
    
    def get_locked_achievements(self) -> List[Achievement]:
        """Returns list of locked achievements."""
        return [a for a in self.achievements.values() if not a.is_unlocked()]
    
    def get_achievements_by_rarity(self, rarity: AchievementRarity) -> List[Achievement]:
        """
        Gets achievements of specific rarity.
        
        Args:
            rarity: Rarity level to filter by
            
        Returns:
            List of achievements with specified rarity
        """
        return [a for a in self.achievements.values() if a.get_rarity() == rarity]
    
    def get_total_points(self) -> int:
        """Calculates total points from unlocked achievements."""
        return sum(a.get_points() for a in self.get_unlocked_achievements())
    
    def get_completion_percentage(self) -> float:
        """Calculates percentage of achievements unlocked."""
        if not self.achievements:
            return 0.0
        unlocked = len(self.get_unlocked_achievements())
        total = len(self.achievements)
        return (unlocked / total) * 100
    
    def add_unlock_notification(self, callback: Callable):
        """
        Adds callback for achievement unlocks (Observer pattern).
        
        Args:
            callback: Function to call when achievement unlocked
        """
        self.notification_callbacks.append(callback)
    
    def _notify_unlock(self, achievement: Achievement):
        """
        Notifies all observers of achievement unlock.
        
        Args:
            achievement: Newly unlocked achievement
        """
        for callback in self.notification_callbacks:
            try:
                callback(achievement)
            except Exception as e:
                logger.error(f"Error in unlock notification: {e}")
    
    def get_summary(self) -> Dict:
        """Returns summary of achievement progress."""
        return {
            'total_achievements': len(self.achievements),
            'unlocked': len(self.get_unlocked_achievements()),
            'locked': len(self.get_locked_achievements()),
            'total_points': self.get_total_points(),
            'completion_percentage': self.get_completion_percentage(),
            'by_rarity': {
                rarity.value: len(self.get_achievements_by_rarity(rarity))
                for rarity in AchievementRarity
            }
        }
    
    def get_next_achievements(self, limit: int = 3) -> List[Achievement]:
        """
        Gets closest locked achievements to unlocking.
        
        Args:
            limit: Maximum number to return
            
        Returns:
            List of achievements closest to unlocking
        """
        locked = self.get_locked_achievements()
        # Sort by progress percentage (descending)
        locked.sort(key=lambda a: a.get_progress_percentage(), reverse=True)
        return locked[:limit]
    
    def to_dict(self) -> Dict:
        """Serializes all achievements to dictionary."""
        return {
            achievement_id: achievement.to_dict()
            for achievement_id, achievement in self.achievements.items()
        }


def integrate_achievements_with_profile(profile):
    """
    Integrates achievement system with player profile.
    
    Args:
        profile: PlayerProfile instance
        
    Returns:
        AchievementManager instance
    """
    if not hasattr(profile, '_achievement_manager'):
        profile._achievement_manager = AchievementManager()
        
        # Add notification callback
        def announce_achievement(achievement: Achievement):
            print(f"🏆 Achievement Unlocked: {achievement.get_name()}")
            print(f"   {achievement.get_description()}")
            print(f"   +{achievement.get_points()} points")
        
        profile._achievement_manager.add_unlock_notification(announce_achievement)
    
    return profile._achievement_manager


# Example usage
if __name__ == "__main__":
    print("=== Achievement System Demo ===\n")
    
    manager = AchievementManager()
    
    # Simulate game progress
    print("Starting game session...\n")
    
    # Game 1: Win
    stats = {
        'total_games': 1,
        'wins': 1,
        'losses': 0,
        'pushes': 0,
        'blackjacks': 1,
        'current_streak': 1,
        'win_rate': 100.0,
        'total_playtime_hours': 0.1
    }
    
    unlocked = manager.update_achievements(stats)
    if unlocked:
        print(f"Unlocked {len(unlocked)} achievements after game 1!")
        for achievement in unlocked:
            print(f"  ✓ {achievement.get_name()}")
    
    print(f"\n Progress: {manager.get_completion_percentage():.1f}% complete")
    print(f"Total Points: {manager.get_total_points()}")
    
    print("\n=== Next Achievements to Unlock ===")
    next_achievements = manager.get_next_achievements(3)
    for achievement in next_achievements:
        progress = achievement.get_progress_percentage()
        print(f"{achievement.get_name()}: {progress:.0f}% complete")
        print(f"  {achievement.get_description()}")


