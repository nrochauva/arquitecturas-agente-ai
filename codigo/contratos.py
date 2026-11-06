"""Contrato estructural. La verificación de hechos la hace dominio.validar_resultado."""
from typing import Annotated, Literal, Union
from pydantic import BaseModel, ConfigDict, Field, model_validator

Motivo = Literal['parametro_ausente', 'idioma_sin_resultados', 'sistema_sin_resultados',
                 'fila_invalida', 'incomparable']


class Estricto(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class MedidaWER(Estricto):
    sistema: str = Field(min_length=1)
    wer: float = Field(ge=0, allow_inf_nan=False)  # Sin cota superior: WER > 1 es válida.
    fuente: str = Field(min_length=1)


class Comparacion(Estricto):
    """Dos o más sistemas comparables, con su decisión y su procedencia."""
    estado: Literal['comparacion']
    corpus: str
    idioma: str
    sistemas: list[MedidaWER] = Field(min_length=2)
    decision: Literal['ganador', 'empate']
    ganador: str | None
    fuentes: list[str] = Field(min_length=2)
    limitaciones: str = Field(min_length=10)

    @model_validator(mode='after')
    def _ganador_coherente(self):
        if (self.decision == 'empate') != (self.ganador is None):
            raise ValueError('Un empate no lleva ganador y una victoria sí')
        if self.ganador is not None and self.ganador not in [m.sistema for m in self.sistemas]:
            raise ValueError('El ganador debe ser uno de los sistemas comparados')
        return self


class DatosInsuficientes(Estricto):
    """Abstención. No admite ganador ni métricas, por construcción."""
    estado: Literal['datos_insuficientes']
    corpus: str
    idioma: str | None  # En el caso 6 no existe: obligarlo forzaría a inventarlo.
    sistemas: list[str]
    motivo: Motivo
    detalle: str = Field(min_length=10)
    falta: list[str]
    siguiente_paso: str = Field(min_length=10)


Salida = Annotated[Union[Comparacion, DatosInsuficientes], Field(discriminator='estado')]
