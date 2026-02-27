# Seção 1.3. Análise de Convergência

## 1. Introdução e Visão Geral da Topologia
A rede simulada baseada em Vetor de Distância utiliza o algoritmo de Bellman-Ford e é dividida logicamente em duas camadas:
1. **Núcleo (Core)**: Constituído pelos roteadores R1 a R6. Todos os roteadores dessa malha estão conectados entre si diretamente com enlaces de custo 1.
2. **Borda (Edge)**: Constituída pelos roteadores R7 a R12. Cada um se conecta a exatamente dois roteadores do núcleo com conexões de custo 2.
    - Ex: R7 conecta-se a R1 e R2; R8 a R2 e R3, ..., R12 a R6 e R1.

O protocolo implementa a mecânica de *Split Horizon com Poison Reverse* e agregação/sumarização de rotas com blocos adjacentes sob um mesmo *next hop* (conforme função analítica localizada no código do roteador).

## 2. Cronologia Global de Convergência

A convergência ocorre através de sucessivas trocas de atualizações a cada intervalo do protocolo ($t_0, t_1, \dots$). 

- **$t_0$ (Carga Inicial)**:
  - **Estado**: Todos os roteadores acabam de inicializar. Cada roteador ($Rx$) carrega apenas a sua respectiva rede local `10.0.x.0/24` (com custo 0) e os IPs diretos configurados em sua vizinhança na tabela de roteamento interna. Nenhuma informação foi trocada.

- **$t_1$ (Propagação de Vizinhança Direta - 1 Salto)**:
  - **Troca**: Todos os roteadores enviam o seu estado de $t_0$.
  - **Estado**: Cada roteador aprende as redes locais de todos os seus vizinhos físicos diretos.
    - *Núcleo*: R1, por exemplo, aprende as redes de R2 a R6 (`10.0.2.0/24` a `10.0.6.0/24` a custo 1) e as redes de seus agregados em borda, como R7 e R12 (`10.0.7.0/24` e `10.0.12.0/24` a custo 2).
    - *Borda*: R7 aprende as redes exclusivas de R1 e R2 (`10.0.1.0/24` e `10.0.2.0/24` a custo 2).

- **$t_2$ (Visibilidade Indireta - 2 Saltos)**:
  - **Troca**: Os roteadores transmitem as atualizações massivas assimiladas em $t_1$.
  - **Estado do Núcleo**:
    - O núcleo da topologia atinge a visibilidade global completa das redes, visto que a distância máxima lógica para cruzar o Core não ultrapassa 2 conexões transversais. Redes opostas, como N8, N9, N10 e N11 tornam-se completamente conhecidas por nós transversais como R1 e R6 (ex: R1 chega à N9 de R9 pulando através de R3 — com custo logado de $1+2=3$).
  - **Estado da Borda**:
    - A periferia absorve o "mapa" interior. R7 aprende sobre R3...R6 através da intermediação do núcleo (com custo derivado de $2+1=3$) e absorve informações vitais de redes de borda vizinhas como `10.0.8.0/24`, atingindo o destino indiretamente via R2 por custo reflexivo de $2+2=4$. 

- **$t_3$ (Propagação Final - Visibilidade de Sistema)**:
  - **Troca**: Os nós repassam o conhecimento massivo descoberto no ciclo de $t_2$.
  - **Estado**: As pontas restantes totalmente desconectadas do núcleo na perspectiva individual da topologia entram em convergência visual. Roteadores de extremo como R7 descobrem o lado reverso geográfico da operação (redes N9, N10, N11) partindo de anúncios de seus uplinks (R1 e R2). Os caminhos mínimos absolutos fecham e os roteadores arquivam essas rotas finais com o custo extremo (Roteador de Borda $\leftrightarrow$ Core $\leftrightarrow$ Core $\leftrightarrow$ Roteador de Borda = $2 + 1 + 2 = 5$). 

