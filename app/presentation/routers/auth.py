from fastapi import APIRouter, Depends

from app.application.use_cases.autenticar import Autenticar
from app.presentation.deps import get_autenticar_dev, get_autenticar_google, get_usuario_atual
from app.presentation.schemas.auth import (
    LoginDevRequest,
    LoginGoogleRequest,
    SessaoResponse,
    UsuarioResponse,
)

router = APIRouter(prefix="/auth", tags=["Login"])


def _sessao(token, usuario) -> SessaoResponse:
    return SessaoResponse(
        token=token,
        usuario=UsuarioResponse(id=usuario.id, email=usuario.email, nome=usuario.nome),
    )


@router.post("/google", response_model=SessaoResponse, summary="Login com o ID token do Google")
def login_google(
    body: LoginGoogleRequest,
    caso_de_uso: Autenticar = Depends(get_autenticar_google),
):
    return _sessao(*caso_de_uso.executar(body.idToken))


@router.post(
    "/dev",
    response_model=SessaoResponse,
    summary="Login de desenvolvimento (só com AUTH_MODO_DEV=true)",
)
def login_dev(body: LoginDevRequest, caso_de_uso: Autenticar = Depends(get_autenticar_dev)):
    return _sessao(*caso_de_uso.executar(body.id))


@router.get("/me", response_model=UsuarioResponse, summary="Quem está logado")
def eu(usuario=Depends(get_usuario_atual)):
    return UsuarioResponse(id=usuario.id, email=usuario.email, nome=usuario.nome)
