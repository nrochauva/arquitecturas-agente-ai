# Módulo 5 · Agentes con IA

Asistente que compara sistemas ASR por idioma con smolagents, Pydantic AI y MCP.
Los datos son sintéticos y no se ejecuta ASR. La memoria está en `latex/`.

## Entorno

Se usó Python 3.13.14. Las dependencias exactas están en `requirements-lock.txt`.
Los comandos se ejecutan desde la raíz del proyecto.

```bash
uv venv --python 3.13 .venv
uv pip install --python .venv/bin/python -r codigo/requirements-lock.txt
cp .env.example .env
```

Después se añade la clave en `GEMINI_API_KEY` dentro de `.env`, que git ignora.
No hay ninguna clave en el repositorio.

## Demostración sin red

Desde `codigo`, sin clave ni modelo.

```bash
../.venv/bin/python referencia.py
../.venv/bin/python smoke_offline.py
../.venv/bin/python probar_mcp.py
```

El primero resuelve los casos con parámetros explícitos y solo usa la biblioteca
estándar. El segundo prueba dominio y contratos, incluidas salidas válidas pero falsas.
El tercero prueba el servidor MCP, la denegación, los fallos de transporte y la latencia.
La validación semántica comprueba valores, decisión y fuentes, y no juzga la prosa.

## Ejecución con modelo

Desde la raíz del proyecto.

```bash
correr() {
  VIRTUAL_ENV=$PWD/.venv PYDANTIC_AI_NO_BANNER=1 uv run --no-project --active --env-file .env \
    python "codigo/$1" "${@:2}"
}
correr probar_modelo.py
correr smol_demo.py
correr pydantic_demo.py
correr pydantic_mcp.py
correr experimento.py
correr experimento.py --casos 1,6,6b --salida despues.csv --control
correr resumen.py
```

`experimento.py` espera 32 segundos entre ejecuciones por los límites del nivel gratuito.
Se reanuda solo, salta lo ya medido y repite lo cortado por infraestructura, salvo T1.
Sin opciones genera `resultados/mediciones.csv`, y con `--control` aplica la modificación.
`resumen.py` no llama al modelo y genera `antes_despues.csv` y `resumen_configuraciones.csv`.

## Configuración usada

| Elemento | Valor |
|---|---|
| Modelo | `gemini-3.5-flash-lite`, nivel gratuito |
| `SMOL_MODEL` | `gemini/gemini-3.5-flash-lite` |
| `PYDANTIC_MODEL` | `google:gemini-3.5-flash-lite` |
| Límites | 8 solicitudes, 1 reintento, 6 pasos, 120 segundos por ejecución |
| Temperatura | 0,2, fijada también en `casos.json` |
| Transporte MCP | stdio |
| Revisión MCP | 2025-11-25, la negociada por este cliente |
| Paquete `mcp` | 1.30.0 |
| Paquete `pydantic-ai-slim` | 2.66.0 |
| Paquete `smolagents` | 1.26.0 |
| Paquete `litellm` | 1.99.4 |

La versión de un paquete no identifica por sí sola la revisión del protocolo.
`mcp` no pasa a la serie 2.x porque elimina `mcp.server.fastmcp` y, en la prueba
realizada, oculta el motivo de los errores de herramienta. `litellm` 1.108 falla con
herramientas sobre `mcp` 1.30 sin que el instalador lo detecte, por eso se fija 1.99.4.

## Resultados

Todo está en `resultados/` en la raíz del proyecto. `mediciones.csv` es el estado anterior
a la modificación y `despues.csv` el posterior. Las trazas están en `trazas/mediciones` y
`trazas/despues`. Los cortes por error 503 quedan como filas `fallo_infraestructura` y se
excluyen de los porcentajes. Las tres trazas comentadas están en el anexo de la memoria.

La fila del caso 9 de Pydantic AI local se corrigió tras medir, de 0 a 1 llamadas,
recalculando desde su traza. El contador original omitía las llamadas denegadas.

## No realizado

CodeAgent no se ejecutó por decisión de alcance. La rama `SMOL_CODE=1` de `smol_demo.py`
requeriría Docker y `smolagents[docker]` y no forma parte de la evaluación. Tampoco se
comprobó el acceso a las herramientas dentro del contenedor. No se probó transporte HTTP.
El servidor colgado se probó sin LLM y T1 ejercitó el servidor caído con el agente.
El coste figura como no disponible porque el proveedor no lo facilitó en la ejecución.

## Cambios respecto al código proporcionado

El código de partida es el proporcionado en el módulo. Esta tabla resume qué cambió y por qué.

| Fichero | Cambio | Motivo |
|---|---|---|
| `datos.json` | Metadatos, idiomas, sistemas C y D, filas señuelo | Comparar por idioma y detectar fugas |
| `dominio.py` | Descubrimiento, ausencia como estado, regla general, validación general, control de la petición. `wer` no cambia | Abstención y comprobación semántica |
| `contratos.py` | Unión discriminada en lugar de `Resultado` | Dos resultados de negocio |
| `smol_demo.py`, `pydantic_demo.py` | Dos herramientas, contrato común, sin `calcular_wer` | La WER viaja con la fila |
| `servidor_mcp.py`, `pydantic_mcp.py` | Mismas herramientas, recurso y prompt que el host incorpora de forma explícita | Mismas instrucciones que en local |
| `referencia.py`, `smoke_offline.py` | Todos los casos y salidas válidas pero falsas | Referencia y pruebas sin LLM |
| `requirements.txt` | Versiones fijadas de `mcp` y `litellm` | Compatibilidad comprobada |

Los ficheros nuevos son `casos.json`, `escenarios/`, `experimento.py`, `resumen.py`,
`probar_modelo.py`, `probar_mcp.py`, `servidor_roto.py` y `requirements-lock.txt`.
