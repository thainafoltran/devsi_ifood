from math import ceil
from app.services.geo import haversine_km

FRANQUIA_KM = 5          # até 5 km só a taxa do restaurante
VALOR_KM_EXTRA = 1.50    # R$ por km adicional
LIMITE_KM = 20           # acima disso o restaurante não entrega


def calcular_frete(restaurante, endereco, tipo_entrega):
    """Retorna (valor, distancia_km). Lança ValueError se fora da área de entrega."""
    if tipo_entrega == "retirada":
        return 0.0, None
    taxa = float(restaurante["taxa_entrega"])
    if (endereco and endereco["latitude"] is not None and endereco["longitude"] is not None
            and restaurante["latitude"] is not None and restaurante["longitude"] is not None):
        d = haversine_km(restaurante["latitude"], restaurante["longitude"],
                         endereco["latitude"], endereco["longitude"])
        if d > LIMITE_KM:
            raise ValueError(f"Endereço fora da área de entrega ({d:.1f} km; máximo {LIMITE_KM} km).")
        extra = max(0, ceil(d - FRANQUIA_KM)) * VALOR_KM_EXTRA
        return round(taxa + extra, 2), round(d, 1)
    return round(taxa, 2), None
