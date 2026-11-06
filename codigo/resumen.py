"""Resume las mediciones sin llamar a ningún modelo y escribe los CSV que usa la memoria.

Los cortes de infraestructura no cuentan como fallo del modelo: se excluyen de los
porcentajes y se informan aparte. T1 es la excepción, porque ahí el corte es lo esperado.
"""
import csv
import json
import statistics

from dominio import DATOS

RESULTADOS = DATOS.parents[1] / 'resultados'
CONFIGURACIONES = ('referencia', 'smolagents', 'pydantic_local', 'pydantic_mcp')


def leer(nombre: str) -> list[dict]:
    with (RESULTADOS / nombre).open(encoding='utf-8', newline='') as fichero:
        return list(csv.DictReader(fichero))


def validas(filas: list[dict]) -> list[dict]:
    return [f for f in filas if f['estado'] != 'fallo_infraestructura' or f['caso'] == 'T1']


def mediana(filas: list[dict], campo: str):
    valores = [float(f[campo]) for f in filas if f[campo].replace('.', '', 1).isdigit()]
    return round(statistics.median(valores), 2) if valores else 'no disponible'


def por_configuracion(filas: list[dict]) -> list[dict]:
    salida = []
    for nombre in CONFIGURACIONES:
        todas = [f for f in filas if f['configuracion'] == nombre]
        grupo = validas(todas)
        conteo = lambda campo: sum(f[campo] == 'si' for f in grupo)
        salida.append({'configuracion': nombre, 'ejecuciones_validas': len(grupo),
                       'cortes_infraestructura': len(todas) - len(grupo),
                       'exito_tarea': conteo('exito_tarea'),
                       'validez_estructural': conteo('validez_estructural'),
                       'coherencia_evidencia': conteo('coherencia_evidencia'),
                       'permisos': conteo('permisos'),
                       'mediana_tiempo_s': mediana(grupo, 'tiempo_s'),
                       'mediana_solicitudes': mediana(grupo, 'solicitudes'),
                       'mediana_herramientas': mediana(grupo, 'llamadas_herramientas'),
                       'mediana_tokens_entrada': mediana(grupo, 'tokens_entrada'),
                       'mediana_tokens_salida': mediana(grupo, 'tokens_salida')})
    return salida


def veces_control(configuracion: str, caso: str) -> int:
    trazas = (RESULTADOS / 'trazas' / 'despues').glob(f'{configuracion}_caso{caso}_r*.json')
    return sum(json.loads(t.read_text(encoding='utf-8'))['control_intervino'] for t in trazas)


def antes_despues(antes: list[dict], despues: list[dict]) -> list[dict]:
    salida = []
    for nombre in CONFIGURACIONES:
        for caso in ('6', '1', '6b'):
            grupo_a = [f for f in validas(antes) if (f['configuracion'], f['caso']) == (nombre, caso)]
            grupo_d = [f for f in validas(despues) if (f['configuracion'], f['caso']) == (nombre, caso)]
            salida.append({'configuracion': nombre, 'caso': caso,
                           'exito_antes': sum(f['exito_tarea'] == 'si' for f in grupo_a),
                           'validas_antes': len(grupo_a),
                           'exito_despues': sum(f['exito_tarea'] == 'si' for f in grupo_d),
                           'validas_despues': len(grupo_d),
                           'coherentes_despues': sum(f['coherencia_evidencia'] == 'si' for f in grupo_d),
                           'control_intervino': veces_control(nombre, caso)})
    return salida


def guardar(nombre: str, filas: list[dict]) -> None:
    with (RESULTADOS / nombre).open('w', encoding='utf-8', newline='') as fichero:
        escritor = csv.DictWriter(fichero, fieldnames=list(filas[0]))
        escritor.writeheader()
        escritor.writerows(filas)


if __name__ == '__main__':
    antes, despues = leer('mediciones.csv'), leer('despues.csv')
    configuraciones = por_configuracion(antes)
    comparacion = antes_despues(antes, despues)
    guardar('resumen_configuraciones.csv', configuraciones)
    guardar('antes_despues.csv', comparacion)
    for fila in configuraciones + comparacion:
        print(fila)
