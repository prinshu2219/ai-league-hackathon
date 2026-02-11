const DEFAULT_BASE_URL = 'http://localhost:8501';

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: 'verify-claim',
    title: 'Verify claim with AI Claim Verifier',
    contexts: ['selection']
  });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId !== 'verify-claim') return;
  const selectedText = (info.selectionText || '').trim();
  openClaimVerifierWithClaim(selectedText);
});

function openClaimVerifierWithClaim(claim) {
  chrome.storage.local.get({ baseUrl: DEFAULT_BASE_URL }, (items) => {
    const base = items.baseUrl.replace(/\/$/, '');
    const url = claim
      ? `${base}?claim=${encodeURIComponent(claim)}`
      : base;
    chrome.tabs.create({ url });
  });
}
