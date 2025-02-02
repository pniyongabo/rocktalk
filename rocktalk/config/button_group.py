from typing import List

import streamlit as st
from utils.log import logger


class ButtonGroupManager:
    """Manages mutually exclusive button actions in session state"""

    def __init__(self, group_name: str, action_keys: List[str]):
        """Initialize button group

        Args:
            group_name: Unique identifier for this button group
            action_keys: List of action keys that are mutually exclusive
        """
        self.group_name = group_name
        self.action_keys = action_keys
        self._init_state()

    def _init_state(self):
        """Initialize session state for all actions in group"""
        for key in self.action_keys:
            if key not in st.session_state:
                st.session_state[key] = False

    def toggle_action(self, action_key: str):
        """Toggle specified action and disable all others

        Args:
            action_key: The action to toggle
        """
        if action_key not in self.action_keys:
            raise ValueError(f"Action {action_key} not in group {self.group_name}")

        # Toggle target action
        st.session_state[action_key] = not st.session_state[action_key]

        # Disable all other actions
        for key in self.action_keys:
            if key != action_key:
                st.session_state[key] = False

    def is_active(self, action_key: str) -> bool:
        """Check if an action is currently active"""
        return st.session_state.get(action_key, False)

    def clear_all(self):
        """Clear all actions in the group"""
        for key in self.action_keys:
            st.session_state[key] = False

    def rerun(self):
        """Rerun the app to reflect changes in session state"""
        self.clear_all()
        try:
            st.rerun(scope="fragment")
        except Exception as e:
            logger.error(
                f"Could not rerun using scope='fragement'. is {self} running in fragment/dialog?\n{e}"
            )
            st.rerun()
