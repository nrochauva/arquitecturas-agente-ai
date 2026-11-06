"""Prueba de integración de la fase 1: llamada a herramienta y salida estructurada.
Demuestra que el modelo responde desde ambas librerías, no evalúa su capacidad.
Uso desde la raíz del proyecto:
VIRTUAL_ENV=$PWD/.venv PYDANTIC_AI_NO_BANNER=1 uv run --no-project --active --env-file .env \
    python codigo/probar_modelo.py
"""
import json
import os

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings
from pydantic_ai.usage import UsageLimits
from smolagents import LiteLLMModel, ToolCallingAgent, tool

# Ajena a los diez casos para no observar salidas del protocolo antes de ejecutarlo.
PETICION = 'Usa la herramienta para leer el valor del código Z9 e informa de su valor y su código.'


class Salida(BaseModel):
    codigo: str
    valor: int


def leer(codigo: str) -> int:
    return {'Z9': 1234}[codigo]


def con_pydantic() -> None:
    agente = Agent(os.environ['PYDANTIC_MODEL'], output_type=Salida, retries=1,
                   model_settings=ModelSettings(temperature=0.2))

    @agente.tool_plain
    def leer_valor(codigo: str) -> int:
        """Devuelve el valor asociado a un código."""
        return leer(codigo)

    r = agente.run_sync(PETICION, usage_limits=UsageLimits(request_limit=4))
    u = r.usage
    assert r.output.valor == 1234 and u.tool_calls >= 1, r.output
    print('pydantic-ai OK', r.output.model_dump(), 'solicitudes', u.requests,
          'herramientas', u.tool_calls, 'tokens', u.input_tokens, u.output_tokens)


def con_smolagents() -> None:
    @tool
    def leer_valor(codigo: str) -> int:
        """Devuelve el valor asociado a un código.

        Args:
            codigo: Código que se quiere leer.
        """
        return leer(codigo)

    modelo = LiteLLMModel(model_id=os.environ['SMOL_MODEL'], temperature=0.2)
    agente = ToolCallingAgent(tools=[leer_valor], model=modelo, max_steps=4, verbosity_level=0)
    r = agente.run(PETICION + ' Responde con un JSON con las claves codigo y valor.',
                   return_full_result=True)
    salida = r.output if isinstance(r.output, dict) else json.loads(r.output)
    assert int(salida['valor']) == 1234, salida
    print('smolagents OK', salida, 'tokens', r.token_usage)


if __name__ == '__main__':
    con_pydantic()
    con_smolagents()
