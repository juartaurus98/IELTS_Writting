const DEFAULT_API_BASE = 'http://127.0.0.1:8001';
const apiBase = (typeof window !== 'undefined' && window.API_BASE)
  ? window.API_BASE
  : DEFAULT_API_BASE;

const prompt1El = document.getElementById('prompt1');
const prompt2El = document.getElementById('prompt2');
const promptErrorEl = document.getElementById('prompt-error');
const chartDataContainerEl = document.getElementById('chart-data-container');
const chartDataEl = document.getElementById('chart-data');
const chartImageEl = document.getElementById('chart-image');
const chartDataFallbackEl = document.getElementById('chart-data-fallback');
const modeAutoEl = document.getElementById('mode-auto');
const modeManualEl = document.getElementById('mode-manual');
const manualPromptsWrapEl = document.getElementById('manual-prompts');
const customPrompt1El = document.getElementById('customPrompt1');
const customPrompt2El = document.getElementById('customPrompt2');
const essay1El = document.getElementById('essay1');
const essay2El = document.getElementById('essay2');
const result1El = document.getElementById('result1');
const result2El = document.getElementById('result2');
const btnHealth = document.getElementById('btn-health');
const btnGenerate = document.getElementById('btn-generate');
const btnSubmitBatch = document.getElementById('btn-submit-batch');

function renderOneResult(container, data) {
  if (!data || typeof data !== 'object') {
    container.innerHTML = '<p class="small">Không có dữ liệu.</p>';
    return;
  }
  const criteriaHtml = (data.criteria || []).map(c => `
    <div class="card">
      <h3>${c.name}</h3>
      <div><strong>Band:</strong> ${c.band?.toFixed ? c.band.toFixed(1) : c.band}</div>
      <div class="small">${escapeHtml(c.comment || '')}</div>
    </div>
  `).join('');
  const improvedBlock = data.improved_version
    ? `<div class="card"><h3>Bản viết mượt hơn</h3><div class="small">${escapeHtml(data.improved_version)}</div></div>`
    : '';
  container.innerHTML = `
    <div class="band">Overall Band: ${data.overall_band?.toFixed ? data.overall_band.toFixed(1) : data.overall_band}</div>
    <div class="card"><h3>Tóm tắt</h3><div>${escapeHtml(data.feedback || '')}</div></div>
    <div class="card"><h3>Gợi ý cải thiện</h3><div>${escapeHtml(data.suggestions || '')}</div></div>
    <div class="criteria">${criteriaHtml}</div>
    ${improvedBlock}
  `;
}

