from math import radians, sin, cos, asin, sqrt
from app.db import run_query


def haversine_km(lat1, lon1, lat2, lon2):
    p1, p2 = radians(lat1), radians(lat2)
    a = sin((p2 - p1) / 2) ** 2 + cos(p1) * cos(p2) * sin(radians(lon2 - lon1) / 2) ** 2
    return 6371.0 * 2 * asin(sqrt(a))


def origem(conta_id, args):
    """Ponto de referência do 'próximos a mim': GPS do navegador > endereço escolhido > principal."""
    lat, lng = args.get("lat", type=float), args.get("lng", type=float)
    if lat is not None and lng is not None and -90 <= lat <= 90 and -180 <= lng <= 180:
        return {"lat": lat, "lng": lng, "cidade": None, "fonte": "localização atual"}
    if not conta_id:
        return None
    eid = args.get("endereco_id", type=int)
    if eid:
        e = run_query("SELECT * FROM enderecos WHERE id=? AND conta_id=?", (eid, conta_id), fetchone=True)
    else:
        e = run_query("SELECT * FROM enderecos WHERE conta_id=? ORDER BY principal DESC, id LIMIT 1",
                      (conta_id,), fetchone=True)
    if not e:
        return None
    return {"lat": e["latitude"], "lng": e["longitude"], "cidade": e["cidade"], "fonte": e["apelido"]}


def filtrar_proximos(linhas, ref, raio_km):
    """Anota 'distancia_km' e mantém só o que está no raio (ou na mesma cidade, se faltar coordenada)."""
    saida = []
    for r in linhas:
        d = None
        if ref and ref["lat"] is not None and r.get("latitude") is not None and r.get("longitude") is not None:
            d = haversine_km(ref["lat"], ref["lng"], r["latitude"], r["longitude"])
            r["distancia_km"] = round(d, 1)
            if d <= raio_km:
                saida.append(r)
        elif ref and ref.get("cidade") and (r.get("cidade") or "").lower() == ref["cidade"].lower():
            r["distancia_km"] = None
            saida.append(r)
    saida.sort(key=lambda r: (r["distancia_km"] is None, r["distancia_km"] or 0))
    return saida


def anotar_distancia(linhas, ref):
    for r in linhas:
        r["distancia_km"] = None
        if ref and ref["lat"] is not None and r.get("latitude") is not None and r.get("longitude") is not None:
            r["distancia_km"] = round(haversine_km(ref["lat"], ref["lng"], r["latitude"], r["longitude"]), 1)
    return linhas
