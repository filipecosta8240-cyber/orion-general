const passages = [
  {
    title: 'O gato curioso',
    difficulty: 'Fácil',
    text: 'O gato curioso caminha devagar pelo jardim e observa as flores coloridas.',
  },
  {
    title: 'A aventura no parque',
    difficulty: 'Médio',
    text: 'A criança corre no parque e conta as nuvens brancas enquanto o vento sopra suave.',
  },
  {
    title: 'O livro especial',
    difficulty: 'Difícil',
    text: 'No final da manhã, ela lê um livro especial que fala sobre viagens, estrelas e novas ideias.',
  },
];

const textContainer = document.getElementById('textContainer');
const passageTitle = document.getElementById('passageTitle');
const difficultyLabel = document.getElementById('difficultyLabel');
const startButton = document.getElementById('startButton');
const stopButton = document.getElementById('stopButton');
const assistButton = document.getElementById('assistButton');
const nextButton = document.getElementById('nextButton');
const messageEl = document.getElementById('message');
const scoreValue = document.getElementById('scoreValue');
const scoreTableBody = document.querySelector('#scoreTable tbody');
const memoryMessage = document.getElementById('memoryMessage');
const memoryResults = document.getElementById('memoryResults');
const memoryAgentInput = document.getElementById('memoryAgent');
const memoryDomainInput = document.getElementById('memoryDomain');
const memorySearchButton = document.getElementById('memorySearchButton');
const memoryRefreshButton = document.getElementById('memoryRefreshButton');
const suggestionBox = document.getElementById('suggestionBox');
const suggestionRefreshButton = document.getElementById('suggestionRefreshButton');
const ORION_API_BASE = '/api';
const proposalsList = document.getElementById('proposalsList');
const proposalToolInput = document.getElementById('proposalTool');
const proposalObjectiveInput = document.getElementById('proposalObjective');
const proposalCreateButton = document.getElementById('proposalCreateButton');

let currentIndex = 0;
let recognition = null;
let inProgress = false;
let userStopped = false;
let words = [];
let currentMatchCount = 0;
let readingTranscript = '';

function hasSpeechRecognition() {
  return !!(window.SpeechRecognition || window.webkitSpeechRecognition);
}

