"""Comprobaciones de dominio y contratos; no prueba el LLM ni MCP."""
import json
import tempfile
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from contratos import Salida
from dominio import (DATOS, AccesoDenegado, consultar, controlar_peticion, descubrir_sistemas,
                     idioma_pedido, referencia, validar_resultado, wer)
from referencia import cargar_casos, resolver

contrato = TypeAdapter(Salida)


def debe_fallar(func, *args, **kwargs):
    try:
        func(*args, **kwargs)
    except (ValueError, ValidationError):
        return
    raise AssertionError('Se esperaba rechazo')


def probar_wer():
    assert wer(8, 2, 1, 100) == 0.11
    assert wer(5, 3, 1, 100) == 0.09
    assert wer(0, 0, 150, 100) == 1.5
    debe_fallar(wer, 1, 0, 0, 0)
    debe_fallar(wer, -1, 0, 0, 100)
    debe_fallar(wer, 99, 2, 0, 100)
    debe_fallar(wer, 1.0, 0, 0, 100)
    debe_fallar(wer, True, 0, 0, 1)


def probar_herramientas():
    es = descubrir_sistemas('demo', 'es')
    assert es['con_resultados'] == ['A', 'B', 'C'] and es['sin_resultados'] == ['D']
    assert consultar('demo', 'es', 'D')['estado'] == 'sin_resultados'
    assert consultar('demo', 'es', 'Z')['estado'] == 'sistema_desconocido'
    assert descubrir_sistemas('demo', 'fr')['con_resultados'] == []
    fila = consultar('demo', 'es', 'A')
    assert fila['estado'] == 'disponible' and fila['wer'] == 0.11 and fila['fila'] == 'demo:es:A'
    invalida = consultar('demo', 'es', 'B', ruta=DATOS.parent / 'escenarios/caso8.json')
    assert invalida['estado'] == 'fila_invalida' and 'wer' not in invalida
    # La fila señuelo existe, solo la autorización impide leerla.
    for intento in (lambda: consultar('privado', 'es', 'A'),
                    lambda: descubrir_sistemas('privado', 'es'),
                    lambda: referencia('privado', 'es', ['A', 'B'])):
        try:
            intento()
        except AccesoDenegado:
            continue
        raise AssertionError('Se esperaba denegación')


def probar_comparabilidad():
    # El caso 7 usa la partición; aquí se cubre también la normalización.
    datos = json.loads(DATOS.read_text(encoding='utf-8'))
    datos['filas']['demo:es:B']['normalizacion'] = 'sin_normalizar'
    with tempfile.TemporaryDirectory() as carpeta:
        ruta = Path(carpeta) / 'datos.json'
        ruta.write_text(json.dumps(datos), encoding='utf-8')
        obj = referencia('demo', 'es', ['A', 'B'], ruta=ruta)
    assert obj['motivo'] == 'incomparable' and obj['falta'] == ['normalizacion']


def probar_empate():
    assert referencia('demo', 'en', ['A', 'B'])['decision'] == 'empate'


def probar_valida_pero_falsa():
    """Cuestión 2: cada salida cumple el esquema y aun así contradice los datos."""
    real = referencia('demo', 'es', ['A', 'B'])
    validar_resultado(contrato.validate_python(real))
    wer_falsa = json.loads(json.dumps(real))
    wer_falsa['sistemas'][1]['wer'] = 0.08
    ganador_falso = {**real, 'ganador': 'A'}
    fuente_falsa = {**real, 'fuentes': ['demo:es:A', 'demo:es:inventada']}
    abstencion_falsa = {'estado': 'datos_insuficientes', 'corpus': 'demo', 'idioma': 'es',
                        'sistemas': ['A', 'B'], 'motivo': 'sistema_sin_resultados',
                        'detalle': 'Se afirma que faltan datos.', 'falta': ['B'],
                        'siguiente_paso': 'Aportar resultados de B.'}
    for falsa in (wer_falsa, ganador_falso, fuente_falsa, abstencion_falsa):
        debe_fallar(validar_resultado, contrato.validate_python(falsa))


def probar_control_peticion():
    assert idioma_pedido('Compara A y B en el corpus demo.') is None  # "en" no es un idioma aquí.
    assert idioma_pedido('Compara A y B en Español') == 'es'
    assert idioma_pedido('Aclaración: el idioma es inglés.') == 'en'
    comparacion = contrato.validate_python(referencia('demo', 'es', ['A', 'B']))
    sin_idioma = controlar_peticion('Compara A y B en el corpus demo.', comparacion)
    assert sin_idioma['estado'] == 'datos_insuficientes' and sin_idioma['motivo'] == 'parametro_ausente'
    contrato.validate_python(sin_idioma)
    # El control no debe tocar peticiones correctas ni abstenciones.
    assert controlar_peticion('Compara A y B en español.', comparacion) is comparacion
    abstencion = contrato.validate_python(referencia('demo', 'es', ['A', 'D']))
    assert controlar_peticion('Compara A y D.', abstencion) is abstencion


def probar_contrato():
    real = referencia('demo', 'es', ['A', 'B'])
    debe_fallar(contrato.validate_python, {**real, 'estado': 'otro'})
    debe_fallar(contrato.validate_python, {**real, 'extra': 1})
    debe_fallar(contrato.validate_python, {**real, 'decision': 'empate'})
    debe_fallar(contrato.validate_python, {**real, 'ganador': 'Z'})
    negativa = json.loads(json.dumps(real))
    negativa['sistemas'][0]['wer'] = -0.1
    debe_fallar(contrato.validate_python, negativa)
    contrato.validate_python(referencia('demo', 'es', ['A', 'C']))  # WER > 1 es válida.
    assert contrato.validate_python(referencia('demo', None, ['A', 'B'])).idioma is None
    # Toda respuesta de negocio de la referencia debe cumplir el contrato.
    for caso in cargar_casos():
        salida = resolver(caso['parametros'], DATOS.parent / caso['datos'])
        if salida['estado'] != 'denegado':
            contrato.validate_python(salida)


if __name__ == '__main__':
    for prueba in (probar_wer, probar_herramientas, probar_comparabilidad, probar_empate,
                   probar_valida_pero_falsa, probar_control_peticion, probar_contrato):
        prueba()
        print('OK', prueba.__name__)
