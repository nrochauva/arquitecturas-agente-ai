"""Servidor averiado a propósito para probar fallos de transporte. Solo se usa en pruebas."""
import os
import time
from mcp.server.fastmcp import FastMCP
from dominio import POLITICA, ROL

app = FastMCP('resultados-asr-roto')

# Prompt y recurso funcionan: la avería debe aparecer con el agente ya en marcha.
@app.resource('asr://politica')
def politica() -> str:
    return POLITICA

@app.prompt()
def comparar() -> str:
    return ROL

@app.tool()
def sistemas(corpus: str, idioma: str) -> dict:
    """Simula un proceso servidor que muere a mitad de la llamada."""
    os._exit(1)

@app.tool()
def resultados(corpus: str, idioma: str, sistema: str) -> dict:
    """Simula un servidor colgado que nunca responde."""
    time.sleep(3600)
    return {}

if __name__ == '__main__':
    app.run(transport='stdio')
