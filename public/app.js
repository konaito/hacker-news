(() => {
  const rows = [...document.querySelectorAll('#news-rows tr')];
  const body = document.querySelector('#news-rows');
  const tabs = [...document.querySelectorAll('.filter-tab')];
  const search = document.querySelector('#search');
  const month = document.querySelector('#month-filter');
  const category = document.querySelector('#category-filter');
  const region = document.querySelector('#region-filter');
  const sort = document.querySelector('#sort');
  const more = document.querySelector('#load-more');
  const dialog = document.querySelector('#detail-dialog');
  let filter = 'all', limit = 10;
  function render() {
    const query = search.value.trim().normalize('NFKC').toLocaleLowerCase();
    const ordered = [...rows].sort((a,b) => sort.value === 'asc' ? a.dataset.date.localeCompare(b.dataset.date) : b.dataset.date.localeCompare(a.dataset.date));
    let count = 0;
    ordered.forEach(row => {
      const d = row.dataset;
      const match = (filter === 'all' || d.kind === filter || d.region === filter)
        && (month.value === 'all' || d.date.startsWith(month.value))
        && (category.value === 'all' || d.category === category.value)
        && (region.value === 'all' || d.region === region.value)
        && (!query || d.search.normalize('NFKC').toLocaleLowerCase().includes(query));
      row.hidden = !match || count >= limit;
      if (match) count++;
      body.append(row);
    });
    tabs.forEach(tab => { const active = tab.dataset.filter === filter; tab.classList.toggle('active',active); tab.setAttribute('aria-pressed',String(active)); });
    document.querySelector('#result-count').textContent = `${count}件中${Math.min(count,limit)}件を表示`;
    document.querySelector('#empty-state').hidden = count !== 0;
    more.hidden = count <= limit;
    const state = document.querySelector('#search-state');
    state.hidden = !query;
    state.querySelector('span').textContent = `「${search.value.trim()}」の検索結果`;
  }
  tabs.forEach(tab => tab.addEventListener('click', () => { filter=tab.dataset.filter; limit=10; render(); }));
  [month,category,region,sort].forEach(input => input.addEventListener('change', () => { limit=10; render(); }));
  search.addEventListener('input', () => { limit=10; render(); });
  document.querySelector('.search-form').addEventListener('submit',event => { event.preventDefault(); document.querySelector('#incidents').scrollIntoView({behavior:'smooth'}); render(); });
  document.querySelector('#clear-search').addEventListener('click', () => { search.value=''; limit=10; render(); search.focus(); });
  document.querySelector('#reset-filters').addEventListener('click', () => { search.value=''; filter='all'; month.value=category.value=region.value='all'; sort.value='desc'; limit=10; render(); });
  more.addEventListener('click', () => { limit+=10; render(); });
  document.querySelectorAll('[data-month]').forEach(button => button.addEventListener('click', () => { month.value=button.dataset.month; filter='all'; category.value=region.value='all'; search.value=''; limit=10; render(); document.querySelector('#incidents').scrollIntoView({behavior:'smooth'}); }));
  function show(template) {
    if (!template) return;
    const content=document.querySelector('#dialog-content');
    content.replaceChildren(template.content.cloneNode(true));
    const heading=content.querySelector('h2,h3');
    if (heading) heading.id='dialog-heading';
    dialog.showModal(); dialog.scrollTop=0;
  }
  document.querySelectorAll('[data-detail]').forEach(button => button.addEventListener('click', event => { if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return; event.preventDefault(); show(document.getElementById(`detail-${button.dataset.detail}`)); }));
  document.querySelectorAll('[data-about]').forEach(button => button.addEventListener('click', () => show(document.querySelector('#about-content'))));
  document.querySelector('.dialog-close').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => { if(event.target!==dialog)return; const r=dialog.getBoundingClientRect(); if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)dialog.close(); });
  render();
})();
