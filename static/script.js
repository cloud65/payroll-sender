// Элементы
const form = document.getElementById('uploadForm');
const reportInput = document.getElementById('report');
const employeesInput = document.getElementById('employees');
const htmlPreview = document.getElementById('htmlPreview');
const filesList = document.getElementById('filesList');
const sendBtn = document.getElementById('sendBtn');
const progressWrap = document.getElementById('progressWrap');
const progressBar = document.getElementById('progressBar');
const employeesContainer = document.getElementById('employeesContainer');
const result = document.getElementById('sendErrMsg'); // предполагаем, что это для ошибок отправки

const months = [
  "Январь","Февраль","Март","Апрель","Май","Июнь",
  "Июль","Август","Сентябрь","Октябрь","Ноябрь","Декабрь"
];

// --- Утилиты ---
const escapeHTML = s =>
  String(s).replace(/[&<>\"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":"&#39;"})[c]);

const formatFileSize = size => `${size} байт`;

const formatPeriod = period => {
  if (!period) return "—";
  const d = new Date(period);
  return isNaN(d) ? "—" : `${months[d.getMonth()]} ${d.getFullYear()}`;
};

const validateFile = (file, regex, msg) => {
  if (!file) return false;
  if (!regex.test(file.name)) {
    alert(msg);
    return false;
  }
  return true;
};

// --- Файлы ---
const renderSelectedFiles = () => {
  const files = [
    { file: reportInput.files[0], label: 'Расчетные листки', ext: /\.html?$/i },
    { file: employeesInput.files[0], label: 'Получатели', ext: /\.txt$/i }
  ];

  const lines = files
    .filter(f => f.file)
    .map(f => `<strong>${f.label}</strong>: ${escapeHTML(f.file.name)} — ${formatFileSize(f.file.size)}`);

  filesList.innerHTML = lines.length ? lines.map(l => `<div>${l}</div>`).join('') : '<span class="muted">Файлы не выбраны</span>';
  document.getElementById('sendSuccess').textContent = "";
};

reportInput.addEventListener('change', () => {
  if (!validateFile(reportInput.files[0], /\.html?$/i, 'Пожалуйста, выберите файл с расширением .html для report.')) {
    reportInput.value = '';
  }
  renderSelectedFiles();
});

employeesInput.addEventListener('change', () => {
  if (!validateFile(employeesInput.files[0], /\.txt$/i, 'Пожалуйста, выберите файл с расширением .txt для employees.')) {
    employeesInput.value = '';
  }
  renderSelectedFiles();
});

// --- Список сотрудников ---
const renderEmployeeList = (data, container, iframe) => {
  if (!Array.isArray(data)) return;

  Object.assign(container.style, {
    overflowY: "auto",
    maxHeight: "100%",
    border: "1px solid #ddd",
    borderRadius: "8px",
    padding: "10px",
    background: "#fafafa"
  });

  container.innerHTML = "";

  data.forEach(item => {
    const row = document.createElement("div");
    row.className = "employee-row";

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.style.marginTop = "3px";
    checkbox.addEventListener("click", e => e.stopPropagation());
    checkbox.disabled = !item.email;
    checkbox.dataset.guid = item.id;

    const infoBox = document.createElement("div");
    infoBox.innerHTML = `
      <div><strong>${escapeHTML(item.name || "—")}</strong></div>
      <div>${escapeHTML(item.email || "—")}</div>
      <div style="color:#666; font-size:13px">${escapeHTML(formatPeriod(item.period))}</div>
    `;

    row.addEventListener("click", async () => {
      container.querySelectorAll('.employee-row').forEach(r => r.dataset.selected = '0');
      row.dataset.selected = '1';

      const doc = iframe.contentDocument || iframe.contentWindow.document;
      doc.open();
      doc.write("<p>Загрузка...</p>");
      doc.close();

      try {
        const response = await fetch(`/api/v1/report/${item.id}`);
        doc.open();
        doc.write(response.ok ? await response.text() : `<b>Ошибка ${response.status}</b>`);
        doc.close();
      } catch {
        doc.open();
        doc.write("<b>Ошибка сети</b>");
        doc.close();
      }
    });

    row.append(checkbox, infoBox);
    container.appendChild(row);
  });
};

