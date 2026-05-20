import axios from 'axios'
import { MOCK_NODES, MOCK_EDGES, MOCK_STATS, MOCK_CHAT_HISTORY } from '../data/mockData'

const USE_MOCK = true  // set to false when backend is ready

const api = axios.create({ baseURL: '/api', timeout: 10000 })

export async function fetchGraph() {
  if (USE_MOCK) {
    await delay(300)
    return { nodes: MOCK_NODES, edges: MOCK_EDGES }
  }
  const res = await api.get('/graph')
  return res.data
}

export async function fetchStats() {
  if (USE_MOCK) {
    await delay(200)
    const { MOCK_STATS } = await import('../data/mockData')
    return MOCK_STATS
  }
  const res = await api.get('/stats')
  return res.data
}

export async function askAssistant(question, context = null) {
  if (USE_MOCK) {
    await delay(800)
    return mockAssistantResponse(question, context)
  }
  const res = await api.post('/ask', { question, context })
  return res.data.answer
}

export async function fetchNodeDetails(nodeId) {
  if (USE_MOCK) {
    await delay(200)
    return null
  }
  const res = await api.get(`/node/${nodeId}`)
  return res.data
}

function mockAssistantResponse(question, context) {
  if (context) {
    return `**${context.label} — ${context.title}**\n\nEste artigo pertence ao cluster *${context.cluster}* e apresenta uma centralidade de **${context.centrality}** na rede legal portuguesa. É referenciado por **${context.refs} documentos legais**.\n\n${context.desc}\n\nPara uma análise completa das suas conexões, o backend GraphRAG precisa de estar ligado.`
  }
  const q = question.toLowerCase()
  if (q.includes('cluster') || q.includes('denso'))
    return 'O cluster mais denso é **Contratos**, com 3 artigos do Código Civil (217.º, 762.º, 405.º) e forte ligação ao Código do Trabalho. Representa 38% de todas as referências cruzadas na rede.'
  if (q.includes('conflict') || q.includes('inconsist'))
    return 'Foram detetadas **2 potenciais inconsistências**: (1) sobreposição entre Art. 53.º CT e Art. 217.º CC na definição de obrigações negociais; (2) lacuna na regulação de contratos remotos entre DL 83/2021 e Art. 119.º CT.'
  if (q.includes('influent') || q.includes('central'))
    return 'As leis mais influentes por centralidade de betweenness: **Art. 217.º CC** (0.94), **Art. 53.º CT** (0.88), **DL 47/2020** (0.72). Estes três nós são pontes críticas na rede — remover qualquer um fragmentaria o grafo em subclusters isolados.'
  return 'A consultar a rede legal portuguesa... Para respostas precisas com GraphRAG, o backend precisa de estar ligado. No modo demo, posso responder a perguntas sobre clusters, influência, inconsistências e relações específicas entre artigos.'
}

const delay = ms => new Promise(r => setTimeout(r, ms))
