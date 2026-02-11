const DEFAULT_BASE_URL = 'http://localhost:8501';

const claimInput = document.getElementById('claimInput');
const verifyBtn = document.getElementById('verifyBtn');
const optionsLink = document.getElementById('optionsLink');

function openClaimVerifier(claim) {
  chrome.storage.local.get({ baseUrl: DEFAULT_BASE_URL }, (items) => {
    const base = items.baseUrl.replace(/\/$/, '');
    const url = claim.trim()
      ? `${base}?claim=${encodeURIComponent(claim.trim())}`
      : base;
    chrome.tabs.create({ url });
    window.close();
  });
}

verifyBtn.addEventListener('click', () => {
  openClaimVerifier(claimInput.value);
});

optionsLink.addEventListener('click', (e) => {
  e.preventDefault();
  chrome.runtime.openOptionsPage();
});

// Enable/disable button based on input (optional: allow empty to just open app)
claimInput.addEventListener('input', () => {
  verifyBtn.disabled = false;
});
