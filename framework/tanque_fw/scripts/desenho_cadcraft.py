"""PILOTO: folha de conjunto do tanque-base desenhada no CADCraft (sem janela).

Le o mesmo SPEC da REV.02 (`projeto_rev02`) e manda os comandos de desenho ao
`cadcraft-cli mcp` por stdio: planta e elevacao lateral em 1:10 numa folha A1,
com cotas, lista de pecas, notas e carimbo. Grava DXF, DWG e PDF.

Uso: python desenho_cadcraft.py <pasta de saida>

E' um piloto de montagem de folha: nao substitui as pranchas emitidas por
`pranchas_tanque.py` (Blender + Bonsai), que saem do modelo 3D.
"""
import datetime
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import projeto_rev02 as P  # noqa: E402

CLI = os.environ.get("CADCRAFT_CLI") or os.path.join(
    os.environ.get("LOCALAPPDATA", ""), "Programs", "CADCraft", "cadcraft-cli.exe")
ESCALA = 10.0          # 1:10
E0 = -1800.0           # cota z = 0 da elevacao, em y do espaco de modelo


class CadCraft:
    """Sessao sem janela do CADCraft pelo protocolo MCP (JSON por linha)."""

    def __init__(self):
        self.p = subprocess.Popen([CLI, "mcp"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  encoding="utf-8")
        self.n = 0
        self._chama("initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                                   "clientInfo": {"name": "tanque_fw", "version": "1"}})
        self.p.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"})
                           + "\n")
        self.p.stdin.flush()

    def _chama(self, metodo, params):
        self.n += 1
        self.p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": self.n, "method": metodo,
                                       "params": params}) + "\n")
        self.p.stdin.flush()
        while True:
            linha = self.p.stdout.readline()
            if not linha:
                raise RuntimeError("o CADCraft fechou a conexao em %s" % metodo)
            r = json.loads(linha)
            if r.get("id") == self.n:
                if "error" in r:
                    raise RuntimeError("%s %s: %s" % (metodo, params, r["error"]))
                return r["result"]

    def cmd(self, comando, **params):
        r = self._chama("tools/call", {"name": "execute",
                                       "arguments": {"command": comando, "params": params}})
        texto = r["content"][0]["text"] if r.get("content") else ""
        if r.get("isError"):
            raise RuntimeError("%s %s: %s" % (comando, params, texto))
        try:
            return json.loads(texto)
        except ValueError:
            return texto

    def fecha(self):
        self.p.stdin.close()
        self.p.wait(timeout=30)


def _n(v, casas=0):
    return ("%.*f" % (casas, v)).replace(".", ",")


