"""Validações e conversões de campos usadas por mais de um serviço.

As mesmas regras existem em static/js/mascaras.js para avisar o usuário antes
do envio; aqui elas são conferidas de novo, porque o navegador pode ser
contornado.
"""
import re
from datetime import date, datetime

EMAIL_VALIDO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def somente_digitos(texto):
    return re.sub(r"\D", "", texto or "")


def cpf_valido(cpf):
    digitos = somente_digitos(cpf)
    if len(digitos) != 11 or digitos == digitos[0] * 11:
        return False
    for tamanho in (9, 10):
        soma = sum(int(digitos[i]) * (tamanho + 1 - i) for i in range(tamanho))
        if (soma * 10) % 11 % 10 != int(digitos[tamanho]):
            return False
    return True


def formatar_cpf(cpf):
    d = somente_digitos(cpf)
    return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"


def formatar_telefone(telefone):
    """Devolve (47) 99123-4567 ou (47) 3333-4444; None se não tiver 10 ou 11 dígitos."""
    d = somente_digitos(telefone)
    if len(d) == 11:
        return f"({d[:2]}) {d[2:7]}-{d[7:]}"
    if len(d) == 10:
        return f"({d[:2]}) {d[2:6]}-{d[6:]}"
    return None


def converter_data(texto):
    """'2026-03-14' (formato do <input type="date">) -> date; None se vazio. ValueError se inválida."""
    texto = (texto or "").strip()
    return date.fromisoformat(texto) if texto else None


def converter_hora(texto):
    """'08:30' (formato do <input type="time">) -> time; None se vazio. ValueError se inválida."""
    texto = (texto or "").strip()
    return datetime.strptime(texto[:5], "%H:%M").time() if texto else None
