from pydantic import BaseModel, field_validator
from email_validator import validate_email, EmailNotValidError
import string
from redis_connect import client
from passlib.hash import pbkdf2_sha256


class RegisterUserScheme(BaseModel):
    """Scheme for user registration"""
    username: str
    password1: str
    password2: str
    email: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, username):
        """Validate field username"""
        response = dict(error="Username is not valid")
        if len(username.replace(" ", "")) < 3:
            return response
        if any(char in string.punctuation for char in username):
            return response
        with client as client_redis:
            if client_redis.exists(username):
                return {"error": f"user with name: {username} already exists"}
        return username

    @field_validator("password2")
    @classmethod
    def validate_passwords(cls, password2, values):
        """Validate fields password"""
        if len(password2) < 5:
            return {"error": "Password length must be at least 5 characters"}
        if password2 != values.data.get("password1"):
            return {"error": "passwords do not match"}
        if not password2.isalnum():
            return {"error": "password must contain only letters and numbers"}
        return password2

    @field_validator('email')
    @classmethod
    def validate_email(cls, email):
        """Validate field email"""
        try:
            validate_email(email)
        except EmailNotValidError:
            return {"error": "Email is not valid"}
        return email


class AuthUserScheme(BaseModel):
    """Scheme for user authenticate"""
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def check_user(cls, username):
        """User existence check"""
        with client as client_redis:
            if not client_redis.exists(username):
                return {"error": f"username: {username} does not exist"}
            return username

    @field_validator("password")
    @classmethod
    def check_password(cls, password, values):
        """Password check"""
        with client as client_redis:
            if isinstance(values.data.get("username"), dict):
                return password
            hash_pass = client_redis.hget(name=values.data.get("username"), key="password")
            if not pbkdf2_sha256.verify(password, hash_pass):
                return {"error": f"{password} not correct"}
            return password