function normalizeText(text) {
  return text
    .toLowerCase()
    .replace(/[.,;:!?]/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

function showPassage(index) {
  const passage = passages[index];
  passageTitle.textContent = passage.title;
  difficultyLabel.textContent = passage.difficulty;
  textContainer.innerHTML = '';
  words = normalizeText(passage.text).split(' ');
  words.forEach((word) => {
    const span = document.createElement('span');
    span.className = 'word';
    span.textContent = word + ' ';
    textContainer.appendChild(span);
  });
  scoreValue.textContent = '0';
  messageEl.textContent = 'Texto fica verde enquanto lês. O jogo só começa a ler depois de terminares.';
  nextButton.disabled = true;
  currentMatchCount = 0;
  readingTranscript = '';
  userStopped = false;
}

function updateHighlight(matchedIndex) {
  const spans = textContainer.querySelectorAll('.word');
  spans.forEach((span, idx) => {
    span.classList.toggle('active', idx < matchedIndex);
    span.classList.toggle('correct', idx < matchedIndex);
  });
}

function compareTranscript(transcript, highlight = true) {
  const normalizedTranscript = normalizeText(transcript);
  const transcriptWords = normalizedTranscript.split(' ');
  let matched = 0;
  for (let i = 0; i < words.length; i += 1) {
    if (transcriptWords[i] === words[i]) {
      matched += 1;
    } else {
      break;
    }
  }
  currentMatchCount = matched;
  if (highlight) {
    updateHighlight(matched);
  }
  return matched;
}

function calculateScore(matched) {
  const baseScore = Math.round((matched / words.length) * 100);
  return Math.max(0, Math.min(100, baseScore));
}

function saveResult(score) {
  const history = JSON.parse(localStorage.getItem('readingGameHistory') || '[]');
  history.unshift({
    title: passages[currentIndex].title,
    difficulty: passages[currentIndex].difficulty,
    score,
    date: new Date().toLocaleString('pt-BR', { hour12: false }),
  });
  localStorage.setItem('readingGameHistory', JSON.stringify(history.slice(0, 10)));
  renderHistory();
}

function renderHistory() {
  const history = JSON.parse(localStorage.getItem('readingGameHistory') || '[]');
  scoreTableBody.innerHTML = '';
  history.forEach((entry) => {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td>${entry.title}</td>
      <td>${entry.difficulty}</td>
      <td>${entry.score}</td>
      <td>${entry.date}</td>
    `;
    scoreTableBody.appendChild(row);
  });
}

function isServerMode() {
  return window.location.protocol.startsWith('http');
}

function setMemoryMessage(text) {
  memoryMessage.textContent = text;
}

async function orionFetch(path, options = {}) {
  if (!isServerMode()) {
    throw new Error('Abra o jogo via servidor ORION local para acessar a memória.');
  }

  const response = await fetch(`${ORION_API_BASE}${path}`, options);
  if (!response.ok) {
    throw new Error(`ORION não disponível (status ${response.status})`);
  }
  return response.json();
}

function renderMemoryEntries(entries) {
  if (!entries || entries.length === 0) {
    memoryResults.innerHTML = '<p>Nenhuma memória encontrada.</p>';
    return;
  }

  memoryResults.innerHTML = entries
    .map((entry) => {
      const tags = Object.entries(entry.tags)
        .map(([key, value]) => `<span>${key}: ${value}</span>`)
        .join('');
      return `
        <div class="memory-entry">
          <div class="memory-entry-title">${entry.title}</div>
          <div class="memory-entry-tags">${tags}</div>
          <p>${entry.content}</p>
          <div class="memory-entry-meta">Fonte: ${entry.source} • ${new Date(entry.created_at).toLocaleString('pt-BR')}</div>
        </div>
      `;
    })
    .join('');
}

async function refreshMemory() {
  try {
    setMemoryMessage('Atualizando memórias...');
    const data = await orionFetch('/memory');
    renderMemoryEntries(data);
    setMemoryMessage('Memória ORION sincronizada.');
  } catch (error) {
    setMemoryMessage(error.message);
    memoryResults.innerHTML = '';
  }
}

async function refreshSuggestion() {
  try {
    setMemoryMessage('Buscando sugestão personalizada...');
    const data = await orionFetch('/suggestions');
    suggestionBox.innerHTML = `
      <p><strong>${data.recommendation}</strong></p>
      <p>Dificuldade recomendada: <strong>${data.recommended_difficulty}</strong></p>
      <p>${data.reasoning.join(' ')}</p>
    `;
    setMemoryMessage('Sugestão ORION atualizada.');
  } catch (error) {
    suggestionBox.textContent = `Não foi possível obter sugestão: ${error.message}`;
    setMemoryMessage(error.message);
  }
}

function renderProposals(items) {
  if (!items || items.length === 0) {
    proposalsList.innerHTML = '<p>Nenhuma proposta disponível.</p>';
    return;
  }
  proposalsList.innerHTML = items
    .map(p => {
      return `
      <div class="proposal-item" data-id="${p.id}">
        <div><strong>${p.subject}</strong> — ${p.status}</div>
        <div>${p.summary}</div>
        <div style="margin-top:8px">${p.recommendation}</div>
        <div style="margin-top:8px">
          <button class="approve-btn secondary">Aprovar</button>
          <button class="decline-btn secondary">Recusar</button>
        </div>
      </div>
    `;
    })
    .join('');

  Array.from(document.querySelectorAll('.approve-btn')).forEach(btn => {
    btn.addEventListener('click', async (e) => {
      const id = e.target.closest('.proposal-item').dataset.id;
      try {
        await fetch(`${ORION_API_BASE}/proposals/approve`, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({id}) });
        await refreshProposals();
      } catch (err) {
        alert('Erro ao aprovar proposta');
      }
    });
  });
  Array.from(document.querySelectorAll('.decline-btn')).forEach(btn => {
    btn.addEventListener('click', async (e) => {
      const id = e.target.closest('.proposal-item').dataset.id;
      try {
        await fetch(`${ORION_API_BASE}/proposals/decline`, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({id}) });
        await refreshProposals();
      } catch (err) {
        alert('Erro ao recusar proposta');
      }
    });
  });
}

async function refreshProposals() {
  try {
    const data = await orionFetch('/proposals');
    renderProposals(data);
  } catch (err) {
    proposalsList.innerHTML = `<p>Erro: ${err.message}</p>`;
  }
}

async function createProposal() {
  const tool = proposalToolInput.value.trim();
  const objective = proposalObjectiveInput.value.trim();
  if (!tool || !objective) {
    alert('Preenche ferramenta e objetivo.');
    return;
  }
  try {
    const res = await fetch(`${ORION_API_BASE}/proposals/create`, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({tool, objective}) });
    if (!res.ok) throw new Error('Erro ao criar proposta');
    await refreshProposals();
    proposalToolInput.value = '';
    proposalObjectiveInput.value = '';
  } catch (err) {
    alert(err.message);
  }
}

async function searchMemory() {
  try {
    const agent = memoryAgentInput.value.trim();
    const domain = memoryDomainInput.value.trim();
    const query = new URLSearchParams();
    if (agent) query.set('agent', agent);
    if (domain) query.set('domain', domain);
    const path = query.toString() ? `/memory/search?${query.toString()}` : '/memory';
    setMemoryMessage('Buscando memórias...');
    const data = await orionFetch(path);
    renderMemoryEntries(data);
    setMemoryMessage(data.length ? 'Resultados carregados.' : 'Nenhuma memória encontrada para esses filtros.');
  } catch (error) {
    setMemoryMessage(error.message);
    memoryResults.innerHTML = '';
  }
}

async function saveResultToORION(score) {
  if (!isServerMode()) {
    return;
  }

  const payload = {
    title: `Resultado de Leitura: ${passageTitle.textContent}`,
    content: `Texto: ${passageTitle.textContent}\nDificuldade: ${difficultyLabel.textContent}\nPontuação: ${score}\nData: ${new Date().toLocaleString('pt-BR', { hour12: false })}`,
    agent: 'DOCUMENTALISTA',
    domain: 'jogo',
    priority: 'normal',
    freshness: 'today',
  };

  try {
    await orionFetch('/log', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    setMemoryMessage('Resultado enviado para ORION com sucesso.');
    await refreshMemory();
    await refreshSuggestion();
  } catch (error) {
    setMemoryMessage(`Não foi possível salvar no ORION: ${error.message}`);
  }
}

function speakText(text) {
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = 'pt-BR';
  utterance.rate = 0.95;
  utterance.pitch = 1.05;
  window.speechSynthesis.speak(utterance);
}

function handleRecognitionError(errorMessage) {
  const normalizedError = String(errorMessage).toLowerCase();
  if (/not-allowed|service-not-allowed|permission/.test(normalizedError)) {
    messageEl.textContent = `Reconhecimento de voz bloqueado: ${errorMessage}. Clica em "Ler automaticamente" se quiseres ver o texto a mudar.`;
    startButton.disabled = false;
    stopButton.disabled = true;
    assistButton.disabled = false;
    inProgress = false;
    if (recognition) {
      try {
        recognition.stop();
      } catch (err) {
        // ignore
      }
      recognition = null;
    }
    return;
  }

  if (/no-speech|aborted|audio-capture/.test(normalizedError)) {
    messageEl.textContent = 'Pausa detectada. Continua a ler devagar e o reconhecimento será reiniciado automaticamente.';
    if (recognition && inProgress && !userStopped) {
      setTimeout(() => {
        try {
          recognition.start();
        } catch (err) {
          messageEl.textContent = `Falha ao reiniciar o reconhecimento: ${err.message}`;
          startButton.disabled = false;
          stopButton.disabled = true;
          assistButton.disabled = false;
          inProgress = false;
          recognition = null;
        }
      }, 600);
    }
    return;
  }

  messageEl.textContent = `Não foi possível iniciar o reconhecimento de voz: ${errorMessage}. Usa "Ler automaticamente" ou abre o jogo num servidor local/HTTPS.`;
  startButton.disabled = false;
  stopButton.disabled = true;
  assistButton.disabled = false;
  inProgress = false;
  if (recognition) {
    try {
      recognition.stop();
    } catch (err) {
      // ignore
    }
    recognition = null;
  }
}

function autoReadPassage() {
  const passage = passages[currentIndex];
  const spans = Array.from(textContainer.querySelectorAll('.word'));
  let index = 0;

  if (!window.speechSynthesis) {
    messageEl.textContent = 'A leitura automática não está disponível neste navegador.';
    return;
  }

  startButton.disabled = true;
  stopButton.disabled = true;
  assistButton.disabled = true;
  messageEl.textContent = 'Lendo o texto automaticamente...';

  const interval = setInterval(() => {
    if (index >= spans.length) {
      clearInterval(interval);
      const score = 100;
      finishPassage(score);
      return;
    }
    spans[index].classList.add('active', 'correct');
    index += 1;
  }, 500);
}

function finishPassage(score) {
  compareTranscript(readingTranscript, true);
  scoreValue.textContent = String(score);
  messageEl.textContent = `Pontuação final: ${score}. Agora ouve o texto para reforçar a leitura.`;
  saveResult(score);
  saveResultToORION(score);
  if (recognition) {
    try {
      recognition.stop();
    } catch (err) {
      // ignore
    }
    recognition = null;
  }
  speakText(passages[currentIndex].text);
  nextButton.disabled = currentIndex >= passages.length - 1;
  stopButton.disabled = true;
  startButton.disabled = false;
  assistButton.disabled = false;
  inProgress = false;
}

function startRecognition() {
  if (!hasSpeechRecognition()) {
    messageEl.textContent = 'Este navegador não suporta reconhecimento de voz. Tenta no Chrome ou Edge ou usa a leitura automática.';
    assistButton.disabled = false;
    return;
  }

  if (recognition) {
    try {
      recognition.stop();
    } catch (err) {
      // ignore
    }
    recognition = null;
  }

  readingTranscript = '';
  userStopped = false;
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SpeechRecognition();
  recognition.lang = 'pt-BR';
  recognition.interimResults = true;
  recognition.maxAlternatives = 1;
  recognition.continuous = true;

  recognition.onstart = () => {
    inProgress = true;
    userStopped = false;
    messageEl.textContent = 'Estou a ouvir. Fala devagar e termina a leitura quando estiveres pronto.';
    startButton.disabled = true;
    stopButton.disabled = false;
    assistButton.disabled = true;
  };

  recognition.onresult = (event) => {
    let interimTranscript = '';
    let finalTranscript = '';

    for (let i = 0; i < event.results.length; i += 1) {
      const result = event.results[i];
      if (result.isFinal) {
        finalTranscript += result[0].transcript + ' ';
      } else {
        interimTranscript += result[0].transcript + ' ';
      }
    }

    if (finalTranscript.trim().length > 0) {
      readingTranscript += finalTranscript;
      const matchCount = compareTranscript(readingTranscript, true);
      const score = calculateScore(matchCount);
      scoreValue.textContent = String(score);
      messageEl.textContent = 'Leitura registada. Continua até terminares e clica em Parar.';
    }

    if (interimTranscript.trim().length > 0) {
      const currentTranscript = `${readingTranscript} ${interimTranscript}`.trim();
      const matchCount = compareTranscript(currentTranscript, true);
      const score = calculateScore(matchCount);
      scoreValue.textContent = String(score);
      messageEl.textContent = 'O texto está a ficar verde enquanto lês. Continua...' ;
    }
  };

  recognition.onerror = (event) => {
    handleRecognitionError(event.error || event.message || 'erro desconhecido');
  };

  recognition.onend = () => {
    if (!inProgress) {
      return;
    }

    const finalMatchCount = compareTranscript(readingTranscript, false);
    if (userStopped || finalMatchCount === words.length) {
      finishPassage(finalMatchCount);
      return;
    }

    if (recognition && !userStopped) {
      setTimeout(() => {
        try {
          recognition.start();
        } catch (err) {
          handleRecognitionError(err.message || 'erro ao reiniciar reconhecimento');
        }
      }, 300);
    }
  };

  try {
    recognition.start();
  } catch (startError) {
    handleRecognitionError(startError.message || 'erro ao iniciar reconhecimento');
  }
}

function stopRecognition() {
  if (recognition) {
    userStopped = true;
    recognition.stop();
    recognition = null;
  }
  stopButton.disabled = true;
  messageEl.textContent = 'A leitura foi finalizada. Aguarda que o jogo termine a avaliação e torne o texto verde.';
}

function handleStartClick() {
  updateHighlight(0);
  currentMatchCount = 0;
  startRecognition();
}

function handleNextClick() {
  if (currentIndex < passages.length - 1) {
    currentIndex += 1;
    showPassage(currentIndex);
  }
}

startButton.addEventListener('click', handleStartClick);
startButton.onclick = handleStartClick;

assistButton.addEventListener('click', autoReadPassage);
assistButton.onclick = autoReadPassage;

stopButton.addEventListener('click', stopRecognition);
stopButton.onclick = stopRecognition;

nextButton.addEventListener('click', handleNextClick);
nextButton.onclick = handleNextClick;

memorySearchButton.addEventListener('click', searchMemory);
memoryRefreshButton.addEventListener('click', refreshMemory);
suggestionRefreshButton.addEventListener('click', refreshSuggestion);
proposalCreateButton.addEventListener('click', createProposal);

window.addEventListener('load', () => {
  showPassage(currentIndex);
  renderHistory();
  refreshMemory();
  refreshSuggestion();
  refreshProposals();
});
