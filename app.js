/* brAIndance - Quiz Management app.
   Front-end for the testapp.py JSON API (topics stored in JSON files). */

let topics = [];
let currentActiveTopicId = null;
let currentEditingQuestionId = null;
let activeQuizQuestions = [];
let activeQuizIndex = 0;
let quizAnswers = [];
let username = 'Guest';

/* NAVIGATION HISTORY */
let navigationStack = ['mainMenu'];

/* ---- API helper ------------------------------------------------------ */
async function api(path, method = 'GET', body) {
  const opts = { method: method, headers: {} };
  if (body !== undefined) {
    opts.headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(path, opts);
  let data = null;
  const ct = res.headers.get('Content-Type') || '';
  if (ct.indexOf('application/json') !== -1) {
    data = await res.json();
  }
  if (!res.ok) {
    throw new Error((data && data.error) ? data.error : ('Request failed (' + res.status + ')'));
  }
  return data;
}

function cap(s) {
  return (s || '').toString().charAt(0).toUpperCase() + (s || '').toString().slice(1);
}

/* ---- Account --------------------------------------------------------- */
async function loadAccount() {
  try {
    const d = await api('/api/account');
    username = d.username || 'Guest';
  } catch (e) {
    username = 'Guest';
  }
  updateWelcomeLabel();
}

function updateWelcomeLabel() {
  const el = document.getElementById('welcomeLabel');
  if (el) el.innerText = 'Hi, ' + username;
}

function openAccountModal() {
  document.getElementById('accountNameInput').value = username;
  document.getElementById('accountModal').classList.remove('hidden');
  document.getElementById('accountModal').classList.add('flex');
  document.getElementById('accountNameInput').focus();
}

function closeAccountModal() {
  document.getElementById('accountModal').classList.add('hidden');
  document.getElementById('accountModal').classList.remove('flex');
}

async function saveAccountName() {
  const name = document.getElementById('accountNameInput').value.trim();
  if (!name) return alert('Please enter a display name.');
  try {
    const d = await api('/api/account', 'POST', { display_name: name });
    username = d.username || name;
    updateWelcomeLabel();
    closeAccountModal();
    showToast('Welcome, ' + username + '!');
  } catch (e) {
    alert(e.message);
  }
}

/* ---- Toast ----------------------------------------------------------- */
let toastTimer = null;
function showToast(text) {
  document.getElementById('appToastText').innerText = text;
  document.getElementById('appToast').classList.remove('hidden');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    document.getElementById('appToast').classList.add('hidden');
  }, 2200);
}

/* ---- Topic loading --------------------------------------------------- */
async function loadTopics() {
  const d = await api('/api/topics');
  topics = d.topics || [];
  return topics;
}

/* NAVIGATION & HEADER LOCKDOWN LOGIC */
function navigateTo(screenId, isBack = false) {
  if (!isBack) {
    if (screenId === 'mainMenu') {
      navigationStack = ['mainMenu'];
    } else if (navigationStack[navigationStack.length - 1] !== screenId) {
      navigationStack.push(screenId);
    }
  }

  // Hide all screens & show active screen
  document.querySelectorAll('.screen-view').forEach(s => s.classList.add('hidden'));
  document.getElementById(screenId).classList.remove('hidden');

  const isMain = (screenId === 'mainMenu');
  const isQuizPlayer = (screenId === 'quizPlayer');
  const isQuizResults = (screenId === 'quizResults');

  if (isQuizPlayer || isQuizResults) {
    // QUIZ ACTIVE LOCKDOWN: Hide header left and right, show ONLY logo
    document.getElementById('headerLeft').classList.add('hidden');
    document.getElementById('headerRight').classList.add('hidden');
    document.getElementById('headerLogo').classList.remove('hidden');
  } else {
    //  NORMAL NAVIGATION HEADER
    document.getElementById('headerLeft').classList.remove('hidden');
    document.getElementById('headerRight').classList.remove('hidden');

    // Left side elements toggling
    document.getElementById('headerTitle').classList.toggle('hidden', !isMain);
    document.getElementById('backBtn').classList.toggle('hidden', isMain);

    // Center logo icon toggling (shows when not on main menu)
    document.getElementById('headerLogo').classList.toggle('hidden', isMain);
  }

  // Populate screen dropdowns if needed
  if (screenId === 'generateQuiz') populateDropdown('quizTopicSelect');
  if (screenId === 'createTopic') populateComboboxOptions();
  if (screenId === 'updateTopic') { populateDropdown('updateTopicSelect'); loadTopicForEdit(); }
  if (screenId === 'deleteTopic') populateDropdown('deleteTopicSelect');
}

