"""Demostración sin LLM, sin SDK externos y sin credenciales."""
import json
import math
from dominio import DATOS, AccesoDenegado, referencia, validar_resultado


def cargar_casos() -> list[dict]:
    return json.loads(DATOS.with_name('casos.json').read_text(encoding='utf-8'))['casos']


def resolver(parametros: dict, ruta=None) -> dict:
    """Recibe los parámetros explícitos del caso, no interpreta lenguaje natural."""
    try:
        return referencia(parametros['corpus'], parametros['idioma'], parametros['sistemas'], ruta=ruta)
    except AccesoDenegado as error:
        return {'estado': 'denegado', 'motivo': str(error)}


def cumple_esperado(obj: dict, esperado: dict) -> bool:
    """Éxito de tarea frente al caso. Compara campos de decisión, nunca texto."""
    if obj['estado'] != esperado['estado']:
        return False
    if esperado['estado'] == 'datos_insuficientes':
        return obj['motivo'] == esperado['motivo']
    if esperado['estado'] == 'denegado':
        return True
    medidas = {m['sistema']: m['wer'] for m in obj['sistemas']}
    return (obj['decision'] == esperado['decision'] and obj['ganador'] == esperado['ganador']
            and medidas.keys() == esperado['wer'].keys()
            and all(math.isclose(medidas[s], w, abs_tol=1e-9) for s, w in esperado['wer'].items())
            and set(obj['fuentes']) == set(esperado['fuentes']))


if __name__ == '__main__':
    correcto = True
    for caso in cargar_casos():
        ruta = DATOS.parent / caso['datos']
        salida = resolver(caso['parametros'], ruta)
        if salida['estado'] != 'denegado':
            validar_resultado(salida, ruta=ruta)
        exito = cumple_esperado(salida, caso['esperado'])
        correcto &= exito
        detalle = salida.get('ganador') or salida.get('decision') or salida.get('motivo')
        print(f"caso {caso['id']:>3} {'OK' if exito else 'FALLO':5} {salida['estado']:20} {detalle}")
    raise SystemExit(0 if correcto else 1)
