"""Auth service business logic — re-exports from sub-modules."""

from app.services.auth import (
    seed_default_admin,
    create_user,
    authenticate_user,
    create_token_pair,
    rotate_refresh_token,
    revoke_refresh_token,
    change_password,
)
from app.services.users import (
    get_user_by_id,
    get_user_by_username,
    update_user_profile,
    deactivate_own_account,
    delete_own_account,
)
from app.services.admin import (
    list_users,
    update_user_role,
    deactivate_user,
    reactivate_user,
)

__all__ = [
    # auth
    "seed_default_admin", "create_user", "authenticate_user",
    "create_token_pair", "rotate_refresh_token", "revoke_refresh_token",
    "change_password",
    # users
    "get_user_by_id", "get_user_by_username", "update_user_profile",
    "deactivate_own_account", "delete_own_account",
    # admin
    "list_users", "update_user_role", "deactivate_user", "reactivate_user",
]
