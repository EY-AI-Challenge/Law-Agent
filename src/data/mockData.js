export const MOCK_NODES = [
  {
    id: 'cc-217', type: 'lawNode',
    position: { x: 420, y: 180 },
    data: {
      label: 'Art. 217.º', code: 'CC',
      title: 'Declaração Negocial',
      cluster: 'Contratos', refs: 89, centrality: 0.94,
      desc: 'Norma central do Código Civil. Regula a validade e eficácia das declarações negociais, sendo a mais referenciada em litígios laborais e civis.',
      isHub: true,
    }
  },
  {
    id: 'cc-334', type: 'lawNode',
    position: { x: 580, y: 320 },
    data: {
      label: 'Art. 334.º', code: 'CC',
      title: 'Abuso de Direito',
      cluster: 'Direitos', refs: 45, centrality: 0.71,
      desc: 'Proíbe o exercício abusivo de direitos. Frequentemente invocado em casos de despedimento e conflitos laborais.',
    }
  },
  {
    id: 'cc-762', type: 'lawNode',
    position: { x: 460, y: 420 },
    data: {
      label: 'Art. 762.º', code: 'CC',
      title: 'Princípio da Boa-Fé',
      cluster: 'Contratos', refs: 38, centrality: 0.65,
      desc: 'Obrigação de agir de boa-fé na execução de contratos. Pilar fundamental do direito contratual português.',
    }
  },
  {
    id: 'cc-405', type: 'lawNode',
    position: { x: 320, y: 390 },
    data: {
      label: 'Art. 405.º', code: 'CC',
      title: 'Liberdade Contratual',
      cluster: 'Contratos', refs: 29, centrality: 0.51,
      desc: 'Consagra a liberdade das partes na celebração de contratos, dentro dos limites da lei.',
    }
  },
  {
    id: 'ct-53', type: 'lawNode',
    position: { x: 160, y: 140 },
    data: {
      label: 'Art. 53.º', code: 'CT',
      title: 'Garantia de Ocupação',
      cluster: 'Trabalho', refs: 74, centrality: 0.88,
      desc: 'Garante ao trabalhador o direito à ocupação efetiva. Um dos artigos mais litigados do Código do Trabalho.',
      isHub: true,
    }
  },
  {
    id: 'ct-98', type: 'lawNode',
    position: { x: 80, y: 300 },
    data: {
      label: 'Art. 98.º', code: 'CT',
      title: 'Direito a Férias',
      cluster: 'Trabalho', refs: 52, centrality: 0.68,
      desc: 'Estabelece o regime base do direito a férias. 22 dias úteis mínimos por ano.',
    }
  },
  {
    id: 'ct-119', type: 'lawNode',
    position: { x: 200, y: 420 },
    data: {
      label: 'Art. 119.º', code: 'CT',
      title: 'Retribuição Base',
      cluster: 'Remuneração', refs: 41, centrality: 0.59,
      desc: 'Define retribuição base e diuturnidades. Referência para cálculo de subsídios e indemnizações.',
    }
  },
  {
    id: 'ct-340', type: 'lawNode',
    position: { x: 130, y: 480 },
    data: {
      label: 'Art. 340.º', code: 'CT',
      title: 'Cessação do Contrato',
      cluster: 'Cessação', refs: 33, centrality: 0.48,
      desc: 'Regula os modos de cessação do contrato de trabalho por iniciativa do empregador.',
    }
  },
  {
    id: 'dl-47-2020', type: 'lawNode',
    position: { x: 300, y: 230 },
    data: {
      label: 'DL 47/2020', code: 'DL',
      title: 'Contratos Especiais',
      cluster: 'Regulação', refs: 61, centrality: 0.72,
      desc: 'Decreto-Lei n.º 47/2020. Regula contratos especiais de trabalho e situações atípicas de emprego.',
    }
  },
  {
    id: 'dl-83-2021', type: 'lawNode',
    position: { x: 230, y: 340 },
    data: {
      label: 'DL 83/2021', code: 'DL',
      title: 'Trabalho Remoto',
      cluster: 'Trabalho', refs: 28, centrality: 0.44,
      desc: 'Decreto-Lei n.º 83/2021. Adapta o regime do teletrabalho e trabalho remoto em Portugal.',
    }
  },
  {
    id: 'dl-12-2019', type: 'lawNode',
    position: { x: 500, y: 100 },
    data: {
      label: 'DL 12/2019', code: 'DL',
      title: 'Regime Geral',
      cluster: 'Regulação', refs: 19, centrality: 0.31,
      desc: 'Decreto-Lei n.º 12/2019. Disposições gerais de regulação do mercado laboral.',
    }
  },
]

export const MOCK_EDGES = [
  { id: 'e1',  source: 'ct-53',  target: 'cc-217',    animated: false },
  { id: 'e2',  source: 'ct-53',  target: 'cc-334',    animated: false },
  { id: 'e3',  source: 'ct-53',  target: 'dl-47-2020',animated: false },
  { id: 'e4',  source: 'ct-98',  target: 'cc-217',    animated: false },
  { id: 'e5',  source: 'ct-98',  target: 'cc-762',    animated: false },
  { id: 'e6',  source: 'ct-98',  target: 'dl-83-2021',animated: false },
  { id: 'e7',  source: 'ct-119', target: 'cc-762',    animated: false },
  { id: 'e8',  source: 'ct-119', target: 'cc-405',    animated: false },
  { id: 'e9',  source: 'ct-119', target: 'dl-83-2021',animated: false },
  { id: 'e10', source: 'ct-340', target: 'cc-334',    animated: false },
  { id: 'e11', source: 'ct-340', target: 'cc-405',    animated: false },
  { id: 'e12', source: 'dl-47-2020', target: 'cc-217',animated: false },
  { id: 'e13', source: 'dl-47-2020', target: 'cc-762',animated: false },
  { id: 'e14', source: 'cc-217', target: 'cc-334',    animated: false },
  { id: 'e15', source: 'cc-217', target: 'cc-762',    animated: false },
  { id: 'e16', source: 'dl-12-2019', target: 'cc-217',animated: false },
  { id: 'e17', source: 'dl-12-2019', target: 'dl-47-2020', animated: false },
  { id: 'e18', source: 'ct-53',  target: 'ct-98',     animated: false },
  { id: 'e19', source: 'ct-98',  target: 'ct-119',    animated: false },
]

export const MOCK_STATS = {
  totalDocs: 247,
  totalRefs: 1842,
  clusters: 34,
  centralLaw: 'Art. 217.º CC',
}

export const MOCK_CLUSTERS = ['Todos', 'Contratos', 'Trabalho', 'Direitos', 'Remuneração', 'Cessação', 'Regulação']

export const MOCK_CHAT_HISTORY = [
  {
    role: 'assistant',
    text: 'Olá! Sou o assistente legal da EY. Exploro as relações entre o Código do Trabalho e o Código Civil português. Clica num nó do grafo para análise detalhada, ou faz-me uma pergunta.',
    highlight: 'Dica: usa os filtros de cluster para focar numa área temática.'
  }
]