function goBack() {
  if (navigationStack.length > 1) {
    navigationStack.pop();
    const prevScreen = navigationStack[navigationStack.length - 1];
    navigateTo(prevScreen, true);
  } else {
    navigateTo('mainMenu', true);
  }
}

function populateDropdown(selectId) {
  const select = document.getElementById(selectId);
  if (topics.length === 0) {
    select.innerHTML = '<option value="">No Topics Available</option>';
  } else {
    const optionsHtml = selectId === 'updateTopicSelect' ? '<option value="">Select Topic</option>' : '';
    select.innerHTML = optionsHtml + topics.map(t => `<option value="${t.id}">${t.name}</option>`).join('');
  }
}

/* COMBOBOX LOGIC */
function populateComboboxOptions() {
  const dropdown = document.getElementById('comboboxDropdown');
  if (!dropdown) return;

  if (topics.length === 0) {
    dropdown.innerHTML = '<div class="px-3 py-2 text-xs opacity-70">No existing topics</div>';
    return;
  }

  dropdown.innerHTML = topics.map(t => `
    <div onclick="selectComboboxOption('${t.name.replace(/'/g, "\\'")}')" class="px-3 py-2.5 text-sm rounded-lg hover:bg-white/20 cursor-pointer transition flex justify-between items-center">
      <span class="font-medium">${t.name}</span>
      <span class="text-[11px] opacity-70 bg-white/10 px-2 py-0.5 rounded">${t.questions.length} Qs</span>
    </div>
  `).join('');
}

function showComboboxOptions() {
  filterComboboxOptions();
  document.getElementById('comboboxDropdown').classList.remove('hidden');
}

function toggleComboboxOptions() {
  const dropdown = document.getElementById('comboboxDropdown');
  if (dropdown.classList.contains('hidden')) {
    showComboboxOptions();
  } else {
    dropdown.classList.add('hidden');
  }
}

function filterComboboxOptions() {
  const val = document.getElementById('newTopicName').value.toLowerCase();
  const dropdown = document.getElementById('comboboxDropdown');

  const filtered = topics.filter(t => t.name.toLowerCase().includes(val));

  if (filtered.length === 0) {
    dropdown.innerHTML = '<div class="px-3 py-2 text-xs opacity-70">New topic will be created</div>';
  } else {
    dropdown.innerHTML = filtered.map(t => `
      <div onclick="selectComboboxOption('${t.name.replace(/'/g, "\\'")}')" class="px-3 py-2.5 text-sm rounded-lg hover:bg-white/20 cursor-pointer transition flex justify-between items-center">
        <span class="font-medium">${t.name}</span>
        <span class="text-[11px] opacity-70 bg-white/10 px-2 py-0.5 rounded">${t.questions.length} Qs</span>
      </div>
    `).join('');
  }
  dropdown.classList.remove('hidden');
}

function selectComboboxOption(name) {
  document.getElementById('newTopicName').value = name;
  document.getElementById('comboboxDropdown').classList.add('hidden');
}

document.addEventListener('click', (e) => {
  const wrapper = document.getElementById('comboboxWrapper');
  if (wrapper && !wrapper.contains(e.target)) {
    const dropdown = document.getElementById('comboboxDropdown');
    if (dropdown) dropdown.classList.add('hidden');
  }
});

/* MODAL DIALOGS WITH YES/NO CALLBACKS */
function showModal(text, onYes, onNo) {
  document.getElementById('confirmModalText').innerText = text;
  const modal = document.getElementById('confirmModal');
  modal.classList.remove('hidden');
  modal.classList.add('flex');

  document.getElementById('modalYesBtn').onclick = () => {
    closeModal();
    if (onYes) onYes();
  };

  document.getElementById('modalNoBtn').onclick = () => {
    closeModal();
    if (onNo) onNo();
  };
}

function closeModal() {
  const modal = document.getElementById('confirmModal');
  modal.classList.add('hidden');
  modal.classList.remove('flex');
}

/* QUIZ FLOW */
function confirmQuizStart() {
  const topicId = document.getElementById('quizTopicSelect').value;
  if (!topicId) return alert("Please create or select a topic first.");
  showModal("Do you want to take this quiz now?", () => startQuiz(topicId));
}

