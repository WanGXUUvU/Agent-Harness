/**
 * 将带 markdown 语法的文本渲染成 HTML 字符串。
 * 在 MessageList 和 ChildAgentPanel 中共用。
 */
export function formatContent(text: string | null): string {
  if (!text) return '';
  text = text.replace('[COMPACT_SUMMARY]\nThe following is a compressed summary of the middle part of the conversation. It is not a verbatim transcript. Preserve task goals, constraints, important tool results, and unfinished work.\n\n', '');

  let html = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

  html = html.replace(/```([\w-]*)\n([\s\S]*?)```/g, (_match, lang, code) => {
    const langLabel = lang ? `<div class="code-lang mono-label">${lang}</div>` : '';
    return `<div class="code-block">${langLabel}<pre><code>${code}</code></pre></div>`;
  });

  html = html.replace(/((?:^\|.+\|$\n?){2,})/gm, (tableBlock) => {
    const rows = tableBlock.trim().split('\n').filter(r => r.trim());
    if (rows.length < 2) return tableBlock;
    const sepLine = rows[1];
    if (!/^\|[\s-:|]+\|$/.test(sepLine)) return tableBlock;

    const parseRow = (row: string) => row.split('|').slice(1, -1).map(cell => cell.trim());
    const headerCells = parseRow(rows[0]);
    const bodyRows = rows.slice(2);

    let tableHtml = '<div class="md-table-wrapper"><table class="md-table">';
    tableHtml += '<thead><tr>' + headerCells.map(c => `<th>${c}</th>`).join('') + '</tr></thead>';
    tableHtml += '<tbody>';
    for (const row of bodyRows) {
      const cells = parseRow(row);
      tableHtml += '<tr>' + cells.map(c => `<td>${c}</td>`).join('') + '</tr>';
    }
    tableHtml += '</tbody></table></div>';
    return tableHtml;
  });

  html = html.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');
  html = html.replace(/^---+$/gm, '<hr style="border:none;border-top:1px solid var(--border-dim);margin:12px 0;">');
  html = html.replace(/^### (.+)$/gm, '<div style="font-size:13px;font-weight:600;color:var(--text-primary);margin:10px 0 4px;">$1</div>');
  html = html.replace(/^## (.+)$/gm, '<div style="font-size:14px;font-weight:600;color:var(--text-primary);margin:12px 0 4px;">$1</div>');
  html = html.replace(/^# (.+)$/gm, '<div style="font-size:15px;font-weight:700;color:var(--text-primary);margin:14px 0 4px;">$1</div>');
  html = html.replace(/\*\*([^\*]+)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/(?<!\*)\*(?!\*)([^\*]+)(?<!\*)\*(?!\*)/g, '<em>$1</em>');

  html = html.replace(/((?:^- .+$\n?)+)/gm, (block) => {
    const items = block.trim().split('\n').filter(l => l.trim().startsWith('- ')).map(l => `<li>${l.replace(/^- /, '')}</li>`);
    return `<ul class="md-list">${items.join('')}</ul>`;
  });

  html = html.replace(/((?:^\d+\. .+$\n?)+)/gm, (block) => {
    const items = block.trim().split('\n').filter(l => /^\d+\. /.test(l.trim())).map(l => `<li>${l.replace(/^\d+\. /, '')}</li>`);
    return `<ol class="md-list">${items.join('')}</ol>`;
  });

  return html;
}
