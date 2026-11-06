"""Servidor de lectura local. stdout queda reservado al protocolo MCP.
Usa FastMCP del SDK oficial mcp; no el import del paquete independiente fastmcp.
"""
from mcp.server.fastmcp import FastMCP
from dominio import consultar, descubrir_sistemas, POLITICA, ROL

app = FastMCP('resultados-asr')

@app.tool()
def sistemas(corpus: str, idioma: str) -> dict:
    """Lista qué sistemas del catálogo tienen resultados en un corpus e idioma.

    Args:
        corpus: Corpus a consultar, solo demo está autorizado.
        idioma: Código de idioma, por ejemplo es o en.
    """
    return descubrir_sistemas(corpus, idioma)

@app.tool()
def resultados(corpus: str, idioma: str, sistema: str) -> dict:
    """Devuelve conteos, metadatos y WER de un sistema, o el estado que explica su ausencia.

    Args:
        corpus: Corpus a consultar, solo demo está autorizado.
        idioma: Código de idioma, por ejemplo es o en.
        sistema: Sistema del catálogo, por ejemplo A.
    """
    return consultar(corpus, idioma, sistema)

@app.resource('asr://politica')
def politica() -> str:
    """Describe los límites de interpretación de los resultados."""
    return POLITICA

@app.prompt()
def comparar() -> str:
    """Plantilla seleccionable por el host; no se aplica automáticamente."""
    return ROL

if __name__ == '__main__':
    app.run(transport='stdio')
