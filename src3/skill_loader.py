"""
Skill Loader - Loads and manages skill files for LLM prompts
"""

from pathlib import Path
from typing import Optional
import os


class SkillLoader:
    """Loads skill files from the skills directory"""
    
    def __init__(self, skills_dir: Optional[str] = None):
        if skills_dir:
            self.skills_dir = Path(skills_dir)
        else:
            # Default to src3/skills relative to this file
            self.skills_dir = Path(__file__).parent / "skills"
    
    def load_skill(self, skill_name: str) -> str:
        """
        Load a skill file by name.
        
        Args:
            skill_name: Name of the skill (e.g., "EXTRACT_FACTS", "GENERATE_SUMMARY")
        
        Returns:
            Content of the skill file
        """
        skill_path = self.skills_dir / f"{skill_name}.md"
        
        if not skill_path.exists():
            raise FileNotFoundError(f"Skill file not found: {skill_path}")
        
        with open(skill_path, "r", encoding="utf-8") as f:
            return f.read()
    
    def get_skill_prompt(self, skill_name: str, task_context: str = "") -> str:
        """
        Get a complete prompt with skill loaded.
        
        Args:
            skill_name: Name of the skill to load
            task_context: Additional context for the specific task
        
        Returns:
            Complete prompt with skill instructions
        """
        skill_content = self.load_skill(skill_name)
        
        prompt = f"""# SKILL INSTRUCTIONS
{skill_content}

# YOUR TASK
{task_context}"""
        
        return prompt
    
    def list_skills(self) -> list:
        """List all available skills"""
        if not self.skills_dir.exists():
            return []
        
        return [f.stem for f in self.skills_dir.glob("*.md")]


# Global skill loader instance
_skill_loader = None


def get_skill_loader() -> SkillLoader:
    """Get the global skill loader instance"""
    global _skill_loader
    if _skill_loader is None:
        _skill_loader = SkillLoader()
    return _skill_loader


def load_skill(skill_name: str) -> str:
    """Convenience function to load a skill"""
    return get_skill_loader().load_skill(skill_name)
