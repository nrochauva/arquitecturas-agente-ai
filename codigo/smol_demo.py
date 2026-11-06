"""Adaptador smolagents. Requiere proveedor/modelo configurado en el entorno.
Configuración inicial con llamadas a funciones; ver README para CodeAgent.
"""
import json
import os
from pydantic import TypeAdapter
from smolagents import CodeAgent, LiteLLMModel, ToolCallingAgent, tool
from contratos import Salida
from dominio import consultar, descubrir_sistemas, validar_resultado, PREGUNTA, INSTRUCCIONES

contrato = TypeAdapter(Salida)
# smolagents no impone un tipo de salida: el contrato se exige por texto y se valida después.
FORMATO = ('Termina con final_answer y un único objeto JSON que cumpla este esquema: '
           + json.dumps(contrato.json_schema(), ensure_ascii=False))

@tool
def sistemas(corpus: str, idioma: str) -> dict:
    """Lista qué sistemas del catálogo tienen resultados en un corpus e idioma.

    Args:
        corpus: Corpus a consultar, solo demo está autorizado.
        idioma: Código de idioma, por ejemplo es o en.
    """
    return descubrir_sistemas(corpus, idioma)

@tool
def resultados(corpus: str, idioma: str, sistema: str) -> dict:
    """Devuelve conteos, metadatos y WER de un sistema, o el estado que explica su ausencia.

    Args:
        corpus: Corpus a consultar, solo demo está autorizado.
        idioma: Código de idioma, por ejemplo es o en.
        sistema: Sistema del catálogo, por ejemplo A.
    """
    return consultar(corpus, idioma, sistema)

def crear_modelo():
    return LiteLLMModel(model_id=os.environ['SMOL_MODEL'], temperature=0.2)

def crear_agente():
    return ToolCallingAgent(tools=[sistemas, resultados], model=crear_modelo(), max_steps=6,
                            verbosity_level=0)

def tarea(peticion: str) -> str:
    return f'{INSTRUCCIONES}\n{FORMATO}\n{peticion}'

def interpretar(respuesta):
    """Aplica el contrato común. Una respuesta que no lo cumpla lanza ValidationError."""
    if isinstance(respuesta, str):
        return contrato.validate_json(respuesta)
    return contrato.validate_python(respuesta)

if __name__ == '__main__':
    if os.environ.get('SMOL_CODE') == '1':
        # No usar el intérprete local como frontera de seguridad.
        # Esta variante requiere Docker y smolagents[docker]. No forma parte de la evaluación.
        with CodeAgent(tools=[sistemas, resultados], model=crear_modelo(),
                       max_steps=6, executor_type='docker') as agent:
            print(agent.run(tarea(PREGUNTA)))
    else:
        result = crear_agente().run(tarea(PREGUNTA), return_full_result=True)
        salida = interpretar(result.output)
        validar_resultado(salida)
        print(salida.model_dump_json(indent=2))
        print('Uso:', result.token_usage)
