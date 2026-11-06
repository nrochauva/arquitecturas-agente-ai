"""Agente con salida tipada, contexto controlado y verificación de dominio."""
import os
from dataclasses import dataclass
from pathlib import Path
from pydantic_ai import Agent, RunContext
from pydantic_ai.settings import ModelSettings
from pydantic_ai.usage import UsageLimits
from contratos import Comparacion, DatosInsuficientes
from dominio import (CORPUS_AUTORIZADOS, consultar, descubrir_sistemas, validar_resultado,
                     PREGUNTA, INSTRUCCIONES)

@dataclass
class Dependencias:
    # Quedan en el programa: el modelo no ve estos valores ni puede cambiarlos.
    corpus_autorizados: frozenset = CORPUS_AUTORIZADOS
    ruta_datos: Path | None = None

def crear_agente():
    agent = Agent(os.environ['PYDANTIC_MODEL'], deps_type=Dependencias,
                  output_type=[Comparacion, DatosInsuficientes], instructions=INSTRUCCIONES,
                  retries=1, model_settings=ModelSettings(temperature=0.2))

    @agent.tool
    def sistemas(ctx: RunContext[Dependencias], corpus: str, idioma: str) -> dict:
        """Lista qué sistemas del catálogo tienen resultados en un corpus e idioma.

        Args:
            corpus: Corpus a consultar, solo demo está autorizado.
            idioma: Código de idioma, por ejemplo es o en.
        """
        return descubrir_sistemas(corpus, idioma, ctx.deps.corpus_autorizados, ctx.deps.ruta_datos)

    @agent.tool
    def resultados(ctx: RunContext[Dependencias], corpus: str, idioma: str, sistema: str) -> dict:
        """Devuelve conteos, metadatos y WER de un sistema, o el estado que explica su ausencia.

        Args:
            corpus: Corpus a consultar, solo demo está autorizado.
            idioma: Código de idioma, por ejemplo es o en.
            sistema: Sistema del catálogo, por ejemplo A.
        """
        return consultar(corpus, idioma, sistema, ctx.deps.corpus_autorizados, ctx.deps.ruta_datos)
    return agent

if __name__ == '__main__':
    agent = crear_agente()
    result = agent.run_sync(PREGUNTA, deps=Dependencias(),
                            usage_limits=UsageLimits(request_limit=8))
    # Rechazo determinista; no implica reparación automática.
    validar_resultado(result.output)
    print(result.output.model_dump_json(indent=2))
    # Guardar solo trazas revisadas, evitando datos o secretos sensibles.
    print('Uso:', result.usage)
