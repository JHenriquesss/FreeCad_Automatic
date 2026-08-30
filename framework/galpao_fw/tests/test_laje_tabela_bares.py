"""CONFERENCIA INDEPENDENTE das tabelas de Bares transcritas em laje_concreto.

Por que este teste existe: as tabelas dos Quadros 7.2 a 7.5 de Carvalho &
Figueiredo tem 9 casos x 21 valores de lambda x ate 4 colunas - quase mil numeros
que entraram no codigo por transcricao de um PDF com OCR. Cristalizar num teste um
numero lido errado ja aconteceu neste projeto (o episodio "AR300"), e a barra
verde de um teste que so compara o codigo consigo mesmo nao pega isso.

A conferencia aqui NAO usa a mesma fonte: resolve a placa de Kirchhoff
(nabla^4 w = p/D, nu = 0,20 - a mesma hipotese declarada pelo livro) por
DIFERENCAS FINITAS, com as condicoes de contorno de cada caso, e compara. Um erro
de digitacao/OCR aparece como um desvio de 10% ou mais isolado numa celula,
enquanto o erro proprio do metodo fica na casa de 3 a 5% (malha grosseira, de
proposito, para o teste rodar em ~1 s).

Achados que este teste produziu na transcricao (todos corrigidos e marcados com
[OCR] no modulo): caso 1 mu_y em lambda 1,60 (lido "3,14"), caso 2 mu_x na faixa
1,65-1,85, caso 4 mu_y em 1,45, caso 5 mu_y' em 1,80, caso 7 mu_x/mu_x' em 1,25 e
o alpha do caso 8 na faixa 1,55-1,65.
"""

import pytest

import laje_concreto as lj

np = pytest.importorskip("numpy")
sp = pytest.importorskip("scipy.sparse")
spl = pytest.importorskip("scipy.sparse.linalg")

NU = 0.20
N_MALHA = 28          # divisoes no menor vao

# Condicao de contorno de cada caso (x0, x1, y0, y1): S apoiada, E engastada.
# x0/x1 sao as bordas perpendiculares a x (as MAIORES, de comprimento ly) e
# y0/y1 as perpendiculares a y (as MENORES, de comprimento lx).
BC_CASO = {caso: "".join("E" if b in lj.ENGASTES[caso] else "S"
                         for b in ("x0", "x1", "y0", "y1"))
           for caso in range(1, 10)}
LAMBDAS = (1.00, 1.25, 1.50, 1.75, 2.00)


def _resolve(lam, bc, n=N_MALHA):
    """Placa retangular sob carga uniforme: nabla^4 w = p/D, com p = 1, D = 1,
    lx = 1 e ly = lam. Contorno w = 0 em todas as bordas; borda apoiada tem
    w'' = 0 (no fantasma = -no interno) e borda engastada w' = 0 (no fantasma =
    +no interno). Estencil biharmonico de 13 pontos."""
    N = n
    M = int(round(n * lam))
    h = 1.0 / N
    nj = M - 1

    def idx(i, j):
        return (i - 1) * nj + (j - 1)

    def espalha(i, j):
        alvo = {}

        def poe(ii, jj, w):
            if ii == 0 or ii == N or jj == 0 or jj == M:
                return                                   # w = 0 no contorno
            if ii == -1:
                return poe(1, jj, (-1.0 if bc[0] == "S" else 1.0) * w)
            if ii == N + 1:
                return poe(N - 1, jj, (-1.0 if bc[1] == "S" else 1.0) * w)
            if jj == -1:
                return poe(ii, 1, (-1.0 if bc[2] == "S" else 1.0) * w)
            if jj == M + 1:
                return poe(ii, M - 1, (-1.0 if bc[3] == "S" else 1.0) * w)
            alvo[(ii, jj)] = alvo.get((ii, jj), 0.0) + w

        poe(i, j, 20.0)
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            poe(i + di, j + dj, -8.0)
        for di, dj in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
            poe(i + di, j + dj, 2.0)
        for di, dj in ((2, 0), (-2, 0), (0, 2), (0, -2)):
            poe(i + di, j + dj, 1.0)
        return alvo

    linhas, colunas, valores = [], [], []
    for i in range(1, N):
        for j in range(1, M):
            for (ii, jj), v in espalha(i, j).items():
                linhas.append(idx(i, j)); colunas.append(idx(ii, jj)); valores.append(v)
    n_inc = (N - 1) * (M - 1)
    A = sp.csr_matrix((valores, (linhas, colunas)), shape=(n_inc, n_inc))
    w = np.zeros((N + 1, M + 1))
    w[1:N, 1:M] = spl.spsolve(A, np.full(n_inc, h ** 4)).reshape(N - 1, M - 1)

    def wf(i, j):
        if i == -1:
            return (-1.0 if bc[0] == "S" else 1.0) * w[1, j]
        if i == N + 1:
            return (-1.0 if bc[1] == "S" else 1.0) * w[N - 1, j]
        if j == -1:
            return (-1.0 if bc[2] == "S" else 1.0) * w[i, 1]
        if j == M + 1:
            return (-1.0 if bc[3] == "S" else 1.0) * w[i, M - 1]
        return w[i, j]

    mx = np.zeros((N + 1, M + 1)); my = np.zeros((N + 1, M + 1))
    for i in range(N + 1):
        for j in range(M + 1):
            wxx = (wf(i + 1, j) - 2 * w[i, j] + wf(i - 1, j)) / h ** 2
            wyy = (wf(i, j + 1) - 2 * w[i, j] + wf(i, j - 1)) / h ** 2
            mx[i, j] = -(wxx + NU * wyy)
            my[i, j] = -(wyy + NU * wxx)
    ci, cj = N // 2, M // 2
    return {"mu_x": 100 * mx[ci, cj], "mu_y": 100 * my[ci, cj],
            "mu_x_max": 100 * mx.max(), "mu_y_max": 100 * my.max(),
            "mu_x_neg": 100 * max(abs(mx[0, :].min()), abs(mx[-1, :].min())),
            "mu_y_neg": 100 * max(abs(my[:, 0].min()), abs(my[:, -1].min())),
            "alpha": 100 * w[ci, cj] * 11.52}   # D = E h^3/(12(1-nu^2)) -> 11,52