function startQuiz(topicId) {
  const topic = topics.find(t => t.id === topicId);
  const diff = document.getElementById('quizDiffSelect').value;

  activeQuizQuestions = topic ? topic.questions.filter(q => q.diff === diff) : [];
  if (activeQuizQuestions.length === 0 && topic) {
    activeQuizQuestions = topic.questions;
  }

  if (!activeQuizQuestions || activeQuizQuestions.length === 0) {
    return alert("No questions available in this topic.");
  }

  activeQuizIndex = 0;
  quizAnswers = [];
  document.getElementById('quizTopicBadge').innerText = topic.name;
  renderQuizQuestion();
  navigateTo('quizPlayer');
}

function renderQuizQuestion() {
  const q = activeQuizQuestions[activeQuizIndex];
  document.getElementById('quizProgress').innerText = `Question #${activeQuizIndex + 1} of ${activeQuizQuestions.length}`;
  document.getElementById('quizQuestionText').innerText = q.prompt;

  // Manage Back Button visibility and button widths
  const backBtn = document.getElementById('quizBackBtn');
  const nextBtn = document.getElementById('nextQBtn');

  if (activeQuizIndex === 0) {
    backBtn.classList.add('hidden');
    nextBtn.classList.remove('w-1/2');
    nextBtn.classList.add('w-full');
  } else {
    backBtn.classList.remove('hidden');
    backBtn.classList.add('w-1/2');
    nextBtn.classList.remove('w-full');
    nextBtn.classList.add('w-1/2');
  }

  // Change Next to Submit on the last question
  if (activeQuizIndex === activeQuizQuestions.length - 1) {
    nextBtn.innerText = 'Submit →';
  } else {
    nextBtn.innerText = 'Next →';
  }

  const container = document.getElementById('quizOptionsContainer');
  container.innerHTML = q.options.map((opt, i) => {
    const isSelected = quizAnswers[activeQuizIndex] === i;
    const bgStyle = isSelected ? 'background-color: rgba(255, 255, 255, 0.4); border-color: #ffffff;' : 'background-color: rgba(0, 0, 0, 0.2); border-color: rgba(255, 255, 255, 0.2);';
    return `
      <button onclick="selectOption(${i})" class="quiz-opt-btn brand-btn text-left px-4 border transition" style="${bgStyle}">
        ${String.fromCharCode(65 + i)}. ${opt}
      </button>
    `;
  }).join('');
}

function selectOption(index) {
  quizAnswers[activeQuizIndex] = index;
  renderQuizQuestion();
}

function prevQuestion() {
  if (activeQuizIndex > 0) {
    activeQuizIndex--;
    renderQuizQuestion();
  }
}

function handleQuizNext() {
  if (activeQuizIndex < activeQuizQuestions.length - 1) {
    activeQuizIndex++;
    renderQuizQuestion();
  } else {
    openQuizSummary();
  }
}

function openQuizSummary() {
  const summaryList = document.getElementById('quizSummaryList');

  summaryList.innerHTML = activeQuizQuestions.map((q, i) => {
    const ansIdx = quizAnswers[i];
    const ansText = ansIdx !== undefined ? `${String.fromCharCode(65 + ansIdx)}. ${q.options[ansIdx]}` : '<span class="text-yellow-300 font-semibold">Unanswered</span>';

    return `
      <div onclick="jumpToQuestion(${i})" class="p-3 rounded-xl bg-black/20 border border-white/20 text-xs flex justify-between items-center cursor-pointer hover:bg-black/30 transition">
        <div class="truncate pr-2">
          <p class="font-bold">Q${i + 1}: ${q.prompt}</p>
          <p class="opacity-80 mt-0.5">Answer: ${ansText}</p>
        </div>
        <i class="fa-solid fa-chevron-right opacity-60"></i>
      </div>
    `;
  }).join('');

  navigateTo('quizSummary');
}

function jumpToQuestion(index) {
  activeQuizIndex = index;
  renderQuizQuestion();
  navigateTo('quizPlayer');
}

function confirmFinalSubmit() {
  showModal("Are you sure you want to submit the quiz?", () => {
    finishQuiz();
  });
}