- **$t_4$ (Estabilidade e Manutenção)**:
  - **Estado**: Nenhuma nova rota com vetor-distância inferior é descoberta. O Poison Reverse previne anomalias ou contagens ao infinito enquanto a sumarização achata os payloads. A rede cimenta o traçado, enviando unicamente "Keep-alives" das tabelas idênticas para manutenção física da adjacência.
  
*(Nota: Devido à dinâmica do código e protocolo, IPs individuais hospedeiros de túnel configurados nas interfaces também constam ativamente nas tabelas, mas sua explicação fora suprimida pela mesma linearidade percorrida pelas redes bloco `/24` e com o intuito focado em simplificar a transparência didática.)*


## 3. Demonstração Analítica do Processo: Roteador R7

Para demonstrar a comprovação matemática das mecânicas do modelo, aplicaremos e verificaremos a progressão gradual partindo da perspectiva estrita do roteador **R7**.
O **R7** é um nó classificado fisicamente como "Edge" (nó folha na periferia da topologia) conectado a **$R1$ (custo link de 2)** e **$R2$ (custo link de 2)**. Acompanhe a lei de convergência aplicando: `Custo Final = Custo_Adjacência + Custo_Anunciado_por_Vizinho`.

### Instante $t_0$
- **R7 Inicializado**: R7 gera nativamente e de maneira intrínseca sua própria vizinhança no registro, assumindo conectividade raiz à rede que administra.

| Rede de Destino | Next Hop | Custo Computado |
|-----------------|----------|-----------------|
| 10.0.7.0/24     | (direto) | 0               |

---

### Instante $t_1$
**Tabelas Recebidas:**
- R1 envia o vetor da própria rede local ativa: `10.0.1.0/24` anunciada com custo bruto (0).
- R2 envia o vetor análogo: `10.0.2.0/24` com custo (0).

**Processamento matemático de R7:**
- R1 é o transmissor via link de salto custo 2. O custo absoluto fixado em tabela para subrede N1 é o mínimo: $min(\infty, 2 + 0) = 2$ – Atribuído via Next Hop $= R1$.
- R2 segue o mesmo modelo para Métrica Absoluta de N2: $min(\infty, 2 + 0) = 2$ – Aprovada via Next Hop $= R2$.

**Tabela de R7 em $t_1$:**
| Rede de Destino | Next Hop | Custo Computado |
|-----------------|----------|-----------------|
| 10.0.7.0/24     | (direto) | 0               |
| 10.0.1.0/24     | R1       | 2               |
| 10.0.2.0/24     | R2       | 2               |

---

### Instante $t_2$
R7 passa a receber tabelas mais adensadas e robustas em informações estruturais, já que R1 e R2 operam como um hub de convergência antecipada do núcleo inteiro da topologia.

**Tabela enviada por R1 a R7 (reflexo de R1 pós-$t_1$):**
- Rede própria `10.0.1.0/24` descrita de $t_1$ (custo de R1 para N1 é 0)
- Redes centrais descobertas: `10.0.2.0/24` até `10.0.6.0/24` (custo logado em R1 = 1)
- Redes perimetrais anexas descobertas em $t_1$: `10.0.12.0/24` (custo 2)
- *Para seu anúncio à R7, R1 engatilha a mecânica de Poison-Reverse na subrede própria de R7 (`10.0.7.0/24` via 16).* 

**Tabela enviada por R2 (reflexo de R2 pós-$t_1$):**
- `10.0.2.0/24` (custo logado = 0)
- `10.0.1.0/24` & Redes diretas centrais: `10.0.3.0/24` até `10.0.6.0/24` (custo logado em R2 = 1)
- Borda anexa detectada: `10.0.8.0/24` (custo 2)
- *Cargas idênticas de Poison Reverse a N7 engatilhadas (16).*

**Processamento matemático de tabela final (R7)** (R7 aplica penalidade de adjacência $+2$ fixada):
- *Cálculos dos pacotes de R1*: 
  - Subredes de Núcleo (N3 a N6): Novo Custo = $2 + 1 = 3$. Como antes possuíam métrica inacessível (não descritas na tabela de R7 em *t1*), estas inserem R1 como o melhor vetor disponível.
  - Rede N12 anexada de fora: Novo Custo = $2 + 2 = 4$. Next Hop definido em R1.
