from fastapi import Depends, HTTPException, status
from routers.auth import get_current_user

def roles_required(*roles):
    def wrapper(user=Depends(get_current_user)):
        if user["user_role"] not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="無此權限")
        return user
    return wrapper