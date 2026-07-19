// PWA feature 1: register the offline-caching service worker.
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/service-worker.js').catch((err) => {
      console.warn('Service worker registration failed:', err);
    });
  });
}

// PWA feature 2: custom "Install App" prompt, using the browser's
// beforeinstallprompt event so the app can be added to the home screen.
let deferredInstallPrompt = null;

window.addEventListener('beforeinstallprompt', (event) => {
  event.preventDefault();
  deferredInstallPrompt = event;
  const installButton = document.getElementById('pwa-install-button');
  if (installButton) {
    installButton.classList.remove('hidden');
  }
});

document.addEventListener('click', (event) => {
  if (event.target && event.target.id === 'pwa-install-button') {
    if (!deferredInstallPrompt) return;
    deferredInstallPrompt.prompt();
    deferredInstallPrompt.userChoice.finally(() => {
      deferredInstallPrompt = null;
      event.target.classList.add('hidden');
    });
  }
});

window.addEventListener('appinstalled', () => {
  const installButton = document.getElementById('pwa-install-button');
  if (installButton) {
    installButton.classList.add('hidden');
  }
});
