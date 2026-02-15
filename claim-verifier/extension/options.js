const DEFAULT_BASE_URL = 'http://65.0.149.214:8501';

const baseUrlInput = document.getElementById('baseUrl');
const saveBtn = document.getElementById('saveBtn');
const messageEl = document.getElementById('message');

chrome.storage.local.get({ baseUrl: DEFAULT_BASE_URL }, (items) => {
  baseUrlInput.value = items.baseUrl;
});

saveBtn.addEventListener('click', () => {
  const url = baseUrlInput.value.trim() || DEFAULT_BASE_URL;
  chrome.storage.local.set({ baseUrl: url }, () => {
    messageEl.textContent = 'Saved.';
    messageEl.style.display = 'block';
    setTimeout(() => {
      messageEl.style.display = 'none';
    }, 2000);
  });
});