def desenhar(pasta, spec=None):
    spec = spec or P.SPEC_REV02
    g = P.geometria(spec)
    cap = P.capacidade(spec)
    s, q, ch, det = spec["skid"], spec["tubo_quadro"], spec["chapas"], spec["detalhes"]
    ti, ts = spec["tubo_travessa_inf"], spec["tubo_travessa_sup"]
    L, B, H = s["comp"], s["larg"], s["alt"]
    qh, qb = q["h"], q["b"]
    x0 = qb + spec["folga_lateral"]
    ce, le, _ = g["tanque_ext"]
    xt_testa = x0 + ce
    zf, zt, ztg = g["z_fundo"], g["z_tampa"], g["z_topo_gaiola"]
    ct, cal, ol = det["chapa_topo"], det["calco"], det["olhal"]
    S, Pc = spec["conteiner"]["S"], spec["conteiner"]["P"]
    xs_m = (qh / 2, L / 2, L - qh / 2)
    passo, nt = g["passo"], g["n_travessas"]
    h_txt = 2.5 * ESCALA

    def x_trav(i, t):
        meia = t["b"] / 2
        return min(max(x0 + i * passo, x0 + meia), x0 + ce - meia)

    c = CadCraft()
    c.cmd("new", metric=True, template=".")
    c.cmd("style", name="TEXTO", font="Arial", current=True)
    c.cmd("linetype", load="DASHED")
    c.cmd("linetype", load="CENTER")
    c.cmd("ltscale", scale=0.25)     # o viewport ja multiplica pela escala
    c.cmd("dimstyle", name="COTA-1-10", current=True, DIMSCALE=ESCALA, DIMTXT=2.5, DIMASZ=2.0,
          DIMEXO=1.0, DIMEXE=1.5, DIMDEC=0, DIMTAD=1, DIMGAP=0.8, DIMTXSTY="TEXTO")
    for nome, cor, lt, lw in (
            ("EST-QUADRO", 5, "Continuous", 0.50), ("EST-TRAVESSA", 3, "Continuous", 0.35),
            ("TANQUE", 1, "Continuous", 0.50), ("OCULTO", 8, "DASHED", 0.18),
            ("ACESSORIO", 6, "Continuous", 0.25), ("APOIO", 30, "Continuous", 0.25),
            ("EIXO", 8, "CENTER", 0.13), ("COTA", 7, "Continuous", 0.18),
            ("TEXTO", 7, "Continuous", 0.18), ("FOLHA", 7, "Continuous", 0.50),
            ("JANELA", 8, "Continuous", 0.13)):
        c.cmd("layer.new", name=nome, color=cor, linetype=lt, lineweight=lw)
    c.cmd("layer.set", name="JANELA", plot=False)

    def camada(nome):
        c.cmd("setvar", name="CLAYER", value=nome)

    def ret(x1, y1, x2, y2):
        c.cmd("rectang", p1=[x1, y1], p2=[x2, y2])

    def lin(*pts):
        c.cmd("line", points=[list(p) for p in pts])

    def txt(x, y, texto, h=h_txt, just="L", rot=0.0):
        c.cmd("text", at=[x, y], text=texto, height=h, justify=just, rotation=rot)

    def cota(p1, p2, at, texto=None):
        par = {"p1": list(p1), "p2": list(p2), "at": list(at)}
        if texto:
            par["text"] = texto
        c.cmd("dimlinear", **par)

    # ------------------------------------------------------------- PLANTA
    camada("EST-QUADRO")
    ret(0, 0, L, B)
    ret(qb, qb, L - qb, B - qb)
    for xc in xs_m:                                   # montantes
        for y1 in (0, B - qb):
            ret(xc - qh / 2, y1, xc + qh / 2, y1 + qb)
    for sx in (0, 1):                                 # chapas de topo e cones
        for sy in (0, 1):
            xa = L - ct["comp"] if sx else 0
            ya = B - ct["larg"] if sy else 0
            ret(xa, ya, xa + ct["comp"], ya + ct["larg"])
            c.cmd("circle", center=[(L + S) / 2 if sx else (L - S) / 2,
                                    (B + Pc) / 2 if sy else (B - Pc) / 2],
                  diameter=det["cone"]["d"])
    for xa in (-ol["proj"], L):                       # olhais
        for yc in (qb / 2, B - qb / 2):
            ret(xa, yc - ol["t"] / 2, xa + ol["proj"], yc + ol["t"] / 2)
    camada("TANQUE")
    ret(x0, x0, xt_testa, x0 + le)
    camada("EST-TRAVESSA")
    for i in range(nt):
        xc = x_trav(i, ts)
        ret(xc - ts["b"] / 2, qb, xc + ts["b"] / 2, B - qb)
    camada("ACESSORIO")
    n_vaos = nt - 1
    y_shaft = B - qb - spec["folga_lateral"] - 300.0
    x_resp = x0 + (n_vaos - 0.5) * passo
    c.cmd("circle", center=[x_resp, y_shaft], diameter=spec["adotado"]["d_respiro_mm"])
    x_ent = [x0 + (int(n_vaos * (k + 1) / (det["n_entradas"] + 1)) + 0.5) * passo
             for k in range(det["n_entradas"])]
    for xe in x_ent:
        c.cmd("circle", center=[xe, B / 2], diameter=det["dn_entrada"])
    y_suc = B / 2 - 600.0
    ret(xt_testa, y_suc - 60, xt_testa + 380, y_suc + 60)
    camada("OCULTO")
    pc = det["poco"]
    xp = x0 + (nt - 1.5) * passo
    ret(xp - pc["comp"] / 2, y_suc - pc["larg"] / 2, xp + pc["comp"] / 2, y_suc + pc["larg"] / 2)
    camada("EIXO")
    lin((-250, B / 2), (L + 250, B / 2))

    camada("TEXTO")
    txt(x_resp, y_shaft - 110, "RESPIRO DN%s" % _n(spec["adotado"]["d_respiro_mm"]), h=20,
        just="C")
    for xe in x_ent:
        txt(xe, B / 2 - 110, "ENTRADA DN%s" % _n(det["dn_entrada"]), h=20, just="C")
    txt(xt_testa + 30, y_suc + 90, "SUCÇÃO DN%s" % _n(det["dn_succao"]), h=20)
    txt(xp, y_suc - pc["larg"] / 2 - 60, "POÇO %s x %s" % (_n(pc["comp"]), _n(pc["larg"])),
        h=20, just="C")
    txt(xt_testa + spec["baia_tecnica"] / 2, B / 2 + 330, "BAIA TÉCNICA", h=20, just="C", rot=90)
    txt(L / 2, -860, "PLANTA (SEM O CONTÊINER)  -  ESC. 1:10", h=35, just="C")
    txt(L / 2, -920, "TANQUE %s x %s x %s (EXTERNO)  -  TAMPA CH %s SOBRE %s TRAVESSAS TB %sx%sx%s" % (
        _n(ce), _n(le), _n(g["tanque_ext"][2]), _n(ch["tampa"], 2), nt, _n(ts["h"]),
        _n(ts["b"]), _n(ts["t"], 2)), h=22, just="C")

    camada("COTA")
    cota((0, 0), (x0, 0), (x0 / 2, -300))
    cota((x0, 0), (xt_testa, 0), ((x0 + xt_testa) / 2, -300))
    cota((xt_testa, 0), (L, 0), ((xt_testa + L) / 2, -300))
    cota((0, 0), (L, 0), (L / 2, -600))
    cota((0, 0), (0, B), (-600, B / 2))
    cota((x0, x0), (x0, x0 + le), (-300, B / 2))
    xa, xb = x_trav(2, ts), x_trav(3, ts)
    cota((xa, B), (xb, B), ((xa + xb) / 2, B + 250), "%s (TÍP.)" % _n(passo, 1))
    cota(((L - S) / 2, (B + Pc) / 2), ((L + S) / 2, (B + Pc) / 2), (L / 2, B + 480))
    cota(((L + S) / 2, (B - Pc) / 2), ((L + S) / 2, (B + Pc) / 2), (L + 400, B / 2))

    # ----------------------------------------------------------- ELEVACAO
    def ez(z):
        return E0 + z

    h_canto = H - ct["t"]
    camada("EST-QUADRO")
    for xc in xs_m:
        ret(xc - qh / 2, ez(0), xc + qh / 2, ez(ztg if xc == L / 2 else h_canto))
    for xa, xb in zip(xs_m, xs_m[1:]):
        for z1 in (0, ztg - qh):
            ret(xa + qh / 2, ez(z1), xb - qh / 2, ez(z1 + qh))
    for xa in (0, L - ct["comp"]):
        ret(xa, ez(h_canto), xa + ct["comp"], ez(H))
    for xc in ((L - S) / 2, (L + S) / 2):
        ret(xc - det["cone"]["d"] / 2, ez(H), xc + det["cone"]["d"] / 2, ez(H + det["cone"]["h"]))
    z_ol = h_canto - 20.0 - ol["alt"]
    for xa in (-ol["proj"], L):
        ret(xa, ez(z_ol), xa + ol["proj"], ez(z_ol + ol["alt"]))
        c.cmd("circle", center=[xa + ol["proj"] / 2, ez(z_ol + ol["alt"] / 2)],
              diameter=ol["furo"])
    camada("TANQUE")                                  # visivel entre as longarinas
    ret(x0, ez(qh), xt_testa, ez(ztg - qh))
    camada("OCULTO")
    lin((x0, ez(zf)), (xt_testa, ez(zf)))
    lin((x0, ez(zt)), (xt_testa, ez(zt)))
    for i in range(nt):
        xc = x_trav(i, ti)
        ret(xc - ti["b"] / 2, ez(0), xc + ti["b"] / 2, ez(ti["h"]))
        xc = x_trav(i, ts)
        ret(xc - ts["b"] / 2, ez(zt), xc + ts["b"] / 2, ez(zt + ts["h"]))
    hh = zf + ch["fundo"] + cap["niveis"]["alarme_alto_alto"]["lamina_mm"]
    camada("EIXO")
    lin((x0, ez(hh)), (xt_testa, ez(hh)))
    camada("APOIO")
    for xc in xs_m:
        ret(xc - cal["comp"] / 2, ez(-cal["t"]), xc + cal["comp"] / 2, ez(0))
        ret(xc - 175, ez(-cal["t"] - 200), xc + 175, ez(-cal["t"]))
    lin((-500, ez(-cal["t"] - 200)), (L + 500, ez(-cal["t"] - 200)))

    camada("TEXTO")
    txt(x0 + 3 * passo, ez(hh) + 15, "NÍVEL ALTO-ALTO (%s %%)" % _n(
        100 * spec["niveis"]["alarme_alto_alto"]), h=20)
    txt(L / 2 + 250, ez(-cal["t"] - 150), "APOIO DE REFERÊNCIA 350 x 350", h=20)
    txt(-ol["proj"] - 30, ez(z_ol + ol["alt"] + 40), "OLHAL CH %s" % _n(ol["t"]), h=20, just="R")
    txt(L / 2, ez(-cal["t"] - 200) - 480, "ELEVAÇÃO LATERAL  -  ESC. 1:10", h=35, just="C")

    camada("COTA")
    cota((L, ez(0)), (L, ez(H)), (L + 400, ez(H / 2)))
    cota((0, ez(0)), (0, ez(zf)), (-300, ez(zf / 2)))
    cota((0, ez(zf)), (0, ez(zt)), (-300, ez((zf + zt) / 2)))
    yb = ez(-cal["t"] - 200)
    cota((xs_m[0], yb), (xs_m[1], yb), ((xs_m[0] + xs_m[1]) / 2, yb - 300))
    cota((xs_m[1], yb), (xs_m[2], yb), ((xs_m[1] + xs_m[2]) / 2, yb - 300))

    # -------------------------------------------------------------- FOLHA
    c.cmd("layout.new", name="TQ-01", viewport=False)
    c.cmd("pagesetup", layout="TQ-01", paper="A1", landscape=True,
          plotStyleTable="monochrome.ctb")
    c.cmd("layout.set", name="TQ-01")
    camada("JANELA")
    vp = c.cmd("mview", p1=[12, 12], p2=[737, 582], layout="TQ-01")
    c.cmd("viewport.set", handle=vp["viewports"][0], scale="1:%d" % ESCALA,
          center=[L / 2 - 150, 215.0], locked=True)
    camada("FOLHA")
    ret(10, 10, 831, 584)
    lin((740, 10), (740, 584))
    x1, x2 = 742.0, 829.0
    camada("TEXTO")
    txt(x1 + 1, 575, "TANQUE-BASE INTEGRAL", h=4.0)
    txt(x1 + 1, 569, "SOB CONTÊINER %s (20 PÉS)" % spec["conteiner"]["tipo"], h=3.0)
    c.cmd("tablestyle", name="LISTA", textHeight=2.0, margin=0.8, current=True)
    c.cmd("tablestyle.cellstyle", style="LISTA", name="Data", textStyle="TEXTO", textHeight=2.0)
    c.cmd("tablestyle.cellstyle", style="LISTA", name="Header", textStyle="TEXTO",
          textHeight=2.0)
    c.cmd("tablestyle.cellstyle", style="LISTA", name="Title", textStyle="TEXTO",
          textHeight=2.5)
    tubo = lambda t: "TB %sx%sx%s" % (_n(t["h"]), _n(t["b"]), _n(t["t"], 2))  # noqa: E731
    linhas = [
        ["Montante", tubo(q), "6"],
        ["Longarina", tubo(q), "8"],
        ["Testeira", tubo(q), "4"],
        ["Travessa inferior", tubo(ti), str(nt)],
        ["Travessa superior", tubo(ts), str(nt)],
        ["Fundo do tanque", "CH %s" % _n(ch["fundo"], 2), "1"],
        ["Lateral e testa", "CH %s" % _n(ch["lateral"], 2), "4"],
        ["Tampa", "CH %s" % _n(ch["tampa"], 2), "1"],
        ["Chapa de topo", "CH %s" % _n(ct["t"]), "4"],
        ["Olhal de içamento", "CH %s" % _n(ol["t"]), "4"],
        ["Calço", "CH %s" % _n(cal["t"], 1), "6"],
    ]
    c.cmd("table", at=[x1, 562], rows=len(linhas), cols=3, rowHeight=5.0, colWidth=29.0,
          title="PEÇAS PRINCIPAIS", header=["PEÇA", "PERFIL / CHAPA", "QTD"], cells=linhas)
    niv = cap["niveis"]
    notas = [
        "NOTAS",
        "1. Medidas em milímetros.",
        "2. Volume geométrico %s m³; alarme alto a %s %% = %s m³." % (
            _n(cap["volume_m3"], 2), _n(100 * spec["niveis"]["alarme_alto"]),
            _n(niv["alarme_alto"]["volume_m3"], 2)),
        "3. Transporte e içamento somente com o tanque vazio.",
        "4. Tudo soldado; única tampa aparafusada: boca de inspeção.",
        "5. Solda do quadro: filete %s mm; travessas: filete %s mm." % (
            _n(spec["perna_solda"]), _n(spec["perna_solda_travessa"])),
        "6. Apoios travados no piso (ver memória de cálculo).",
        "7. Respiro e entradas saem pela tampa, no meio do vão entre travessas.",
        "",
        "FOLHA-PILOTO desenhada no CADCraft a partir do mesmo SPEC da REV.02. "
        "Não substitui as pranchas emitidas.",
    ]
    c.cmd("mtext", at=[x1 + 1, 470], text="\\P".join(notas), height=2.2, width=x2 - x1 - 2,
          style="TEXTO")
    camada("FOLHA")                                   # carimbo
    ret(x1, 12, x2, 72)
    for y in (24, 36, 48, 60):
        lin((x1, y), (x2, y))
    lin((x1 + 43.5, 12), (x1 + 43.5, 36))
    camada("TEXTO")
    hoje = datetime.date.today().strftime("%d/%m/%Y")
    for y, rot, val, x in ((67, "DOCUMENTO", spec["documento"], x1),
                           (55, "TÍTULO", "CONJUNTO - PLANTA E ELEVAÇÃO", x1),
                           (43, "LOCAL", spec["local"]["municipio"], x1),
                           (31, "ESCALA", "1:%d" % ESCALA, x1), (31, "FOLHA", "TQ-01  A1", x1 + 43.5),
                           (19, "DATA", hoje, x1), (19, "SITUAÇÃO", "PILOTO", x1 + 43.5)):
        txt(x + 1.5, y + 1.2, rot, h=1.5)
        txt(x + 1.5, y - 5.0, val, h=2.8)

    os.makedirs(pasta, exist_ok=True)
    base = os.path.join(os.path.abspath(pasta), "tanque_base_conjunto_cadcraft")
    res = {"pdf": c.cmd("plot", path=base + ".pdf", layout="TQ-01", plotArea="layout"),
           "auditoria": c.cmd("audit")}
    c.cmd("saveas", path=base + ".dxf")
    c.cmd("saveas", path=base + ".dwg")
    c.fecha()
    res["arquivos"] = [base + e for e in (".dxf", ".dwg", ".pdf")]
    return res


if __name__ == "__main__":
    r = desenhar(sys.argv[1] if len(sys.argv) > 1 else "piloto-cadcraft")
    print(json.dumps(r, indent=1, ensure_ascii=False, default=str)[:1500])
