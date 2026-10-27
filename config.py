import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "chave-de-desenvolvimento")
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)  # um turno de trabalho

    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "clinica_medica")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")

    # valor sugerido no atendimento enquanto o banco não guarda o valor da consulta
    # (item 5 da seção 5.2 do plano); o médico pode alterar em cada atendimento
    VALOR_CONSULTA_PADRAO = os.getenv("VALOR_CONSULTA_PADRAO", "150.00")