_CACHE = {}


def placa(caso, lam):
    chave = (caso, lam)
    if chave not in _CACHE:
        _CACHE[chave] = _resolve(lam, BC_CASO[caso])
    return _CACHE[chave]


# ---------------------------------------------------------------------------
# 1. O solver reproduz solucoes classicas conhecidas (valida o proprio aferidor)
# ---------------------------------------------------------------------------

def test_solver_reproduz_a_placa_quadrada_apoiada():
    """Serie de Navier (nu = 0,2): m = 0,0442 p l^2 e w = 0,0468 p l^4/(E h^3)."""
    r = placa(1, 1.00)
    assert r["mu_x"] == pytest.approx(4.42, rel=0.02)
    assert r["mu_y"] == pytest.approx(4.42, rel=0.02)
    assert r["alpha"] == pytest.approx(4.67, rel=0.02)


def test_solver_reproduz_a_placa_quadrada_engastada():
    """Timoshenko, placa quadrada com as 4 bordas engastadas."""
    r = placa(9, 1.00)
    assert r["mu_x"] == pytest.approx(2.11, rel=0.03)
    assert r["mu_x_neg"] == pytest.approx(5.15, rel=0.03)


def test_solver_reproduz_a_faixa_biengastada():
    """Caso 6 com lambda 2 tende a faixa engastada-engastada em x:
    m = p l^2/24 (mu 4,17) e X = p l^2/12 (mu 8,33)."""
    r = placa(6, 2.00)
    assert r["mu_x"] == pytest.approx(100.0 / 24.0, rel=0.03)
    assert r["mu_x_neg"] == pytest.approx(100.0 / 12.0, rel=0.03)


# ---------------------------------------------------------------------------
# 2. Cada celula da tabela transcrita bate com a placa resolvida
# ---------------------------------------------------------------------------

# Excecao conhecida da fonte: nos casos com UM UNICO engaste (2 e 3), a coluna do
# momento na direcao PERPENDICULAR a borda engastada nao e o valor do centro do
# painel - o maximo fica deslocado ~0,6 lx do engaste, e o valor tabelado cai
# entre o do centro e o maximo. Para essas duas colunas a conferencia e por
# INTERVALO [centro ; maximo] (com a folga do metodo), e nao por igualdade.
ENTRE_CENTRO_E_MAXIMO = {3: ("mu_x",), 2: ("mu_y",)}


@pytest.mark.parametrize("caso", sorted(BC_CASO))
@pytest.mark.parametrize("lam", LAMBDAS)
def test_tabela_de_momentos_bate_com_a_placa(caso, lam):
    tab = lj._interp(lj.MU_BARES[caso], lam)
    fd = placa(caso, lam)
    for i, chave in enumerate(("mu_x", "mu_x_neg", "mu_y", "mu_y_neg")):
        if tab[i] == 0:
            # onde a tabela nao tem engaste, a placa tambem nao pode ter
            if chave.endswith("neg"):
                assert fd[chave] < 1e-6, (caso, lam, chave)
            continue
        if caso == 3 and chave == "mu_y":
            continue                       # ver test_caso_3_mu_y_e_desvio_conhecido
        if chave in ENTRE_CENTRO_E_MAXIMO.get(caso, ()):
            piso = fd[chave] * 0.93
            teto = fd[chave + "_max" if chave in ("mu_x", "mu_y") else chave] * 1.07
            assert piso <= tab[i] <= teto, (caso, lam, chave, tab[i], piso, teto)
            continue
        assert fd[chave] == pytest.approx(tab[i], rel=0.07), (caso, lam, chave,
                                                              tab[i], fd[chave])


@pytest.mark.parametrize("caso", sorted(BC_CASO))
@pytest.mark.parametrize("lam", LAMBDAS)
def test_tabela_de_flecha_bate_com_a_placa(caso, lam):
    tab = lj._interp(lj.ALPHA_FLECHA[caso], lam)
    assert placa(caso, lam)["alpha"] == pytest.approx(tab, rel=0.06), (caso, lam)


