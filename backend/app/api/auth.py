from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import timedelta

from app.core.database import get_db
from app.core.security import security
from app.models.user import User
from app.api.schemas.user import UserCreate, UserLogin, UserResponse, Token
from app.core.logging import logger

# 创建路由
router = APIRouter(prefix="/auth", tags=["authentication"])
bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
) -> User:
    """获取当前用户"""
    token = credentials.credentials
    payload = security.verify_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    email: str = payload.get("sub")
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


@router.post("/register", response_model=UserResponse)
async def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """用户注册"""

    # 检查用户是否已存在
    existing_user = db.query(User).filter(
        (User.email == user_data.email) | (User.username == user_data.username)
    ).first()

    if existing_user:
        if existing_user.email == user_data.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )

    # 创建新用户
    hashed_password = security.get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        username=user_data.username,
        password_hash=hashed_password,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    logger.info("User registered successfully", user_id=str(db_user.id), email=db_user.email)

    return db_user


@router.post("/login", response_model=Token)
async def login_user(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """用户登录"""

    # 验证用户
    user = db.query(User).filter(User.username == user_credentials.username).first()

    print(user_credentials)
    if not user or not security.verify_password(user_credentials.password, user.password_hash):
        logger.warning("Login failed", username=user_credentials.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )

    # 创建访问令牌
    access_token_expires = timedelta(minutes=300)
    access_token = security.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )

    logger.info("User logged in successfully", user_id=str(user.id), email=user.email)

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return current_user


@router.post("/logout")
async def logout_user(current_user: User = Depends(get_current_user)):
    """用户登出 (简单版本)"""
    logger.info("User logged out", user_id=str(current_user.id), email=current_user.email)
    return {"message": "Successfully logged out"}