- *Cálculos dos pacotes concorrentes de R2*:
  - Redes de Núcleo Conflitantes (N3 a N6): Novo Custo recebido calculando = $2 + 1 = 3$. Bellman-Ford estrito implementado avalia que a rota anterior de R1 inserida possuía o custo idêntico ($3$). Sem a necessidade e prioridade de substituição da rota ativa do Next Hop, o script preserva R1 nativo na tabela mantendo as amarrações do tráfego atativas em Custo $3$.
  - Rede perimetral (N8): Custo recém alcançado = $2$ de uplink $+ 2$ anunciado. Atravessa por $4$.

**Tabela estendida consolidada em R7 ($t_2$):**
| Rede de Destino | Next Hop | Custo Computado |
|-----------------|----------|-----------------|
| 10.0.7.0/24     | (direto) | 0               |
| 10.0.1.0/24     | R1       | 2               |
| 10.0.2.0/24     | R2       | 2               |
| 10.0.3.0/24     | R1       | 3               |
| 10.0.4.0/24     | R1       | 3               |
| 10.0.5.0/24     | R1       | 3               |
| 10.0.6.0/24     | R1       | 3               |
| 10.0.8.0/24     | R2       | 4               |
| 10.0.12.0/24    | R1       | 4               |

---

### Instante $t_3$
A convergência do lado oposto do globo topológico fecha as brechas isoladas da malha na borda.

**Atualizações pertinentes repassadas durante o pulso $t_3$ a R7:**
- R1 transaciona repassando a descoberta das extremidades que ele mesmo aprendeu no ciclo de $t_2$. R1 espelha vetores da subrede vizinha: `10.0.8.0/24` a `10.0.11.0/24`, ambas com os custos internalizados localmente a $3$.
- R2 age num princípio geométrico virtual similar propulcionando repasses descobertos atrelando as redes de borda do outro hemisfério: `10.0.9.0/24` a `10.0.12.0/24`, métricas originais reportadas como 3.

**Processamento matemático para o último pulso (R7)**:
- R7 enxerga N9 (`10.0.9.0/24`), e N10 e N11 recém descobertos sob atualizações provenientes de R1. R7 executa Bellman-Ford somando penalidade de uplink ($2$) + anúncio de R1 em topologia inteira resolvida de repasses saltitantes atráves da malha até a extrema oposta ($3$). $Custo Absoluto: 5$. Métrica fixada via R1 e estabilizada. 
- *Ação da função de Sumarização*: O script inteligente fará agregação binária nos envios (ex: `10.0.4.0/24` e `10.0.5.0/24` são pareados e reduzidos dinamicamente por R7 ao serem injetados fora via `summarize()` sob `Next Hop R1` comprimidos para uma rota singular CIDR limpa de `10.0.4.0/23`, economizando largura de enlace em repasses vindouros).

**Tabela Pós-Convergente Operacional ($t_3 \rightarrow t_n$):**
| Rede de Destino | Next Hop | Custo Computado |
|-----------------|----------|-----------------|
| 10.0.7.0/24     | (direto) | 0               |
| 10.0.1.0/24     | R1       | 2               |
| 10.0.2.0/24     | R2       | 2               |
| 10.0.3.0/24     | R1       | 3               |
| 10.0.4.0/24     | R1       | 3               |
| 10.0.5.0/24     | R1       | 3               |
| 10.0.6.0/24     | R1       | 3               |
| 10.0.8.0/24     | R2       | 4               |
| 10.0.12.0/24    | R1       | 4               |
| 10.0.9.0/24     | R1       | 5               |
| 10.0.10.0/24    | R1       | 5               |
| 10.0.11.0/24    | R1       | 5               |

A topologia termina a transação e se estabiliza de ponta a ponta sem loops ativos causados do roteamento distribuído, pronta para o trânsito da requisição final de empacotamento.