function escapeHtml(str) {
  return String(str)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

async function checkHealth() {
  promptErrorEl.textContent = '';
  try {
    const res = await fetch(`${apiBase}/api/health`);
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    promptErrorEl.style.color = '#22c55e';
    promptErrorEl.textContent = 'Kết nối OK.';
  } catch (e) {
    promptErrorEl.style.color = '#ef4444';
    promptErrorEl.textContent = 'Không kết nối được backend: ' + (e && e.message ? e.message : 'Failed to fetch');
  }
}

async function generateTasks() {
  promptErrorEl.textContent = '';
  btnGenerate.disabled = true;
  if (modeManualEl?.checked) {
    // Ở chế độ nhập thủ công, nút này sẽ chỉ đồng bộ textarea vào khung hiển thị
    const t1 = (customPrompt1El?.value || '').trim();
    const t2 = (customPrompt2El?.value || '').trim();
    if (!t1 || !t2) {
      promptErrorEl.style.color = '#ef4444';
      promptErrorEl.textContent = 'Hãy nhập đủ đề Task 1 và Task 2.';
    }
    prompt1El.textContent = t1 || 'Chưa nhập đề Task 1.';
    prompt2El.textContent = t2 || 'Chưa nhập đề Task 2.';
    btnGenerate.disabled = false;
    return;
  }
  [prompt1El, prompt2El].forEach(el => { el.classList.add('loading'); el.textContent = 'Đang sinh đề...'; });
  try {
    const url = `${apiBase}/api/generate_tasks`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    const data = await res.json();
    const t1 = (data && data.task1) ? String(data.task1).trim() : '';
    const t2 = (data && data.task2) ? String(data.task2).trim() : '';
    const chartData = (data && data.task1_chart_data) ? String(data.task1_chart_data).trim() : '';
    const chartImage = (data && data.task1_chart_image) ? String(data.task1_chart_image).trim() : '';
    if (!t1 || !t2) {
      promptErrorEl.style.color = '#ef4444';
      promptErrorEl.textContent = 'Không lấy được đề từ máy chủ. Hãy kiểm tra API key hoặc log server.';
    }
    prompt1El.textContent = t1 || 'Không lấy được đề Task 1.';
    prompt2El.textContent = t2 || 'Không lấy được đề Task 2.';
    
    // Hiển thị hình ảnh biểu đồ hoặc dữ liệu text
    if (chartImage) {
      chartImageEl.src = 'data:image/png;base64,' + chartImage;
      chartImageEl.style.display = 'block';
      chartDataFallbackEl.style.display = 'none';
      chartDataContainerEl.style.display = 'block';
    } else if (chartData) {
      chartImageEl.style.display = 'none';
      chartDataEl.textContent = chartData;
      chartDataFallbackEl.style.display = 'block';
      chartDataContainerEl.style.display = 'block';
    } else {
      chartDataContainerEl.style.display = 'none';
    }
  } catch (e) {
    console.error('Generate tasks failed:', e);
    promptErrorEl.style.color = '#ef4444';
    promptErrorEl.textContent = 'Lỗi sinh đề: ' + (e && e.message ? e.message : 'Failed to fetch');
    prompt1El.textContent = 'Lỗi khi lấy đề Task 1';
    prompt2El.textContent = 'Lỗi khi lấy đề Task 2';
  } finally {
    [prompt1El, prompt2El].forEach(el => el.classList.remove('loading'));
    btnGenerate.disabled = false;
  }
}

async function submitBatch() {
  const task1_prompt = (prompt1El.textContent || '').trim();
  const task2_prompt = (prompt2El.textContent || '').trim();
  const task1_essay = (essay1El.value || '').trim();
  const task2_essay = (essay2El.value || '').trim();

  if (!task1_prompt || task1_prompt.startsWith('Lỗi') || task1_prompt.startsWith('Không') || task1_prompt.startsWith('Chưa')) {
    alert('Task 1 chưa sẵn sàng. Hãy sinh đề trước.');
    return;
  }
  if (!task2_prompt || task2_prompt.startsWith('Lỗi') || task2_prompt.startsWith('Không') || task2_prompt.startsWith('Chưa')) {
    alert('Task 2 chưa sẵn sàng. Hãy sinh đề trước.');
    return;
  }
  if (!task1_essay || !task2_essay) {
    alert('Hãy nhập cả bài Task 1 và Task 2 trước khi nộp.');
    return;
  }

  btnSubmitBatch.disabled = true;
  result1El.classList.add('loading');
  result2El.classList.add('loading');
  result1El.innerHTML = '<p class="small">Đang chấm Task 1...</p>';
  result2El.innerHTML = '<p class="small">Đang chấm Task 2...</p>';

  try {
    const url = `${apiBase}/api/grade_batch`;
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task1_prompt, task1_essay, task2_prompt, task2_essay })
    });
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    const data = await res.json();
    renderOneResult(result1El, data.task1);
    renderOneResult(result2El, data.task2);
  } catch (e) {
    console.error('Grade batch failed:', e);
    const msg = escapeHtml(e && e.message ? e.message : 'Failed to fetch');
    result1El.innerHTML = `<p class="small" style="color:#ef4444">Lỗi: ${msg}</p>`;
    result2El.innerHTML = `<p class="small" style="color:#ef4444">Lỗi: ${msg}</p>`;
  } finally {
    result1El.classList.remove('loading');
    result2El.classList.remove('loading');
    btnSubmitBatch.disabled = false;
  }
}

btnHealth?.addEventListener('click', checkHealth);
btnGenerate.addEventListener('click', generateTasks);
btnSubmitBatch.addEventListener('click', submitBatch);

// Toggle UI giữa auto vs manual
function updatePromptMode() {
  const manual = !!modeManualEl?.checked;
  if (manual) {
    manualPromptsWrapEl.style.display = '';
  } else {
    manualPromptsWrapEl.style.display = 'none';
  }
}
modeAutoEl?.addEventListener('change', updatePromptMode);
modeManualEl?.addEventListener('change', updatePromptMode);
updatePromptMode();
