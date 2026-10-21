from typing import Optional

from pydantic import BaseModel, Field


class LoginGoogleRequest(BaseModel):
    idToken: str = Field(..., description="ID token do google_sign_in (GoogleSignInAuthentication.idToken)")


class LoginDevRequest(BaseModel):
    id: str = Field(..., description="Qualquer identificador; vira o usuário dev:<id>")


class UsuarioResponse(BaseModel):
    id:    str
    email: Optional[str] = None
    nome:  Optional[str] = None


class SessaoResponse(BaseModel):
    token:   str = Field(..., description="Envie como Authorization: Bearer <token> nas demais rotas")
    usuario: UsuarioResponse
