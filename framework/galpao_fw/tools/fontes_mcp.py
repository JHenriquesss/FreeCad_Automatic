"""Consulta ao MCP_Fontes por stdio. Uso: fontes.py <ferramenta> '<json de argumentos>' [...]
Varias chamadas numa execucao: pares ferramenta/json em sequencia. 'tools' lista as ferramentas."""
import json
import os
import subprocess
import sys

EXE = os.path.join(os.environ["LOCALAPPDATA"], "MCP_Fontes_Rust", "bin", "fontes.exe")


def chamar(pedidos):
    msgs = [{"jsonrpc": "2.0", "id": 0, "method": "initialize",
             "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                        "clientInfo": {"name": "cc", "version": "1"}}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"}]
    for i, (nome, args) in enumerate(pedidos, 1):
        if nome == "tools":
            msgs.append({"jsonrpc": "2.0", "id": i, "method": "tools/list"})
        else:
            msgs.append({"jsonrpc": "2.0", "id": i, "method": "tools/call",
                         "params": {"name": nome, "arguments": args}})
    ent = "\n".join(json.dumps(m) for m in msgs) + "\n"
    p = subprocess.run([EXE, "mcp"], input=ent.encode("utf-8"), capture_output=True, timeout=120)
    out = {}
    for lin in p.stdout.decode("utf-8", "replace").splitlines():
        try:
            d = json.loads(lin)
        except ValueError:
            continue
        if d.get("id"):
            out[d["id"]] = d
    return [out.get(i) for i in range(1, len(pedidos) + 1)]


if __name__ == "__main__":
    a = sys.argv[1:]
    ped = [(a[i], json.loads(a[i + 1]) if i + 1 < len(a) else {}) for i in range(0, len(a), 2)]
    for (nome, args), r in zip(ped, chamar(ped)):
        print("=" * 20, nome, json.dumps(args, ensure_ascii=False))
        if r is None:
            print("SEM RESPOSTA")
            continue
        res = r.get("result", r)
        for c in res.get("content", []) if isinstance(res, dict) else []:
            if c.get("type") == "text":
                try:
                    _d = json.loads(c["text"])
                    if isinstance(_d.get("data"), dict) and "texto" in _d["data"]:
                        print("PAGINAS", sorted({p["page_index"] for p in _d["data"]["pecas"]}),
                              "cobertura", _d["coverage"]["state"])
                        print(_d["data"]["texto"])
                        continue
                    print(json.dumps(json.loads(c["text"]), ensure_ascii=False, indent=1)[:int(os.environ.get("LIM", "6000"))])
                except ValueError:
                    print(c["text"][:6000])
            elif c.get("type") == "image":
                import base64
                nome_arq = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        "pag_%s.png" % abs(hash(json.dumps(args))) )
                open(nome_arq, "wb").write(base64.b64decode(c["data"]))
                print("IMAGEM:", nome_arq)
        if "content" not in (res if isinstance(res, dict) else {}):
            print(json.dumps(res, ensure_ascii=False, indent=1)[:6000])
