(function () {
  function ready(fn) {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', fn);
      return;
    }
    fn();
  }

  ready(function () {
    document.querySelectorAll('[data-master-list]').forEach(function (table) {
      const wrapper = table.closest('[data-master-list-wrap]') || table.parentElement;
      if (!wrapper) return;

      const tbody = table.querySelector('tbody');
      if (!tbody) return;

      const allRows = Array.from(tbody.querySelectorAll('tr')).filter(function (tr) {
        return tr.querySelectorAll('td').length > 0;
      });

      if (!allRows.length) return;

      const searchInput = wrapper.querySelector('[data-master-search]');
      const filterInputs = Array.from(wrapper.querySelectorAll('[data-master-filter]'));
      const paginationBox = wrapper.querySelector('[data-master-pagination]');
      const pageSize = Number(table.getAttribute('data-page-size') || 10);
      let searchTimer = null;

      let currentPage = 1;

      function rowMatches(tr) {
        const text = tr.innerText.toLowerCase();
        const query = (searchInput ? searchInput.value : '').toLowerCase().trim();
        if (query && !text.includes(query)) return false;

        for (const filterEl of filterInputs) {
          const val = (filterEl.value || '').toLowerCase().trim();
          if (!val) continue;
          const colIndex = Number(filterEl.getAttribute('data-master-filter'));
          const cell = tr.children[colIndex];
          const cellText = cell ? cell.innerText.toLowerCase() : '';
          if (!cellText.includes(val)) return false;
        }

        return true;
      }

      function visibleRows() {
        return allRows.filter(rowMatches);
      }

      function renderPagination(totalPages) {
        if (!paginationBox) return;
        if (totalPages <= 1) {
          paginationBox.innerHTML = '';
          return;
        }

        let html = '';
        for (let i = 1; i <= totalPages; i += 1) {
          html += `<button type="button" class="btn ${i === currentPage ? 'unified-btn-primary' : 'unified-btn-outline'}" data-page="${i}">${i}</button>`;
        }
        paginationBox.innerHTML = html;

        paginationBox.querySelectorAll('button[data-page]').forEach(function (btn) {
          btn.addEventListener('click', function () {
            currentPage = Number(btn.getAttribute('data-page'));
            render();
          });
        });
      }

      function render() {
        const filtered = visibleRows();
        const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
        if (currentPage > totalPages) currentPage = 1;

        const start = (currentPage - 1) * pageSize;
        const end = start + pageSize;

        allRows.forEach(function (tr) {
          tr.style.display = 'none';
        });

        if (filtered.length) {
          filtered.slice(start, end).forEach(function (tr) {
            tr.style.display = '';
          });
        }

        renderPagination(totalPages);
      }

      if (searchInput) {
        searchInput.addEventListener('input', function () {
          if (searchTimer) window.clearTimeout(searchTimer);
          searchTimer = window.setTimeout(function () {
            currentPage = 1;
            render();
          }, 120);
        });
      }

      filterInputs.forEach(function (filterEl) {
        filterEl.addEventListener('change', function () {
          currentPage = 1;
          render();
        });
        filterEl.addEventListener('input', function () {
          currentPage = 1;
          render();
        });
      });

      render();
    });
  });
})();