async function finishQuiz() {
  let correctCount = 0;
  const topicName = document.getElementById('quizTopicBadge').innerText;
  const diff = document.getElementById('quizDiffSelect').value;

  const resultsHtml = activeQuizQuestions.map((q, i) => {
    const userAns = quizAnswers[i];
    const isCorrect = userAns === q.correct;
    if (isCorrect) correctCount++;
    const ansDisplay = userAns !== undefined ? `${String.fromCharCode(65 + userAns)}. ${q.options[userAns]}` : 'Unanswered';

    return `
      <div class="p-3 rounded-lg bg-black/20 border border-white/20 flex items-center justify-between">
        <div class="text-xs">
          <p class="font-bold">Q${i + 1}: ${q.prompt}</p>
          <p class="opacity-80">Your Answer: ${ansDisplay}</p>
        </div>
        <div class="text-lg">${isCorrect ? '✅' : '❌'}</div>
      </div>
    `;
  }).join('');

  const percentage = Math.round((correctCount / activeQuizQuestions.length) * 100);
  document.getElementById('scoreDisplay').innerText = `${correctCount} / ${activeQuizQuestions.length}`;
  document.getElementById('percentageDisplay').innerText = `${percentage}% Correct`;
  document.getElementById('quizSummaryDetails').innerText = `Topic: ${topicName} | Difficulty: ${cap(diff)}`;
  document.getElementById('resultsList').innerHTML = resultsHtml;

  // Record the result on the server (best effort)
  try {
    await api('/api/quizzes', 'POST', {
      topic_id: currentActiveTopicId,
      difficulty: diff,
      answers: activeQuizQuestions.map((q, i) => ({ question_id: q.id, selected: quizAnswers[i] !== undefined ? quizAnswers[i] : null }))
    });
  } catch (e) { /* non-fatal */ }

  navigateTo('quizResults');
}

/* TOPIC & QUESTION CRUD LOGIC */
async function handleCreateTopic() {
  const name = document.getElementById('newTopicName').value.trim();
  if (!name) return alert("Please enter or select a topic name.");

  const existingTopic = topics.find(t => t.name.toLowerCase() === name.toLowerCase());

  if (existingTopic) {
    currentActiveTopicId = existingTopic.id;
    document.getElementById('newTopicName').value = '';
    showModal(`Topic "${existingTopic.name}" already exists. Open it to add a question?`, () => {
      document.getElementById('addQTitle').innerText = `Add Question: ${existingTopic.name}`;
      navigateTo('addQuestion');
    });
    return;
  }

  try {
    const d = await api('/api/topics', 'POST', { name: name });
    topics = d.topics || topics;
    const created = (topics.find(t => t.name.toLowerCase() === name.toLowerCase()));
    currentActiveTopicId = created ? created.id : null;
    document.getElementById('newTopicName').value = '';
    showToast('Topic "' + name + '" created.');
    showModal(`Topic "${name}" created. Do you want to add a question now?`, () => {
      document.getElementById('addQTitle').innerText = `Add Question: ${name}`;
      navigateTo('addQuestion');
    });
  } catch (e) {
    alert(e.message);
  }
}

function openAddQuestionForCurrentTopic() {
  currentActiveTopicId = document.getElementById('updateTopicSelect').value;
  const t = topics.find(item => item.id === currentActiveTopicId);
  if (t) {
    document.getElementById('addQTitle').innerText = `Add Question: ${t.name}`;
    navigateTo('addQuestion');
  }
}

async function saveQuestionAndAskMore() {
  const prompt = document.getElementById('qPrompt').value.trim();
  const optA = document.getElementById('qOptionA').value.trim();
  const optB = document.getElementById('qOptionB').value.trim();
  const correct = parseInt(document.getElementById('qCorrect').value);
  const diff = document.getElementById('qDiff').value;

  if (!prompt || !optA || !optB) return alert("Please fill in all fields.");

  const topic = topics.find(t => t.id === currentActiveTopicId);
  if (!topic) return alert("Select a topic first.");

  try {
    const d = await api(`/api/topics/${encodeURIComponent(topic.id)}/questions`, 'POST', {
      prompt: prompt, optionA: optA, optionB: optB, correct: correct, diff: diff
    });
    topics = d.topics || topics;

    document.getElementById('qPrompt').value = '';
    document.getElementById('qOptionA').value = '';
    document.getElementById('qOptionB').value = '';

    showToast('Question saved.');
    showModal("Question saved! Do you want to add another question?",
      () => {
        document.getElementById('qPrompt').focus();
      },
      () => {
        goBack();
      }
    );
  } catch (e) {
    alert(e.message);
  }
}