def test_caso_3_mu_y_e_desvio_conhecido_da_fonte():
    """PINO de um desvio REAL da fonte, nao um bug do modulo: no caso 3 a coluna
    mu_y do Quadro 7.3 fica ABAIXO do momento no centro obtido pela teoria de
    placas (ate ~20% em lambda 2). O desvio esta registrado aqui para que uma
    alteracao futura da celula nao passe calada. Consequencia pratica pequena:
    e a direcao secundaria, onde a armadura minima governa - no proprio exemplo
    do livro (L3) esse momento da As = 0,85 cm2/m contra As,min = 1,80 cm2/m."""
    for lam, limite in ((1.00, 0.08), (1.50, 0.12), (2.00, 0.22)):
        tab = lj._interp(lj.MU_BARES[3], lam)[2]
        fd = placa(3, lam)["mu_y"]
        assert tab < fd, lam                      # a tabela e a MENOR das duas
        assert abs(fd - tab) / fd <= limite, (lam, tab, fd)
    # e a armadura minima realmente governa nesse momento (exemplo L3 do livro)
    r = lj.dimensiona_seccao(1.4 * 2.06, 1.0, 0.08, 0.12, 20e3, 500e3, "positiva_2d")
    assert r["governa_minimo"]


# ---------------------------------------------------------------------------
# 3. Sanidade puramente tabular (roda mesmo sem numpy/scipy no ambiente)
# ---------------------------------------------------------------------------

def test_tabelas_tem_o_mesmo_numero_de_linhas_dos_lambdas():
    for caso in range(1, 10):
        assert len(lj.MU_BARES[caso]) == len(lj._LAMBDAS)
        assert len(lj.ALPHA_FLECHA[caso]) == len(lj._LAMBDAS)
        assert all(len(linha) == 4 for linha in lj.MU_BARES[caso])


def _celulas_suspeitas(serie, fator=0.15, piso=0.05):
    """Devolve os indices em que o valor foge da reta local (media dos vizinhos).
    Detector barato de OCR: foi assim que apareceram 3,14 no lugar de 4,14 no
    caso 1 e 8,81 no lugar de 8,16 no caso 7."""
    faixa = max(serie) - min(serie)
    tol = max(fator * faixa, piso)
    return [i for i in range(1, len(serie) - 1)
            if abs(serie[i] - (serie[i - 1] + serie[i + 1]) / 2.0) > tol]


def _series_das_tabelas():
    for caso in range(1, 10):
        for col in range(4):
            s = [linha[col] for linha in lj.MU_BARES[caso]]
            if all(v > 0 for v in s):
                yield ("mu", caso, col, s)
        yield ("alpha", caso, 0, list(lj.ALPHA_FLECHA[caso]))


# Unica quebra de suavidade que NAO e erro de transcricao: no caso 2, a coluna
# mu_y vale 3,94 em lambda 1,00 e cai para 3,78 em 1,05. Conferido contra a placa
# (centro: 3,67 em 1,00 e 3,80 em 1,05): o 3,78 esta CERTO - quem destoa e o valor
# de lambda 1,00, onde a fonte tabela algo proximo do maximo (3,90) e nao do
# centro. Corrigir o 3,78 "para alinhar a serie" seria inventar numero.
QUEBRAS_CONFERIDAS = {("mu", 2, 2): [1]}


def test_series_sao_suaves():
    for tipo, caso, col, s in _series_das_tabelas():
        esperadas = QUEBRAS_CONFERIDAS.get((tipo, caso, col), [])
        assert _celulas_suspeitas(s) == esperadas, (tipo, caso, col, s)


def test_o_detector_de_celula_suspeita_nao_e_vazio():
    """Um detector que nunca acusa nao vale nada: reinjetando o valor que o OCR
    tinha lido (3,14 no caso 1, lambda 1,60) ele TEM de acusar aquela celula."""
    s = [linha[2] for linha in lj.MU_BARES[1]]
    corrompida = list(s)
    corrompida[12] = 3.14
    assert 12 in _celulas_suspeitas(corrompida)
    assert _celulas_suspeitas(s) == []


def test_alpha_cresce_com_lambda():
    """A flecha de um painel mais alongado nunca diminui (mesma menor dimensao)."""
    for caso in range(1, 10):
        s = lj.ALPHA_FLECHA[caso]
        assert all(b >= a - 1e-9 for a, b in zip(s, s[1:])), caso


def test_engastes_e_colunas_nulas_sao_coerentes():
    """Coluna de momento negativo so pode existir onde ha borda engastada."""
    for caso in range(1, 10):
        tem_x = any(b in ("x0", "x1") for b in lj.ENGASTES[caso])
        tem_y = any(b in ("y0", "y1") for b in lj.ENGASTES[caso])
        for linha in lj.MU_BARES[caso]:
            assert (linha[1] > 0) == tem_x, caso
            assert (linha[3] > 0) == tem_y, caso
