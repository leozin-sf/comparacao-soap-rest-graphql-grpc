"""Conexão e modelos ORM compartilhados por TODOS os serviços Python.

Usar a mesma camada de persistência em SOAP/REST/GraphQL/gRPC garante que a
única variável da comparação seja a tecnologia de comunicação.
"""
import os
from sqlalchemy import (
    create_engine, Integer, String, ForeignKey
)
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker
)

# Em Docker, DATABASE_URL aponta para o container postgres.
# Fallback em SQLite para rodar/testar localmente sem Postgres.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://app:app@localhost:5432/streaming",
)

# pool_pre_ping evita conexões mortas sob carga; pool maior ajuda no Locust.
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=40,
    future=True,
)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(180), nullable=False, unique=True)
    playlists: Mapped[list["Playlist"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Music(Base):
    __tablename__ = "musics"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    artist: Mapped[str] = mapped_column(String(160), nullable=False)
    album: Mapped[str | None] = mapped_column(String(200))
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)


class Playlist(Base):
    __tablename__ = "playlists"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user: Mapped["User"] = relationship(back_populates="playlists")


class PlaylistMusic(Base):
    __tablename__ = "playlist_musics"
    playlist_id: Mapped[int] = mapped_column(
        ForeignKey("playlists.id", ondelete="CASCADE"), primary_key=True
    )
    music_id: Mapped[int] = mapped_column(
        ForeignKey("musics.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    position: Mapped[int] = mapped_column(Integer, default=0)


def init_db() -> None:
    """Cria as tabelas caso ainda não existam."""
    Base.metadata.create_all(engine)
