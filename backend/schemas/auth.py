from pydantic import BaseModel, EmailStr

class RegisterRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class SessionResponse(BaseModel):
    id: str
    email: str
    full_name: str
    is_admin: bool
    onboarding_complete: bool