// --- Отправка формы ---
const handleFormSubmit = async ev => {
  ev.preventDefault();

  const reportFile = reportInput.files[0];
  const employeesFile = employeesInput.files[0];

  if (!validateFile(reportFile, /\.html?$/i, 'Выберите report.html')) return;
  if (!validateFile(employeesFile, /\.txt$/i, 'Выберите employees.txt')) return;

  const fd = new FormData();
  fd.append('report', reportFile);
  fd.append('employees', employeesFile);

  sendBtn.disabled = true;
  employeesContainer.textContent = 'Загрузка...';
  progressWrap.style.display = 'block';
  progressBar.style.width = '0%';

  try {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/v1/upload');

    xhr.onreadystatechange = () => {
      if (xhr.readyState === 4) {
        sendBtn.disabled = false;
        progressBar.style.width = '100%';
        let data;
        try {
          data = xhr.getResponseHeader('content-type')?.includes('application/json') ? JSON.parse(xhr.responseText) : xhr.responseText;
        } catch {
          data = xhr.responseText;
        }

        if (xhr.status >= 200 && xhr.status < 300) {
          if (Array.isArray(data)) {
            htmlPreview.dataset.count = data.length;
            document.getElementById('employeesContent').dataset.count = data.length;
            document.getElementById('div-upload').dataset.count = data.length;
            reportInput.value = employeesInput.value = '';
            filesList.innerHTML = '';
            renderEmployeeList(data, employeesContainer, document.getElementById("htmlFrame"));
          } else {
            employeesContainer.textContent = data;
          }
        } else {
          employeesContainer.textContent = `Ошибка ${xhr.status}: ${xhr.statusText}\n${xhr.responseText || ''}`;
        }

        setTimeout(() => {
          progressWrap.style.display = 'none';
          progressBar.style.width = '0%';
        }, 1200);
      }
    };

    xhr.upload.onprogress = e => {
      if (e.lengthComputable) progressBar.style.width = `${Math.round((e.loaded / e.total) * 100)}%`;
    };

    xhr.onerror = () => {
      sendBtn.disabled = false;
      progressWrap.style.display = 'none';
      result.textContent = 'Сетевая ошибка при отправке.';
    };

    xhr.send(fd);

  } catch (err) {
    sendBtn.disabled = false;
    progressWrap.style.display = 'none';
    result.textContent = 'Ошибка: ' + (err.message || String(err));
  }
};

form.addEventListener('submit', handleFormSubmit);

// --- Работа с чекбоксами ---
const toggleCheckboxes = (action) => {
  employeesContainer.querySelectorAll('.employee-row input[type="checkbox"]').forEach(cb => {
    if (action === 'check') cb.checked = !cb.disabled;
    if (action === 'uncheck') cb.checked = false;
    if (action === 'invert' && !cb.disabled) cb.checked = !cb.checked;
  });
};

document.getElementById('checkAll').addEventListener('click', () => toggleCheckboxes('check'));
document.getElementById('uncheckAll').addEventListener('click', () => toggleCheckboxes('uncheck'));
document.getElementById('invertCheck').addEventListener('click', () => toggleCheckboxes('invert'));

// --- Перезагрузка данных ---
const reloadData = async () => {
  try {
    const response = await fetch('/api/v1/reload', { credentials: 'same-origin' });
    if (!response.ok) throw new Error(`Ошибка загрузки данных: ${response.status}`);
    const data = await response.json();
    htmlPreview.dataset.count = data.length;
    document.getElementById('employeesContent').dataset.count = data.length;
    document.getElementById('div-upload').dataset.count = data.length;
    renderEmployeeList(data, employeesContainer, document.getElementById("htmlFrame"));
  } catch (err) {
    console.error("Ошибка при reload:", err);
  }
};

// --- Отправка email ---
document.getElementById('sendEmailBtn').addEventListener('click', async () => {
  const selectedIds = Array.from(employeesContainer.querySelectorAll('.employee-row input[type="checkbox"]:checked'))
                           .map(cb => cb.dataset.guid);
  result.textContent = "";
  if (!selectedIds.length) return result.textContent = "Нет отмеченных данных для отправки";

  const overlay = document.getElementById('overlay');
  overlay.style.visibility = 'visible';

  try {
    const response = await fetch('/api/v1/send', {
      method: 'POST',
      credentials: 'same-origin',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(selectedIds)
    });

    overlay.style.visibility = 'hidden';
    if (!response.ok) return alert(`Ошибка отправки данных: ${response.status}`);

    const json = await response.json();
    if (json.status) {
      [htmlPreview, document.getElementById('employeesContent'), document.getElementById('div-upload')].forEach(el => el.dataset.count = 0);
      document.getElementById('sendSuccess').textContent = "✅ Отправка завершена";
    } else {
      alert(`Ошибка отправки данных: ${json.error}`);
    }
  } catch (err) {
    overlay.style.visibility = 'hidden';
    alert(`Ошибка отправки: ${err.message || err}`);
  }
});

// --- Инициализация ---
window.addEventListener('DOMContentLoaded', () => {
  reloadData();
  renderSelectedFiles();
});
