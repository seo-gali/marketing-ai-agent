(() => {
  const repository = 'https://github.com/seo-gali/marketing-ai-agent/blob/main/';
  const source = 'https://raw.githubusercontent.com/seo-gali/marketing-ai-agent/main/';
  const tabs = [...document.querySelectorAll('[role="tab"]')];
  const dialog = document.querySelector('#document-dialog');
  const content = document.querySelector('#document-content');
  const title = document.querySelector('#document-title');
  let request;
  let trigger;

  function selectTab(tab) {
    tabs.forEach(item => {
      const selected = item === tab;
      item.setAttribute('aria-selected', String(selected));
      item.tabIndex = selected ? 0 : -1;
      document.getElementById(item.getAttribute('aria-controls')).hidden = !selected;
    });
  }

  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => selectTab(tab));
    tab.addEventListener('keydown', event => {
      let next;
      if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
      if (event.key === 'ArrowLeft') next = (index + tabs.length - 1) % tabs.length;
      if (event.key === 'Home') next = 0;
      if (event.key === 'End') next = tabs.length - 1;
      if (next === undefined) return;
      event.preventDefault();
      selectTab(tabs[next]);
      tabs[next].focus();
    });
  });

  function node(tag, text) {
    const element = document.createElement(tag);
    if (text !== undefined) element.textContent = text;
    return element;
  }

  function inline(parent, text, path) {
    const tokens = /(`[^`\n]+`|\*\*[^*\n]+\*\*|\[[^\]\n]+\]\([^\s)]+\))/g;
    let position = 0;
    for (const match of text.matchAll(tokens)) {
      parent.append(document.createTextNode(text.slice(position, match.index)));
      const value = match[0];
      if (value.startsWith('`')) parent.append(node('code', value.slice(1, -1)));
      else if (value.startsWith('**')) parent.append(node('strong', value.slice(2, -2)));
      else {
        const [, label, href] = value.match(/^\[([^\]]+)\]\((.+)\)$/);
        const link = node('a', label);
        try {
          const url = new URL(href, repository + path);
          if (!['https:', 'http:'].includes(url.protocol) || url.username || url.password) throw new Error();
          link.href = url.href;
          link.target = '_blank';
          link.rel = 'noopener noreferrer';
          parent.append(link);
        } catch { parent.append(document.createTextNode(label)); }
      }
      position = match.index + value.length;
    }
    parent.append(document.createTextNode(text.slice(position)));
    return parent;
  }

  // 저장소 문서의 제목·표·목록·코드·인용·링크 지원, HTML 직접 실행 제외
  function markdown(text, path) {
    const fragment = document.createDocumentFragment();
    const lines = text.replace(/\r\n?/g, '\n').split('\n');
    const divider = line => /^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(line);
    const cells = line => line.trim().replace(/^\||\|$/g, '').split('|').map(cell => cell.trim());
    const special = line => /^(#{1,6}\s|```|>\s?|\s*[-*+]\s|\s*\d+[.)]\s|\s*([-*_])(?:\s*\2){2,}\s*$)/.test(line);
    let index = 0;
    while (index < lines.length) {
      const line = lines[index];
      if (!line.trim()) { index++; continue; }
      if (line.startsWith('```')) {
        const code = [];
        index++;
        while (index < lines.length && !lines[index].startsWith('```')) code.push(lines[index++]);
        const pre = node('pre');
        pre.append(node('code', code.join('\n')));
        fragment.append(pre);
        index++;
      } else if (/^#{1,6}\s/.test(line)) {
        const [, markers, text] = line.match(/^(#{1,6})\s+(.*)$/);
        fragment.append(inline(node(`h${Math.min(markers.length + 2, 6)}`), text, path));
        index++;
      } else if (index + 1 < lines.length && line.includes('|') && divider(lines[index + 1])) {
        const table = node('table');
        const head = node('thead');
        const row = node('tr');
        cells(line).forEach(cell => {
          const th = inline(node('th'), cell, path);
          th.scope = 'col';
          row.append(th);
        });
        head.append(row);
        table.append(head);
        const body = node('tbody');
        index += 2;
        while (index < lines.length && lines[index].trim() && lines[index].includes('|')) {
          const row = node('tr');
          cells(lines[index++]).forEach(cell => row.append(inline(node('td'), cell, path)));
          body.append(row);
        }
        table.append(body);
        fragment.append(table);
      } else if (/^\s*([-*_])(?:\s*\1){2,}\s*$/.test(line)) {
        fragment.append(node('hr'));
        index++;
      } else if (/^>/.test(line)) {
        const quote = [];
        while (index < lines.length && /^>/.test(lines[index])) quote.push(lines[index++].replace(/^>\s?/, ''));
        fragment.append(inline(node('blockquote'), quote.join(' '), path));
      } else if (/^\s*(?:[-*+]|\d+[.)])\s/.test(line)) {
        const ordered = /^\s*\d+[.)]/.test(line);
        const list = node(ordered ? 'ol' : 'ul');
        const item = ordered ? /^\s*\d+[.)]\s+(.*)$/ : /^\s*[-*+]\s+(.*)$/;
        if (ordered) list.start = Number(line.match(/^\s*(\d+)/)[1]);
        while (index < lines.length && item.test(lines[index])) {
          list.append(inline(node('li'), lines[index++].match(item)[1], path));
        }
        fragment.append(list);
      } else {
        const paragraph = [line];
        index++;
        while (index < lines.length && lines[index].trim() && !special(lines[index]) && !(index + 1 < lines.length && divider(lines[index + 1]))) paragraph.push(lines[index++]);
        fragment.append(inline(node('p'), paragraph.join(' '), path));
      }
    }
    return fragment;
  }

  async function openDocument(button) {
    request?.abort();
    trigger = button;
    const path = button.dataset.doc;
    title.textContent = button.dataset.title || button.textContent.trim();
    document.querySelector('#document-source').href = repository + path;
    content.replaceChildren(node('p', '문서를 불러오는 중…'));
    content.setAttribute('aria-busy', 'true');
    if (!dialog.open) dialog.showModal();
    document.body.classList.add('modal-open');
    document.querySelector('#document-close').focus();
    const controller = new AbortController();
    request = controller;
    const timeout = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch(source + path, { signal: controller.signal });
      if (!response.ok) throw new Error();
      const text = await response.text();
      if (text.length > 250000) throw new Error();
      if (request !== controller || !dialog.open) return;
      content.replaceChildren(markdown(text, path));
      content.scrollTop = 0;
    } catch {
      if (request !== controller || !dialog.open) return;
      const message = node('p', '문서를 불러오지 못했습니다. 인터넷 연결을 확인한 뒤 다시 시도하세요.');
      message.setAttribute('role', 'alert');
      const retry = node('button', '다시 시도');
      retry.className = 'button';
      retry.addEventListener('click', () => openDocument(button));
      content.replaceChildren(message, retry);
    } finally {
      clearTimeout(timeout);
      if (request === controller) content.setAttribute('aria-busy', 'false');
    }
  }

  document.querySelectorAll('[data-doc]').forEach(button => button.addEventListener('click', () => openDocument(button)));
  document.querySelector('#document-close').addEventListener('click', () => dialog.close());
  dialog.addEventListener('keydown', event => {
    if (event.key !== 'Tab') return;
    const controls = [...dialog.querySelectorAll('button:not([disabled]), a[href], [tabindex="0"]')];
    const first = controls[0];
    const last = controls.at(-1);
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  });
  dialog.addEventListener('click', event => {
    const box = dialog.getBoundingClientRect();
    if (event.target === dialog && (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom)) dialog.close();
  });
  dialog.addEventListener('close', () => {
    request?.abort();
    document.body.classList.remove('modal-open');
    trigger?.focus();
  });
})();
