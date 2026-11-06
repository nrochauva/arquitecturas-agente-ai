"""Comprueba el servidor MCP sin LLM: descubrimiento, acceso, denegación, fallos y latencia."""
import asyncio
import logging
import statistics
import time

from fastmcp.exceptions import ToolError

from dominio import INSTRUCCIONES, DATOS, consultar
from pydantic_mcp import SERVIDOR, crear_toolset, leer_instrucciones

SERVIDOR_ROTO = SERVIDOR.with_name('servidor_roto.py')
ARGS = {'corpus': 'demo', 'idioma': 'es', 'sistema': 'A'}
REPETICIONES = 200


async def probar_descubrimiento_y_acceso():
    toolset = crear_toolset()
    async with toolset:
        herramientas = sorted(t.name for t in await toolset.list_tools())
        assert herramientas == ['resultados', 'sistemas'], herramientas
        assert [str(r.uri) for r in await toolset.list_resources()] == ['asr://politica']
        assert [p.name for p in await toolset.list_prompts()] == ['comparar']

        # Sin esto, cambiar el transporte cambiaría también las instrucciones del modelo.
        assert await leer_instrucciones(toolset) == INSTRUCCIONES

        fila = await toolset.direct_call_tool('resultados', ARGS)
        assert fila == consultar(**ARGS) and fila['wer'] == 0.11
        ausente = await toolset.direct_call_tool('resultados', {**ARGS, 'sistema': 'D'})
        assert ausente['estado'] == 'sin_resultados'
        hay = await toolset.direct_call_tool('sistemas', {'corpus': 'demo', 'idioma': 'es'})
        assert hay['sin_resultados'] == ['D']

        try:
            await toolset.direct_call_tool('resultados', {**ARGS, 'corpus': 'privado'})
        except ToolError as error:
            assert 'Corpus no autorizado: privado' in str(error), error
        else:
            raise AssertionError('El servidor no denegó el corpus privado')
    print('OK descubrimiento, recurso, prompt, consulta y denegación con motivo')


async def probar_escenario():
    toolset = crear_toolset(ruta=DATOS.parent / 'escenarios/caso8.json')
    async with toolset:
        fila = await toolset.direct_call_tool('resultados', {**ARGS, 'sistema': 'B'})
    assert fila['estado'] == 'fila_invalida', fila
    print('OK el servidor recibe el escenario por entorno')


async def probar_fallos_transporte():
    for nombre, herramienta, args in (('colgado', 'resultados', ARGS),
                                      ('caido', 'sistemas', {'corpus': 'demo', 'idioma': 'es'})):
        toolset = crear_toolset(servidor=SERVIDOR_ROTO, read_timeout=2)
        inicio = time.perf_counter()
        try:
            async with toolset:
                await asyncio.wait_for(toolset.direct_call_tool(herramienta, args), timeout=15)
        except Exception as error:
            print(f'OK {nombre}: {type(error).__name__} a los '
                  f'{time.perf_counter() - inicio:.1f} s: {str(error)[:90]}')
        else:
            raise AssertionError(f'Fallo no detectado: {nombre}')


async def medir_latencia():
    """Sin modelo de por medio: compara solo el coste de la llamada."""
    directas, mcp = [], []
    for _ in range(REPETICIONES):
        inicio = time.perf_counter()
        consultar(**ARGS)
        directas.append(time.perf_counter() - inicio)
    toolset = crear_toolset()
    async with toolset:
        for _ in range(REPETICIONES):
            inicio = time.perf_counter()
            await toolset.direct_call_tool('resultados', ARGS)
            mcp.append(time.perf_counter() - inicio)
    print(f'Latencia mediana en {REPETICIONES} llamadas: directa '
          f'{statistics.median(directas) * 1000:.2f} ms, MCP {statistics.median(mcp) * 1000:.2f} ms')


async def main():
    logging.disable(logging.CRITICAL)  # El cliente registra como error los fallos provocados aquí.
    await probar_descubrimiento_y_acceso()
    await probar_escenario()
    await probar_fallos_transporte()
    await medir_latencia()


if __name__ == '__main__':
    asyncio.run(main())
