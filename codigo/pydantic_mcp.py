"""Mismo contrato, herramientas publicadas mediante un servidor stdio.
MCPToolset es la API de la documentación consultada; ver compatibilidad en LEEME.
"""
import asyncio
import os
import sys
from pathlib import Path
from fastmcp.client.transports import PythonStdioTransport
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.settings import ModelSettings
from pydantic_ai.usage import UsageLimits
from contratos import Comparacion, DatosInsuficientes
from dominio import PREGUNTA, validar_resultado

SERVIDOR = Path(__file__).with_name('servidor_mcp.py').resolve()

def crear_toolset(ruta=None, servidor=SERVIDOR, read_timeout=30):
    # El escenario lo elige el programa y llega por entorno: el modelo nunca ve rutas.
    transporte = PythonStdioTransport(servidor, python_cmd=sys.executable,
                                      env={'ASR_DATOS': str(ruta)} if ruta else None)
    # 'error' y no 'retry': una denegación debe terminar la ejecución, no invitar a insistir.
    return MCPToolset(transporte, read_timeout=read_timeout, tool_error_behavior='error')

async def leer_instrucciones(toolset) -> str:
    """El host incorpora prompt y recurso de forma explícita: publicarlos no los añade solos."""
    prompt = await toolset.get_prompt('comparar')
    politica = await toolset.read_resource('asr://politica')
    return f'{prompt.messages[0].content.content} {politica}'

async def crear_agente(toolset):
    return Agent(os.environ['PYDANTIC_MODEL'], toolsets=[toolset],
                 output_type=[Comparacion, DatosInsuficientes],
                 instructions=await leer_instrucciones(toolset),
                 retries=1, model_settings=ModelSettings(temperature=0.2))

async def main():
    toolset = crear_toolset()
    async with toolset:
        agent = await crear_agente(toolset)
        result = await agent.run(PREGUNTA, usage_limits=UsageLimits(request_limit=8))
        validar_resultado(result.output)
        print(result.output.model_dump_json(indent=2))
        print('Uso:', result.usage)

if __name__ == '__main__':
    asyncio.run(main())