/* UPDATE TOPIC & MODIFY QUESTION FLOW */
function loadTopicForEdit() {
  const id = document.getElementById('updateTopicSelect').value;
  currentActiveTopicId = id;

  const topic = topics.find(t => t.id === id);
  const section = document.getElementById('modifyQuestionSection');
  const list = document.getElementById('updateQuestionsList');
  const saveBtn = document.getElementById('saveModificationsBtn');

  if (!topic) {
    section.classList.add('hidden');
    saveBtn.classList.add('hidden');
    return;
  }

  section.classList.remove('hidden');
  saveBtn.classList.remove('hidden');

  if (topic.questions.length === 0) {
    list.innerHTML = '<p class="text-xs opacity-75 text-center py-3">No questions saved yet. Click below to add one.</p>';
    return;
  }

  list.innerHTML = topic.questions.map((q, idx) => `
    <div onclick="openModifyQuestion('${q.id}')" class="question-card-item p-3 rounded-xl bg-black/20 border border-white/20 text-xs flex justify-between items-center">
      <div class="truncate pr-2">
        <span class="font-bold opacity-90">${idx + 1}.</span> ${q.prompt}
      </div>
      <div class="flex items-center gap-2">
        <span class="font-semibold px-2 py-0.5 rounded bg-white/20 text-[10px]">${cap(q.diff)}</span>
        <i class="fa-solid fa-chevron-right opacity-60"></i>
      </div>
    </div>
  `).join('');
}

function openModifyQuestion(questionId) {
  currentEditingQuestionId = questionId;
  const topic = topics.find(t => t.id === currentActiveTopicId);
  if (!topic) return;

  const q = topic.questions.find(item => item.id === questionId);
  if (!q) return;

  document.getElementById('editQPrompt').value = q.prompt || '';
  document.getElementById('editQOptionA').value = q.options[0] || '';
  document.getElementById('editQOptionB').value = q.options[1] || '';
  document.getElementById('editQCorrect').value = q.correct !== undefined ? q.correct : 0;
  document.getElementById('editQDiff').value = q.diff || 'easy';

  navigateTo('modifyQuestion');
}

async function saveModifiedQuestion() {
  const prompt = document.getElementById('editQPrompt').value.trim();
  const optA = document.getElementById('editQOptionA').value.trim();
  const optB = document.getElementById('editQOptionB').value.trim();
  const correct = parseInt(document.getElementById('editQCorrect').value);
  const diff = document.getElementById('editQDiff').value;

  if (!prompt || !optA || !optB) return alert("Please fill in all fields.");

  try {
    const d = await api(`/api/topics/${encodeURIComponent(currentActiveTopicId)}/questions/${encodeURIComponent(currentEditingQuestionId)}`, 'PUT', {
      prompt: prompt, optionA: optA, optionB: optB, correct: correct, diff: diff
    });
    topics = d.topics || topics;
    showToast('Question updated.');
  } catch (e) {
    alert(e.message);
  }

  goBack();
  if (document.getElementById('updateTopicSelect')) {
    document.getElementById('updateTopicSelect').value = currentActiveTopicId;
    loadTopicForEdit();
  }
}

function confirmSaveModifications() {
  showModal("Save all topic modifications?", async () => {
    try {
      const d = await api('/api/topics');
      topics = d.topics || topics;
    } catch (e) { /* non-fatal */ }
    navigateTo('mainMenu');
  });
}

function promptDeleteQuestion() {
  const topic = topics.find(t => t.id === currentActiveTopicId);
  if (!topic) return;

  showModal('Do you want to delete this question?', async () => {
    try {
      const d = await api(`/api/topics/${encodeURIComponent(currentActiveTopicId)}/questions/${encodeURIComponent(currentEditingQuestionId)}`, 'DELETE');
      topics = d.topics || topics;
      showToast('Question deleted.');
      goBack();
      if (document.getElementById('updateTopicSelect')) {
        document.getElementById('updateTopicSelect').value = currentActiveTopicId;
        loadTopicForEdit();
      }
    } catch (e) {
      alert(e.message);
    }
  });
}

async function promptDeleteTopic() {
  const id = document.getElementById('deleteTopicSelect').value;
  const topic = topics.find(t => t.id === id);
  if (!topic) return alert("Please select a topic.");

  showModal(`Do you want to delete "${topic.name}"?`, async () => {
    try {
      const d = await api(`/api/topics/${encodeURIComponent(id)}`, 'DELETE');
      topics = d.topics || topics;
      showToast('Topic "' + topic.name + '" deleted.');
      navigateTo('mainMenu');
    } catch (e) {
      alert(e.message);
    }
  });
}

function toggleMenu() {

}

/* Boot */
(async function init() {
  try {
    await loadTopics();
  } catch (e) {
    /* topics stay empty; API errors will surface on each action */
  }
  loadAccount();
})();