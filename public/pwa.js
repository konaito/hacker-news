(() => {
  if ('serviceWorker' in navigator) window.addEventListener('load', () => navigator.serviceWorker.register('/sw.js', { updateViaCache: 'none' }).catch(() => {}));
  const standalone = matchMedia('(display-mode: standalone)').matches || navigator.standalone;
  const panel = document.createElement('aside');
  panel.className = 'app-install';
  panel.innerHTML = '<button type="button" class="outline-button" id="install-app">アプリとして使う</button><p id="install-help" hidden>iPhone：Safariの共有メニューから「ホーム画面に追加」。Android：ブラウザのメニューから「アプリをインストール」。</p>';
  if (!standalone) (document.querySelector('.sidebar') || document.querySelector('main')).append(panel);
  let prompt;
  window.addEventListener('beforeinstallprompt', event => { event.preventDefault(); prompt = event; });
  panel.querySelector('button').addEventListener('click', async () => {
    if (prompt) { await prompt.prompt(); await prompt.userChoice; prompt = null; }
    else panel.querySelector('p').hidden = !panel.querySelector('p').hidden;
  });
  window.addEventListener('appinstalled', () => panel.remove());
  const status = document.createElement('p'); status.className = 'offline-status'; status.setAttribute('role','status');
  status.textContent = 'オフライン：保存済みの情報を表示しています。最新情報・出典の確認には接続が必要です。';
  document.body.prepend(status);
  const update = () => { status.hidden = navigator.onLine; };
  addEventListener('online', update); addEventListener('offline', update); update();
})();
