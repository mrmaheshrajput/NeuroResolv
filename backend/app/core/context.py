from contextvars import ContextVar
from typing import Optional

# Context variable to hold the authenticated user ID
# I know, I know, but please let's not argue about this
current_user_id: ContextVar[Optional[int]] = ContextVar("current_user_id", default=None)
