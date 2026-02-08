document.addEventListener('DOMContentLoaded', function () {
  // Smooth scroll for in-page anchors
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
      const href = this.getAttribute('href');
      if (!href || href === '#') {
        return;
      }
      const target = document.querySelector(href);
      if (!target) {
        return;
      }
      e.preventDefault();
      target.scrollIntoView({
        behavior: 'smooth',
        block: 'start'
      });
    });
  });

  // Navbar scroll effect
  window.addEventListener('scroll', function () {
    const header = document.querySelector('header');
    if (!header) {
      return;
    }
    if (window.scrollY > 100) {
      header.style.background = 'rgba(255, 255, 255, 0.98)';
    } else {
      header.style.background = 'rgba(255, 255, 255, 0.95)';
    }
  });

  // Collapsible docs sidebar
  const sidebar = document.querySelector('.docs-sidebar');
  if (!sidebar) {
    return;
  }

  sidebar.querySelectorAll('li').forEach(li => {
    const childList = li.querySelector(':scope > ul');
    const link = li.querySelector(':scope > a');
    if (!childList || !link) {
      return;
    }

    li.classList.add('has-children');

    const toggle = document.createElement('button');
    toggle.type = 'button';
    toggle.className = 'toc-toggle';
    toggle.textContent = '−';

    toggle.addEventListener('click', function (e) {
      e.stopPropagation();
      li.classList.toggle('collapsed');
      if (li.classList.contains('collapsed')) {
        toggle.textContent = '+';
      } else {
        toggle.textContent = '−';
      }
    });

    li.insertBefore(toggle, link);
  });
});
